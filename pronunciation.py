"""
pronunciation.py — Azure-powered pronunciation assessment engine.

HOW IT WORKS:
─────────────
1. App shows user a target sentence
2. User records themselves saying it
3. Azure Speech SDK compares their audio against the target sentence
4. Returns phoneme-level scores for every single sound
5. Claude explains exactly what went wrong and how to fix it

WHY AZURE INSTEAD OF WHISPER:
──────────────────────────────
Whisper auto-corrects pronunciation mistakes (it guesses what you MEANT to say).
Azure Pronunciation Assessment compares what you ACTUALLY said against the target,
scoring every phoneme (individual sound) from 0-100.

This is the same technology used by ELSA Speak, Speechace, and other
professional pronunciation apps.

SCORES EXPLAINED:
─────────────────
- AccuracyScore:    How correctly each phoneme was pronounced (0-100)
- FluencyScore:     How naturally you connected words (0-100)
- CompletenessScore: Did you say all the words? (0-100)
- ProsodyScore:     Rhythm, stress, and intonation (0-100)
- OverallScore:     Weighted combination of all above
"""

import io
import json
import tempfile
import os
import wave

# Azure Speech SDK
import azure.cognitiveservices.speech as speechsdk

# ── American English pronunciation drills ─────────────────────────────────────
# Organized by difficulty and common problem areas for non-native speakers.

PRONUNCIATION_DRILLS = {
    "beginner": [
        {
            "sentence": "The weather in America is very different from other countries.",
            "targets": ["weather", "America", "different", "countries"],
            "focus": "TH sound + R sound",
            "tip": "For 'the/weather', put your tongue between your teeth. For 'very/different', make a strong R sound.",
        },
        {
            "sentence": "I would like to think about this carefully before deciding.",
            "targets": ["would", "think", "carefully", "deciding"],
            "focus": "W sound + TH sound + ending sounds",
            "tip": "Round your lips for 'would'. Tongue between teeth for 'think'.",
        },
        {
            "sentence": "Please call me when you arrive at the airport.",
            "targets": ["please", "call", "arrive", "airport"],
            "focus": "L sound + R sound",
            "tip": "For L, touch tongue to roof of mouth behind teeth. For R, curl tongue back slightly — don't touch anything.",
        },
        {
            "sentence": "My father and mother live in a comfortable neighborhood.",
            "targets": ["father", "mother", "comfortable", "neighborhood"],
            "focus": "TH sound + unstressed syllables",
            "tip": "'Comfortable' = 3 syllables: COMF-ter-ble. Don't pronounce every letter.",
        },
        {
            "sentence": "She sells seashells by the seashore every single summer.",
            "targets": ["sells", "seashells", "seashore", "single", "summer"],
            "focus": "S sound vs SH sound",
            "tip": "S: teeth together, air through center. SH: lips slightly forward, broader airflow.",
        },
    ],
    "intermediate": [
        {
            "sentence": "The entrepreneur identified three extraordinary opportunities for growth.",
            "targets": ["entrepreneur", "identified", "extraordinary", "opportunities"],
            "focus": "Multi-syllable words + stress patterns",
            "tip": "entrepreneur = on-tre-pre-NEUR. Always stress the final syllable.",
        },
        {
            "sentence": "Particularly in February, the temperature drops significantly throughout the region.",
            "targets": ["particularly", "February", "temperature", "significantly", "throughout"],
            "focus": "Commonly mispronounced words",
            "tip": "February = FEB-roo-ery. Temperature = TEM-pra-chure. Don't say every letter.",
        },
        {
            "sentence": "I thoroughly enjoy challenging myself with difficult vocabulary words.",
            "targets": ["thoroughly", "challenging", "difficult", "vocabulary"],
            "focus": "TH + complex consonant clusters",
            "tip": "thoroughly = THUR-oh-lee. The TH at the start is voiced — feel your throat vibrate.",
        },
        {
            "sentence": "The world requires both strength and vulnerability to lead effectively.",
            "targets": ["world", "requires", "strength", "vulnerability", "effectively"],
            "focus": "R-colored vowels + consonant clusters",
            "tip": "'World' is not 'word'. Feel the L before the D: wer-LD. Don't drop it.",
        },
        {
            "sentence": "Successful people consistently practice their communication skills daily.",
            "targets": ["successful", "consistently", "practice", "communication"],
            "focus": "Word stress + clear endings",
            "tip": "Don't drop word endings. 'Practice' ends with a crisp S sound.",
        },
    ],
    "advanced": [
        {
            "sentence": "The pharmaceutical representatives enthusiastically presented their revolutionary research.",
            "targets": ["pharmaceutical", "representatives", "enthusiastically", "revolutionary"],
            "focus": "Long professional vocabulary",
            "tip": "phar-ma-SEU-ti-cal. Break long words into syllables and master each part separately.",
        },
        {
            "sentence": "Simultaneously addressing multiple stakeholders requires exceptional diplomatic communication.",
            "targets": ["simultaneously", "stakeholders", "exceptional", "diplomatic"],
            "focus": "High-level business vocabulary",
            "tip": "si-mul-TAY-nee-us-lee. The TAY syllable carries the stress.",
        },
        {
            "sentence": "The quintessential American experience encompasses extraordinary diversity and contradictions.",
            "targets": ["quintessential", "encompasses", "extraordinary", "contradictions"],
            "focus": "Academic and literary vocabulary",
            "tip": "quin-te-SEN-tial. QUIN sounds like KWIN. Stress the SEN syllable.",
        },
        {
            "sentence": "Worcestershire sauce is notoriously difficult for non-native speakers to pronounce.",
            "targets": ["Worcestershire", "notoriously", "difficult", "pronounce"],
            "focus": "Silent letters + British loan words",
            "tip": "Worcestershire = WUS-ter-sheer. Most letters are silent. This trips up even native speakers!",
        },
    ],
}


