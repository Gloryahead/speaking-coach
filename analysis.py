"""
analysis.py — Speech analysis functions.

Takes a transcript + word timestamps from Groq Whisper + raw audio bytes and extracts:
  - Words per minute (WPM)
  - Filler words (um, uh, like, you know, etc.)
  - Pauses (strategic vs too long) from word timestamps
  - Volume variation (loud vs quiet sections) from audio waveform
  - Overall score (composite of above)
"""

import io
import struct
import wave

import numpy as np

# ── Filler words to detect ────────────────────────────────────────────────────
FILLER_WORDS = [
    "um", "uh", "er", "ah",
    "like", "basically", "literally", "actually",
    "right", "so", "well", "okay",
    "you know", "i mean", "kind of", "sort of",
]


def detect_fillers(transcript: str) -> dict:
    """Counts filler words in the transcript."""
    text = transcript.lower()
    words = text.split()
    found = {}

    for filler in FILLER_WORDS:
        if " " in filler:
            count = text.count(filler)
        else:
            count = words.count(filler)
        if count > 0:
            found[filler] = count

    return found


def calculate_wpm(word_timestamps: list, duration: float, word_count: int) -> int:
    """
    Calculates words per minute.
    Uses word timestamps if available, falls back to total duration.
    Ideal range: 120–160 WPM for public speaking.
    """
    if word_timestamps and len(word_timestamps) >= 2:
        start = word_timestamps[0].get("start", 0)
        end = word_timestamps[-1].get("end", 0)
        duration_minutes = (end - start) / 60
        if duration_minutes > 0:
            return round(len(word_timestamps) / duration_minutes)

    # Fallback: use total duration
    if duration and duration > 0:
        return round(word_count / (duration / 60))

    return 0


def detect_pauses(word_timestamps: list) -> list:
    """
    Detects pauses between words using timestamp gaps.

    Pause types:
      - strategic 0.5–2.5s  (good — shows confidence and lets ideas land)
      - too_long  > 2.5s    (loses the audience)
    """
    pauses = []

    for i in range(1, len(word_timestamps)):
        prev = word_timestamps[i - 1]
        curr = word_timestamps[i]
        gap = curr.get("start", 0) - prev.get("end", 0)

        if gap >= 0.5:
            pause_type = "strategic" if gap <= 2.5 else "too_long"
            pauses.append({
                "duration": round(gap, 2),
                "after_word": prev.get("word", "").strip(),
                "before_word": curr.get("word", "").strip(),
                "type": pause_type,
            })

    return pauses


