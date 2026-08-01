"""
pronunciation.py — Pronunciation scoring engine.

HOW IT WORKS:
─────────────
1. App shows user a target sentence
2. User records themselves saying it
3. Whisper transcribes what they ACTUALLY said
4. We compare word-by-word: expected vs actual
5. Claude explains the pronunciation mistakes and how to fix them

This approach works because:
- If you say "world" but Whisper hears "word" → you dropped the L sound
- If you say "comfortable" but Whisper hears "comftable" → syllable reduction
- If you say "this" but Whisper hears "dis" → TH sound issue (common for many accents)

It's not as precise as ELSA's phoneme model but catches real pronunciation
patterns that need work.
"""

import difflib


# ── American English pronunciation drills ─────────────────────────────────────
# Organized by difficulty and common problem areas for non-native speakers.
# Each drill targets specific sounds or patterns.

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
            "sentence": "She sells seashells by the seashore every single summer.",
            "targets": ["sells", "seashells", "seashore", "single", "summer"],
            "focus": "S sound vs SH sound",
            "tip": "S: teeth together, air through center. SH: lips forward, air through sides.",
        },
        {
            "sentence": "Please call me when you arrive at the airport.",
            "targets": ["please", "call", "arrive", "airport"],
            "focus": "L sound + R sound",
            "tip": "For L, touch tongue to roof of mouth. For R, curl tongue back slightly.",
        },
        {
            "sentence": "My father and mother live in a comfortable neighborhood.",
            "targets": ["father", "mother", "comfortable", "neighborhood"],
            "focus": "TH sound + unstressed syllables",
            "tip": "'Comfortable' = 3 syllables: COMF-ter-ble. Don't say every letter.",
        },
    ],
    "intermediate": [
        {
            "sentence": "The entrepreneur identified three extraordinary opportunities for growth.",
            "targets": ["entrepreneur", "identified", "extraordinary", "opportunities"],
            "focus": "Multi-syllable words + stress patterns",
            "tip": "entrepreneur = on-tre-pre-NEUR. Stress the last syllable.",
        },
        {
            "sentence": "Particularly in February, the temperature drops significantly throughout the region.",
            "targets": ["particularly", "February", "temperature", "significantly", "throughout"],
            "focus": "Commonly mispronounced words",
            "tip": "February = FEB-roo-ery (not Feb-you-ary). Temperature = TEM-pra-chure.",
        },
        {
            "sentence": "I thoroughly enjoy challenging myself with difficult vocabulary words.",
            "targets": ["thoroughly", "challenging", "difficult", "vocabulary"],
            "focus": "TH + complex consonant clusters",
            "tip": "thoroughly = THUR-oh-lee. Don't skip the TH at the start.",
        },
        {
            "sentence": "The world requires both strength and vulnerability to lead effectively.",
            "targets": ["world", "requires", "strength", "vulnerability", "effectively"],
            "focus": "R-colored vowels + consonant clusters",
            "tip": "'World' = not 'word'. Feel the L before the D: wer-LD.",
        },
        {
            "sentence": "Successful people consistently practice their communication skills.",
            "targets": ["successful", "consistently", "practice", "communication"],
            "focus": "Word stress + clear endings",
            "tip": "Don't drop word endings. 'Practice' ends in a clear S sound.",
        },
    ],
    "advanced": [
        {
            "sentence": "The pharmaceutical representatives enthusiastically presented their revolutionary research.",
            "targets": ["pharmaceutical", "representatives", "enthusiastically", "revolutionary"],
            "focus": "Long professional vocabulary",
            "tip": "phar-ma-SEU-ti-cal. Break long words into syllables and practice each part.",
        },
        {
            "sentence": "Simultaneously addressing multiple stakeholders requires exceptional diplomatic communication.",
            "targets": ["simultaneously", "stakeholders", "exceptional", "diplomatic"],
            "focus": "High-level business vocabulary",
            "tip": "si-mul-TAY-nee-us-lee. Stress the TAY syllable.",
        },
        {
            "sentence": "The quintessential American experience encompasses extraordinary diversity and contradictions.",
            "targets": ["quintessential", "encompasses", "extraordinary", "contradictions"],
            "focus": "Academic and literary vocabulary",
            "tip": "quin-te-SEN-tial. The QUIN sounds like KWIN.",
        },
    ],
}

