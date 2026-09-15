/**
 * Hardened visual eval. The page shows a server-rendered image.
 * Clicks go to the server; cubie JSON never reaches this page.
 */
const view = document.getElementById("view");
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

let frameSeq = 0;
async function refreshFrame() {
  frameSeq += 1;
  const url = `${boot.frame}&t=${frameSeq}`;
  view.src = url;
  if (view.decode) await view.decode().catch(() => {});
  else await new Promise((r) => { view.onload = r; });
}

function mapPoint(event) {
  const rect = view.getBoundingClientRect();
  const nw = view.naturalWidth || 1280;
  const nh = view.naturalHeight || 800;
  const x = ((event.clientX - rect.left) / Math.max(rect.width, 1)) * nw;
  const y = ((event.clientY - rect.top) / Math.max(rect.height, 1)) * nh;
  return { x: Math.round(x), y: Math.round(y) };
}

async function sendInput(payload) {
  await fetch("/api/visual/input", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: boot.id, ...payload }),
  });
  await refreshFrame();
}

let drag = null;
let lastClickAt = 0;
let ignoreClick = false;

view.addEventListener("pointerdown", (event) => {
  const p = mapPoint(event);
  drag = { ...p, button: event.button, moved: false };
});
view.addEventListener("pointermove", (event) => {
  if (!drag) return;
  const p = mapPoint(event);
  if (Math.hypot(p.x - drag.x, p.y - drag.y) > 14) drag.moved = true;
});
view.addEventListener("pointerup", async (event) => {
  if (!drag) return;
  const start = drag;
  drag = null;
  if (!start.moved) return;
  ignoreClick = true;
  const p = mapPoint(event);
  await sendInput({ type: "orbit", x: start.x, y: start.y, dx: p.x - start.x, dy: p.y - start.y });
});

view.addEventListener("click", async (event) => {
  if (ignoreClick) {
    ignoreClick = false;
    return;
  }
  const p = mapPoint(event);
  const now = performance.now();
  const dbl = event.detail === 2 || now - lastClickAt < 320;
  lastClickAt = now;
  await sendInput({ type: "click", x: p.x, y: p.y, button: 0, dbl });
});
view.addEventListener("contextmenu", async (event) => {
  event.preventDefault();
  const p = mapPoint(event);
  await sendInput({ type: "click", x: p.x, y: p.y, button: 2, dbl: false });
});

window.__rubixEval = {
  id: boot.id,
  kind: boot.kind,
  usage,
  setUsage(next) {
    Object.assign(usage, next || {});
  },
  input: sendInput,
};

done.addEventListener("click", async () => {
  const payload = {
    id: boot.id,
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

await refreshFrame();
