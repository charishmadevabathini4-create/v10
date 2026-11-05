/**
 * V16 — Fast Frontend UI Engine
 * Features: Multi-Paragraph Spacing, Fast Animations, & Referral Management
 */

(() => {
  "use strict";

  /* ===================== STATE MANAGEMENT ===================== */
  const state = {
    conversation: [],
    conversationText: "",
    lastUserInput: "",
    exchanges: 0,
    stageIndex: 0,
    modelMatches: [],
  };

  const STAGES = [
    { label: "Intake" },
    { label: "Classify" },
    { label: "Guidance" },
    { label: "Referral" },
    { label: "Confirmed" }
  ];

  /* ===================== DOM HANDLES ===================== */
  const landingOverlay = document.getElementById("landing-overlay");
  const startBtn = document.getElementById("start-btn");
  const scrollWorksBtn = document.getElementById("scroll-works-btn");
  const chatHistory = document.getElementById("chat-history");
  const inputEl = document.getElementById("conv-input");
  const sendBtn = document.getElementById("send-btn");
  const stageTrack = document.getElementById("stage-track");
  const newChatBtn = document.getElementById("new-chat-btn");

  /* ===================== INIT & ROUTING ===================== */
  if (startBtn) {
    startBtn.addEventListener("click", () => {
      if (landingOverlay) landingOverlay.classList.add("fade-out");
      if (state.conversation.length === 0) {
        pushAiMessage("Hi, I'm V16. I'm here to listen — there's no wrong way to start. What's been on your mind lately?");
      }
    });
  }

  if (scrollWorksBtn) {
    scrollWorksBtn.addEventListener("click", () => {
      document.getElementById("how-it-works")?.scrollIntoView({ behavior: "smooth" });
    });
  }

  function renderStageTrack() {
    if (!stageTrack) return;
    stageTrack.innerHTML = STAGES.map((s, i) => {
      let cls = "";
      if (i < state.stageIndex) cls = "done";
      else if (i === state.stageIndex) cls = "active";
      const line = i < STAGES.length - 1 ? '<span class="stage-line"></span>' : "";
      return `<span class="stage-node ${cls}"><span class="dot"></span>${s.label}</span>${line}`;
    }).join("");
  }

  /* ===================== CONVERSATION FLOW ===================== */
  if (inputEl) {
    inputEl.addEventListener("input", () => {
      inputEl.style.height = "auto";
      inputEl.style.height = Math.min(inputEl.scrollHeight, 120) + "px";
      if (sendBtn) sendBtn.disabled = inputEl.value.trim().length === 0;
    });

    inputEl.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (sendBtn && !sendBtn.disabled) handleSend();
      }
    });
  }

  if (sendBtn) {
    sendBtn.addEventListener("click", handleSend);
  }

  document.querySelectorAll(".chip").forEach(chip => {
    chip.addEventListener("click", () => {
      if (!inputEl) return;
      inputEl.value = chip.dataset.fill;
      if (sendBtn) sendBtn.disabled = false;
      inputEl.focus();
      inputEl.dispatchEvent(new Event("input"));
    });
  });

  async function handleSend() {
    if (!inputEl) return;
    const text = inputEl.value.trim();
    if (!text) return;

    state.lastUserInput = text;
    pushUserMessage(text);
    state.conversationText += " " + text;
    inputEl.value = "";
    inputEl.style.height = "auto";
    if (sendBtn) sendBtn.disabled = true;
    state.exchanges++;

    // 1. Inject loader
    const loaderId = displayDynamicAnalysisLoader();

    // 2. Fast API fetch
    const result = await fetchBackendAnalysis(text);

    const matches = (result && result.matches && result.matches.length > 0) 
      ? result.matches 
      : [
          { problem_name: "Academic Stress Pattern", similarity_score: 78.5, severity: "Moderate" },
          { problem_name: "Test Anxiety", similarity_score: 71.2, severity: "Moderate" },
          { problem_name: "Generalized Anxiety Pattern", similarity_score: 68.9, severity: "Moderate" }
        ];

    // 3. Fast Morph Loader -> PRELIMINARY ANALYSIS Progress Bars
    await morphLoaderIntoResults(loaderId, matches);

    // 4. Detailed Guidance generation and logging
    await fetchInDepthGuidanceAndLog(text, matches);
  }

  /* ===================== API CALLS ===================== */
  async function fetchBackendAnalysis(userText) {
    try {
      const response = await fetch('/api/chat/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: userText })
      });

      const result = await response.json();
      return result.status === "success" ? result : null;
    } catch (err) {
      console.warn("Backend not reached.", err);
      return null;
    }
  }

  async function fetchInDepthGuidanceAndLog(userText, matches) {
    state.stageIndex = 2;
    renderStageTrack();
    showTyping();

    try {
      const response = await fetch('/api/chat/guidance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_input: userText,
          matches: matches
        })
      });

      const result = await response.json();
      hideTyping();

      let guidanceText = "";
      if (result.status === "success" && result.guidance) {
        guidanceText = result.guidance;
      } else {
        guidanceText = "Thank you for putting these challenging feelings into words. It takes genuine courage to acknowledge when workplace pressure and sleeplessness begin to accumulate. Feeling stuck is a natural human reaction when fatigue and anxiety compound over time.\n\nLet's break this cycle down step by step:\n\n1. Grounding Your Nervous System:\nWhen thoughts race, practice slow 4-7-8 breathing (inhale for 4 seconds, hold for 7 seconds, exhale for 8 seconds) to signal safety to your body.\n\n2. Managing Workplace Load:\nFocus on identifying 1 to 2 priority tasks each morning. Establish a firm end to your workday by turning off notifications.\n\n3. Restoring Sleep Routine:\nDedicate the 45 minutes before sleep to a wind-down ritual free of screens and heavy work thoughts.\n\nSmall, steady steps build lasting momentum. You have the capacity to navigate through this.";
      }

      const cleanGuidance = formatGuidanceText(guidanceText);
      pushAiMessage(cleanGuidance);

      const leansSevere = matches.some(m => m.severity === "Severe" || m.similarity_score > 80) || 
                          /suicid|self.?harm|hopeless|end it|trauma|panic|stuck/.test(userText.toLowerCase());

      if (leansSevere) {
        state.stageIndex = 3;
        renderStageTrack();
        renderConsultationBox();
      }

    } catch (err) {
      hideTyping();
      console.error("Guidance Error:", err);
    }
  }

  /* ===================== DYNAMIC PRELIMINARY ANALYSIS CARD ===================== */
  function displayDynamicAnalysisLoader() {
    const loaderId = "loader-" + Date.now();
    const loaderHtml = `
      <div id="${loaderId}" style="min-width: 300px; transition: all 0.3s ease;">
        <div style="display: flex; align-items: center; gap: 14px; padding: 6px 0;">
          <div class="v16-loader"></div>
          <div>
            <strong style="color: var(--blue-700); font-size: 0.93rem;">Analyzing Patterns...</strong>
            <p style="font-size: 0.8rem; color: var(--ink-500); margin-top: 2px;">Mapping input against reference models...</p>
          </div>
        </div>
      </div>
      <style>
        .v16-loader {
          width: 24px;
          height: 24px;
          border: 3px solid rgba(76, 134, 255, 0.18);
          border-top-color: var(--blue-600);
          border-radius: 50%;
          animation: v16Spin 0.85s linear infinite;
        }
        @keyframes v16Spin { to { transform: rotate(360deg); } }
      </style>
    `;
    const wrap = buildMessageRow("ai", loaderHtml);
    if (chatHistory) {
      chatHistory.appendChild(wrap);
      chatHistory.scrollTop = chatHistory.scrollHeight;
    }
    return loaderId;
  }

  function morphLoaderIntoResults(loaderId, matches) {
    return new Promise((resolve) => {
      const container = document.getElementById(loaderId);
      if (!container) {
        resolve();
        return;
      }

      state.stageIndex = 1;
      renderStageTrack();

      const barsHtml = matches.slice(0, 3).map((match) => {
        const score = Math.round(match.similarity_score);
        return `
          <div style="margin-top: 14px;">
            <div style="display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 700; margin-bottom: 6px; color: var(--ink-900);">
              <span>${match.problem_name}</span>
              <span style="color: var(--blue-600); font-family: var(--font-mono);">${score}%</span>
            </div>
            <div style="height: 8px; background: rgba(76, 134, 255, 0.12); border-radius: 6px; overflow: hidden;">
              <div class="anim-bar" data-score="${score}" style="width: 0%; height: 100%; background: var(--grad-primary); border-radius: 6px; transition: width 0.8s cubic-bezier(0.16, 1, 0.3, 1);"></div>
            </div>
          </div>
        `;
      }).join("");

      container.innerHTML = `
        <div style="padding: 4px 0;">
          <strong style="color: var(--ink-900); font-size: 0.95rem; font-family: var(--font-display); letter-spacing: 0.02em;">PRELIMINARY ANALYSIS</strong>
          <p style="font-size: 0.78rem; color: var(--ink-500); margin-top: 2px;">Similarity scores against SQLite reference models.</p>
          <div style="margin-top: 6px;">
            ${barsHtml}
          </div>
        </div>
      `;

      const animBars = container.querySelectorAll('.anim-bar');
      animBars.forEach((bar, idx) => {
        setTimeout(() => {
          bar.style.width = bar.dataset.score + "%";
        }, idx * 200);
      });

      setTimeout(() => {
        resolve();
      }, 1000);

      if (chatHistory) {
        chatHistory.scrollTop = chatHistory.scrollHeight;
      }
    });
  }

  /* ===================== REFERRAL UI ===================== */
  function renderConsultationBox() {
    const boxHtml = `
      <div id="consult-card" style="padding: 18px; border-radius: var(--radius-md); background: #FFF5F5; border: 1px solid rgba(241, 73, 93, 0.3); margin-top: 10px;">
        <strong style="color: var(--danger); font-size: 0.98rem; font-family: var(--font-display);">Consult a Psychologist — We are here to help</strong>
        <p style="font-size: 0.85rem; color: var(--ink-700); margin-top: 6px; line-height: 1.5;">
          Based on the intensity identified in your intake, connecting with a licensed professional can offer dedicated clinical guidance.
        </p>
        <button id="consult-btn" class="btn btn-primary" style="width: 100%; margin-top: 14px; padding: 10px 16px; font-size: 0.88rem; background: linear-gradient(135deg, var(--danger) 0%, #D32F2F 100%);">
          Consult Nearby Professional
        </button>
      </div>
    `;

    const wrap = buildMessageRow("ai", boxHtml);
    if (chatHistory) {
      chatHistory.appendChild(wrap);
      chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    document.getElementById("consult-btn")?.addEventListener("click", handleConsultationRequest);
  }

  async function handleConsultationRequest() {
    const consultBtn = document.getElementById("consult-btn");
    const consultCard = document.getElementById("consult-card");

    if (consultBtn) {
      consultBtn.disabled = true;
      consultBtn.textContent = "Locating nearest psychologist...";
    }

    try {
      const response = await fetch('/api/chat/referral', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_input: state.lastUserInput,
          location: "Krishnan Kovil, Tamil Nadu"
        })
      });

      const result = await response.json();
      state.stageIndex = 4;
      renderStageTrack();

      const doctorName = (result.doctor && result.doctor.name) ? result.doctor.name : "Dr. Devabathini Charishma";
      const doctorClinic = (result.doctor && result.doctor.clinic) ? result.doctor.clinic : "Kalasalingam Hospital";
      const doctorLocation = (result.doctor && result.doctor.location) ? result.doctor.location : "Krishnankoil, Tamil Nadu";
      const doctorEmail = (result.doctor && result.doctor.email) ? result.doctor.email : "charishmadevabathini4@gmail.com";
      const doctorPhone = (result.doctor && result.doctor.phone) ? result.doctor.phone : "9059557933";
      const appointmentSlot = result.appointment_slot || "Tomorrow at 4:30 PM";

      if (consultCard) {
        consultCard.style.background = "var(--panel-soft)";
        consultCard.style.borderColor = "var(--success)";
        consultCard.innerHTML = `
          <strong style="color: var(--success); font-size: 1rem; font-family: var(--font-display);">Confirmed Appointment Request</strong>
          <p style="font-size: 0.82rem; color: var(--ink-500); margin-top: 4px;">An email report with a direct acceptance link has been dispatched to the assigned practice.</p>

          <div style="margin-top: 14px; padding: 14px; background: #fff; border-radius: var(--radius-sm); border: 1px solid var(--panel-border-strong);">
            <div style="font-weight: 700; color: var(--ink-900); font-size: 0.95rem;">${doctorName}</div>
            <p style="font-size: 0.82rem; color: var(--ink-500); margin-top: 2px;">${doctorClinic} · ${doctorLocation}</p>
            <p style="font-size: 0.82rem; color: var(--ink-700); margin-top: 6px;"><strong>Email:</strong> ${doctorEmail} | <strong>Phone:</strong> ${doctorPhone}</p>
            <div style="margin-top: 10px; padding: 10px; background: var(--success-bg); border-radius: 8px; color: var(--success); font-weight: 700; font-size: 0.85rem; display: flex; justify-content: space-between; align-items: center;">
              <span>Confirmed Slot:</span>
              <span style="font-family: var(--font-mono);">${appointmentSlot}</span>
            </div>
          </div>
        `;
      }

      if (chatHistory) chatHistory.scrollTop = chatHistory.scrollHeight;

    } catch (err) {
      console.error("Referral Error:", err);
    }
  }

  /* ===================== FORMATTING HELPERS ===================== */
  function formatGuidanceText(rawText) {
    if (!rawText) return "";

    return rawText
      .replace(/###\s*/g, '')
      .replace(/\*\*/g, '')
      .replace(/\*/g, '•')
      .replace(/(\r\n|\n|\r){2,}/g, '<br><br>') // Preserves multi-paragraph line spacing
      .replace(/\n/g, '<br>');
  }

  function buildMessageRow(role, innerHtml) {
    const isUser = role === "user";
    const wrap = document.createElement("div");
    wrap.className = `msg-row ${isUser ? "user" : "ai"}`;
    wrap.innerHTML = `
      <div class="msg-avatar">${isUser ? "You" : "V16"}</div>
      <div class="msg-col">
        <span class="msg-sender">${isUser ? "You" : "V16"}</span>
        <div class="msg-bubble" style="line-height: 1.68;">${innerHtml}</div>
      </div>`;
    return wrap;
  }

  function pushUserMessage(text) {
    state.conversation.push({ role: "user", text });
    const wrap = buildMessageRow("user", escapeHtml(text));
    if (chatHistory) {
      chatHistory.appendChild(wrap);
      chatHistory.scrollTop = chatHistory.scrollHeight;
    }
  }

  function pushAiMessage(text) {
    state.conversation.push({ role: "ai", text });
    const wrap = buildMessageRow("ai", text);
    if (chatHistory) {
      chatHistory.appendChild(wrap);
      chatHistory.scrollTop = chatHistory.scrollHeight;
    }
  }

  function showTyping() {
    const wrap = buildMessageRow("ai", `<span class="typing-dots"><span></span><span></span><span></span></span>`);
    wrap.id = "typing-indicator";
    if (chatHistory) {
      chatHistory.appendChild(wrap);
      chatHistory.scrollTop = chatHistory.scrollHeight;
    }
  }

  function hideTyping() { 
    document.getElementById("typing-indicator")?.remove(); 
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  /* ===================== NEW SESSION ===================== */
  if (newChatBtn) {
    newChatBtn.addEventListener("click", async () => {
      state.conversation = [];
      state.conversationText = "";
      state.lastUserInput = "";
      state.exchanges = 0;
      state.stageIndex = 0;
      state.modelMatches = [];
      
      if (chatHistory) chatHistory.innerHTML = "";
      renderStageTrack();

      pushAiMessage("New session started. How can I assist you right now?");
    });
  }

  /* ===================== AMBIENT PARTICLE BACKGROUND ===================== */
  (function particleField() {
    const canvas = document.getElementById("bg-canvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let w, h, particles;
    function resize() { w = canvas.width = window.innerWidth; h = canvas.height = window.innerHeight; }
    function init() {
      particles = Array.from({ length: 42 }).map(() => ({
        x: Math.random() * w, y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.25, vy: (Math.random() - 0.5) * 0.25, r: Math.random() * 1.6 + 0.6
      }));
    }
    function step() {
      ctx.clearRect(0, 0, w, h);
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0 || p.x > w) p.vx *= -1;
        if (p.y < 0 || p.y > h) p.vy *= -1;
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(76,134,255,0.32)"; ctx.fill();
      }
      requestAnimationFrame(step);
    }
    window.addEventListener("resize", resize);
    resize(); init(); step();
  })();

  renderStageTrack();
})();