"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              🎤 SPEAKING COACH — AI-POWERED COMMUNICATION TRAINER           ║
╚══════════════════════════════════════════════════════════════════════════════╝

HOW IT WORKS:
─────────────
1. You record yourself speaking on your phone or computer
2. Groq Whisper transcribes your audio with word-level timestamps
3. The app analyzes: WPM, filler words, pauses, flow
4. Groq LLaMA generates science-based coaching feedback
5. ElevenLabs speaks the feedback to you like a real coach
6. Your progress is saved to Supabase permanently

PAGES:
  "home"     → Daily drill + your stats
  "practice" → Record → Analyze → Coach feedback
  "history"  → Past sessions + progress charts
"""

import json
import os
import random
import tempfile
from datetime import datetime

import streamlit as st
from groq import Groq
from elevenlabs.client import ElevenLabs

from analysis import analyze_speech
from database import save_session, get_recent_sessions, get_all_sessions
from pronunciation import (
    PRONUNCIATION_DRILLS, score_pronunciation, get_pronunciation_feedback
)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1: DAILY DRILL CURRICULUM
# Science-based exercises that rotate daily.
# Based on: deliberate practice, spaced repetition, Toastmasters framework.
# ══════════════════════════════════════════════════════════════════════════════

DRILLS = {
    0: {  # Monday
        "name": "Pace Control",
        "icon": "⏱",
        "instruction": (
            "Speak about your morning routine for 60–90 seconds. "
            "Aim for a relaxed, steady pace. Imagine explaining it to a friend over coffee."
        ),
        "target": "120–140 WPM",
        "science": "Studies show 130 WPM maximises both audience comprehension and perceived speaker confidence.",
    },
    1: {  # Tuesday
        "name": "Filler Word Detox",
        "icon": "🚫",
        "instruction": (
            "Describe your dream holiday for 60 seconds. "
            "Every time you feel an 'um' or 'uh' coming — PAUSE instead. Silence is power."
        ),
        "target": "0–2 filler words",
        "science": "Fillers signal uncertainty to listeners. Strategic silence signals confidence and gives brains time to process.",
    },
    2: {  # Wednesday
        "name": "Power Pause",
        "icon": "⏸",
        "instruction": (
            "Introduce yourself as if speaking at a TED conference. "
            "After every key point, pause for a full second before continuing."
        ),
        "target": "3+ strategic pauses",
        "science": "Pauses activate the audience's prefrontal cortex — making your message land deeper and be remembered longer.",
    },
    3: {  # Thursday
        "name": "Vocal Energy",
        "icon": "🔥",
        "instruction": (
            "Tell a story from your life for 90 seconds. "
            "Start softly, build energy through the middle, end with full conviction."
        ),
        "target": "Volume + energy variation",
        "science": "Vocal variety activates the limbic system in listeners, creating emotional connection and sustained attention.",
    },
    4: {  # Friday
        "name": "Impromptu Speaking",
        "icon": "💡",
        "instruction": (
            "Speak for 90 seconds on: 'What is the most important skill everyone should learn?' "
            "No preparation — just go. Use the PREP structure: Point, Reason, Example, Point."
        ),
        "target": "Fluency + clear structure",
        "science": "Impromptu practice builds neural pathways for confident spontaneous communication — the most feared situation.",
    },
    5: {  # Saturday
        "name": "Storytelling Flow",
        "icon": "📖",
        "instruction": (
            "Tell a story with a clear beginning, middle, and end. "
            "Use the structure: Situation → Complication → Resolution. "
            "Keep it under 2 minutes."
        ),
        "target": "Clear narrative arc",
        "science": "Stories activate mirror neurons in listeners, making your message up to 22× more memorable than facts alone.",
    },
    6: {  # Sunday
        "name": "Full Integration",
        "icon": "🎯",
        "instruction": (
            "Give a 2-minute speech on any topic you care about. "
            "Apply everything: pace, strategic pauses, zero fillers, vocal energy. "
            "Pretend you're presenting to 100 people."
        ),
        "target": "Overall score > 75",
        "science": "Integration practice consolidates the week's skills into long-term procedural memory.",
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2: PAGE CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="🎤 Speaking Coach",
    page_icon="🎤",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3: CUSTOM CSS — Mobile-first design
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
h1 { text-align: center; }

/* Score cards */
.score-card {
    background: #1a1a2e;
    border-radius: 12px;
    padding: 1rem;
    text-align: center;
    border: 1px solid #333;
}
.score-big {
    font-size: 2.5rem;
    font-weight: 700;
    margin: 0;
}
.score-label {
    font-size: 0.8rem;
    color: #888;
    margin: 0;
}

/* Drill card */
.drill-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid #a855f7;
    border-radius: 16px;
    padding: 1.5rem;
    margin: 1rem 0;
}

/* Info box */
.info-box {
    background: #1a1a2e;
    border-left: 4px solid #a855f7;
    padding: 1rem 1.2rem;
    border-radius: 0 8px 8px 0;
    margin: 0.8rem 0;
}

/* Filler word badge */
.filler-badge {
    display: inline-block;
    background: #7f1d1d;
    color: #fca5a5;
    padding: 2px 10px;
    border-radius: 99px;
    font-size: 0.85rem;
    margin: 3px;
}

/* Primary buttons */
div.stButton > button[kind="primary"] {
    width: 100%;
    padding: 0.75rem;
    border-radius: 10px;
    font-size: 1.1rem;
    font-weight: 600;
    background-color: #a855f7;
    border: none;
}
div.stButton > button[kind="primary"]:hover {
    background-color: #9333ea;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4: SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════

st.session_state.setdefault("page", "home")
st.session_state.setdefault("analysis", None)
st.session_state.setdefault("session_saved", False)
st.session_state.setdefault("chat_history", [])
st.session_state.setdefault("pronun_drill", None)
st.session_state.setdefault("pronun_level", "beginner")
st.session_state.setdefault("pronun_score", None)
st.session_state.setdefault("streak", 0)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5: CORE AI FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def transcribe_audio(audio_bytes: bytes) -> dict:
    """
    Sends audio to Groq Whisper for transcription.
    Returns transcript text + word-level timestamps.
    Word timestamps let us calculate WPM and detect pauses precisely.
    """
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            response = client.audio.transcriptions.create(
                file=("audio.wav", f, "audio/wav"),
                model="whisper-large-v3-turbo",
                response_format="verbose_json",
                timestamp_granularities=["word"],
            )

        # response.words is a list of objects with .word, .start, .end
        words = []
        if hasattr(response, "words") and response.words:
            for w in response.words:
                # Groq returns either objects or dicts depending on SDK version
                if isinstance(w, dict):
                    words.append({"word": w.get("word", ""), "start": w.get("start", 0), "end": w.get("end", 0)})
                else:
                    words.append({"word": getattr(w, "word", ""), "start": getattr(w, "start", 0), "end": getattr(w, "end", 0)})

        duration = getattr(response, "duration", 0) or 0

        return {
            "text":     response.text,
            "words":    words,
            "duration": duration,
        }
    finally:
        os.unlink(tmp_path)


def chat_with_coach(user_message: str, analysis: dict, chat_history: list) -> str:
    """
    Continues a coaching conversation. Knows the full context:
    - The speaker's transcript and metrics
    - The entire conversation so far
    Responds like a real coach — warm, specific, actionable.
    """
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])

    vol = analysis.get("volume", {})
    vol_var = vol.get("volume_variation", 0)
    filler_summary = (
        ", ".join(f'"{k}" ({v}×)' for k, v in analysis["fillers"].items())
        if analysis["fillers"] else "none"
    )

    system_prompt = f"""You are Coach Alex, an expert communication scientist and public speaking coach.