def analyze_volume(audio_bytes: bytes) -> dict:
    """
    Analyzes volume variation from the raw audio waveform.

    Reads the WAV audio, splits it into chunks, and measures amplitude.
    Returns:
      - avg_volume: overall loudness (0–100 scale)
      - volume_variation: how much volume changes (higher = more expressive)
      - peak_volume: loudest moment
      - quiet_sections: number of very quiet stretches (may indicate mumbling)
    """
    try:
        with wave.open(io.BytesIO(audio_bytes), 'rb') as wav:
            n_channels = wav.getnchannels()
            sampwidth = wav.getsampwidth()
            n_frames = wav.getnframes()
            raw_data = wav.readframes(n_frames)

        # Convert raw bytes to numpy array of samples
        if sampwidth == 2:
            samples = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32)
        elif sampwidth == 1:
            samples = np.frombuffer(raw_data, dtype=np.uint8).astype(np.float32) - 128
        else:
            return _default_volume()

        # If stereo, take one channel
        if n_channels == 2:
            samples = samples[::2]

        if len(samples) == 0:
            return _default_volume()

        # Normalize to 0–1
        max_val = 32768.0 if sampwidth == 2 else 128.0
        samples = np.abs(samples) / max_val

        # Split into 0.5-second chunks and measure RMS per chunk
        chunk_size = max(1, len(samples) // 20)
        chunks = [samples[i:i+chunk_size] for i in range(0, len(samples), chunk_size)]
        rms_values = [float(np.sqrt(np.mean(c**2))) for c in chunks if len(c) > 0]

        if not rms_values:
            return _default_volume()

        avg_rms = float(np.mean(rms_values))
        std_rms = float(np.std(rms_values))
        peak_rms = float(np.max(rms_values))

        # Scale to 0–100 for display
        avg_volume = min(100, round(avg_rms * 300))
        variation = min(100, round(std_rms * 500))
        peak = min(100, round(peak_rms * 300))
        quiet_sections = sum(1 for r in rms_values if r < avg_rms * 0.3)

        return {
            "avg_volume":      avg_volume,
            "volume_variation": variation,
            "peak_volume":     peak,
            "quiet_sections":  quiet_sections,
        }

    except Exception:
        return _default_volume()


def _default_volume() -> dict:
    """Returns neutral volume stats when audio can't be parsed."""
    return {
        "avg_volume":       50,
        "volume_variation": 20,
        "peak_volume":      60,
        "quiet_sections":   0,
    }


def score_speech(wpm: int, filler_total: int, strategic_pauses: int,
                 long_pauses: int, volume_variation: int) -> dict:
    """
    Calculates sub-scores and an overall score out of 100.
    """
    # WPM score — ideal 120–160
    ideal_wpm = 140
    wpm_score = max(0, 100 - abs(wpm - ideal_wpm) * 1.5) if wpm > 0 else 50

    # Filler score — starts at 100, -10 per filler
    filler_score = max(0, 100 - filler_total * 10)

    # Pause score — reward strategic pauses, penalise too-long ones
    pause_score = min(100, strategic_pauses * 20) - (long_pauses * 15)
    pause_score = max(0, pause_score)

    # Volume score — variation between 15–60 is ideal (expressive but not erratic)
    if 15 <= volume_variation <= 60:
        volume_score = 100
    elif volume_variation < 15:
        volume_score = max(0, 60 + volume_variation * 2)   # too monotone
    else:
        volume_score = max(0, 100 - (volume_variation - 60) * 2)  # too erratic

    # Weighted overall
    overall = (
        wpm_score    * 0.30 +
        filler_score * 0.35 +
        pause_score  * 0.20 +
        volume_score * 0.15
    )

    return {
        "wpm_score":    round(wpm_score),
        "filler_score": round(filler_score),
        "pause_score":  round(pause_score),
        "volume_score": round(volume_score),
        "overall":      round(overall),
    }


def analyze_speech(transcript: str, word_timestamps: list,
                   duration: float, audio_bytes: bytes = b"") -> dict:
    """
    Master analysis function — runs all checks and returns a complete report.
    """
    fillers = detect_fillers(transcript)
    filler_total = sum(fillers.values())

    word_count = len(transcript.split())
    wpm = calculate_wpm(word_timestamps, duration, word_count)

    pauses = detect_pauses(word_timestamps)
    strategic_pauses = [p for p in pauses if p["type"] == "strategic"]
    long_pauses = [p for p in pauses if p["type"] == "too_long"]

    volume = analyze_volume(audio_bytes) if audio_bytes else _default_volume()

    scores = score_speech(
        wpm, filler_total,
        len(strategic_pauses), len(long_pauses),
        volume["volume_variation"],
    )

    return {
        "transcript":        transcript,
        "word_count":        word_count,
        "duration":          round(duration, 1),
        "wpm":               wpm,
        "fillers":           fillers,
        "filler_total":      filler_total,
        "pauses":            pauses,
        "strategic_pauses":  len(strategic_pauses),
        "long_pauses":       len(long_pauses),
        "pause_details":     strategic_pauses[:5],  # top 5 for display
        "volume":            volume,
        "overall_score":     scores["overall"],
        "wpm_score":         scores["wpm_score"],
        "filler_score":      scores["filler_score"],
        "pause_score":       scores["pause_score"],
        "volume_score":      scores["volume_score"],
    }
