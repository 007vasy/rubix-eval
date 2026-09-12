import { CubeViewer } from "./viewer.js";
import { generateScramble, stepCost } from "./engine.js";

const $ = (id) => document.getElementById(id);

const viewer = new CubeViewer($("view"), updateStats);

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
  $("modCw").setAttribute("aria-pressed", String(turns === 1));
  $("modPrime").setAttribute("aria-pressed", String(turns === 3));
  $("mod2").setAttribute("aria-pressed", String(turns === 2));
}

function updateStats(state) {
  const cost = stepCost(state.history, state.scramble.length);
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
  } else {
    badge.textContent = `${state.cube.size}×${state.cube.size}×${state.cube.size} scrambled`;
    badge.className = "badge scrambled";
  }
}

$("size").addEventListener("input", () => {
  updateSizeLabel();
  viewer.setSize(sizeValue());
});
$("scramble").addEventListener("click", () => {
  const moves = generateScramble(sizeValue(), Number($("depth").value), Number($("seed").value));
  viewer.applyScramble(moves);
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

for (const button of document.querySelectorAll(".pad [data-face]")) {
  button.addEventListener("click", () => {
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
viewer.notify();
