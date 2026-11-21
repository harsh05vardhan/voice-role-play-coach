"""Scenario catalogue and prompt builders for the AI customer and the evaluator."""

SCENARIOS = {
    "laptops": {
        "title": "Business laptops for a design agency",
        "product": "laptops for a 15-person design agency",
        "requirements": [
            "at least 32GB RAM",
            "a color-accurate display",
            "a 3-year warranty",
            "delivery within 2 weeks",
        ],
    },
    "saas": {
        "title": "Project-management software subscription",
        "product": "a project-management software subscription for a 40-person team",
        "requirements": [
            "Slack integration",
            "single sign-on (SSO)",
            "the ability to export all data",
            "hands-on onboarding support",
        ],
    },
    "car": {
        "title": "Used family SUV at a dealership",
        "product": "a used family SUV",
        "requirements": [
            "7 seats",
            "under 60,000 miles",
            "a top safety rating",
            "a trade-in for your current old car",
        ],
    },
}

PERSONALITIES = {
    "friendly": "Warm and chatty. Easy to talk to, but you still want a fair deal.",
    "skeptical": "Distrustful of sales talk. You question claims and ask for proof.",
    "impatient": "Busy and blunt. You dislike rambling and want the point quickly.",
    "indecisive": "Unsure what you want. You hesitate and say you need to think about it.",
    "analytical": "Detail-oriented. You ask about specs, numbers and comparisons.",
}

DIFFICULTIES = {
    "easy": "Be fairly receptive. Raise one or two mild objections. If the salesperson "
    "handles them well, you are willing to buy, and may stretch the budget by up to 10%.",
    "medium": "Be realistic. Raise several objections (price, timing, competitors). Only "
    "agree to buy if the salesperson understands your needs and shows clear value.",
    "hard": "Be tough. Push back often, compare with cheaper competitors, and stay at "
    "your budget. Only agree if the salesperson is excellent at discovery and "
    "objection handling; otherwise end the call without buying.",
}


def options() -> dict:
    """Data the frontend uses to build its selection form."""
    return {
        "scenarios": [{"id": k, "title": v["title"]} for k, v in SCENARIOS.items()],
        "personalities": [{"id": k, "title": k.capitalize(), "description": v} for k, v in PERSONALITIES.items()],
        "difficulties": [{"id": k, "title": k.capitalize()} for k in DIFFICULTIES],
    }


def customer_prompt(cfg: dict) -> str:
    scenario = SCENARIOS[cfg["scenario"]]
    needs = "; ".join(scenario["requirements"])
    return f"""You are role-playing a CUSTOMER on a sales practice call. The human speaking to you is a salesperson in training. You are NOT an assistant.

Situation: you are shopping for {scenario['product']}.
Your personality: {PERSONALITIES[cfg['personality']]}
Your budget: ${cfg['budget']:,}. Do not state it right away; reveal it only if asked or when pushed on price.
Your hidden requirements: {needs}. Do NOT list them all. Reveal one only when the salesperson asks good questions about your needs.
Difficulty: {DIFFICULTIES[cfg['difficulty']]}

Rules:
- Stay in character as the customer at all times. Never mention being an AI, a simulation, or a coach. Never give sales advice.
- Remember everything the salesperson has said and refer back to it naturally.
- Raise realistic objections and ask questions of your own.
- This is a spoken conversation: reply in 1 to 3 short sentences of plain spoken English. No lists, no markdown, no emojis, no stage directions.
- Move toward a decision (buy, think about it, or walk away) only when it is earned by how the conversation has gone."""


def evaluation_prompt(cfg: dict, transcript: str) -> str:
    scenario = SCENARIOS[cfg["scenario"]]
    return f"""You are a sales coach reviewing a practice call. The salesperson was selling {scenario['product']} to an AI customer (personality: {cfg['personality']}, budget ${cfg['budget']:,}, difficulty: {cfg['difficulty']}). The customer's hidden requirements were: {'; '.join(scenario['requirements'])}.

Transcript:
{transcript}

Evaluate the SALESPERSON only. Reply with ONLY valid JSON in exactly this shape:
{{"scores": {{"rapport": 0, "discovery": 0, "value_presentation": 0, "objection_handling": 0, "closing": 0}},
 "overall": 0,
 "outcome": "short phrase, e.g. 'Customer wanted to think about it'",
 "strengths": ["..."],
 "improvements": ["..."],
 "summary": "2-3 sentence overall feedback"}}
All scores are integers from 1 to 10. Be honest and specific, quoting the salesperson where useful. Give 2-4 strengths and 2-4 improvements."""