You are warm, encouraging, specific, and science-based. You help people find their authentic voice.

You just analysed this speaker's recording. Here is their full data:
- Speaking pace: {analysis['wpm']} WPM (ideal: 120–160)
- Filler words: {filler_summary}
- Strategic pauses: {analysis['strategic_pauses']}
- Long pauses: {analysis['long_pauses']}
- Volume variation: {vol_var}/100 (ideal: 15–60, higher = more expressive)
- Overall score: {analysis['overall_score']}/100
- Their transcript: "{analysis['transcript']}"

You are now having a follow-up coaching conversation with this speaker.
- Answer their questions with specific, actionable advice
- Reference their actual transcript when relevant ("In your story, when you said X...")
- Suggest concrete techniques from communication science
- Keep responses under 120 words — this will be spoken aloud
- Be conversational, warm, and encouraging — like a real human coach"""

    # Build message history for the LLM
    messages = [{"role": "system", "content": system_prompt}]
    for msg in chat_history:
        role = "assistant" if msg["role"] == "coach" else "user"
        messages.append({"role": role, "content": msg["text"]})
    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=250,
        temperature=0.7,
    )

    return response.choices[0].message.content


def get_coaching_feedback(analysis: dict, drill_name: str) -> str:
    """
    Sends analysis data to Groq LLaMA for science-based coaching feedback.
    The coach persona: warm, specific, evidence-based, encouraging.
    """
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])

    # Format filler words for the prompt
    filler_summary = (
        ", ".join(f'"{k}" ({v}×)' for k, v in analysis["fillers"].items())
        if analysis["fillers"] else "none detected — excellent!"
    )

    vol = analysis.get("volume", {})
    vol_var = vol.get("volume_variation", 0)
    vol_feedback = "monotone — needs more variation" if vol_var < 15 else "well varied" if vol_var <= 60 else "very erratic"

    prompt = f"""You are Coach Alex, an expert communication scientist and public speaking coach.
