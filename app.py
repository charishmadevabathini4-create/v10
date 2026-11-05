import os
import json
import re
import sqlite3
import smtplib
import threading
from email.message import EmailMessage
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template
from google import genai
from google.genai import types

# Import PyTorch SentenceTransformer matcher model
from psychological_model import analyze_gemini_output

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SECONDARY_DB_PATH = os.path.join(BASE_DIR, "Secondary_data.db")
THIRD_DB_PATH = os.path.join(BASE_DIR, "Third_data.db")

# SMTP Credentials
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465  # SSL Port
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "your_email@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "your_16_char_app_password")

# EMBEDDED INTAKE SYSTEM PROMPT (Layer 1 - Extraction)
EMBEDDED_INTAKE_PROMPT = """
You are a psychological text-structure extraction system.

Your task is to analyze the user's written description and extract observable psychological indicators, symptoms, behaviors, emotions, triggers, events, cognitive patterns, and functional effects.

IMPORTANT RULES:
1. Do NOT diagnose the user.
2. Do NOT determine a psychological disorder.
3. Do NOT invent information that is not present.
4. Only extract information supported by the user's text.
5. If a field is not mentioned, return an empty array [].
6. Keep extracted items short and descriptive.
7. Preserve the user's meaning.
8. Separate symptoms, behaviors, emotions, triggers, events, and cognitive patterns.
9. Identify anxiety-related indicators only when supported by the text.
10. Identify trauma-related indicators only when supported by the text.
11. Identify sleep-related indicators only when supported by the text.
12. Identify social/relationship effects only when supported by the text.
13. Identify functional impact such as study, work, daily activities, or relationships.
14. Do not assign a disorder or diagnosis.
15. Do not calculate a probability.
16. Do not provide treatment recommendations.
17. Return ONLY valid JSON.
18. Do not use Markdown.
19. Do not add explanations outside the JSON.

OUTPUT FORMAT:
{
  "age": null,
  "duration": "",
  "frequency": "",
  "intensity": null,
  "onset": "",
  "triggers": [],
  "symptoms": [],
  "behaviors": [],
  "emotions": [],
  "trauma_indicators": [],
  "anxiety_indicators": [],
  "sleep_indicators": [],
  "social_indicators": [],
  "cognitive_patterns": [],
  "functional_impact": [],
  "events": []
}
"""

