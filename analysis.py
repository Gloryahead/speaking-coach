"""
analysis.py — Speech analysis functions.

Takes a transcript + word timestamps from Groq Whisper and extracts:
  - Words per minute (WPM)
  - Filler words (um, uh, like, you know, etc.)
  - Pauses (strategic vs too long)
  - Overall score (composite of above)
"""

# ── Filler words to detect ────────────────────────────────────────────────────
# These are the most common spoken filler words in English.
# We check single words AND multi-word phrases (e.g. "you know").
FILLER_WORDS = [
    "um", "uh", "er", "ah",
    "like", "basically", "literally", "actually",
    "right", "so", "well", "okay",
    "you know", "i mean", "kind of", "sort of",
]


def detect_fillers(transcript: str) -> dict:
    """
    Counts filler words in the transcript.
    Returns a dict like: {"um": 3, "like": 5, "you know": 2}
    """
    text = transcript.lower()
    words = text.split()
    found = {}

    for filler in FILLER_WORDS:
        if " " in filler:
            # Multi-word filler — search in full text
            count = text.count(filler)
        else:
            # Single word — count exact matches
            count = words.count(filler)

        if count > 0:
            found[filler] = count

    return found


def calculate_wpm(word_timestamps: list) -> int:
    """
    Calculates words per minute from Whisper word-level timestamps.
    Ideal range: 120–160 WPM for public speaking.
    """
    if not word_timestamps or len(word_timestamps) < 2:
        return 0

    start = word_timestamps[0].get("start", 0)
    end = word_timestamps[-1].get("end", 0)
    duration_minutes = (end - start) / 60

    if duration_minutes <= 0:
        return 0

    return round(len(word_timestamps) / duration_minutes)


def detect_pauses(word_timestamps: list) -> list:
    """
    Detects pauses between words using timestamp gaps.

    Pause types:
      - natural   < 0.5s  (normal word gap, not a pause)
      - strategic 0.5–2s  (good! shows confidence)
      - too_long  > 2s    (loses the audience)
    """
    pauses = []

    for i in range(1, len(word_timestamps)):
        prev = word_timestamps[i - 1]
        curr = word_timestamps[i]
        gap = curr.get("start", 0) - prev.get("end", 0)

        if gap >= 0.5:
            pause_type = "strategic" if gap <= 2.0 else "too_long"
            pauses.append({
                "duration": round(gap, 2),
                "after_word": prev.get("word", "").strip(),
                "before_word": curr.get("word", "").strip(),
                "type": pause_type,
            })

    return pauses


def score_speech(wpm: int, filler_total: int, strategic_pauses: int, long_pauses: int) -> dict:
    """
    Calculates sub-scores and an overall score out of 100.

    Scoring logic:
      WPM score:    100 if 120–160 WPM, drops by 2 per WPM away from ideal
      Filler score: starts at 100, -10 per filler word
      Pause score:  +20 per strategic pause (max 100), -15 per long pause
    """
    # WPM score — ideal range 120–160
    ideal_wpm = 140
    wpm_score = max(0, 100 - abs(wpm - ideal_wpm) * 1.5) if wpm > 0 else 0

    # Filler score
    filler_score = max(0, 100 - filler_total * 10)

    # Pause score
    pause_score = min(100, strategic_pauses * 20) - (long_pauses * 15)
    pause_score = max(0, pause_score)

    # Weighted overall score
    overall = (wpm_score * 0.35) + (filler_score * 0.40) + (pause_score * 0.25)

    return {
        "wpm_score":    round(wpm_score),
        "filler_score": round(filler_score),
        "pause_score":  round(pause_score),
        "overall":      round(overall),
    }


def analyze_speech(transcript: str, word_timestamps: list, duration: float) -> dict:
    """
    Master analysis function — runs all checks and returns a complete report.
    This is what the app calls after Whisper transcribes the audio.
    """
    fillers = detect_fillers(transcript)
    filler_total = sum(fillers.values())

    wpm = calculate_wpm(word_timestamps)

    pauses = detect_pauses(word_timestamps)
    strategic_pauses = [p for p in pauses if p["type"] == "strategic"]
    long_pauses = [p for p in pauses if p["type"] == "too_long"]

    scores = score_speech(wpm, filler_total, len(strategic_pauses), len(long_pauses))

    return {
        "transcript":       transcript,
        "word_count":       len(transcript.split()),
        "duration":         round(duration, 1),
        "wpm":              wpm,
        "fillers":          fillers,
        "filler_total":     filler_total,
        "pauses":           pauses,
        "strategic_pauses": len(strategic_pauses),
        "long_pauses":      len(long_pauses),
        "overall_score":    scores["overall"],
        "wpm_score":        scores["wpm_score"],
        "filler_score":     scores["filler_score"],
        "pause_score":      scores["pause_score"],
    }