# ── Common pronunciation patterns by accent background ─────────────────────────
# What speakers with certain first languages typically struggle with in American English.
COMMON_ISSUES = {
    "TH sounds": {
        "problem": "Saying 'D' or 'T' instead of TH",
        "examples": ["the→de", "this→dis", "three→tree", "think→tink"],
        "fix": "Touch the tip of your tongue lightly to the back of your upper front teeth. Let air flow through.",
    },
    "R sounds": {
        "problem": "Rolling R or dropping R entirely",
        "examples": ["right→light", "very→vely", "world→wold"],
        "fix": "Curl your tongue back slightly. Don't touch the roof of your mouth. Tighten the back of your tongue.",
    },
    "L sounds": {
        "problem": "Substituting R for L or dropping L",
        "examples": ["light→right", "call→car", "world→word"],
        "fix": "Touch the tip of your tongue firmly to the ridge just behind your upper front teeth.",
    },
    "V vs B": {
        "problem": "Saying B instead of V",
        "examples": ["very→berry", "vote→boat", "video→bideo"],
        "fix": "For V, your upper teeth touch your lower lip. For B, both lips press together.",
    },
    "Word endings": {
        "problem": "Dropping final consonants",
        "examples": ["fact→fac", "test→tes", "world→wor"],
        "fix": "Americans pronounce final consonants clearly. Practice stopping the airflow for final T, D, K sounds.",
    },
}


def score_pronunciation(expected: str, actual: str) -> dict:
    """
    Compares expected sentence with what Whisper transcribed.
    Returns word-by-word scoring and overall accuracy.

    Uses difflib SequenceMatcher to align words and find differences.
    """
    # Normalize: lowercase, remove punctuation
    def clean(text):
        import re
        return re.sub(r"[^\w\s]", "", text.lower()).split()

    expected_words = clean(expected)
    actual_words = clean(actual)

    # Use SequenceMatcher to align expected vs actual words
    matcher = difflib.SequenceMatcher(None, expected_words, actual_words)
    blocks = matcher.get_matching_blocks()

    # Build word-level results
    word_results = []
    matched = set()
    actual_matched = set()

    for block in blocks:
        i, j, n = block
        for k in range(n):
            word_results.append({
                "expected": expected_words[i + k],
                "actual": actual_words[j + k],
                "correct": True,
            })
            matched.add(i + k)
            actual_matched.add(j + k)

    # Find missed/wrong words
    for i, word in enumerate(expected_words):
        if i not in matched:
            # Find closest match in actual
            close = difflib.get_close_matches(word, actual_words, n=1, cutoff=0.6)
            word_results.append({
                "expected": word,
                "actual": close[0] if close else "—",
                "correct": False,
            })

    # Sort by expected word order
    word_results.sort(key=lambda x: expected_words.index(x["expected"])
                      if x["expected"] in expected_words else 999)

    # Calculate accuracy
    correct_count = sum(1 for w in word_results if w["correct"])
    total = len(expected_words)
    accuracy = round((correct_count / total) * 100) if total > 0 else 0

    # Identify problem words
    problem_words = [w["expected"] for w in word_results if not w["correct"]]

    return {
        "accuracy":      accuracy,
        "word_results":  word_results,
        "problem_words": problem_words,
        "correct_count": correct_count,
        "total_words":   total,
    }


def get_pronunciation_feedback(expected: str, actual: str,
                               score: dict, drill: dict) -> str:
    """
    Asks Claude/LLaMA to explain pronunciation mistakes and give specific tips.
    Returns coaching text to be spoken aloud.
    """
    if score["problem_words"]:
        problems = ", ".join(f'"{w}"' for w in score["problem_words"][:5])
        problem_text = f"These words were unclear or mispronounced: {problems}"
    else:
        problem_text = "All words were recognized correctly!"

    return f"""TARGET: "{expected}"
WHAT WAS HEARD: "{actual}"
ACCURACY: {score['accuracy']}%
FOCUS AREA: {drill['focus']}
PRONUNCIATION TIP: {drill['tip']}
ISSUES: {problem_text}

Give warm, specific American English pronunciation coaching in under 100 words.
Reference the specific words that were wrong. Explain the mouth/tongue position needed.
Be encouraging. This will be spoken aloud."""