def init_secondary_db():
    conn = sqlite3.connect(SECONDARY_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            user_input TEXT,
            pytorch_model_output TEXT,
            gemini_input TEXT,
            gemini_output TEXT
        )
    """)
    conn.commit()
    conn.close()

init_secondary_db()

# Initialize Gemini Client
api_key = os.getenv("GEMNI_API") or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None


def clean_json_response(raw_text: str) -> str:
    cleaned = re.sub(r'```(?:json)?\s*', '', raw_text)
    cleaned = re.sub(r'\s*```', '', cleaned)
    return cleaned.strip()


def send_email_in_background(doctor_email, doctor_name, user_input, model_output, gemini_guidance, report_id, appointment_time):
    """
    Background worker thread function to send referral email without blocking HTTP response.
    Formats pattern recognition outputs into clean HTML tables instead of raw JSON.
    """
    msg = EmailMessage()
    msg['Subject'] = f"V16 Clinical Referral Request — Intake Case #{report_id}"
    msg['From'] = SMTP_EMAIL
    msg['To'] = doctor_email

    accept_link = f"http://127.0.0.1:5000/api/doctor/accept/{report_id}"

    # Parse JSON string into list for HTML table generation
    try:
        matches_list = json.loads(model_output) if isinstance(model_output, str) else model_output
    except Exception:
        matches_list = []

    # Build HTML Table Rows
    table_rows = ""
    if isinstance(matches_list, list) and len(matches_list) > 0:
        for match in matches_list:
            p_name = match.get('problem_name', 'Identified Pattern')
            cat = match.get('category', 'Psychological Indicator')
            score = match.get('similarity_score', 0)
            sev = match.get('severity', 'Moderate')
            table_rows += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; font-weight: 600; color: #0f172a;">{p_name}</td>
                <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; color: #475569;">{cat}</td>
                <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; font-weight: 700; color: #2563eb;">{score}%</td>
                <td style="padding: 10px; border-bottom: 1px solid #e2e8f0;"><span style="background: #fef2f2; color: #dc2626; padding: 3px 8px; border-radius: 4px; font-weight: 700; font-size: 12px;">{sev}</span></td>
            </tr>
            """
    else:
        table_rows = """
        <tr>
            <td colspan="4" style="padding: 12px; text-align: center; color: #64748b;">No high-confidence pattern matches recorded.</td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Inter', Helvetica, Arial, sans-serif; background-color: #f8fafc; color: #0f172a; padding: 20px; }}
            .container {{ max-width: 620px; background: #ffffff; padding: 26px; border-radius: 12px; border: 1px solid #e2e8f0; margin: 0 auto; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
            .header {{ font-size: 20px; font-weight: bold; color: #1d4ed8; margin-bottom: 6px; }}
            .sub-header {{ font-size: 13px; color: #64748b; margin-bottom: 18px; }}
            .section {{ margin-top: 18px; padding: 16px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; font-size: 14px; line-height: 1.6; }}
            .section-title {{ font-size: 13px; font-weight: 700; color: #334155; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 8px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 13px; }}
            th {{ background: #f1f5f9; text-align: left; padding: 10px; border-bottom: 2px solid #cbd5e1; color: #475569; font-weight: 700; }}
            .btn {{ display: inline-block; margin-top: 22px; padding: 12px 26px; background-color: #16a34a; color: #ffffff; text-decoration: none; font-weight: bold; border-radius: 8px; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">V16 Clinical Intake Referral</div>
            <div class="sub-header">Case Reference ID: #{report_id} · Location Proximity Match</div>
            
            <p>Dear {doctor_name},</p>
            <p>A new psychological intake report has been evaluated and assigned to your practice. Below is the clinical summary:</p>
            
            <div class="section">
                <div class="section-title">Patient Intake Description</div>
                <div style="font-style: italic; color: #334155;">"{user_input}"</div>
            </div>

            <div class="section">
                <div class="section-title">Pattern Recognition Analysis</div>
                <table>
                    <thead>
                        <tr>
                            <th>Condition Pattern</th>
                            <th>Category</th>
                            <th>Predictive Match</th>
                            <th>Severity</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
            </div>

            <div class="section">
                <div class="section-title">Clinical Guidance Assessment</div>
                <div style="color: #334155;">{gemini_guidance}</div>
            </div>

            <div class="section">
                <div class="section-title">Proposed Consultation Slot</div>
                <div style="font-weight: 700; color: #1d4ed8;">{appointment_time}</div>
            </div>

            <p style="margin-top: 22px; font-size: 14px;">Click the button below to accept this appointment request:</p>
            <a href="{accept_link}" class="btn">Accept Appointment Request</a>
        </div>
    </body>
    </html>
    """

    msg.set_content(f"Dear {doctor_name},\n\nReferral Case #{report_id} has been assigned to your practice.\nProposed Slot: {appointment_time}\nAccept link: {accept_link}")
    msg.add_alternative(html_content, subtype='html')

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
        print(f"[BACKGROUND THREAD] Email successfully sent to {doctor_email}")
    except Exception as e:
        print(f"[BACKGROUND THREAD] SMTP Error: {str(e)}")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/chat/analyze', methods=['POST'])
