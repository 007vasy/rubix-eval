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
if (bootQs.has("turns") && !bootQs.has("depth")) bootQs.set("depth", bootQs.get("turns"));
if (bootQs.has("n") && !bootQs.has("size")) bootQs.set("size", bootQs.get("n"));
if (bootQs.has("ndim") && !bootQs.has("kind")) bootQs.set("kind", `${bootQs.get("ndim")}d`);
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

const canon = new URL(location.href);
canon.searchParams.set("kind", boot.kind || "3d");
canon.searchParams.set("size", String(boot.size || 3));
if (boot.depth) canon.searchParams.set("depth", String(boot.depth));
canon.searchParams.delete("turns");
canon.searchParams.delete("n");
canon.searchParams.delete("d");
canon.searchParams.delete("scramble");
canon.searchParams.delete("ndim");
if (canon.searchParams.get("random") !== "1") canon.searchParams.delete("random");
history.replaceState(null, "", canon);

const SIZES_3D = [2, 3, 4, 5, 6, 7, 8, 9, 10];
const SIZES_4D = [2, 3, 4, 5];
const DEPTHS = ["", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "full"];

function fillSelect(el, values, selected, labels) {
  el.innerHTML = "";
  for (const value of values) {
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = labels && labels[value] != null ? labels[value] : value || "any";
    if (String(value) === String(selected ?? "")) opt.selected = true;
    el.append(opt);
  }
}

const pick = document.getElementById("pick");
const kindSel = document.getElementById("pick-kind");
const sizeSel = document.getElementById("pick-size");
const depthSel = document.getElementById("pick-depth");

function syncSizeOptions() {
  const four = kindSel.value === "4d";
  const sizes = four ? SIZES_4D : SIZES_3D;
  const current = sizeSel.value || String(boot.size || 3);
  fillSelect(sizeSel, sizes, sizes.includes(Number(current)) ? current : sizes[1] || sizes[0]);
}

kindSel.value = boot.kind === "4d" ? "4d" : "3d";
syncSizeOptions();
fillSelect(sizeSel, kindSel.value === "4d" ? SIZES_4D : SIZES_3D, boot.size);
fillSelect(
  depthSel,
  DEPTHS,
  boot.depth || "",
  { "": "any", full: "full scramble" },
);
kindSel.addEventListener("change", syncSizeOptions);
pick.addEventListener("submit", (event) => {
  event.preventDefault();
  const next = new URL(location.href);
  next.searchParams.set("kind", kindSel.value);
  next.searchParams.set("size", sizeSel.value);
  if (depthSel.value) next.searchParams.set("depth", depthSel.value);
  else next.searchParams.delete("depth");
  next.searchParams.delete("random");
  const ai = bootQs.get("ai") || bootQs.get("agent") || bootQs.get("model");
  if (ai) next.searchParams.set("ai", ai);
  location.assign(next);
});
document.getElementById("pick-shuffle").addEventListener("click", () => {
  const next = new URL(location.href);
  next.searchParams.set("kind", kindSel.value);
  next.searchParams.set("size", sizeSel.value);
  if (depthSel.value) next.searchParams.set("depth", depthSel.value);
  else next.searchParams.delete("depth");
  next.searchParams.set("random", "1");
  const ai = bootQs.get("ai") || bootQs.get("agent") || bootQs.get("model");
  if (ai) next.searchParams.set("ai", ai);
  location.assign(next);
});

window.__rubixEval = {
  id: boot.id,
  kind: boot.kind,
  size: boot.size,
  depth: boot.depth,
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
