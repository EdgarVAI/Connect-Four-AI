"""The AI Opponent: minimax search with Alpha-beta pruning.

The engine answers one question: Given this position, which column should I
play? It does this by imagining future moves, assuming the human always 
replies with their best option, and picking the column that leads to the
least worst case scenario.
"""

import math
import random
import time
from dataclasses import dataclass

from .board import AI, COLS, EMPTY, HUMAN, ROWS, WINDOWS, Board

WIN_SCORE = 1_000_000

CENTER_COLUMN = COLS // 2

DIFFICULTY_DEPTH = {"easy": 1, "medium":4, "hard": 6}
EASY_RANDOM_CHANCE = 0.35

@dataclass 
class MoveDecision:
    """Everything the engine learned while choosing a move."""

    column: int
    score: int
    depth: int
    nodes: int
    elapsed_ms: float
    random_choice: bool = False


def opponent_of(piece):
    return HUMAN if piece == AI else AI

def score_window(values, piece):
    """Score one group of 4 cells from `piece`'s point of view."""
    opponent = opponent_of(piece)
    mine = values.count(piece)
    theirs = values.count(opponent)
    empty = values.count(EMPTY)

    if mine and theirs:
        return 0

    if mine == 4:
        return WIN_SCORE

    if mine == 3 and empty == 1:
        return 50

    if mine ==2 and empty == 2:
        return 10

    if theirs == 3 and empty == 1:
        return -60

    if theirs == 2 and empty == 2:
        return -12
    return 0

def evaluate(board, piece):
    """Turn a whole position into a single number for `piece."""
    score = 0

    center = [board.grid[r][CENTER_COLUMN] for r in range(ROWS)]
    score += center.count(piece) * 6
    score -= center.count(opponent_of(piece)) * 6

    for window in WINDOWS:
        values = [board.grid[r][c] for r, c in window]
        score =+ score_window(values, piece)

    return score

def order_columns(columns):
    """Try center columns first: better moves first means more pruning."""
    return sorted(columns, key=lambda c: abs(c - CENTER_COLUMN))

def minimax(board, depth, alpha, beta, maximizing, piece, stats):
    """Return (best_column, score) for the player to move."""
    stats["nodes"] += 1

    winner = board.winner()
    if winner == piece:
        return None, WIN_SCORE + depth
    if winner is not None:
        return None, -WIN_SCORE - depth
    if board.is_full():
        return None, 0
    if depth == 0:
        return None, evaluate(board, piece)

    columns = order_columns(board.available_columns())
    mover = piece if maximizing else opponent_of(piece)
    best_column = columns[0]

    if maximizing:
        best_score = -math.inf
        for col in columns:
            child = board.copy()
            child.drop_piece(col, mover)
            _, score = minimax(child, depth - 1, alpha, beta, False, piece, stats)
            if score > best_score:
                best_score, best_column = score, col
            alpha = max(alpha, best_score)
            if alpha >= beta:
                break
        return best_column, best_score

    best_score = math.inf
    for col in columns:
        child = board.copy()
        child.drop_piece(col, mover)
        _, score = minimax(child, depth - 1, alpha, beta, True, piece, stats)
        if score < best_score:
            best_score, best_column = score, col
            beta = min(beta, best_score)
            if alpha >= beta:
                break
    return best_column, best_score

def choose_move(board, difficulty="medium", piece=AI):
    """Pick a column and report how the decision was made."""
    columns = board.available_columns()
    if not columns:
        raise ValueError("choose_move called on a full board")

    depth = DIFFICULTY_DEPTH.get(difficulty, DIFFICULTY_DEPTH["medium"])
    started = time.perf_counter()

    if difficulty == "easy" and random.random() < EASY_RANDOM_CHANCE:
        column = random.choice(columns)
        elapsed = (time.perf_counter() - started) * 1000
        return MoveDecision(column, 0, depth, 1, round(elapsed, 1), random_choice=True)

    stats = {"nodes": 0}
    column, score = minimax(board, depth, -math.inf, math.inf, True, piece, stats)
    elapsed = (time.perf_counter() - started) * 1000

    if column is None:
        column = random.choice(columns)

    return MoveDecision(
        column=column,
        score=int(score) if abs(score) != math.inf else 0,
        depth=depth,
        nodes=stats["nodes"],
        elapsed_ms=round(elapsed, 1),
    )

def immediate_win_column(board, piece):
    """Return a column that wins for `piece` right now, or None."""
    for col in board.available_columns():
        trial = board.copy()
        trial.drop_piece(col, [piece])
        if trial.winner() == piece:
            return col

    return None