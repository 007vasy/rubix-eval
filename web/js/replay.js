import { CubeViewer } from "./viewer.js";
import { HyperViewer } from "./hyperviewer.js";

const params = new URLSearchParams(location.search);
const recordId = params.get("id");
const title = document.getElementById("title");
const statsEl = document.getElementById("stats");
const eventsEl = document.getElementById("events");
const progressEl = document.getElementById("progress");
const nodraw = document.getElementById("nodraw");
const canvas = document.getElementById("view");
const stage = document.getElementById("stage");
const stageWrap = document.getElementById("stage-wrap");
const overlay = document.getElementById("overlay");
const actionEl = document.getElementById("action");
const clockEl = document.getElementById("clock");
const thinkEl = document.getElementById("think");
const playBtn = document.getElementById("play");
const speedSel = document.getElementById("speed");
const timeline = document.getElementById("timeline");
const tlMarks = document.getElementById("tl-marks");
const tlHead = document.getElementById("tl-head");
const tlSpan = document.getElementById("tl-span");
const notice = document.getElementById("notice");
const SVG = "http://www.w3.org/2000/svg";

function fmtTime(s) {
  if (s == null || Number.isNaN(Number(s))) return "—";
  s = Number(s);
  if (s < 0.1) return `${(s * 1000).toFixed(1)} ms`;
  if (s < 60) return `${s.toFixed(2)} s`;
  const m = Math.floor(s / 60);
  const r = (s - m * 60).toFixed(2).padStart(5, "0");
  return `${m}:${r}`;
}

