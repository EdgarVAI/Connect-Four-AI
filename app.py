"""The flask web layer for Connect Four.

This file is intetionally thin. It has three jobs and nothing else:

    1. Serves the HtML page,
    2. Translates the HTTP requests into calls on the game modules,
    3. Translates the results back into JSON.

The actual rules live in the game/board.py file and all the intelligence lives in
game//ai.py. That seperation is the point: you could delete this file and put a
terminal interface on top of the same engine without changing a single rule.
"""

import os
from flask import Flask, jsonify, render_template, request, session

from game.ai import DIFFICULTY_DEPTH, MoveDecision, choose_move
from game.board import AI, HUMAN, Board
from game.coach import explain_move, llm_available, llm_commentary

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-me")

def load_board():
    """Rebuild the Board object from the player's session cookie."""
    grid = session.get("grid")
    if grid is None:
        board = Board()
        session["grid"] = board.grid
        return board
    return Board(grid)

def save_board(board):
    session["grid"] = board.grid

def build_state(board, last_move=None, message=None):
    """The single JSON shape every endpoint returns."""
    winner, cells = board.find_winner()

    if winner == HUMAN:
        status = "human_win"
    elif winner == AI:
        status = "ai_win"
    elif board.is_full():
        status = "draw"
    else:
        status = "in_progress"

    return {
        "board": board.grid,
        "status": status,
        "winning_cells": [list(cell) for cell in (cells or [])],
        "valid_columns": board.available_columns(),
        "last_move": last_move,
        "message": message,
        "coach_available": llm_available(),
    }

@app.get("/")
def index():
    return render_template("index.html")

@app.post("/api/new-game")
def new_game():
    board = Board()
    save_board(board)
    session.pop("last_decision", None)
    session.pop("grid_before_ai", None)
    return jsonify(build_state(board, message="New game. You are red and move first."))

@app.get("/api/state")
def state():
    return jsonify(build_state(load_board()))

@app.post("/api/move")
def move():
    payload = request.get_json(silent=True) or {}

    difficulty = payload.get("difficulty", "medium")
    if difficulty not in DIFFICULTY_DEPTH:
        return jsonify({"error": f"Unknow difficulty '{difficulty}'."}), 400

    try: 
        column = int(payload["column"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Request body must include an integer 'column'."}), 400

    board = load_board()

    if board.is_terminal():
        return jsonify({"error": "This game is already over. Start a new game."}), 409
    if not board.is_valid_move(column):
        return jsonify({"error": f"Column {column} is not a legal move."}), 400

    board.drop_piece(column, HUMAN)
    if board.is_terminal():
        save_board(board)
        return jsonify(build_state(board))

    grid_before_ai = [list(row) for row in board.grid]
    decision = choose_move(board, difficulty)
    board.drop_piece(decision.column, AI)
    save_board(board)

    explanation = explain_move(Board(grid_before_ai), decision)

    session["grid_before_ai"] = grid_before_ai
    session["last_decision"] = {
        "column": decision.column,
        "score": decision.score,
        "depth": decision.depth,
        "nodes": decision.nodes,
        "elapsed_ms": decision.elapsed_ms,
        "random_choice": decision.random_choice,
        "difficulty": difficulty,
        "explanation": explanation,
    }

    return jsonify(build_state(board, last_move=session["last_decision"]))

@app.post("/api/coach")
def coach():
    """Optional: ask a language model to narrate the AI's last move."""
    saved = session.get("last_decision")
    grid_before = session.get("grid_before_ai")
    if not saved or not grid_before:
        return jsonify({"error": "No AI move to explain yet."}), 400

    decision = MoveDecision(
        column=saved["column"],
        score=saved["score"],
        depth=saved["depth"],
        nodes=saved["nodes"],
        elapsed_ms=saved["elapsed_ms"],
        random_choice=saved["random_choice"],
    )
    text = llm_commentary(
        grid_before, decision, saved["difficulty"], saved["explanation"]
    )
    return jsonify({"commentary": text, "used_llm": llm_available()})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)