"""region_timeline -> plain-English per-second captions (Backboard). Owner: D."""
import json

from backend.generation.llm import _post

PROMPT = """You caption a brain-activity animation that plays beside a short video. Below is a
per-second timeline of the viewer's predicted brain response: at each second t, the most
active brain network/region and its activation strength (0-1).

Write ONE short caption per second for a creator with no neuroscience background — what their
viewer's brain is doing and what it means for the video ("locking onto a face — strong hook",
"language centers lit up — the words are landing", "attention drifting — this beat drags").
Under 12 words each. Plain, punchy, second person about "your viewer".

How to read the networks (use OUR interpretation, exactly):
- visual: eyes locked on the frame (faces/motion on screen are landing)
- auditory: the sound/music/voice has their attention
- language: the words are being processed — the script is landing
- motion: action and movement on screen is gripping them
- default_mode: HIGH = deep narrative immersion — the story feels personally meaningful
  (this is GOOD, our strongest engagement signal; never call it distraction or mind-wandering)
- low activation everywhere = attention drifting; that's when to warn the creator

Timeline:
{timeline}

Return JSON only: [{{"t": 0, "text": "..."}}, ...] — exactly one entry per timeline second."""


def explain(region_timeline: list) -> list:
    """[{t, top_network, top_region, activation}] -> [{t, text}] (CONTRACTS §5 /explain)."""
    out = _post(PROMPT.format(timeline=json.dumps(region_timeline)))
    text = out["content"].strip()
    if "[" in text:  # tolerate prose/code-fence wrapping around the JSON
        text = text[text.index("["):text.rindex("]") + 1]
    captions = json.loads(text)
    return [{"t": int(c["t"]), "text": str(c["text"])} for c in captions]
