"""The `coach` layer: explains why the engine played the move it played.

Two tiers, on purpose:

1. `explain_move()` -- pure Python rules. Instant and always available.
2. `llm_commentary()` -- sends the position to a language model for a richer,
    conversational explanation. Optional, used only when API key exists.

Designing it this way means the project runs perfectly with no API rather at all,
and the llm feature is an enhancement rather than a hard dependency.

"""

import os

from .ai import immediate_win_column
from .board import AI, HUMAN, Board

SYMBOLS = {0: ".", HUMAN: "X", AI: "O"}

def render_for_prompt(grid):
    """Turns the grid into plain text a language model can read."""
    lines = ["".join(SYMBOLS[cell] for cell in row) for row in grid]
    lines.append("0123456  (X = human, O = AI, . = empty)")
    return "\n".join(lines)

def explain_move(board_before, decision):
    """Rule-based explanation. `board_before` is the position BEFORE the AI moved."""
    if decision.random_choice:
        return "Easy mode: that move was picked at random to give you a chance to win."

    column = decision.column

    after = board_before.copy()
    after.drop_piece(column, AI)
    if after.winner() == AI:
        return f"Winning move: column {column} completed four in a row."

    human_threat = immediate_win_column(board_before, HUMAN)
    if human_threat == column:
        return f"Blocking move: you were one piece away from winning in column {column}."

    if immediate_win_column(after, AI) is not None:
        return (
            f"Attacking move: column {column} builds a three-in-a-row, so the AI"
            "now threatens to win on its next turn."
        )

    if human_threat is not None:
        return (
            f"You have a winning threat in column {human_threat} that cannot be"
            f"stopped, so the AI played column {column} to build its own position."
        )

    if column == 3:
        return (
            "Positional move: the center column belongs to more possible winning"
            f"lines than any other, so the AI claimed it. (search score {decision.score}.)"
        )
    return (
        f"Positional move: after looking {decision.depth} moves ahead across"
        f"{decision.nodes} positions, the column {column} scored best "
        f"({decision.score}.)"
    )

def llm_available():
    """True when an API key is configured for the optional commentary feature."""
    return bool(os.environ.get("OPENAI_API_KEY"))

def llm_commentary(grid_before, decision, difficulty, rule_explanation):
    """Ask the language model to narrate the move like a friendly coach.
    
    Returns a string. Never raises any failure degrades to the rule-based text,
    because a broken commentary feature must not break the game.
    """
    if not llm_available():
        return rule_explanation

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.environ.get("OPENAI_BASE_URL") or None,
        )
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

        system_prompt = (
            "You are a friendly Connect Four coach for a beginner."
            "You are given a board position, the move the computer engine chose,"
            "and the engine's own technical reason. Explain the move in at most"
            "three short sentences of plain English. Address the player as `you`."
            "Never invent moves that are not described. Do not use markdown."
        )
        user_prompt = (
            f"Board before the AI moved:\n{render_for_prompt(grid_before)}\n\n"
            f"AI played column: {decision.column}\n"
            f"Difficulty: {difficulty} (searched {decision.depth} moves ahead, "
            f"{decision.nodes} positions, score {decision.score})\n"
            f"Engine's technical reason: {rule_explanation}\n\n"
            "Explain this move to the player."
        )

        response = client.chat.completions.create(
            model=model,
            max_tokens=160,
            temperature=0.6,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        text = (response.choices[0].messages.content or "").strip()
        return text or rule_explanation

    except Exception as error:
        print(f"[coach] language model unavailable, using rules instead: {error}")
        return rule_explanation
    