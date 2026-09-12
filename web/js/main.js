import { CubeViewer } from "./viewer.js";
import { generateScramble, stepCost as stepCost3 } from "./engine.js";
import { HyperViewer } from "./hyperviewer.js";
import { adjacentCells, generateHyperScramble, stepCost as stepCost4 } from "./hyperengine.js";

const $ = (id) => document.getElementById(id);

let mode = "3d";
let viewer = new CubeViewer($("view"), updateStats);
let modifier = 1;
let wide = false;
let twoShot = false;

function sizeValue() {
  return Number($("size").value);
}

function layerValue() {
  return Math.max(1, Math.min(sizeValue() - 1, Number($("layer").value) || 1));
}

function updateSizeLabel() {
  const n = sizeValue();
  $("sizeLabel").textContent = `${n}×${n}×${n}`;
  $("layer").max = String(Math.max(1, n - 1));
  if (Number($("layer").value) > n - 1) $("layer").value = "1";
}

function setModifier(turns) {
  modifier = turns;
  if (viewer.modifier !== undefined) viewer.modifier = turns;
  $("modCw").setAttribute("aria-pressed", String(turns === 1));
  $("modPrime").setAttribute("aria-pressed", String(turns === 3));
  $("mod2").setAttribute("aria-pressed", String(turns === 2));
}

function fillHyperAxes() {
  const cell = $("hyperCell").value;
  const pad = $("hyperAxes");
  pad.innerHTML = "";
  for (const axis of adjacentCells(cell)) {
    const btn = document.createElement("button");
    btn.textContent = cell + axis;
    btn.addEventListener("click", () => {
      if (mode !== "4d") return;
      viewer.enqueue({ cell, axis, turns: modifier, order: 4, axisCells: [axis] });
    });
    pad.appendChild(btn);
  }
}

function setMode(next) {
  if (next === mode) return;
  mode = next;
  viewer.dispose();
  const canvas = $("view");
  if (mode === "4d") {
    viewer = new HyperViewer(canvas, updateStats);
    viewer.modifier = modifier;
  } else {
    viewer = new CubeViewer(canvas, updateStats);
  }
  $("mode3d").setAttribute("aria-pressed", String(mode === "3d"));
  $("mode4d").setAttribute("aria-pressed", String(mode === "4d"));
  const four = mode === "4d";
  for (const [id, hide] of [
    ["sizeRow", four],
    ["pad3d", four],
    ["pad4d", !four],
    ["hint3d", four],
    ["hint4d", !four],
    ["modWide", four],
    ["layerRow", four],
  ]) {
    const el = $(id);
    el.hidden = hide;
    el.style.display = hide ? "none" : "";
  }
  if (mode === "4d") fillHyperAxes();
  viewer.notify();
}

function updateStats(state) {
  const costFn = state.kind === "4d" ? stepCost4 : stepCost3;
  const cost = costFn(state.history, state.scramble.length);
  $("htm").textContent = String(cost.htm);
  $("qtm").textContent = String(cost.qtm);
  $("scrambleDepth").textContent = String(cost.scrambleDepth);
  const excess = $("excess");
  if (!state.history.length) {
    excess.textContent = "—";
    excess.className = "";
    $("eff").textContent = "—";
  } else {
    excess.textContent = String(cost.excessHtm);
    excess.className = cost.excessHtm > 0 ? "warn" : "ok";
    $("eff").textContent = `${Math.round(cost.efficiency * 100)}%`;
  }
  $("misplaced").textContent = String(state.cube.misplacedStickers());
  $("history").textContent = state.moves || "(none)";
  const badge = $("badge");
  if (state.solved) {
    badge.textContent = "solved";
    badge.className = "badge solved";
  } else if (state.kind === "4d") {
    badge.textContent = "3×3×3×3 scrambled";
    badge.className = "badge scrambled";
  } else {
    badge.textContent = `${state.cube.size}×${state.cube.size}×${state.cube.size} scrambled`;
    badge.className = "badge scrambled";
  }
}

$("mode3d").addEventListener("click", () => setMode("3d"));
$("mode4d").addEventListener("click", () => setMode("4d"));
$("hyperCell").addEventListener("change", fillHyperAxes);

$("size").addEventListener("input", () => {
  updateSizeLabel();
  if (mode === "3d") viewer.setSize(sizeValue());
});
$("scramble").addEventListener("click", () => {
  if (mode === "4d") {
    viewer.applyScramble(generateHyperScramble(Number($("depth").value), Number($("seed").value)));
  } else {
    viewer.applyScramble(generateScramble(sizeValue(), Number($("depth").value), Number($("seed").value)));
  }
});
$("reset").addEventListener("click", () => viewer.reset());
$("undo").addEventListener("click", () => viewer.undo());
$("solve").addEventListener("click", () => viewer.solveByReverse());
$("modCw").addEventListener("click", () => setModifier(1));
$("modPrime").addEventListener("click", () => setModifier(3));
$("mod2").addEventListener("click", () => setModifier(2));
$("modWide").addEventListener("click", () => {
  wide = !wide;
  $("modWide").setAttribute("aria-pressed", String(wide));
});

for (const button of document.querySelectorAll("#pad3d [data-face]")) {
  button.addEventListener("click", () => {
    if (mode !== "3d") return;
    viewer.enqueue({
      face: button.dataset.face,
      layer: layerValue(),
      wide,
      turns: modifier,
    });
  });
}

window.addEventListener("keydown", (event) => {
  if (event.metaKey || event.ctrlKey || event.altKey) return;
  if (mode === "4d") return;
  const key = event.key;
  if (key === "2") {
    twoShot = true;
    return;
  }
  const map = { u: "U", d: "D", l: "L", r: "R", f: "F", b: "B" };
  const face = map[key.toLowerCase()];
  if (!face) return;
  event.preventDefault();
  const turns = twoShot ? 2 : event.shiftKey ? 3 : 1;
  twoShot = false;
  viewer.enqueue({ face, layer: layerValue(), wide: event.shiftKey && event.altKey ? true : wide, turns });
});

updateSizeLabel();
fillHyperAxes();
viewer.notify();