You have helped hundreds of people find their authentic voice and speak with confidence.
Your feedback is warm, specific, science-based, and always actionable.

Here is the speaker's session data:
- Drill: {drill_name}
- Duration: {analysis['duration']} seconds
- Words spoken: {analysis['word_count']}
- Speaking pace: {analysis['wpm']} WPM (ideal: 120–160 WPM)
- Filler words: {filler_summary}
- Strategic pauses (0.5–2.5s): {analysis['strategic_pauses']} (aim for 3+)
- Overly long pauses (>2.5s): {analysis['long_pauses']}
- Volume variation: {vol_var}/100 — {vol_feedback} (ideal: 15–60)
- Average volume: {vol.get('avg_volume', 0)}/100
- Overall score: {analysis['overall_score']}/100

Their transcript: "{analysis['transcript']}"

Give feedback in this exact structure — speak directly to them, use "you":
1. ONE specific thing they did well (be genuine and specific, not generic)
2. Their #1 area to improve RIGHT NOW based on the data
3. ONE practical exercise they can do in the next 5 minutes to improve it
4. A brief insight from communication science that explains WHY this matters
5. An encouraging closing sentence that mentions their score

IMPORTANT: Keep total response under 160 words. This will be spoken aloud.
Be conversational and warm — like a real coach, not a report."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.7,
    )

    return response.choices[0].message.content


def speak_feedback(text: str) -> bytes:
    """
    Converts coaching feedback text to speech using ElevenLabs.
    Uses a warm, professional voice that sounds like a real coach.
    Returns audio bytes that Streamlit can play directly.
    """
    client = ElevenLabs(api_key=st.secrets["ELEVENLABS_API_KEY"])

    # George — warm, captivating storyteller (free premade voice)
    audio_generator = client.text_to_speech.convert(
        voice_id="JBFqnCBsd6RMkjVDRZzb",
        text=text,
        model_id="eleven_turbo_v2_5",
        output_format="mp3_44100_128",
    )

    # The API returns a generator — collect all chunks into bytes
    return b"".join(chunk for chunk in audio_generator if chunk)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6: PAGE RENDERERS
# ══════════════════════════════════════════════════════════════════════════════

