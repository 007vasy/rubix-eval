/**
 * Public computer-use eval. The cube draws in this browser (WebGL).
 * Oracle / scramble string stay on the server. Done posts the viewer's history.
 */
import { CubeViewer } from "./viewer.js";
import { HyperViewer } from "./hyperviewer.js";

const canvas = document.getElementById("view");
const done = document.getElementById("done");
const flash = document.getElementById("flash");

const bootQs = new URLSearchParams(location.search);
if (!bootQs.has("random")) bootQs.set("random", "1");
const kindHint = bootQs.get("kind") || "3d";
if (kindHint !== "3d" && !bootQs.get("size")) bootQs.set("size", "3");
const boot = await fetch(`/api/visual/boot?${bootQs}`, { cache: "no-store" }).then(async (r) => {
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    const msg = data.error || "visual session missing — start with: rubix-eval visual";
    document.body.insertAdjacentHTML("afterbegin", `<p style="color:#f88;padding:16px">${msg}</p>`);
    throw new Error(msg);
  }
  return data;
});

const usage = {
  tokens_used: bootQs.get("tokens") || bootQs.get("tokens_used") || null,
  token_cost_usd: bootQs.get("cost") || bootQs.get("token_cost") || bootQs.get("token_cost_usd") || null,
};

const clicks = [];
function onChange() {
  /* CubeViewer / HyperViewer notify on turns; history lives on the viewer. */
}

const viewer =
  boot.kind === "3d"
    ? new CubeViewer(canvas, onChange, { clickToTurn: true, size: (boot.state && boot.state.size) || boot.size || 3 })
    : new HyperViewer(canvas, onChange, { showLabels: false });
if (boot.state) viewer.loadState(boot.state);
if (typeof viewer.resize === "function") viewer.resize();

canvas.addEventListener("pointerup", (event) => {
  const rect = canvas.getBoundingClientRect();
  clicks.push({
    t: Math.round(performance.now()),
    x: Math.round(event.clientX - rect.left),
    y: Math.round(event.clientY - rect.top),
    button: event.button,
    dbl: event.detail === 2,
    kind: "pointer",
  });
});

window.__rubixEval = {
  id: boot.id,
  kind: boot.kind,
  github: boot.github,
  issues: boot.issues,
  usage,
  setUsage(next) {
    Object.assign(usage, next || {});
  },
};

done.addEventListener("click", async () => {
  const payload = {
    id: boot.id,
    history: (viewer && viewer.history) || [],
    clicks,
    click_count: clicks.length,
    tokens_used: usage.tokens_used,
    token_cost_usd: usage.token_cost_usd,
  };
  const ai = bootQs.get("ai") || bootQs.get("agent") || bootQs.get("model");
  if (ai) payload.ai = ai;
  const res = await fetch("/api/visual/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const grade = await res.json();
  flash.hidden = false;
  flash.textContent = grade.solved ? "solved" : "not solved";
  flash.className = grade.solved ? "ok" : "bad";
  document.body.classList.toggle("solved", Boolean(grade.solved));
  setTimeout(() => {
    flash.hidden = true;
  }, 700);
});
