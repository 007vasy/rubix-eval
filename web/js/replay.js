import { CubeViewer } from "./viewer.js";
import { HyperViewer } from "./hyperviewer.js";

const params = new URLSearchParams(location.search);
const recordId = params.get("id");
const title = document.getElementById("title");
const statsEl = document.getElementById("stats");
const movesEl = document.getElementById("moves");
const clicksEl = document.getElementById("clicks");
const clicksTitle = document.getElementById("clicks-title");
const progressEl = document.getElementById("progress");
const nodraw = document.getElementById("nodraw");
const canvas = document.getElementById("view");
const playBtn = document.getElementById("play");

function fmtTime(s) {
  if (s == null || Number.isNaN(Number(s))) return "—";
  s = Number(s);
  if (s < 0.1) return `${(s * 1000).toFixed(1)} ms`;
  if (s < 60) return `${s.toFixed(2)} s`;
  const m = Math.floor(s / 60);
  const r = (s - m * 60).toFixed(2).padStart(5, "0");
  return `${m}:${r}`;
}

function fmtTokens(n) {
  if (n == null) return "—";
  const v = Number(n);
  if (Number.isNaN(v)) return "—";
  return v >= 1000 ? v.toLocaleString() : String(v);
}

function fmtCost(n) {
  if (n == null) return "—";
  const v = Number(n);
  if (Number.isNaN(v)) return "—";
  return `$${v.toFixed(v < 0.01 ? 4 : 2)}`;
}

function moveLabel(move, kind) {
  if (typeof move === "string") return move;
  if (kind !== "3d") {
    const letters = (move.cell || "") + (move.axisCells || []).join("") || move.axis || "";
    const suffix = { 1: "", 2: "2", 3: "'" }[move.turns] || "";
    const layer = move.layer && move.layer > 1 ? String(move.layer) : "";
    return layer + letters + suffix;
  }
  const face = move.face || "";
  const suffix = { 1: "", 2: "2", 3: "'" }[move.turns] || "";
  if (move.wide) return `${move.layer && move.layer !== 2 ? move.layer : ""}${face}w${suffix}`;
  if (move.layer && move.layer > 1) return `${move.layer}${face}${suffix}`;
  return face + suffix;
}

if (!recordId) {
  title.textContent = "Missing record id";
  throw new Error("missing id");
}

const rec = await fetch(`/api/solves?id=${encodeURIComponent(recordId)}`, { cache: "no-store" }).then((r) => {
  if (!r.ok) throw new Error("record not found");
  return r.json();
});
const att = rec.attempt || {};
const kind = rec.kind || "3d";
const drawable = kind === "3d" || kind === "4d";
const history = att.history && att.history.length ? att.history : att.moves ? String(att.moves).split(/\s+/).filter(Boolean) : [];
const clicks = att.clicks || [];

title.textContent = `${rec.ai || att.ai || "AI"} · ${kind} ${rec.size} · d${rec.depth_label || rec.scramble_depth}`;
statsEl.innerHTML = [
  ["Result", att.solved ? "solved" : "unsolved"],
  ["Steps", att.step_count ?? history.length ?? "—"],
  ["Clicks", att.click_count ?? (clicks.length || "—")],
  ["Time", fmtTime(att.elapsed_sec)],
  ["Tokens", fmtTokens(att.tokens_used)],
  ["Token cost", fmtCost(att.token_cost_usd)],
  ["HTM", att.htm ?? "—"],
  ["QTM", att.qtm ?? "—"],
]
  .map(([k, v]) => `<div class="stat"><b>${k}</b><span>${v}</span></div>`)
  .join("");

history.forEach((move, i) => {
  const li = document.createElement("li");
  li.textContent = `${i + 1}. ${moveLabel(move, kind)}`;
  movesEl.append(li);
});
if (clicks.length) {
  clicksTitle.hidden = false;
  clicksEl.hidden = false;
  clicks.forEach((c, i) => {
    const li = document.createElement("li");
    const xy = c.x != null ? ` (${c.x},${c.y})` : "";
    li.textContent = `${i + 1}. ${c.kind || "pointer"}${xy}`;
    clicksEl.append(li);
  });
}

let viewer = null;
if (drawable && rec.state) {
  viewer =
    kind === "4d"
      ? new HyperViewer(canvas, null, { showLabels: true })
      : new CubeViewer(canvas, null, { clickToTurn: false, size: rec.size });
  viewer.loadState(rec.state);
} else {
  canvas.hidden = true;
  nodraw.hidden = false;
}

let index = 0;
let playing = false;
let timer = 0;

function waitIdle() {
  return new Promise((resolve) => {
    const tick = () => {
      if (!viewer || (!viewer.animating && !(viewer.queue && viewer.queue.length))) resolve();
      else requestAnimationFrame(tick);
    };
    tick();
  });
}

function mark() {
  progressEl.textContent = `${index} / ${history.length}`;
  [...movesEl.children].forEach((li, i) => {
    li.classList.toggle("current", i === index);
    li.classList.toggle("done", i < index);
  });
}

async function reset() {
  playing = false;
  playBtn.textContent = "Play";
  index = 0;
  if (viewer && rec.state) viewer.loadState(rec.state);
  mark();
}

function applyInstant(move) {
  if (!viewer) return;
  if (typeof move === "string") viewer.cube.apply(move);
  else viewer.cube.apply([move]);
  viewer.rebuild();
}

async function step(dir) {
  if (!history.length) return;
  if (dir < 0) {
    const target = Math.max(0, index - 1);
    if (viewer && rec.state) viewer.loadState(rec.state);
    for (let i = 0; i < target; i += 1) applyInstant(history[i]);
    index = target;
    mark();
    return;
  }
  if (index >= history.length) return;
  const move = history[index];
  if (viewer) {
    if (typeof move === "string") viewer.applyText(move);
    else viewer.enqueue(move);
    await waitIdle();
  }
  index += 1;
  mark();
}

async function play() {
  if (playing) {
    playing = false;
    playBtn.textContent = "Play";
    return;
  }
  playing = true;
  playBtn.textContent = "Pause";
  while (playing && index < history.length) {
    await step(1);
    await new Promise((r) => {
      timer = setTimeout(r, 280);
    });
  }
  playing = false;
  playBtn.textContent = "Play";
}

document.getElementById("reset").addEventListener("click", () => reset());
document.getElementById("next").addEventListener("click", () => {
  playing = false;
  playBtn.textContent = "Play";
  step(1);
});
document.getElementById("prev").addEventListener("click", () => {
  playing = false;
  playBtn.textContent = "Play";
  step(-1);
});
playBtn.addEventListener("click", () => play());
mark();
