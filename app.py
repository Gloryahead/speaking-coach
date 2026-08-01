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
from streamlit_mic_recorder import mic_recorder

from analysis import analyze_speech
from database import save_session, get_recent_sessions, get_all_sessions
from exercises import EXERCISES
from pronunciation import (
    PRONUNCIATION_DRILLS, assess_pronunciation, build_feedback_prompt
)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1: DAILY DRILL CURRICULUM
# Science-based exercises that rotate daily.
# Based on: deliberate practice, spaced repetition, Toastmasters framework.
# ══════════════════════════════════════════════════════════════════════════════

# DRILLS is now sourced from exercises.py — EXERCISES[day] is the canonical source.
# Kept for any legacy references.
DRILLS = EXERCISES


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
st.session_state.setdefault("pending_question", None)


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


def get_coaching_feedback(analysis: dict, exercise: dict) -> str:
    """
    Sends analysis data to Groq LLaMA for targeted, technique-specific coaching.
    The feedback is focused on how well the speaker executed the day's specific exercise.
    """
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])

    filler_summary = (
        ", ".join(f'"{k}" ({v}×)' for k, v in analysis["fillers"].items())
        if analysis["fillers"] else "none detected — excellent!"
    )

    vol = analysis.get("volume", {})
    vol_var = vol.get("volume_variation", 0)
    vol_feedback = "monotone — needs more variation" if vol_var < 15 else "well varied" if vol_var <= 60 else "very erratic"

    prompt = f"""You are Coach Alex — a world-class communication coach, public speaking expert,
and behavioral scientist. You coach TEDx speakers, executives, and everyday people
to communicate with power, clarity, and authenticity.

Your expertise draws on:
- Toastmasters evaluation framework (vocal variety, pace, emphasis)
- Carmine Gallo's TED Talk analysis (500 talks studied)
- Stanford GSB communication research (Matt Abrahams)
- Obama's speechwriting principles (deliberate pause, rule of three)
- Mehrabian's 7-38-55 rule (words/tone/body)
- Neuroscience: mirror neurons, cortisol/oxytocin in speaking

TODAY'S EXERCISE: {exercise['name']}
TECHNIQUE BEING TRAINED: {exercise['technique']}
SCIENCE: {exercise['science']}

SPEAKER'S DATA:
- Duration: {analysis['duration']} seconds
- Speaking pace: {analysis['wpm']} WPM (ideal: 120–160)
- Filler words: {filler_summary}
- Strategic pauses: {analysis['strategic_pauses']} (target: 3+)
- Long pauses: {analysis['long_pauses']}
- Volume variation: {vol_var}/100 — {vol_feedback} (ideal: 15–60)
- Overall score: {analysis['overall_score']}/100

Their transcript: "{analysis['transcript']}"

COACHING FOCUS FOR THIS SESSION:
{exercise['coaching_instruction']}

Structure your feedback:
1. One genuine strength — quote a specific line from their transcript
2. How well they executed TODAY'S specific technique (be precise with the data)
3. One science-based fix they can apply in the next attempt
4. A real example from a famous speaker who mastered this technique
5. Encouraging close — make them want to try again immediately

Under 200 words. Speak directly to them. This will be read aloud by text-to-speech.
Be sophisticated, warm, and inspiring."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=320,
        temperature=0.7,
    )

    return response.choices[0].message.content


def animated_coach_message(text: str, audio_bytes: bytes | None):
    """
    Displays coach feedback with animated word-by-word text
    and a prominent play button — feels alive even with browser autoplay restrictions.
    """
    # Prominent audio player with custom styling
    if audio_bytes:
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            border: 2px solid #a855f7;
            border-radius: 16px;
            padding: 1rem 1.5rem;
            margin: 0.5rem 0;
            text-align: center;
        ">
            <p style="color:#a855f7; font-weight:700; margin:0 0 0.5rem;">
                🔊 TAP PLAY TO HEAR COACH ALEX
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.audio(audio_bytes, format="audio/mp3", autoplay=False)

    # Animated word-by-word text display
    words = text.split()
    placeholder = st.empty()
    displayed = ""
    import time
    for word in words:
        displayed += word + " "
        placeholder.markdown(
            f"<div style='"
            f"background:#1a1a2e; border-left:4px solid #a855f7; "
            f"padding:1rem 1.2rem; border-radius:0 12px 12px 0; "
            f"font-size:1.05rem; line-height:1.6; color:#e2e8f0;'>"
            f"{displayed}"
            f"<span style='color:#a855f7;'>▌</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        time.sleep(0.05)
    # Final display without cursor
    placeholder.markdown(
        f"<div style='"
        f"background:#1a1a2e; border-left:4px solid #a855f7; "
        f"padding:1rem 1.2rem; border-radius:0 12px 12px 0; "
        f"font-size:1.05rem; line-height:1.6; color:#e2e8f0;'>"
        f"{text}"
        f"</div>",
        unsafe_allow_html=True,
    )


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
        f"<p style='color:#a855f7; margin:0; font-size:0.85rem; font-weight:600;'>TODAY'S EXERCISE</p>"
        f"<h2 style='margin:0.3rem 0;'>{drill['icon']} {drill['name']}</h2>"
        f"<p style='margin:0.4rem 0; color:#a855f7; font-size:0.9rem; font-weight:600;'>"
        f"Technique: {drill['technique']}</p>"
        f"<p style='margin:0.5rem 0; font-size:0.85rem;'>🎯 <strong>Target:</strong> {drill['target_label']}</p>"
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

    if st.button("🌟 Effective Speaking Masterclass", use_container_width=True):
        st.session_state.page = "effective_speaking"
        st.session_state.chat_history = []
        st.session_state.pending_question = None
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
    """Practice page — guided script → record → targeted coaching feedback."""
    day = datetime.now().weekday()
    exercise = EXERCISES[day]

    if st.button("← Home"):
        st.session_state.page = "home"
        st.rerun()

    st.title(f"{exercise['icon']} {exercise['name']}")

    # ── Technique banner ──────────────────────────────────────────────────────
    st.markdown(
        f"<div class='drill-card'>"
        f"<p style='color:#a855f7; margin:0 0 0.3rem; font-size:0.8rem; font-weight:700;'>"
        f"TODAY'S TECHNIQUE</p>"
        f"<p style='margin:0; font-weight:600; font-size:1.05rem; color:#e2e8f0;'>"
        f"{exercise['technique']}</p>"
        f"<p style='margin:0.6rem 0 0; font-size:0.78rem; color:#94a3b8;'>"
        f"🔬 {exercise['science']}</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ── Step 1: Show the guided script ───────────────────────────────────────
    if not st.session_state.analysis:
        st.markdown("### 📖 Your Script — read this aloud")
        st.markdown(
            f"<div class='info-box' style='font-size:0.9rem; line-height:1.7; color:#cbd5e1;'>"
            f"{exercise['instruction']}"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Render the marked script with styled markers
        marked = exercise["marked_text"]
        # Style ··· pauses in purple, [MARKERS] in orange, CAPS words in bold white
        import re
        styled = marked
        styled = styled.replace("···", "<span style='color:#a855f7; font-weight:700; font-size:1.1rem;'>···</span>")
        styled = re.sub(r'\[([A-Z][^\]]*)\]', r"<span style='color:#f59e0b; font-size:0.8rem; font-weight:700;'>[\1]</span>", styled)
        styled = styled.replace("\n", "<br>")

        st.markdown(
            f"<div style='"
            f"background:#0f0f1a; border:2px solid #a855f7; border-radius:16px; "
            f"padding:1.5rem 1.8rem; margin:1rem 0; "
            f"font-size:1.05rem; line-height:2.0; color:#e2e8f0; font-family:Georgia,serif;'>"
            f"{styled}"
            f"</div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            f"<div style='text-align:center; margin:0.5rem 0 1rem; color:#94a3b8; font-size:0.82rem;'>"
            f"<span style='color:#a855f7'>···</span> = pause 1 second &nbsp;·&nbsp; "
            f"<span style='color:#f59e0b'>[SOFT/BUILD/PEAK]</span> = volume guide &nbsp;·&nbsp; "
            f"CAPS = stress this word"
            f"</div>",
            unsafe_allow_html=True,
        )

        st.markdown("### 🎙 Now deliver it:")
        st.caption("Press 🎙 to start. Recording stops automatically after 2 seconds of silence.")

        audio = mic_recorder(
            start_prompt="🎙 Start recording",
            stop_prompt="⏹ Stop recording",
            just_once=True,
            use_container_width=True,
            key=f"recorder_{st.session_state.get('audio_key', 0)}",
        )

        if audio and audio.get("bytes"):
            with st.status("🔍 Analysing your delivery...", expanded=True) as status:
                st.write("📝 Transcribing audio...")
                transcription = transcribe_audio(audio["bytes"])

                if not transcription["text"].strip():
                    st.error("No speech detected. Please try again.")
                    return

                st.write("📊 Measuring pace, pauses, volume, and filler words...")
                analysis = analyze_speech(
                    transcript=transcription["text"],
                    word_timestamps=transcription["words"],
                    duration=transcription["duration"],
                    audio_bytes=audio["bytes"],
                )

                st.write("🧠 Coach Alex is evaluating your technique...")
                feedback = get_coaching_feedback(analysis, exercise)

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
                if msg.get("audio"):
                    st.markdown("""
                    <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);
                    border:2px solid #a855f7; border-radius:16px; padding:0.8rem 1.2rem;
                    text-align:center; margin-bottom:0.5rem;">
                    <p style="color:#a855f7;font-weight:700;margin:0;">🔊 TAP PLAY TO HEAR COACH ALEX</p>
                    </div>""", unsafe_allow_html=True)
                    st.audio(msg["audio"], format="audio/mp3", autoplay=False)
                st.markdown(
                    f"<div style='background:#1a1a2e; border-left:4px solid #a855f7; "
                    f"padding:1rem 1.2rem; border-radius:0 12px 12px 0; "
                    f"font-size:1.05rem; line-height:1.6; color:#e2e8f0;'>"
                    f"{msg['text']}</div>", unsafe_allow_html=True)
        else:
            with st.chat_message("user", avatar="🧑"):
                st.markdown(msg["text"])

    # Save session once
    if not st.session_state.session_saved and st.session_state.chat_history:
        first_feedback = st.session_state.chat_history[0]["text"]
        save_session(analysis, exercise["name"], first_feedback)
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
    st.caption("Press 🎙 to start. Stops automatically after 2 seconds of silence.")

    audio = mic_recorder(
        start_prompt="🎙 Start recording",
        stop_prompt="⏹ Stop recording",
        just_once=True,
        use_container_width=True,
        key=f"pronun_{st.session_state.get('audio_key', 0)}",
    )

    if audio and audio.get("bytes") and not st.session_state.pronun_score:
        with st.status("🔍 Azure is scoring your pronunciation...", expanded=True) as status:
            st.write("🧠 Analysing phoneme by phoneme...")
            result = assess_pronunciation(
                audio_bytes=audio["bytes"],
                target_sentence=drill["sentence"],
                azure_key=st.secrets["AZURE_SPEECH_KEY"],
                azure_region=st.secrets["AZURE_SPEECH_REGION"],
            )

            if result["error"]:
                st.error(f"Assessment error: {result['error']}")
                return

            st.write("💬 Coach Alex is preparing feedback...")
            feedback_prompt = build_feedback_prompt(drill["sentence"], result, drill)
            groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
            resp = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": feedback_prompt}],
                max_tokens=220,
                temperature=0.7,
            )
            feedback_text = resp.choices[0].message.content

            st.write("🔊 Preparing Coach Alex's voice...")
            try:
                feedback_audio = speak_feedback(feedback_text)
            except Exception:
                feedback_audio = None

            st.session_state.pronun_score = {
                "result": result,
                "feedback_text": feedback_text,
                "feedback_audio": feedback_audio,
            }
            status.update(label="✅ Assessment complete!", state="complete", expanded=False)
        st.rerun()

    # ── Show results ──────────────────────────────────────────────────────────
    if st.session_state.pronun_score:
        data = st.session_state.pronun_score
        result = data["result"]
        overall = result["overall_score"]

        st.markdown("---")
        st.markdown("### 📊 Your Scores")

        # Score cards — 5 dimensions like ELSA
        color = "#22c55e" if overall >= 80 else "#f59e0b" if overall >= 60 else "#ef4444"
        col1, col2, col3, col4, col5 = st.columns(5)

        def score_card(col, label, value):
            c = "#22c55e" if value >= 80 else "#f59e0b" if value >= 60 else "#ef4444"
            col.markdown(
                f"<div class='score-card'>"
                f"<p class='score-big' style='color:{c}'>{value}</p>"
                f"<p class='score-label'>{label}</p></div>",
                unsafe_allow_html=True,
            )

        score_card(col1, "Overall", overall)
        score_card(col2, "Accuracy", result["accuracy_score"])
        score_card(col3, "Fluency", result["fluency_score"])
        score_card(col4, "Complete", result["completeness_score"])
        score_card(col5, "Prosody", result["prosody_score"])

        st.caption("Accuracy = phoneme correctness · Fluency = natural flow · Complete = all words said · Prosody = rhythm & stress")

        # Word-by-word breakdown
        st.markdown("### 🔤 Word by Word")
        if result["word_scores"]:
            cols = st.columns(min(len(result["word_scores"]), 5))
            for i, w in enumerate(result["word_scores"]):
                col = cols[i % len(cols)]
                bg = "#14532d" if w["ok"] else "#7f1d1d"
                text_color = "#86efac" if w["ok"] else "#fca5a5"
                icon = "✅" if w["ok"] else "❌"
                error_note = f"<br><small style='color:#94a3b8'>{w['error_type']}</small>" \
                             if w["error_type"] not in ("None", "", "NoError") else ""
                col.markdown(
                    f"<div style='background:{bg}; border-radius:8px; padding:8px; "
                    f"text-align:center; margin:4px;'>"
                    f"<p style='color:{text_color}; margin:0; font-weight:600; font-size:0.9rem;'>"
                    f"{icon} {w['word']}</p>"
                    f"<p style='color:#94a3b8; margin:0; font-size:0.75rem;'>{w['accuracy']}%{error_note}</p>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        # Problem phonemes for worst word
        if result["problem_words"]:
            worst = result["problem_words"][0]
            bad_phonemes = [p for p in worst["phonemes"] if not p["ok"]]
            if bad_phonemes:
                st.markdown(f"**Problem sounds in '{worst['word']}':**")
                ph_cols = st.columns(min(len(bad_phonemes), 6))
                for i, ph in enumerate(bad_phonemes):
                    ph_cols[i % len(ph_cols)].markdown(
                        f"<div style='background:#7f1d1d; border-radius:6px; padding:6px; "
                        f"text-align:center; margin:3px;'>"
                        f"<p style='color:#fca5a5; margin:0; font-size:1.1rem; font-weight:700;'>/{ph['phoneme']}/</p>"
                        f"<p style='color:#94a3b8; margin:0; font-size:0.7rem;'>{ph['score']}%</p>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

        # What was heard
        st.markdown("---")
        col1, col2 = st.columns(2)
        col1.markdown("**🎯 Target:**")
        col1.info(drill["sentence"])
        col2.markdown("**🗣 Azure heard:**")
        col2.warning(result["actual_text"] or "—")

        # Coach feedback with voice
        st.markdown("### 🎤 Coach Alex")
        with st.chat_message("assistant", avatar="🎤"):
            animated_coach_message(data["feedback_text"], data["feedback_audio"])

        # Streak
        if overall >= 70:
            st.session_state.streak += 1
            st.success(f"🔥 Streak: {st.session_state.streak} in a row! Keep going!")
        else:
            st.session_state.streak = 0

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


def page_effective_speaking():
    """
    Masterclass-style effective speaking coach.
    Covers the science and techniques of world-class communication.
    User can ask any question and get expert coaching back with voice.
    """
    if st.button("← Home"):
        st.session_state.page = "home"
        st.rerun()

    st.title("🌟 Effective Speaking Masterclass")
    st.caption("World-class communication coaching · Powered by AI")

    # ── Topic menu ─────────────────────────────────────────────────────────────
    TOPICS = {
        "🎯 How to Open a Speech Powerfully": "opening",
        "📖 Storytelling That Moves People": "storytelling",
        "💪 Building Confidence & Presence": "confidence",
        "🧠 Persuasion & Influence Science": "persuasion",
        "👁 Body Language & Eye Contact": "body_language",
        "🎭 Vocal Variety & Charisma": "vocal_variety",
        "😰 Overcoming Fear of Public Speaking": "fear",
        "🏆 Structuring Any Speech (PREP/STAR)": "structure",
        "🤝 Connecting With Any Audience": "audience",
        "💼 Speaking in Meetings & Interviews": "professional",
    }

    st.markdown("### 📚 Choose a topic or ask anything below")

    cols = st.columns(2)
    for i, (label, key) in enumerate(TOPICS.items()):
        if cols[i % 2].button(label, use_container_width=True, key=f"topic_{key}"):
            st.session_state.chat_history = []
            # Auto-ask the topic
            question = f"Teach me about: {label.split(' ', 1)[1]}"
            st.session_state.pending_question = question
            st.rerun()

    st.markdown("---")

    # ── Chat interface ─────────────────────────────────────────────────────────
    st.markdown("### 💬 Ask Coach Alex Anything")

    # Display chat history
    for msg in st.session_state.get("chat_history", []):
        if msg["role"] == "coach":
            with st.chat_message("assistant", avatar="🎤"):
                animated_coach_message(msg["text"], msg.get("audio"))
        else:
            with st.chat_message("user", avatar="🧑"):
                st.markdown(msg["text"])

    # Handle pending question from topic button
    pending = st.session_state.pop("pending_question", None)
    user_input = pending or st.chat_input(
        "Ask anything... e.g. 'How do I stop saying um?' or 'How did Obama open his speeches?'"
    )

    if user_input:
        st.session_state.chat_history.append(
            {"role": "user", "text": user_input, "audio": None}
        )

        with st.spinner("Coach Alex is thinking..."):
            client = Groq(api_key=st.secrets["GROQ_API_KEY"])

            system = """You are Coach Alex — a world-class communication coach, behavioral scientist,
