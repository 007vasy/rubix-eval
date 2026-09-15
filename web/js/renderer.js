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
    if (viewer) {
      if (typeof viewer.dispose === "function") viewer.dispose();
      else {
        viewer._stopped = true;
        try {
          viewer.controls?.dispose();
          viewer.renderer?.dispose();
        } catch {
          /* ignore */
        }
      }
      viewer = null;
    }
    viewer =
      kind === "3d"
        ? new CubeViewer(canvas, onChange, { clickToTurn: true, size: (state && state.size) || 3 })
        : new HyperViewer(canvas, onChange, { showLabels: false });
    viewer.loadState(state);
    if (typeof viewer.resize === "function") viewer.resize();
    return { ok: true, kind };
  },
  snapshot() {
    return {
      solved: Boolean(viewer && viewer.cube && viewer.cube.isSolved()),
      history: (viewer && viewer.history) || latest.history || [],
    };
  },
  pointer(x, y, button, dbl) {
    const rect = canvas.getBoundingClientRect();
    const clientX = rect.left + Number(x);
    const clientY = rect.top + Number(y);
    const opts = {
      bubbles: true,
      cancelable: true,
      composed: true,
      clientX,
      clientY,
      button: button || 0,
      buttons: button === 2 ? 2 : 1,
      pointerId: 1,
      pointerType: "mouse",
      isPrimary: true,
      view: window,
    };
    const event = { clientX, clientY, button: button || 0 };
    const hit = viewer && viewer.hitSticker ? viewer.hitSticker(event) : null;
    const down = viewer && (viewer.handlePointerDown || viewer.onPointerDown);
    const up = viewer && (viewer.handlePointerUp || viewer.onPointerUp);
    if (typeof down === "function" && typeof up === "function") {
      down.call(viewer, event);
      up.call(viewer, event);
      if (dbl) {
        down.call(viewer, event);
        up.call(viewer, event);
      }
    }
    return {
      hit: Boolean(hit),
      cell: hit && hit.object && hit.object.userData && hit.object.userData.cell,
      meshes: viewer && viewer.stickerMeshes ? viewer.stickerMeshes.length : 0,
      n: viewer && viewer.history ? viewer.history.length : 0,
    };
  },
};