def page_home():
    """Home page — today's drill + quick stats + navigation."""
    st.title("🎤 Speaking Coach")

    # ── Today's drill ─────────────────────────────────────────────────────────
    day = datetime.now().weekday()  # 0=Monday, 6=Sunday
    drill = DRILLS[day]

    st.markdown(
        f"<div class='drill-card'>"
        f"<p style='color:#a855f7; margin:0; font-size:0.85rem; font-weight:600;'>TODAY'S DRILL</p>"
        f"<h2 style='margin:0.3rem 0;'>{drill['icon']} {drill['name']}</h2>"
        f"<p style='margin:0.5rem 0; color:#cbd5e1;'>{drill['instruction']}</p>"
        f"<p style='margin:0.5rem 0; font-size:0.85rem;'>🎯 <strong>Target:</strong> {drill['target']}</p>"
        f"<p style='margin:0; font-size:0.8rem; color:#94a3b8;'>🔬 {drill['science']}</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    if col1.button("🎤 Speech Practice", type="primary", use_container_width=True):
        st.session_state.page = "practice"
        st.session_state.analysis = None
        st.session_state.session_saved = False
        st.session_state.chat_history = []
        st.rerun()

    if col2.button("🗣 Pronunciation", type="primary", use_container_width=True):
        st.session_state.page = "pronunciation"
        st.session_state.pronun_drill = None
        st.session_state.pronun_score = None
        st.rerun()

    # ── Recent stats ──────────────────────────────────────────────────────────
    st.markdown("---")
    sessions = get_recent_sessions(5)

    if sessions:
        st.markdown("### 📈 Recent Sessions")
        for s in sessions:
            date = s["recorded_at"][:10]
            score = s["overall_score"]
            color = "#22c55e" if score >= 75 else "#f59e0b" if score >= 50 else "#a855f7"
            st.markdown(
                f"<div class='info-box'>"
                f"<strong>{s['drill_type']}</strong> · {date} · "
                f"<span style='color:{color}; font-weight:700;'>{score}/100</span> · "
                f"{s['wpm']} WPM · {s['filler_count']} fillers"
                f"</div>",
                unsafe_allow_html=True,
            )

        if st.button("📊 View Full History", use_container_width=True):
            st.session_state.page = "history"
            st.rerun()
    else:
        st.markdown(
            "<div class='info-box'>No sessions yet — complete your first drill to start tracking progress!</div>",
            unsafe_allow_html=True,
        )


def page_practice():
    """Practice page — record audio, analyze, show results, play coach."""
    day = datetime.now().weekday()
    drill = DRILLS[day]

    if st.button("← Home"):
        st.session_state.page = "home"
        st.rerun()

    st.title(f"{drill['icon']} {drill['name']}")
    st.markdown(
        f"<div class='info-box'>{drill['instruction']}</div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ── Step 1: Record ────────────────────────────────────────────────────────
    if not st.session_state.analysis:
        st.markdown("### 🎙 Record Your Speech")
        st.caption("Press the mic button to start, press again to stop.")
        audio = st.audio_input(
            "Record",
            label_visibility="collapsed",
            key=f"recorder_{st.session_state.get('audio_key', 0)}"
        )

        if audio:
            with st.status("🔍 Analysing your speech...", expanded=True) as status:
                st.write("📝 Transcribing audio...")
                transcription = transcribe_audio(audio.getvalue())

                if not transcription["text"].strip():
                    st.error("No speech detected. Please try again.")
                    return

                st.write("📊 Measuring pace, pauses, volume, and filler words...")
                analysis = analyze_speech(
                    transcript=transcription["text"],
                    word_timestamps=transcription["words"],
                    duration=transcription["duration"],
                    audio_bytes=audio.getvalue(),
                )

                st.write("🧠 Coach Alex is reviewing your speech...")
                feedback = get_coaching_feedback(analysis, drill["name"])

                st.write("🔊 Preparing Coach Alex's voice...")
                try:
                    coach_audio = speak_feedback(feedback)
                except Exception as e:
                    coach_audio = None
                    st.warning(f"Voice unavailable ({e}) — showing text feedback below.")

                # Save to session state
                st.session_state.analysis = analysis
                st.session_state.chat_history = [
                    {"role": "coach", "text": feedback, "audio": coach_audio}
                ]
                status.update(label="✅ Coach Alex is ready!", state="complete", expanded=False)
            st.rerun()
        return

    # ── Step 2: Show metrics ──────────────────────────────────────────────────
    analysis = st.session_state.analysis
    overall = analysis["overall_score"]
    color = "#22c55e" if overall >= 75 else "#f59e0b" if overall >= 50 else "#a855f7"

    with st.expander("📊 Your Speech Metrics", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        col1.markdown(
            f"<div class='score-card'><p class='score-big' style='color:{color}'>{overall}</p>"
            f"<p class='score-label'>Overall</p></div>", unsafe_allow_html=True)
        wpm_color = "#22c55e" if 120 <= analysis["wpm"] <= 160 else "#f59e0b"
        col2.markdown(
            f"<div class='score-card'><p class='score-big' style='color:{wpm_color}'>{analysis['wpm']}</p>"
            f"<p class='score-label'>WPM</p></div>", unsafe_allow_html=True)
        filler_color = "#22c55e" if analysis["filler_total"] <= 2 else "#f59e0b" if analysis["filler_total"] <= 5 else "#ef4444"
        col3.markdown(
            f"<div class='score-card'><p class='score-big' style='color:{filler_color}'>{analysis['filler_total']}</p>"
            f"<p class='score-label'>Fillers</p></div>", unsafe_allow_html=True)
        pause_color = "#22c55e" if analysis["strategic_pauses"] >= 3 else "#f59e0b"
        col4.markdown(
            f"<div class='score-card'><p class='score-big' style='color:{pause_color}'>{analysis['strategic_pauses']}</p>"
            f"<p class='score-label'>Pauses ✓</p></div>", unsafe_allow_html=True)

        vol = analysis.get("volume", {})
        vol_var = vol.get("volume_variation", 0)
        st.markdown("")
        col1, col2, col3 = st.columns(3)
        vol_color = "#22c55e" if 15 <= vol_var <= 60 else "#f59e0b"
        col1.markdown(
            f"<div class='score-card'><p class='score-big' style='color:{vol_color}'>{vol_var}</p>"
            f"<p class='score-label'>Vol. Variety</p></div>", unsafe_allow_html=True)
        col2.markdown(
            f"<div class='score-card'><p class='score-big' style='color:#94a3b8'>{vol.get('avg_volume', 0)}</p>"
            f"<p class='score-label'>Avg Volume</p></div>", unsafe_allow_html=True)
        long_p = analysis["long_pauses"]
        long_color = "#22c55e" if long_p == 0 else "#f59e0b" if long_p <= 2 else "#ef4444"
        col3.markdown(
            f"<div class='score-card'><p class='score-big' style='color:{long_color}'>{long_p}</p>"
            f"<p class='score-label'>Long Pauses</p></div>", unsafe_allow_html=True)

        if analysis["fillers"]:
            st.markdown("**Filler words:**")
            badges = "".join(
                f"<span class='filler-badge'>{word} ×{count}</span>"
                for word, count in analysis["fillers"].items()
            )
            st.markdown(badges, unsafe_allow_html=True)

        with st.expander("📝 Transcript"):
            st.write(analysis["transcript"])

    # ── Step 3: Chat with Coach ───────────────────────────────────────────────
    st.markdown("### 💬 Coach Alex")

    # Display full conversation history
    for msg in st.session_state.chat_history:
        if msg["role"] == "coach":
            with st.chat_message("assistant", avatar="🎤"):
                st.markdown(msg["text"])
                if msg.get("audio"):
                    st.audio(msg["audio"], format="audio/mp3", autoplay=False)
                else:
                    st.warning("🔇 Voice failed — check ElevenLabs key permissions")
        else:
            with st.chat_message("user", avatar="🧑"):
                st.markdown(msg["text"])

    # Save session once
    if not st.session_state.session_saved and st.session_state.chat_history:
        first_feedback = st.session_state.chat_history[0]["text"]
        save_session(analysis, drill["name"], first_feedback)
        st.session_state.session_saved = True

    # ── Text input for follow-up questions ───────────────────────────────────
    st.markdown("---")
    st.caption("Ask Coach Alex anything — how to improve your story, work on specific skills, or get an exercise to try right now.")

    user_input = st.chat_input("Ask your coach... e.g. 'How can I make my story more memorable?'")

    if user_input:
        # Add user message to history
        st.session_state.chat_history.append({"role": "user", "text": user_input, "audio": None})

        # Get coach response
        with st.spinner("Coach Alex is thinking..."):
            reply = chat_with_coach(
                user_message=user_input,
                analysis=analysis,
                chat_history=st.session_state.chat_history[:-1],  # exclude the just-added user msg
            )
            try:
                reply_audio = speak_feedback(reply)
            except Exception as e:
                reply_audio = None
                st.error(f"ElevenLabs: {e}")

        st.session_state.chat_history.append({"role": "coach", "text": reply, "audio": reply_audio})
        st.rerun()

    # ── Navigation ─────────────────────────────────────────────────────────────
    st.markdown("")
    col1, col2 = st.columns(2)
    if col1.button("🔄 New Recording", use_container_width=True):
        st.session_state.analysis = None
        st.session_state.chat_history = []
        st.session_state.session_saved = False
        st.session_state.audio_key = st.session_state.get("audio_key", 0) + 1
        st.rerun()

    if col2.button("🏠 Home", type="primary", use_container_width=True):
        st.session_state.page = "home"
        st.rerun()


def page_history():
    """History page — past sessions and progress charts."""
    if st.button("← Home"):
        st.session_state.page = "home"
        st.rerun()

    st.title("📊 Your Progress")

    sessions = get_all_sessions()

    if not sessions:
        st.info("No sessions yet. Complete your first practice to see progress here!")
        return

    # ── Progress chart ────────────────────────────────────────────────────────
    import pandas as pd

    df = pd.DataFrame(sessions)
    df["date"] = pd.to_datetime(df["recorded_at"]).dt.date

    st.markdown("### Overall Score Over Time")
    st.line_chart(df.set_index("date")["overall_score"])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### WPM Over Time")
        st.line_chart(df.set_index("date")["wpm"])
    with col2:
        st.markdown("### Filler Words Over Time")
        st.line_chart(df.set_index("date")["filler_count"])

    # ── Summary stats ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Your Averages")
    col1, col2, col3 = st.columns(3)
    col1.metric("Avg Score", f"{df['overall_score'].mean():.0f}/100")
    col2.metric("Avg WPM", f"{df['wpm'].mean():.0f}")
    col3.metric("Avg Fillers", f"{df['filler_count'].mean():.1f}")

    # ── Recent sessions ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Recent Sessions")
    recent = get_recent_sessions(20)
    for s in recent:
        date = s["recorded_at"][:16].replace("T", " ")
        score = s["overall_score"]
        color = "#22c55e" if score >= 75 else "#f59e0b" if score >= 50 else "#a855f7"
        with st.expander(f"{s['drill_type']} · {date} · Score: {score}/100"):
            col1, col2, col3 = st.columns(3)
            col1.metric("WPM", s["wpm"])
            col2.metric("Fillers", s["filler_count"])
            col3.metric("Pauses", s["pause_count"])
            if s.get("feedback"):
                st.markdown("**Coach feedback:**")
                st.markdown(s["feedback"])


def page_pronunciation():
    """
    ELSA-style pronunciation trainer.
    Shows a sentence, user records it, app scores word by word.
    """
    if st.button("← Home"):
        st.session_state.page = "home"
        st.session_state.pronun_score = None
        st.session_state.pronun_drill = None
        st.rerun()

    st.title("🗣 Pronunciation Coach")
    st.caption("American English · Powered by AI")

    # ── Level selector ─────────────────────────────────────────────────────────
    level = st.selectbox(
        "Difficulty",
        ["beginner", "intermediate", "advanced"],
        index=["beginner", "intermediate", "advanced"].index(
            st.session_state.pronun_level
        ),
    )
    if level != st.session_state.pronun_level:
        st.session_state.pronun_level = level
        st.session_state.pronun_drill = None
        st.session_state.pronun_score = None

    # ── Pick a drill ──────────────────────────────────────────────────────────
    if not st.session_state.pronun_drill:
        st.session_state.pronun_drill = random.choice(
            PRONUNCIATION_DRILLS[st.session_state.pronun_level]
        )
        st.session_state.pronun_score = None

    drill = st.session_state.pronun_drill

    # ── Show the target sentence ───────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📖 Read this sentence aloud:")
    st.markdown(
        f"<div class='drill-card'>"
        f"<p style='font-size:1.4rem; font-weight:600; margin:0; color:#e2e8f0;'>"
        f"\"{drill['sentence']}\""
        f"</p>"
        f"<p style='margin:0.8rem 0 0; font-size:0.85rem; color:#a855f7;'>"
        f"🎯 Focus: {drill['focus']}</p>"
        f"<p style='margin:0.3rem 0 0; font-size:0.8rem; color:#94a3b8;'>"
        f"💡 {drill['tip']}</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Highlight target words
    st.caption("Key words to nail: " + " · ".join(f"**{w}**" for w in drill["targets"]))

    # ── Record ────────────────────────────────────────────────────────────────
    st.markdown("### 🎙 Now say it:")
    audio = st.audio_input(
        "Record",
        label_visibility="collapsed",
        key=f"pronun_{st.session_state.get('audio_key', 0)}",
    )

    if audio and not st.session_state.pronun_score:
        with st.status("🔍 Scoring your pronunciation...", expanded=True) as status:
            st.write("📝 Transcribing...")
            transcription = transcribe_audio(audio.getvalue())
            actual = transcription["text"].strip()

            if not actual:
                st.error("No speech detected. Try again.")
                return

            st.write("📊 Comparing word by word...")
            score = score_pronunciation(drill["sentence"], actual)

            st.write("🧠 Coach Alex is preparing feedback...")
            feedback_prompt = get_pronunciation_feedback(
                drill["sentence"], actual, score, drill
            )
            client = Groq(api_key=st.secrets["GROQ_API_KEY"])
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are Coach Alex, a warm American English pronunciation coach. Keep responses under 100 words. This will be spoken aloud."},
                    {"role": "user", "content": feedback_prompt},
                ],
                max_tokens=200,
                temperature=0.7,
            )
            feedback_text = resp.choices[0].message.content

            st.write("🔊 Preparing voice feedback...")
            try:
                feedback_audio = speak_feedback(feedback_text)
            except Exception as e:
                feedback_audio = None

            st.session_state.pronun_score = {
                "score": score,
                "actual": actual,
                "feedback_text": feedback_text,
                "feedback_audio": feedback_audio,
            }
            status.update(label="✅ Done!", state="complete", expanded=False)
        st.rerun()

    # ── Show results ──────────────────────────────────────────────────────────
    if st.session_state.pronun_score:
        result = st.session_state.pronun_score
        score = result["score"]
        accuracy = score["accuracy"]

        st.markdown("---")
        st.markdown("### 📊 Your Score")

        # Big accuracy score
        color = "#22c55e" if accuracy >= 80 else "#f59e0b" if accuracy >= 60 else "#ef4444"
        st.markdown(
            f"<div style='text-align:center; padding:1.5rem; background:#1a1a2e; "
            f"border-radius:16px; border: 2px solid {color};'>"
            f"<p style='font-size:4rem; font-weight:700; color:{color}; margin:0;'>{accuracy}%</p>"
            f"<p style='color:#94a3b8; margin:0;'>Pronunciation Accuracy</p>"
            f"<p style='margin:0.5rem 0 0; color:#e2e8f0;'>"
            f"{score['correct_count']} of {score['total_words']} words clear</p>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Word-by-word breakdown
        st.markdown("### 🔤 Word by Word")
        cols = st.columns(min(len(score["word_results"]), 4))
        for i, w in enumerate(score["word_results"]):
            col = cols[i % len(cols)]
            bg = "#14532d" if w["correct"] else "#7f1d1d"
            text_color = "#86efac" if w["correct"] else "#fca5a5"
            icon = "✅" if w["correct"] else "❌"
            actual_show = "" if w["correct"] else f"<br><small>heard: '{w['actual']}'</small>"
            col.markdown(
                f"<div style='background:{bg}; border-radius:8px; padding:8px; "
                f"text-align:center; margin:4px;'>"
                f"<p style='color:{text_color}; margin:0; font-weight:600;'>{icon} {w['expected']}</p>"
                f"<p style='color:#94a3b8; margin:0; font-size:0.75rem;'>{actual_show}</p>"
                f"</div>",
                unsafe_allow_html=True,
            )

        # What you said vs target
        st.markdown("---")
        col1, col2 = st.columns(2)
        col1.markdown("**🎯 Target:**")
        col1.info(drill["sentence"])
        col2.markdown("**🗣 What was heard:**")
        col2.warning(result["actual"])

        # Coach feedback
        st.markdown("### 🎤 Coach Alex")
        with st.chat_message("assistant", avatar="🎤"):
            st.markdown(result["feedback_text"])
            if result["feedback_audio"]:
                st.audio(result["feedback_audio"], format="audio/mp3", autoplay=False)

        # Update streak
        if accuracy >= 70:
            st.session_state.streak += 1
            st.success(f"🔥 Streak: {st.session_state.streak} in a row!")

        # Navigation
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        if col1.button("🔄 Try Again", use_container_width=True):
            st.session_state.pronun_score = None
            st.session_state.audio_key = st.session_state.get("audio_key", 0) + 1
            st.rerun()

        if col2.button("⏭ Next Sentence", type="primary", use_container_width=True):
            st.session_state.pronun_drill = None
            st.session_state.pronun_score = None
            st.session_state.audio_key = st.session_state.get("audio_key", 0) + 1
            st.rerun()

        if col3.button("🏠 Home", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7: MAIN ROUTER
# ══════════════════════════════════════════════════════════════════════════════

def main():
    page = st.session_state.page

    if page == "home":
        page_home()
    elif page == "practice":
        page_practice()
    elif page == "pronunciation":
        page_pronunciation()
    elif page == "history":
        page_history()
    else:
        st.session_state.page = "home"
        st.rerun()


if __name__ == "__main__":
    main()
