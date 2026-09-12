/**
 * Visual-only eval. The agent sees stickers, not text.
 * Left click = 90° CW, right click = 90° CCW, double-click = 180°.
 * Drag empty space to orbit. Green circle = submit.
 */
import { CubeViewer } from "./viewer.js";
import { HyperViewer } from "./hyperviewer.js";
import { stepCost as stepCost3 } from "./engine.js";
import { stepCost as stepCost4 } from "./hyperengine.js";

const canvas = document.getElementById("view");
const done = document.getElementById("done");
const flash = document.getElementById("flash");

const boot = await fetch("/api/visual/boot", { cache: "no-store" }).then((r) => {
  if (!r.ok) throw new Error("visual session missing — start with: rubix-eval visual");
  return r.json();
});

let latest = {
  solved: false,
  htm: 0,
  qtm: 0,
  misplaced: 0,
  history: [],
};

function onChange(state) {
  const costFn = state.kind === "4d" ? stepCost4 : stepCost3;
  const cost = costFn(state.history, 0);
  latest = {
    solved: state.solved,
    htm: cost.htm,
    qtm: cost.qtm,
    misplaced: state.cube.misplacedStickers(),
    history: state.history,
  };
  document.body.classList.toggle("solved", state.solved);
}

const viewer =
  boot.kind === "4d"
    ? new HyperViewer(canvas, onChange, { showLabels: false })
    : new CubeViewer(canvas, onChange, { clickToTurn: true, size: boot.size });
viewer.loadState(boot.state);

window.__rubixEval = {
  id: boot.id,
  kind: boot.kind,
  snapshot() {
    return { id: boot.id, kind: boot.kind, ...latest };
  },
};

done.addEventListener("click", async () => {
  const payload = { id: boot.id, ...latest };
  const res = await fetch("/api/visual/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const grade = await res.json();
  flash.hidden = false;
  flash.className = grade.solved ? "ok" : "bad";
  setTimeout(() => {
    flash.hidden = true;
    flash.className = "";
  }, 700);
});