function fmtClock(ms) {
  const s = Math.max(0, Math.round(ms / 1000));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = String(s % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${sec}` : `${m}:${sec}`;
}

function fmtGap(ms) {
  const s = ms / 1000;
  if (s < 60) return `${Math.round(s)} s`;
  return `${Math.floor(s / 60)} min ${Math.round(s % 60)} s`;
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

function clickKind(c) {
  if (c.kind === "drag" || c.kind === "orbit") return "drag";
  return c.button === 2 ? "right" : "left";
}

function clickLabel(c, outcome) {
  if (c.kind === "drag" || c.kind === "orbit") return "Drag · orbit the view";
  const what = c.button === 2 ? "Right click" : c.dbl ? "Double-click" : "Left click";
  if (outcome == null) return what;
  if (outcome === "first") return `${what} · first half of a double-click`;
  if (outcome === "") return `${what} · missed the cube, no turn`;
  return `${what} → <b>${outcome}</b>`;
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
const moveTimes = Array.isArray(att.move_times) && att.move_times.length === history.length ? att.move_times : null;

const depth = rec.depth_label === "full" ? "full scramble" : `d${rec.depth_label || rec.scramble_depth}`;
title.textContent = `${rec.ai || att.ai || "AI"} · ${kind === "4d" ? "4D" : "3D"} ${rec.size} · ${depth}`;
statsEl.innerHTML = [
  ["Result", att.solved ? `<em class="ok">solved</em>` : `<em class="bad">unsolved</em>`],
  ["Time", fmtTime(att.elapsed_sec)],
  ["Moves", att.step_count ?? history.length ?? "—"],
  ["Clicks", att.click_count ?? (clicks.length || "—")],
  ["HTM", att.htm ?? "—"],
  ["QTM", att.qtm ?? "—"],
  ["Tokens", fmtTokens(att.tokens_used)],
  ["Token cost", fmtCost(att.token_cost_usd)],
]
  .map(([k, v]) => `<div class="stat"><b>${k}</b><span>${v}</span></div>`)
  .join("");

// ---------- One timeline of clicks and the layer turns they caused ----------
// New records store, per click, how many moves had landed (`n`), so each move slots in
// right before the first click that came after it. Older records only have the moves.
const synced = clicks.length > 0 && clicks.every((c) => c.n != null);
const events = [];
if (synced) {
  let mi = 0;
  for (const c of clicks) {
    while (mi < history.length && mi < c.n) events.push({ type: "move", i: mi++ });
    events.push({ type: "click", c });
  }
  while (mi < history.length) events.push({ type: "move", i: mi++ });
} else {
  history.forEach((_, i) => events.push({ type: "move", i }));
}
// What each click achieved: the turns that landed before the next click, or why none did.
if (synced) {
  events.forEach((ev, k) => {
    if (ev.type !== "click" || clickKind(ev.c) === "drag") return;
    const turns = [];
    let j = k + 1;
    for (; j < events.length && events[j].type === "move"; j += 1) turns.push(moveLabel(history[events[j].i], kind));
    const next = events[j];
    if (turns.length) ev.outcome = turns.join(" ");
    else if (next && next.type === "click" && next.c.t - ev.c.t < 400 && Math.hypot(next.c.x - ev.c.x, next.c.y - ev.c.y) < 14)
      ev.outcome = "first";
    else if (next || k === events.length - 1) ev.outcome = "";
  });
}
let lastT = null;
for (const ev of events) {
  if (ev.type === "click") ev.t = ev.c.t;
  else if (moveTimes) ev.t = moveTimes[ev.i];
  else if (synced && lastT != null) ev.t = lastT + 300;
  if (ev.t != null) lastT = ev.t;
}
const timed = events.length > 1 && events.every((ev) => ev.t != null);
const t0 = timed ? Math.min(...events.map((e) => e.t)) : 0;
const t1 = timed ? Math.max(...events.map((e) => e.t)) : 0;
const agentW = synced ? clicks.find((c) => c.w)?.w : null;
const agentH = synced ? clicks.find((c) => c.h)?.h : null;
const showPointer = Boolean(synced && agentW && agentH);

if (!synced && clicks.length) {
  const span = clicks[0].t != null && clicks.at(-1).t != null ? ` over ${fmtClock(clicks.at(-1).t - clicks[0].t)}` : "";
  notice.hidden = false;
  notice.textContent =
    `This run was recorded before click capture: ${clicks.length} clicks${span}, but not where they landed on the cube ` +
    `or which turn each one made, so only the layer turns are replayed. New runs show every click.`;
}
if (timed) tlSpan.textContent = `${fmtClock(t1 - t0)} of agent time`;

// ---------- Event list ----------
events.forEach((ev, k) => {
  const li = document.createElement("li");
  li.dataset.k = String(k);
  const when = timed ? `<time>${fmtClock(ev.t - t0)}</time>` : "";
  if (ev.type === "move") {
    li.className = "ev-move";
    li.innerHTML = `<i class="tick"></i><span>Turn <b>${moveLabel(history[ev.i], kind)}</b></span>${when}`;
  } else {
    li.className = "ev-click";
    li.innerHTML = `<i class="dot ${clickKind(ev.c)}"></i><span>${clickLabel(ev.c, ev.outcome)}</span>${when}`;
  }
  eventsEl.append(li);
});
eventsEl.addEventListener("click", (event) => {
  const li = event.target.closest("li[data-k]");
  if (li) goto(Number(li.dataset.k) + 1);
});

// ---------- Timeline strip ----------
function posOf(k) {
  if (timed && t1 > t0) return (events[k].t - t0) / (t1 - t0);
  return events.length > 1 ? k / (events.length - 1) : 0;
}
const frag = document.createDocumentFragment();
events.forEach((ev, k) => {
  const mark = document.createElement("i");
  mark.className = ev.type === "move" ? "tick" : `dot ${clickKind(ev.c)}`;
  mark.style.left = `${posOf(k) * 100}%`;
  frag.append(mark);
});
tlMarks.append(frag);

function seekFromPointer(event) {
  const rect = timeline.getBoundingClientRect();
  const f = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
  let best = 0;
  let bestD = Infinity;
  events.forEach((_, k) => {
    const d = Math.abs(posOf(k) - f);
    if (d < bestD) {
      bestD = d;
      best = k;
    }
  });
  goto(f === 0 ? 0 : best + 1);
}
let scrubbing = false;
timeline.addEventListener("pointerdown", (event) => {
  scrubbing = true;
  timeline.setPointerCapture(event.pointerId);
  seekFromPointer(event);
});
timeline.addEventListener("pointermove", (event) => {
  if (scrubbing) seekFromPointer(event);
});
timeline.addEventListener("pointerup", () => {
  scrubbing = false;
});

// ---------- Viewer on a stage with the agent's aspect ratio ----------
let viewer = null;
let initialCam = null;

function layoutStage() {
  const w = stageWrap.clientWidth;
  const h = stageWrap.clientHeight;
  if (showPointer) {
    const aspect = agentW / agentH;
    const width = Math.min(w, h * aspect);
    stage.style.width = `${Math.floor(width)}px`;
    stage.style.height = `${Math.floor(width / aspect)}px`;
  } else {
    stage.style.width = `${w}px`;
    stage.style.height = `${h}px`;
  }
  if (viewer) viewer.resize();
}

if (drawable && rec.state) {
  layoutStage();
  viewer =
    kind === "4d"
      ? new HyperViewer(canvas, null, { showLabels: true })
      : new CubeViewer(canvas, null, { clickToTurn: true, size: rec.size });
  // Watching only: sticker presses must not change the recorded cube.
  canvas.removeEventListener("pointerdown", viewer.boundPointerDown || viewer.onDown);
  viewer.loadState(rec.state);
  initialCam = viewer.camera.position.toArray();
  layoutStage();
  window.addEventListener("resize", layoutStage);
} else {
  stage.hidden = true;
  nodraw.hidden = false;
}
if (showPointer) overlay.setAttribute("viewBox", `0 0 ${agentW} ${agentH}`);

// ---------- Playback ----------
let applied = 0; // events[0..applied) are on screen
let playing = false;
let token = 0;
let camTween = 0;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function speed() {
  return Number(speedSel.value) || 1;
}

function waitIdle() {
  return new Promise((resolve) => {
    const tick = () => {
      if (!viewer || (!viewer.animating && !(viewer.queue && viewer.queue.length))) resolve();
      else requestAnimationFrame(tick);
    };
    tick();
  });
}

function setCamera(pos, ms = 0) {
  if (!viewer || !pos) return;
  cancelAnimationFrame(camTween);
  const cam = viewer.camera.position;
  if (!ms) {
    cam.set(...pos);
    viewer.controls.update();
    return;
  }
  // Swing around the orbit target (slerp direction, lerp distance) so the camera never cuts
  // through the puzzle the way a straight line between two views would.
  const target = viewer.controls.target;
  const a = cam.clone().sub(target);
  const b = cam.clone().set(...pos).sub(target);
  const ra = a.length();
  const rb = b.length();
  const qa = [a.x / ra, a.y / ra, a.z / ra];
  const qb = [b.x / rb, b.y / rb, b.z / rb];
  const dot = Math.max(-1, Math.min(1, qa[0] * qb[0] + qa[1] * qb[1] + qa[2] * qb[2]));
  const omega = Math.acos(dot);
  const start = performance.now();
  const tick = (now) => {
    const t = Math.min(1, (now - start) / ms);
    const e = t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2;
    let dir;
    if (omega < 1e-3 || Math.PI - omega < 1e-3) dir = qa.map((v, i) => v + (qb[i] - v) * e);
    else {
      const wa = Math.sin((1 - e) * omega) / Math.sin(omega);
      const wb = Math.sin(e * omega) / Math.sin(omega);
      dir = qa.map((v, i) => v * wa + qb[i] * wb);
    }
    const len = Math.hypot(...dir) || 1;
    const r = ra + (rb - ra) * e;
    cam.set(target.x + (dir[0] / len) * r, target.y + (dir[1] / len) * r, target.z + (dir[2] / len) * r);
    viewer.controls.update();
    if (t < 1) camTween = requestAnimationFrame(tick);
  };
  camTween = requestAnimationFrame(tick);
}

function cameraAt(k) {
  for (let j = k - 1; j >= 0; j -= 1) {
    const c = events[j].type === "click" ? events[j].c : null;
    if (c && (c.cam_end || c.cam)) return c.cam_end || c.cam;
  }
  return initialCam;
}

function applyInstant(move) {
  if (!viewer) return;
  if (typeof move === "string") viewer.cube.apply(move);
  else viewer.cube.apply([move]);
  viewer.rebuild();
}

function svg(tag, attrs, parent = overlay) {
  const el = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, String(v));
  parent.append(el);
  return el;
}

const CURSOR = "M0 0 L0 17 L4.5 13 L7.5 20 L10.5 18.7 L7.6 12 L13 12 Z";

function drawPointer(c, animate) {
  overlay.replaceChildren();
  if (!showPointer || c.x == null) return;
  const scale = Math.max(1, agentW / 900);
  const cls = clickKind(c);
  if (cls === "drag" && c.x0 != null) {
    svg("line", { x1: c.x0, y1: c.y0, x2: c.x, y2: c.y, class: `trail ${animate ? "draw" : ""}` });
    svg("circle", { cx: c.x0, cy: c.y0, r: 5 * scale, class: "trail-start" });
  }
  const ring = svg("g", { transform: `translate(${c.x} ${c.y})` });
  svg("circle", { r: 26 * scale, class: `ripple ${cls} ${animate ? "go" : ""}` }, ring);
  if (c.dbl) svg("circle", { r: 26 * scale, class: `ripple ${cls} ${animate ? "go late" : ""}` }, ring);
  svg("circle", { r: 6 * scale, class: `hit ${cls}` }, ring);
  const start = cls === "drag" && c.x0 != null && animate ? [c.x0, c.y0] : [c.x, c.y];
  const pointer = svg("g", { class: "pointer", transform: `translate(${start[0]} ${start[1]}) scale(${1.3 * scale})` });
  svg("path", { d: CURSOR }, pointer);
  if (start[0] !== c.x || start[1] !== c.y) {
    requestAnimationFrame(() =>
      requestAnimationFrame(() => pointer.setAttribute("transform", `translate(${c.x} ${c.y}) scale(${1.3 * scale})`)),
    );
    pointer.style.transition = `transform ${650 / speed()}ms cubic-bezier(.4,0,.2,1)`;
  }
}

function showAction(text, tone) {
  actionEl.hidden = !text;
  actionEl.className = `action ${tone || ""}`;
  actionEl.innerHTML = text || "";
}

function describe(k) {
  const ev = events[k];
  if (!ev) return;
  if (ev.type === "move") {
    showAction(`Turn <b>${moveLabel(history[ev.i], kind)}</b>`, "move");
  } else {
    showAction(clickLabel(ev.c, ev.outcome), clickKind(ev.c));
  }
}

function mark() {
  const k = applied - 1;
  progressEl.textContent = `${applied} / ${events.length}`;
  const ev = events[k];
  clockEl.textContent = timed && ev ? fmtClock(ev.t - t0) : "0:00";
  const prev = events[k - 1];
  const gap = timed && ev && prev ? ev.t - prev.t : 0;
  thinkEl.hidden = !(gap >= 4000);
  if (!thinkEl.hidden) thinkEl.textContent = `thought for ${fmtGap(gap)}`;
  tlHead.style.left = `${(k >= 0 ? posOf(k) : 0) * 100}%`;
  timeline.setAttribute("aria-valuenow", String(applied));
  for (const li of eventsEl.querySelectorAll("li.current, li.done")) li.classList.remove("current", "done");
  const items = eventsEl.children;
  for (let j = 0; j < applied - 1; j += 1) items[j].classList.add("done");
  if (k >= 0) {
    items[k].classList.add("current");
    items[k].scrollIntoView({ block: "nearest" });
  }
}

function stop() {
  playing = false;
  token += 1;
  playBtn.textContent = "Play";
  playBtn.classList.remove("on");
}

function goto(k) {
  stop();
  k = Math.max(0, Math.min(events.length, k));
  if (viewer && rec.state) viewer.loadState(rec.state);
  for (let j = 0; j < k; j += 1) if (events[j].type === "move") applyInstant(history[events[j].i]);
  applied = k;
  setCamera(k === 0 ? initialCam : cameraAt(k));
  const ev = events[k - 1];
  if (ev && ev.type === "click") drawPointer(ev.c, false);
  else overlay.replaceChildren();
  if (k) describe(k - 1);
  else showAction("");
  mark();
}

async function step(my) {
  if (applied >= events.length) return;
  const k = applied;
  const ev = events[k];
  applied += 1;
  describe(k);
  mark();
  if (ev.type === "click") {
    const c = ev.c;
    const drag = clickKind(c) === "drag";
    if (c.cam) setCamera(c.cam, drag ? 0 : 260 / speed());
    drawPointer(c, true);
    if (drag && c.cam_end) setCamera(c.cam_end, 650 / speed());
    await sleep((drag ? 800 : 480) / speed());
  } else {
    const move = history[ev.i];
    if (viewer) {
      if (typeof move === "string") viewer.applyText(move);
      else viewer.enqueue(move);
      await waitIdle();
    }
    if (token === my) await sleep(160 / speed());
  }
}

async function play() {
  if (playing) {
    stop();
    return;
  }
  if (applied >= events.length) goto(0);
  playing = true;
  const my = ++token;
  playBtn.textContent = "Pause";
  playBtn.classList.add("on");
  while (playing && token === my && applied < events.length) await step(my);
  if (token === my) stop();
}

document.getElementById("reset").addEventListener("click", () => goto(0));
document.getElementById("next").addEventListener("click", () => {
  stop();
  step(token);
});
document.getElementById("prev").addEventListener("click", () => goto(applied - 1));
playBtn.addEventListener("click", () => play());
document.addEventListener("keydown", (event) => {
  if (event.target.closest("select, input")) return;
  if (event.key === " ") {
    event.preventDefault();
    play();
  } else if (event.key === "ArrowRight") {
    stop();
    step(token);
  } else if (event.key === "ArrowLeft") {
    goto(applied - 1);
  } else if (event.key === "Home") {
    goto(0);
  }
});

// Headless hook (GIF export, tests): `goto(n)` shows the cube after n layer turns.
window.__replay = {
  length: history.length,
  events: events.length,
  reset: () => goto(0),
  goto(n) {
    let k = 0;
    let seen = 0;
    while (k < events.length && seen < n) if (events[k++].type === "move") seen += 1;
    goto(k);
  },
  gotoEvent: goto,
};

mark();
