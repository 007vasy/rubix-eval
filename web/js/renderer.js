/**
 * Trusted cube renderer. Loaded only by the eval server's Puppeteer.
 * Exposes pick/turn/orbit — never the scramble, cubies, or oracle.
 */
import { CubeViewer } from "./viewer.js";
import { HyperViewer } from "./hyperviewer.js";

const canvas = document.getElementById("view");
let viewer = null;
let kind = "3d";
let latest = { solved: false, history: [] };

function onChange(state) {
  latest = {
    solved: Boolean(state.solved),
    history: state.history || [],
  };
}

window.__trusted = {
  load(nextKind, state) {
    kind = nextKind || "3d";
    viewer =
      kind === "3d"
        ? new CubeViewer(canvas, onChange, { clickToTurn: true, size: state.size || 3 })
        : new HyperViewer(canvas, onChange, { showLabels: false });
    viewer.loadState(state);
    return { ok: true, kind };
  },
  snapshot() {
    return {
      solved: Boolean(viewer && viewer.cube && viewer.cube.isSolved()),
      history: (viewer && viewer.history) || latest.history || [],
    };
  },
};