and public speaking expert. You have studied and coached the greatest speakers of our time:
Obama, Jobs, Churchill, Brené Brown, Simon Sinek, Oprah, Martin Luther King Jr.

You teach the science and art of effective communication:
- Aristotle's rhetoric: ethos (credibility), pathos (emotion), logos (logic)
- Neuroscience: how stories activate mirror neurons and release oxytocin
- The Rule of Three, Power of Pause, The Hook-Story-Offer framework
- Amy Cuddy's power poses and body language research
- Albert Mehrabian's 7-38-55 rule (words/tone/body language)
- Toastmasters evaluation criteria
- TEDx talk structure and techniques
- The PREP framework (Point-Reason-Example-Point)
- The STAR method (Situation-Task-Action-Result)

Your coaching style:
- Sophisticated, inspiring, and deeply knowledgeable
- Always cite real examples from famous speakers
- Give actionable techniques with specific names
- Include the science behind WHY it works
- Warm, encouraging, never condescending
- Keep responses under 200 words — this will be spoken aloud"""

            messages = [{"role": "system", "content": system}]
            for msg in st.session_state.chat_history[:-1]:
                role = "assistant" if msg["role"] == "coach" else "user"
                messages.append({"role": role, "content": msg["text"]})
            messages.append({"role": "user", "content": user_input})

            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                max_tokens=350,
                temperature=0.7,
            )
            reply = resp.choices[0].message.content

            try:
                reply_audio = speak_feedback(reply)
            except Exception:
                reply_audio = None

        st.session_state.chat_history.append(
            {"role": "coach", "text": reply, "audio": reply_audio}
        )
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
    elif page == "effective_speaking":
        page_effective_speaking()
    else:
        st.session_state.page = "home"
        st.rerun()


if __name__ == "__main__":
    main()