def assess_pronunciation(audio_bytes: bytes, target_sentence: str,
                         azure_key: str, azure_region: str) -> dict:
    """
    Uses Azure Cognitive Services to assess pronunciation against a target sentence.

    Returns detailed scores:
    - overall_score: weighted average of all dimensions
    - accuracy_score: phoneme-level correctness
    - fluency_score: natural connected speech
    - completeness_score: did you say all words?
    - prosody_score: rhythm, stress, intonation
    - word_scores: per-word breakdown with phoneme details
    - problem_words: words that scored below 70
    """

    # Write audio to a temp WAV file — Azure SDK reads from file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        # ── Configure Azure Speech ────────────────────────────────────────────
        speech_config = speechsdk.SpeechConfig(
            subscription=azure_key,
            region=azure_region,
        )
        speech_config.speech_recognition_language = "en-US"

        audio_config = speechsdk.audio.AudioConfig(filename=tmp_path)

        # ── Configure Pronunciation Assessment ───────────────────────────────
        # GradingSystem: HundredMark = scores from 0-100
        # Granularity: Phoneme = score every individual sound
        # EnableMiscue: True = flag words that were added/omitted/substituted
        pronun_config = speechsdk.PronunciationAssessmentConfig(
            reference_text=target_sentence,
            grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
            granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
            enable_miscue=True,
        )
        pronun_config.enable_prosody_assessment()

        # ── Run assessment ────────────────────────────────────────────────────
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config,
        )
        pronun_config.apply_to(recognizer)

        result = recognizer.recognize_once()

        if result.reason != speechsdk.ResultReason.RecognizedSpeech:
            return _fallback_result("Speech not recognized. Please speak clearly and try again.")

        # ── Parse results ─────────────────────────────────────────────────────
        pronun_result = speechsdk.PronunciationAssessmentResult(result)

        # Overall scores
        overall = round(pronun_result.pronunciation_score or 0)
        accuracy = round(pronun_result.accuracy_score or 0)
        fluency = round(pronun_result.fluency_score or 0)
        completeness = round(pronun_result.completeness_score or 0)
        prosody = round(getattr(pronun_result, "prosody_score", 0) or 0)

        # Word-level breakdown
        word_scores = []
        problem_words = []

        for word in pronun_result.words:
            word_accuracy = round(word.accuracy_score or 0)
            error_type = str(word.error_type) if word.error_type else "None"

            # Get phoneme scores for this word
            phonemes = []
            if hasattr(word, "phonemes") and word.phonemes:
                for ph in word.phonemes:
                    ph_score = round(ph.accuracy_score or 0)
                    phonemes.append({
                        "phoneme": ph.phoneme,
                        "score": ph_score,
                        "ok": ph_score >= 60,
                    })

            word_data = {
                "word": word.word,
                "accuracy": word_accuracy,
                "error_type": error_type,
                "phonemes": phonemes,
                "ok": word_accuracy >= 70 and error_type in ("None", ""),
            }
            word_scores.append(word_data)

            if not word_data["ok"]:
                problem_words.append(word_data)

        # What the user actually said
        actual_text = result.text

        return {
            "overall_score":       overall,
            "accuracy_score":      accuracy,
            "fluency_score":       fluency,
            "completeness_score":  completeness,
            "prosody_score":       prosody,
            "word_scores":         word_scores,
            "problem_words":       problem_words,
            "actual_text":         actual_text,
            "error":               None,
        }

    except Exception as e:
        return _fallback_result(str(e))

    finally:
        os.unlink(tmp_path)


def _fallback_result(error_msg: str) -> dict:
    """Returns a safe empty result when Azure assessment fails."""
    return {
        "overall_score":      0,
        "accuracy_score":     0,
        "fluency_score":      0,
        "completeness_score": 0,
        "prosody_score":      0,
        "word_scores":        [],
        "problem_words":      [],
        "actual_text":        "",
        "error":              error_msg,
    }


def build_feedback_prompt(target: str, result: dict, drill: dict) -> str:
    """
    Builds a coaching prompt for LLaMA based on Azure's detailed scores.
    Includes phoneme-level detail for problem words.
    """
    problem_detail = []
    for w in result["problem_words"][:4]:
        bad_phonemes = [p["phoneme"] for p in w["phonemes"] if not p["ok"]]
        phoneme_str = f" (problem sounds: {', '.join(bad_phonemes)})" if bad_phonemes else ""
        error = f" [{w['error_type']}]" if w["error_type"] not in ("None", "") else ""
        problem_detail.append(f'"{w["word"]}" scored {w["accuracy"]}%{phoneme_str}{error}')

    problems = "\n".join(problem_detail) if problem_detail else "All words pronounced clearly!"

    return f"""You are Coach Alex, a warm American English pronunciation coach.

The speaker just attempted: "{target}"
Azure pronunciation assessment results:
- Overall: {result['overall_score']}/100
- Accuracy: {result['accuracy_score']}/100 (phoneme correctness)
- Fluency: {result['fluency_score']}/100 (natural flow)
- Completeness: {result['completeness_score']}/100 (all words said)
- Prosody: {result['prosody_score']}/100 (rhythm & stress)

Problem words:
{problems}

Drill focus: {drill['focus']}
Pronunciation tip: {drill['tip']}

Give specific coaching in under 120 words:
1. Acknowledge their score warmly
2. Focus on their #1 problem word — explain exactly where to put their tongue/lips
3. Give one actionable drill to fix it right now
4. End with encouragement

Speak directly to them. This will be read aloud."""
