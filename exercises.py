"""
exercises.py — Research-backed guided speech scripts.

Each exercise gives the user an ACTUAL passage to deliver — not a free topic.
The script is engineered to train one specific technique, with visual markers
showing exactly where to pause, emphasize, or change volume.

RESEARCH SOURCES:
- Toastmasters International communication curriculum
- Stanford GSB "Communicating as a Leader" (Matt Abrahams)
- Albert Mehrabian's 7-38-55 rule (words / tone / body language)
- Carmine Gallo: "Talk Like TED" — analysis of 500 TED talks
- Nick Morgan: "Power Cues" — neuroscience of speaker credibility
- Amy Cuddy: presence and vocal confidence research
- Celeste Headlee: "We Need to Talk" — listening and pacing
- Toastmasters CC manual: vocal variety, pause, emphasis
- Obama speechwriting principles (Jon Favreau interviews)
- Winston Churchill: "never use a long word where a short one will do"

HOW THE MARKERS WORK:
  ···     = pause here (hold for 1 full second)
  [SOFT]  = drop your volume — draw them in
  [BUILD] = gradually raise energy and volume
  [PEAK]  = full power — your most important idea
  CAPS    = stress / emphasise this word
  (...)   = slightly slower here — savour it

The plain_text version is what the coach uses for analysis reference.
The marked_text version is what the user sees on screen.
"""


