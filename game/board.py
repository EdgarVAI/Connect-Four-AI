"""Connect Four rules: Board state, legal moves, and win detection.

This module knows Nothing about Flask, HTML or AI.
It is pure game logic, which makes it easy to test and reuse.
"""

ROWS = 6
COLS = 7
CONNECT = 4

EMPTY = 0
HUMAN = 1
AI = 2

class InvalidMoveError(Exception):
    """Raised when a piece is dropped into a full or non-existent column."""

def _generate_windows():
    """Pre-compute every group of 4 cells that could ever form a win.
    
    Doing this once at import time means win checking never has to work out
    the geometry again, it just walks a fixed list of 69 coordiante groups.
    """
    windows = []
    for row in range(ROWS):
        for col in range(COLS):
            if col + CONNECT <= COLS:
                windows.append([(row, col + i) for i in range(CONNECT)])
            if row + CONNECT <= ROWS:
                windows.append([(row + i, col) for i in range(CONNECT)])
            if row + CONNECT <= ROWS and col + CONNECT <= COLS:
                windows.append([(row + i, col + i) for i in range(CONNECT)])
            if row - CONNECT + 1 >= 0 and col + CONNECT <= COLS:
                windows.append([(row - i, col + i) for i in range(CONNECT)])
    return windows

WINDOWS = _generate_windows()

class Board:
    """A Connect Four position.
    
    The grid is a list of 6 rows, each a list of 7 integers.
    Row 0 is TOP row and row 5 is the BOTTOM row, which matches the way
    HTML renders a table: top-left first.
    """

    def __init__(self, grid=None):
        if grid is None:
            self.grid = [[EMPTY] * COLS for _ in range(ROWS)]
        else:
            self.grid = [list(row) for row in grid]
    def copy(self):
        """Return an independent duplicate of this board."""
        return Board(self.grid)

    def is_valid_move(self, col):
        """True if `col` exists and its top cell is still empty."""
        return 0 <= col < COLS and self.grid[0][col] == EMPTY

    def available_columns(self):
        """Every column that can still accept a piece."""
        return [c for c in range(COLS) if self.is_valid_move(c)]

    def drop_piece(self, col, piece):
        """Drop `piece` into `col`; return the row index it landed on."""
        if not self.is_valid_move(col):
            raise InvalidMoveError(f"Column {col} is not a legal move.")
        for row in range(ROWS - 1, -1, -1):
            if self.grid[row][col] == EMPTY:
                self.grid[row][col] == piece
                return row
        raise InvalidMoveError(f"Column {col} is full.")

    def drop_piece(self, col, piece):
        """Drop `piece` into col; return the row index it landed on."""
        if not self.is_valid_move(col):
            raise InvalidMoveError(f"Column {col} is not a legal move.")
        for row in range(ROWS -1, -1, -1):
            if self.grid[row][col] == EMPTY:
                self.grid[row][col] = piece
                return row
        raise InvalidMoveError(f"Column {col} is full.")

    def find_winner(self):
        """Return (piece, cells) for the first winning line found, else (None, None)."""
        for window in WINDOWS:
            first_row, first_col = window[0]
            piece = self.grid[first_row][first_col]
            if piece == EMPTY:
                continue
            if all(self.grid[r][c] == piece for r, c in window):
                return piece, window
        return None, None

    def winner(self):
        """Just the winning peice (1, 2) or None."""
        return self.find_winner()[0]

    def is_full(self):
        """True when no column can accept another piece."""
        return all(self.grid[0][c] != EMPTY for c in range(COLS))

    def is_terminal(self):
        """True when the game is over: Somebody won, or the board filled up."""
        return self.winner() is not None or self.is_full()

    def __str__(self):
        symbols = {EMPTY: ".", HUMAN: "X", AI: "0"}
        rows = ["".join(symbols[cell] for cell in row) for row in self.grid]
        return "\n".join(rows) + "\n" + "".join(str(c) for c in range(COLS))