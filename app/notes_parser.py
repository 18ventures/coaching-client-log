"""
Parses a photo of handwritten session notes into structured fields, using the
Claude API's vision support. Requires ANTHROPIC_API_KEY to be set in the
environment (a Railway project variable, separate from your personal Claude
subscription — this is billed per-use on your Anthropic API account).
"""
import base64
import json
import os
from anthropic import Anthropic

MODEL = "claude-sonnet-5"  # good balance of vision accuracy and cost for this task

DISCOVERY_FIELDS = {
    "pain": "Main struggle, in the client's own words",
    "duration": "How long the struggle has been going on (short phrase, e.g. '2 years, on and off')",
    "why_now": "Why they're seeking help now / what changed",
    "tried": "What they've already tried to fix it themselves",
    "cost_scale": "Cost of inaction on a 1-10 scale, as an integer, if mentioned or inferable — else null",
    "outcome": "Desired outcome in 3 months",
    "technique": "Approach or technique discussed / proposed",
    "goal_1": "Their top goal, one sentence",
    "goal_2": "Their second goal, one sentence",
    "goal_detail": "What achieving the goal looks like day-to-day",
    "goal_why": "Why this goal matters to them underneath",
    "work_what": "What they do for work (role, industry, pattern)",
    "work_stop": "What they want to stop doing / do less of",
    "cadence": "Preferred meeting cadence/availability",
    "excited": "What would make them genuinely excited to start",
    "notes": "Any other relevant notes that don't fit elsewhere",
}

FOLLOWUP_FIELDS = {
    "progress_review": "What they actually did since the last session, reviewed against prior action items",
    "win": "Biggest win since the last session",
    "obstacles": "What got in the way / didn't happen",
    "goal_shift": "Any shift in their goals, or new goals surfacing",
    "goal_1": "Goal #1 (current)",
    "goal_2": "Goal #2 (current)",
    "session_focus": "What this session focused on, and why",
    "technique": "Approach or technique used in this session",
    "notes": "Any other relevant notes that don't fit elsewhere",
}


def fields_for(session_type: str) -> dict:
    return FOLLOWUP_FIELDS if session_type == "followup" else DISCOVERY_FIELDS


def build_prompt(session_type: str) -> str:
    fields = fields_for(session_type)
    field_lines = "\n".join(f'  "{k}": "{v}"' for k, v in fields.items())
    return f"""You are reading a coach's handwritten notes from a client session, photographed
as an image. Extract the information into the JSON fields below. This is a
{"follow-up" if session_type == "followup" else "first/intake"} session.

Rules:
- Output ONLY valid JSON, no markdown fences, no commentary before or after.
- If a field isn't mentioned in the notes, use an empty string "" (or null for cost_scale).
- Do not invent information that isn't in the notes — leave fields blank rather than guessing.
- Keep each field's content close to what's actually written; you may lightly clean up
  handwriting artifacts and abbreviations, but do not add interpretation or advice.
- Also extract a list of action items mentioned as next steps, each tagged with who owns
  it ("client" or "coach") based on context — if unclear, default to "client".

Return this exact JSON shape:
{{
{field_lines},
  "action_items": [
    {{"description": "...", "owner": "client"}},
    {{"description": "...", "owner": "coach"}}
  ]
}}"""


def parse_notes_image(image_bytes: bytes, media_type: str, session_type: str) -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add it as a variable in your Railway project "
            "settings (get a key from console.anthropic.com) before using this feature."
        )

    client = Anthropic(api_key=api_key)
    b64_image = base64.standard_b64encode(image_bytes).decode("utf-8")
    prompt = build_prompt(session_type)

    message = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64_image,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )

    raw_text = "".join(block.text for block in message.content if getattr(block, "type", None) == "text")
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        # strip ```json ... ``` fences if the model adds them despite instructions
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Could not parse the model's response as JSON: {e}\nRaw response: {raw_text[:500]}")

    return parsed