def analyze_user_text():
    """
    Steps 1 - 5: Intake -> Gemini JSON Extraction -> PyTorch Matcher
    """
    try:
        data = request.get_json() or {}
        user_text = data.get('text', '').strip()

        if not user_text:
            return jsonify({"status": "error", "message": "No input text provided"}), 400

        if not client:
            return jsonify({"status": "error", "message": "API Key missing"}), 500

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_text,
            config=types.GenerateContentConfig(
                system_instruction=EMBEDDED_INTAKE_PROMPT,
                temperature=0.2,
                response_mime_type="application/json"
            )
        )

        cleaned_output = clean_json_response(response.text)
        extracted_json = json.loads(cleaned_output)

        matched_results = analyze_gemini_output(extracted_json, top_k=3)

        return jsonify({
            "status": "success",
            "user_input": user_text,
            "extracted_data": extracted_json,
            "matches": matched_results
        }), 200

    except Exception as e:
        print(f"Error in analyze_user_text: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/chat/guidance', methods=['POST'])
def generate_guidance_and_log():
    """
    Steps 6 - 8: Merges User Input + Model Matches -> Gemini 2.5 Flash -> Logs to Secondary_data.db
    Generates a COMPREHENSIVE, IN-DEPTH assessment response.
    """
    try:
        data = request.get_json() or {}
        user_input = data.get('user_input', '')
        matches = data.get('matches', [])

        if not client:
            return jsonify({"status": "error", "message": "API Key missing"}), 500

        model_output_summary = json.dumps(matches, indent=2)

        embedded_guidance_prompt = f"""
USER ORIGINAL STATEMENT:
"{user_input}"

PATTERN RECOGNITION ANALYSIS:
{model_output_summary}

TASK:
Provide a detailed, thorough, highly supportive, and comprehensive clinical assessment of the identified conditions.
Offer actionable, step-by-step guidance on how the user can manage and overcome these challenges.

TONE AND STYLE GUIDELINES:
- Serious, deeply caring, warm, respectful, empathetic, and highly motivating.
- Do NOT use patronizing terms like "oh my dear".
- Do NOT use technical/developer jargon (e.g., PyTorch, Gemini, raw JSON, model matches).
- Do NOT use markdown symbols like ### or ** or *. Use clean plain text formatting.
- Make the guidance detailed, in-depth, and thorough—do NOT give brief or short summaries.
- Structure into distinct, well-spaced logical sections:
  1. Deep acknowledgment and empathetic understanding of their situation.
  2. Detailed analysis of how anxiety, workplace stress, and sleep disruption interact.
  3. Actionable, step-by-step grounding and cognitive coping methods.
  4. Specific strategies for workplace boundaries and workload management.
  5. Sleep hygiene and evening routine recommendations.
  6. Encouraging, motivating closing thoughts on moving forward.
- Separate sections with clear double line breaks so it reads cleanly.
"""

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=embedded_guidance_prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=2048
            )
        )

        gemini_output = response.text.strip()

        conn = sqlite3.connect(SECONDARY_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO reports (timestamp, user_input, pytorch_model_output, gemini_input, gemini_output)
            VALUES (?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            user_input,
            model_output_summary,
            embedded_guidance_prompt,
            gemini_output
        ))
        conn.commit()
        report_id = cursor.lastrowid
        conn.close()

        return jsonify({
            "status": "success",
            "report_id": report_id,
            "guidance": gemini_output
        }), 200

    except Exception as e:
        print(f"Error in generate_guidance_and_log: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/chat/referral', methods=['POST'])
def handle_referral():
    """
    Steps 9 - 14: Queries Third_data.db, finds closest specialist via Gemini, dispatches email asynchronously in background thread.
    """
    try:
        data = request.get_json() or {}
        user_location = data.get("location", "Krishnan Kovil, Tamil Nadu")
        user_input = data.get("user_input", "")

        conn = sqlite3.connect(SECONDARY_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, pytorch_model_output, gemini_output FROM reports ORDER BY id DESC LIMIT 1")
        last_report = cursor.fetchone()
        conn.close()

        report_id = last_report[0] if last_report else 1
        model_output = last_report[1] if last_report else ""
        gemini_guidance = last_report[2] if last_report else ""

        conn = sqlite3.connect(THIRD_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        doctors = cursor.execute("""
            SELECT psychologist_id, name, email, phone, clinic_name, location, address, city, state 
            FROM psychologists
        """).fetchall()
        conn.close()

        if not doctors:
            return jsonify({"status": "error", "message": "No records in psychologists table"}), 404

        doctor_list = [{
            "id": d['psychologist_id'],
            "name": d['name'],
            "clinic": d['clinic_name'],
            "location": f"{d['location']}, {d['address']}, {d['city']}, {d['state']}"
        } for d in doctors]

        embedded_location_prompt = f"""
USER LOCATION: "{user_location}"
AVAILABLE PSYCHOLOGISTS: {json.dumps(doctor_list)}

TASK: Return ONLY the integer 'id' of the psychologist physically closest to the user's location. Return NO other text.
"""

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=embedded_location_prompt,
            config=types.GenerateContentConfig(temperature=0.0)
        )

        try:
            closest_id = int(re.search(r'\d+', response.text).group())
        except (AttributeError, ValueError):
            closest_id = doctors[0]['psychologist_id']

        selected_doc = next((d for d in doctors if d['psychologist_id'] == closest_id), doctors[0])
        appointment_time = (datetime.now() + timedelta(days=1)).strftime("%A, %B %d, %Y at 4:30 PM")

        thread = threading.Thread(
            target=send_email_in_background,
            args=(
                selected_doc['email'],
                selected_doc['name'],
                user_input,
                model_output,
                gemini_guidance,
                report_id,
                appointment_time
            )
        )
        thread.start()

        return jsonify({
            "status": "success",
            "email_dispatched_in_background": True,
            "doctor": {
                "id": selected_doc['psychologist_id'],
                "name": selected_doc['name'],
                "email": selected_doc['email'],
                "phone": selected_doc['phone'],
                "clinic": selected_doc['clinic_name'],
                "location": f"{selected_doc['address']}, {selected_doc['city']}"
            },
            "appointment_slot": appointment_time
        }), 200

    except Exception as e:
        print(f"Error in handle_referral: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/doctor/accept/<int:report_id>', methods=['GET'])
def accept_appointment(report_id):
    return f"""
    <html>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 60px; background: #f6f8ff;">
            <div style="max-width: 500px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
                <h2 style="color: #16b981; margin-bottom: 10px;">Appointment Request Confirmed!</h2>
                <p style="color: #33415c; font-size: 15px;">Thank you. Session #{report_id} has been accepted and scheduled for tomorrow at 4:30 PM.</p>
            </div>
        </body>
    </html>
    """


@app.route('/api/chat/clear-temp', methods=['POST'])
def clear_session():
    return jsonify({"status": "success", "message": "Session reset."}), 200


if __name__ == '__main__':
    app.run(debug=True, port=5000)