EXERCISES = {
    0: {  # Monday
        "name": "Pace Control",
        "icon": "⏱",
        "technique": "Speaking at 120–140 WPM — the speed of trust",
        "science": (
            "Stanford communication research shows 130 WPM is the optimal rate: "
            "fast enough to sound confident, slow enough for full comprehension. "
            "Most anxious speakers race above 180 WPM — losing 40% of their message."
        ),
        "instruction": (
            "Read this passage aloud at a RELAXED, steady pace. "
            "Imagine you are explaining something important to a close friend — "
            "not rushing, not dragging. Every word is clear and deliberate."
        ),
        "marked_text": """\
Most people speak too fast when they are nervous.
Their words blur together.
Their message gets lost.

The best speakers do the OPPOSITE.
They slow down ··· deliberately.
They treat each word ··· as important.

Today, speak these words at a comfortable, steady pace.
Imagine you are speaking to someone you care about.
Not rushing. ··· Not dragging.
Just ··· clear.""",
        "plain_text": (
            "Most people speak too fast when they are nervous. "
            "Their words blur together. Their message gets lost. "
            "The best speakers do the opposite. They slow down deliberately. "
            "They treat each word as important. "
            "Today, speak these words at a comfortable, steady pace. "
            "Imagine you are speaking to someone you care about. "
            "Not rushing. Not dragging. Just clear."
        ),
        "target_metric": "wpm",
        "target_range": (120, 160),
        "target_label": "120–140 WPM",
        "coaching_instruction": (
            "Focus your feedback specifically on their speaking pace (WPM). "
            "Was it in the ideal 120-140 WPM range? If too fast, explain how to physically slow down. "
            "If too slow, help them add energy. Reference their actual WPM number."
        ),
    },

    1: {  # Tuesday
        "name": "Silence Over Fillers",
        "icon": "🚫",
        "technique": "Replacing 'um' and 'uh' with powerful silence",
        "science": (
            "Princeton neuroscience research: listeners perceive filler words as signals of low confidence. "
            "A deliberate pause, however, increases perceived authority and gives the audience's "
            "brain time to process your last idea — making you more persuasive."
        ),
        "instruction": (
            "Read this passage aloud. Every time you see ···, STOP completely. "
            "Do NOT fill the gap with 'um' or 'uh'. "
            "Count silently to one. Then continue. The silence is the point."
        ),
        "marked_text": """\
Every 'um' you say ··· tells your audience something.
It tells them you are searching for words.
It tells them ··· you are not sure.
It breaks ··· your authority.

The cure is simple ··· but hard.
When you feel an 'um' coming ··· stop.
Breathe. ···
Let the silence sit. ···
Then continue.

Silence, unlike 'um,' tells your audience something DIFFERENT.
It says: ··· I am thinking.
I am in CONTROL.
I know exactly ··· where I am going.""",
        "plain_text": (
            "Every um you say tells your audience something. "
            "It tells them you are searching for words. "
            "It tells them you are not sure. It breaks your authority. "
            "The cure is simple but hard. "
            "When you feel an um coming, stop. Breathe. Let the silence sit. Then continue. "
            "Silence, unlike um, tells your audience something different. "
            "It says: I am thinking. I am in control. I know exactly where I am going."
        ),
        "target_metric": "filler_total",
        "target_range": (0, 2),
        "target_label": "0–2 filler words",
        "coaching_instruction": (
            "Focus your feedback on their filler word count. "
            "If they used fillers, name the exact words and count. Teach them the physical replacement: "
            "jaw drops open, breath in, silence — then continue. Be specific and encouraging."
        ),
    },

    2: {  # Wednesday
        "name": "Power Pause",
        "icon": "⏸",
        "technique": "Strategic pausing after key ideas — Obama's signature technique",
        "science": (
            "Analysis of Obama's 2008 inaugural address found 47 deliberate pauses in 18 minutes. "
            "Each pause averaged 1.2 seconds. EEG studies show that audience brain activity "
            "spikes during a speaker's pause — this is when ideas are encoded into memory."
        ),
        "instruction": (
            "Read this passage aloud. PAUSE for a full second at every ··· marker. "
            "Do not rush past the pauses — they are the most important part of this exercise. "
            "Let the silence do the work."
        ),
        "marked_text": """\
There is one technique ···
that separates good speakers from great ones.

It is not a louder voice. ···
It is not bigger gestures. ···

It is the pause.

When Obama spoke ··· he didn't rush through his words.
He stopped. ···
He breathed. ···
He let his ideas reach ··· all the way to the back of the room. ···

Today ···
pause after every key sentence.
Make your audience ··· wait for you.
Because the words that follow a pause ···
are the words they will remember.""",
        "plain_text": (
            "There is one technique that separates good speakers from great ones. "
            "It is not a louder voice. It is not bigger gestures. It is the pause. "
            "When Obama spoke, he didn't rush through his words. "
            "He stopped. He breathed. He let his ideas reach all the way to the back of the room. "
            "Today, pause after every key sentence. Make your audience wait for you. "
            "Because the words that follow a pause are the words they will remember."
        ),
        "target_metric": "strategic_pauses",
        "target_range": (4, 99),
        "target_label": "4+ strategic pauses",
        "coaching_instruction": (
            "Focus your feedback on the number of strategic pauses detected. "
            "The target is 4+ pauses of 0.5–2 seconds. "
            "Tell them which pause moments had the most impact based on where they appeared in the transcript. "
            "If they didn't pause enough, explain how it felt rushed."
        ),
    },

    3: {  # Thursday
        "name": "Vocal Dynamics",
        "icon": "🔥",
        "technique": "Volume arc — soft → build → peak → settle",
        "science": (
            "Mehrabian's research: 38% of your message is conveyed through vocal tone alone. "
            "Carmine Gallo's analysis of the most-watched TED talks found all top speakers "
            "used at least 3 distinct volume levels within each 2-minute segment — "
            "creating an emotional journey that keeps audiences riveted."
        ),
        "instruction": (
            "This passage has a volume arc. Follow the [SOFT], [BUILD], and [PEAK] markers. "
            "[SOFT] = almost a whisper, draw them in. "
            "[BUILD] = gradually raise energy. "
            "[PEAK] = full power, your most important words. "
            "Let your voice be an instrument."
        ),
        "marked_text": """\
[SOFT] Lean in. I want to tell you something important.

Your voice ··· is the most powerful instrument you possess.

[BUILD] More powerful than any slide deck.
More powerful than any statistic.
More powerful than any prop or visual aid.

[PEAK] YOUR VOICE CAN MOVE PEOPLE TO TEARS.
It can inspire action.
It can change a room.

[SOFT] And the secret ··· is not to always be loud.

The secret ···
is to know when to be quiet ···
and when ···
to be HEARD.""",
        "plain_text": (
            "Lean in. I want to tell you something important. "
            "Your voice is the most powerful instrument you possess. "
            "More powerful than any slide deck. "
            "More powerful than any statistic. "
            "More powerful than any prop or visual aid. "
            "Your voice can move people to tears. It can inspire action. It can change a room. "
            "And the secret is not to always be loud. "
            "The secret is to know when to be quiet and when to be heard."
        ),
        "target_metric": "volume_variation",
        "target_range": (20, 99),
        "target_label": "Volume variation > 20",
        "coaching_instruction": (
            "Focus your feedback on their vocal dynamics and volume variation score. "
            "Did their volume change throughout the passage? Ideal variation is 20–60. "
            "If monotone, explain how a soft opening followed by a powerful peak creates emotional engagement. "
            "Reference their specific variation score."
        ),
    },

    4: {  # Friday
        "name": "Word Emphasis",
        "icon": "💡",
        "technique": "Stressing the RIGHT words — how emphasis shapes meaning",
        "science": (
            "Linguist Peter Ladefoged's research: emphasis on different words in the same sentence "
            "can produce 7 completely different meanings. Top speakers choose one key word per "
            "sentence to stress — preventing 'emphatic monotony' where everything sounds equally important "
            "(and therefore nothing stands out)."
        ),
        "instruction": (
            "Read this passage aloud. CAPITALIZE words mean: hit that word harder than the rest. "
            "Stress it. Stretch it slightly. Drop your pitch slightly after it. "
            "Let everything else in the sentence flow underneath — "
            "only the stressed word should stand out."
        ),
        "marked_text": """\
NOT every word deserves equal weight.
SOME words carry the meaning.
THOSE are the ones you stress.

Watch what a single shift does:

'I never said SHE stole the money.'
'I NEVER said she stole the money.'
'I never SAID she stole the money.'

Same words. ···
Different EMPHASIS. ···
Completely different MEANING.

Today: find the ONE most important word in each sentence.
Stress ONLY that word.
Let everything else ··· breathe.""",
        "plain_text": (
            "Not every word deserves equal weight. "
            "Some words carry the meaning. Those are the ones you stress. "
            "Watch what a single shift does: "
            "I never said she stole the money. I never said she stole the money. I never said she stole the money. "
            "Same words. Different emphasis. Completely different meaning. "
            "Today: find the one most important word in each sentence. "
            "Stress only that word. Let everything else breathe."
        ),
        "target_metric": "overall_score",
        "target_range": (60, 99),
        "target_label": "Clear, confident delivery",
        "coaching_instruction": (
            "Focus your feedback on how their emphasis landed. "
            "Did they stress key words or did everything sound flat and equal? "
            "Listen for whether the three repeated sentences sounded meaningfully different. "
            "Give them one technique: slow down on the stressed word AND raise pitch slightly."
        ),
    },

    5: {  # Saturday
        "name": "Storytelling Arc",
        "icon": "📖",
        "technique": "Situation → Complication → Resolution — the universal story structure",
        "science": (
            "Neuroscientist Uri Hasson (Princeton) proved stories cause 'neural coupling' — "
            "the listener's brain activity literally mirrors the speaker's. "
            "Harvard Business Review: stories are 22× more memorable than facts alone. "
            "The SCR structure (Situation/Complication/Resolution) is used by McKinsey, "
            "Pixar, and every effective TED speaker."
        ),
        "instruction": (
            "This is a story in three acts. Read each section with its own distinct energy: "
            "SITUATION — calm, scene-setting. "
            "COMPLICATION — tension in your voice. "
            "RESOLUTION — warmth and conviction. "
            "Let the emotion of each act come through."
        ),
        "marked_text": """\
[SITUATION — calm, steady]
Three years ago, I was terrified to speak in public.
My hands would shake. ···
My voice would crack. ···
I would rehearse for hours ···
and still forget everything the moment I stood up.

[COMPLICATION — tension, urgency]
Then one day ··· I had to give a speech.
Two hundred people.
No notes. ···
No second chance.

[RESOLUTION — warmth, conviction]
That day ··· I stopped trying to be perfect.
I decided to just ··· be honest.

And for the first time in my life ···
people didn't just HEAR me.

They FELT me.

That ··· is the power of a real story.""",
        "plain_text": (
            "Three years ago, I was terrified to speak in public. "
            "My hands would shake. My voice would crack. "
            "I would rehearse for hours and still forget everything the moment I stood up. "
            "Then one day I had to give a speech. Two hundred people. No notes. No second chance. "
            "That day I stopped trying to be perfect. I decided to just be honest. "
            "And for the first time in my life, people didn't just hear me. They felt me. "
            "That is the power of a real story."
        ),
        "target_metric": "strategic_pauses",
        "target_range": (3, 99),
        "target_label": "Emotional arc + 3+ pauses",
        "coaching_instruction": (
            "Evaluate their storytelling delivery. "
            "Did their energy change across the three sections (calm → tension → warmth)? "
            "Did they use pauses at emotional moments? "
            "Reference specific lines from their transcript. "
            "Teach them: the pause before the resolution is the most powerful moment in any story."
        ),
    },

    6: {  # Sunday
        "name": "Full Integration",
        "icon": "🎯",
        "technique": "All techniques combined — the complete speaker",
        "science": (
            "Deliberate practice research (Anders Ericsson): skill consolidation requires "
            "integration sessions where all sub-skills are used simultaneously. "
            "This is how Toastmasters' Competent Communicator program works — "
            "individual skills practiced separately, then integrated in full speeches."
        ),
        "instruction": (
            "This is your integration passage. Apply EVERYTHING you have practiced this week: "
            "• 120–140 WPM pace — deliberate and clear\n"
            "• Full pause at every ···\n"
            "• Follow the [SOFT] / [BUILD] / [PEAK] volume arc\n"
            "• Stress the CAPITALISED words\n"
            "This is your weekly performance. Make it count."
        ),
        "marked_text": """\
[SOFT] You have been practicing all week. ···

Today ··· bring everything together.

[BUILD] Speak slowly.
Use your pauses DELIBERATELY.
Stress the words that MATTER.
Let your volume ··· rise and fall like music.

[PEAK] THE WORLD IS FULL OF PEOPLE
who have something important to say ···
but have never learned ··· HOW to say it.

[SOFT] You are learning. ···
You are growing. ···

[BUILD] And every time you practice ···
you are building a skill ···
that will serve you ···
for the REST of your life.

[PEAK] NOW. ···
Take a breath. ···
And begin.""",
        "plain_text": (
            "You have been practicing all week. Today, bring everything together. "
            "Speak slowly. Use your pauses deliberately. Stress the words that matter. "
            "Let your volume rise and fall like music. "
            "The world is full of people who have something important to say "
            "but have never learned how to say it. "
            "You are learning. You are growing. "
            "And every time you practice, you are building a skill "
            "that will serve you for the rest of your life. "
            "Now. Take a breath. And begin."
        ),
        "target_metric": "overall_score",
        "target_range": (70, 99),
        "target_label": "Overall score > 70",
        "coaching_instruction": (
            "This is the integration session — evaluate ALL dimensions: "
            "pace, fillers, pauses, and volume variation. "
            "Give a balanced review. Lead with their strongest skill from this week. "
            "Identify one area that still needs the most work. "
            "End with a personalised plan for next week."
        ),
    },
}
