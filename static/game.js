// Front-end controller. It never decides anything about the game -- it only
// renders whatever state the server sends back and forwards clicks to the API.

const ROWS = 6;
const COLS = 7;
const PIECE_CLASS = { 1: "human", 2: "ai" };

const boardEl = document.getElementById("board");
const statusEl = document.getElementById("status");
const analysisEl = document.getElementById("analysis");
const explanationEl = document.getElementById("explanation");
const commentaryEl = document.getElementById("commentary");
const coachBtn = document.getElementById("ask-coach");
const difficultyEl = document.getElementById("difficulty");

let busy = false;

// Build the 42 buttons once; afterwards we only change their classes.
const cells = [];
for (let row = 0; row < ROWS; row++) {
  for (let col = 0; col < COLS; col++) {
    const button = document.createElement("button");
    button.className = "cell";
    button.dataset.col = col;
    button.setAttribute("aria-label", `Row ${row + 1}, column ${col + 1}`);
    button.addEventListener("click", () => playColumn(col));
    boardEl.appendChild(button);
    cells.push(button);
  }
}

async function api(path, body) {
  const response = await fetch(path, {
    method: body ? "POST" : "GET",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed");
  return data;
}

function render(state) {
  const winSet = new Set((state.winning_cells || []).map(([r, c]) => `${r},${c}`));
  const playable = new Set(state.valid_columns || []);
  const over = state.status !== "in_progress";

  state.board.forEach((rowValues, row) => {
    rowValues.forEach((value, col) => {
      const cell = cells[row * COLS + col];
      cell.className = "cell";
      if (value) cell.classList.add(PIECE_CLASS[value]);
      if (winSet.has(`${row},${col}`)) cell.classList.add("win");
      const canPlay = !over && playable.has(col);
      if (canPlay) cell.classList.add("playable");
      cell.disabled = !canPlay;
    });
  });

  const messages = {
    in_progress: state.message || "Your turn -- click any column.",
    human_win: "You win! Nice.",
    ai_win: "The AI wins this one.",
    draw: "Draw -- the board is full.",
  };
  statusEl.textContent = messages[state.status];

  if (state.last_move) {
    const m = state.last_move;
    analysisEl.hidden = false;
    explanationEl.textContent = m.explanation;
    document.getElementById("m-column").textContent = m.column;
    document.getElementById("m-depth").textContent = m.depth;
    document.getElementById("m-nodes").textContent = m.nodes.toLocaleString();
    document.getElementById("m-time").textContent = `${m.elapsed_ms} ms`;
    coachBtn.hidden = false;
    coachBtn.textContent = state.coach_available
      ? "Ask the AI coach"
      : "Ask the AI coach (no API key set)";
    commentaryEl.hidden = true;
  }
}

async function playColumn(col) {
  if (busy) return;
  busy = true;
  statusEl.textContent = "AI is thinking...";
  try {
    render(await api("/api/move", { column: col, difficulty: difficultyEl.value }));
  } catch (error) {
    statusEl.textContent = error.message;
  } finally {
    busy = false;
  }
}

document.getElementById("new-game").addEventListener("click", async () => {
  analysisEl.hidden = true;
  render(await api("/api/new-game", {}));
});

coachBtn.addEventListener("click", async () => {
  coachBtn.disabled = true;
  commentaryEl.hidden = false;
  commentaryEl.textContent = "Asking the coach...";
  try {
    const data = await api("/api/coach", {});
    commentaryEl.textContent = data.commentary;
  } catch (error) {
    commentaryEl.textContent = error.message;
  } finally {
    coachBtn.disabled = false;
  }
});

api("/api/new-game", {}).then(render);
