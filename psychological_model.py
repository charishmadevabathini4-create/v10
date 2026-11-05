import os
import sqlite3
import torch
from sentence_transformers import SentenceTransformer

# ============================================================
# CONFIGURATION & PATH RESOLUTION
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "Preliminary_data.db")
MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K = 10

# ============================================================
# DATABASE LOADER
# ============================================================
class PsychologicalDatabase:
    def __init__(self, db_path):
        self.db_path = db_path
        self.patterns = []
        self.load_database()

    def get_tables(self, connection):
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return {row[0] for row in cursor.fetchall()}

    def load_database(self):
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at path: {self.db_path}")

        connection = sqlite3.connect(self.db_path)
        tables = self.get_tables(connection)

        if "problems" not in tables:
            connection.close()
            raise RuntimeError("The 'problems' table does not exist in SQLite DB.")

        cursor = connection.cursor()
        cursor.execute("""
            SELECT id, name, category, description, severity
            FROM problems
            ORDER BY id
        """)
        problems = cursor.fetchall()

        for row in problems:
            problem_id, name, category, description, severity = row

            symptoms = self.get_features(connection, "symptoms", "symptom", problem_id)
            behaviors = self.get_features(connection, "behaviors", "behavior", problem_id)
            emotions = self.get_features(connection, "emotions", "emotion", problem_id)
            triggers = self.get_features(connection, "triggers", "trigger", problem_id)
            keywords = self.get_features(connection, "keywords", "keyword", problem_id)
            anxiety_patterns = self.get_features(connection, "anxiety_patterns", "anxiety_pattern", problem_id)
            trauma_patterns = self.get_features(connection, "trauma_patterns", "trauma_pattern", problem_id)

            document = self.create_document(
                name, category, description, severity,
                symptoms, behaviors, emotions, triggers,
                keywords, anxiety_patterns, trauma_patterns
            )

            self.patterns.append({
                "id": problem_id,
                "name": name,
                "category": category,
                "description": description,
                "severity": severity,
                "document": document
            })

        connection.close()

    def get_features(self, connection, table_name, column_name, problem_id):
        valid_tables = {
            "symptoms": "symptom",
            "behaviors": "behavior",
            "emotions": "emotion",
            "triggers": "trigger",
            "keywords": "keyword",
            "anxiety_patterns": "anxiety_pattern",
            "trauma_patterns": "trauma_pattern"
        }
        if table_name not in valid_tables:
            return []

        cursor = connection.cursor()
        query = f"SELECT {column_name} FROM {table_name} WHERE problem_id = ?"
        try:
            cursor.execute(query, (problem_id,))
            rows = cursor.fetchall()
            return [str(row[0]) for row in rows if row[0] is not None]
        except sqlite3.Error:
            return []

    def create_document(self, name, category, description, severity, symptoms, behaviors, emotions, triggers, keywords, anxiety_patterns, trauma_patterns):
        parts = [f"Psychological pattern: {name}", f"Category: {category}"]
        if description: parts.append(f"Description: {description}")
        if severity: parts.append(f"Severity: {severity}")
        if symptoms: parts.append("Symptoms: " + ", ".join(symptoms))
        if behaviors: parts.append("Behaviors: " + ", ".join(behaviors))
        if emotions: parts.append("Emotions: " + ", ".join(emotions))
        if triggers: parts.append("Triggers: " + ", ".join(triggers))
        if keywords: parts.append("Keywords: " + ", ".join(keywords))
        if anxiety_patterns: parts.append("Anxiety patterns: " + ", ".join(anxiety_patterns))
        if trauma_patterns: parts.append("Trauma patterns: " + ", ".join(trauma_patterns))
        return "\n".join(parts)

# ============================================================
# CONVERT GEMINI JSON TO TEXT
# ============================================================
def gemini_to_text(data):
    parts = []
    if data.get("age") is not None: parts.append(f"Age: {data['age']}")
    if data.get("duration"): parts.append(f"Duration: {data['duration']}")
    if data.get("frequency"): parts.append(f"Frequency: {data['frequency']}")
    if data.get("intensity") is not None: parts.append(f"Intensity: {data['intensity']} out of 10")
    if data.get("onset"): parts.append(f"Onset: {data['onset']}")

    fields = [
        ("triggers", "Triggers"),
        ("symptoms", "Symptoms"),
        ("behaviors", "Behaviors"),
        ("emotions", "Emotions"),
        ("trauma_indicators", "Trauma indicators"),
        ("anxiety_indicators", "Anxiety indicators"),
        ("sleep_indicators", "Sleep indicators"),
        ("social_indicators", "Social indicators"),
        ("cognitive_patterns", "Cognitive patterns"),
        ("functional_impact", "Functional impact"),
        ("events", "Events")
    ]

    for key, label in fields:
        values = data.get(key, [])
        if not values:
            continue
        if isinstance(values, list):
            values = [str(v) for v in values if v]
            if values:
                parts.append(f"{label}: " + ", ".join(values))
        else:
            parts.append(f"{label}: {values}")

    return "\n".join(parts)

# ============================================================
# TRANSFORMER MATCHER ENGINE
# ============================================================
class PsychologicalMatcher:
    def __init__(self, database, model):
        self.database = database
        self.model = model
        self.database_embeddings = None
        self.prepare_database()

    def prepare_database(self):
        documents = [pattern["document"] for pattern in self.database.patterns]
        self.database_embeddings = self.model.encode(
            documents,
            convert_to_tensor=True,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        if self.database_embeddings.dim() == 1:
            self.database_embeddings = self.database_embeddings.unsqueeze(0)

    def match(self, gemini_data):
        if not isinstance(gemini_data, dict):
            raise TypeError("gemini_data must be a dictionary.")

        user_text = gemini_to_text(gemini_data)
        if not user_text.strip():
            # Fallback text if user input was minimal
            user_text = "General psychological distress, stress, and anxiety indicators."

        user_embedding = self.model.encode(
            user_text,
            convert_to_tensor=True,
            normalize_embeddings=True
        ).flatten()

        similarity_scores = torch.matmul(self.database_embeddings, user_embedding).flatten()
        sorted_indices = torch.argsort(similarity_scores, descending=True)

        results = []
        for index in sorted_indices.tolist():
            pattern = self.database.patterns[index]
            score = max(-1.0, min(1.0, similarity_scores[index].item()))

            results.append({
                "id": pattern["id"],
                "problem_name": pattern["name"],
                "category": pattern["category"],
                "severity": pattern["severity"],
                "similarity": round(score, 4),
                "similarity_score": round(score * 100, 2)
            })

        return results

    def top_matches(self, gemini_data, top_k=TOP_K):
        results = self.match(gemini_data)
        return results[:top_k]

# ============================================================
# SINGLETON INITIALIZATION (LOADS ONCE ON SERVER STARTUP)
# ============================================================
print("Initializing SentenceTransformer model & SQLite Database Embeddings...")
transformer_model = SentenceTransformer(MODEL_NAME)
database = PsychologicalDatabase(DB_PATH)
matcher = PsychologicalMatcher(database, transformer_model)
print("Psychological Matcher Engine Ready.")

def analyze_gemini_output(gemini_output, top_k=TOP_K):
    """
    Flask Endpoint Interface: Receives Gemini dict and outputs similarity matches.
    """
    if isinstance(gemini_output, dict) and "extracted_data" in gemini_output:
        extracted_data = gemini_output["extracted_data"]
    else:
        extracted_data = gemini_output

    return matcher.top_matches(extracted_data, top_k=top_k)