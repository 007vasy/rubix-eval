const kind = location.pathname.includes("/4d") ? "4d" : "3d";
const title = document.getElementById("title");
const subtitle = document.getElementById("subtitle");
const blurb = document.getElementById("blurb");
const empty = document.getElementById("empty");
const stats = document.getElementById("stats");
const chart = document.getElementById("chart");
const tableWrap = document.getElementById("table-wrap");
const rows = document.getElementById("rows");
document.getElementById(kind === "4d" ? "link4d" : "link3d").setAttribute("aria-current", "page");

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}

function replayHref(id) {
  return id ? `/replay?id=${encodeURIComponent(id)}` : "";
}

function replayLink(id) {
  if (!id) return "";
  return `<a class="replay" href="${replayHref(id)}">Replay</a>`;
}

function ticks(full) {
  const step = full > 30 ? 10 : 5;
  const marks = new Set([0, full]);
  for (let n = step; n < full; n += step) if (full - n >= step / 2) marks.add(n);
  return [...marks].sort((a, b) => a - b);
}

function laneName(lane) {
  return lane === "verified" ? "Verified (offline)" : "Open computer-use";
}

const data = await fetch(`/api/verified/depth?kind=${kind}`, { cache: "no-store" }).then((r) => r.json());
const full = data.full_turns;
title.textContent = `Verified ${data.title}`;
subtitle.textContent = `Deepest official scramble solved · full scramble = ${full} turns`;
blurb.textContent =
  `Each bar is one model: how many random turns deep the hardest official ${data.title} scramble it solved was. ` +
  `The line at the right edge is a full scramble (${full} turns). Ties are broken by fewer moves (HTM). ` +
  `Open computer-use runs are included and shown in blue.`;

// Deepest first; among equals the more efficient (fewer HTM) solve ranks higher.
const models = [...(data.models || [])].sort(
  (a, b) => b.solved_turns - a.solved_turns || (a.htm ?? Infinity) - (b.htm ?? Infinity),
);

if (!models.length) {
  empty.hidden = false;
} else {
  const fullSolves = models.filter((m) => m.reached_full);
  const bestFull = fullSolves.reduce((best, m) => (best && best.htm <= m.htm ? best : m), null);
  const verifiedCount = models.filter((m) => m.lane === "verified").length;
  stats.hidden = false;
  stats.innerHTML = `
    <div class="stat"><div class="k">Reached a full scramble</div>
      <div class="v">${fullSolves.length}<small> / ${models.length} models</small></div>
      <div class="d">${full} random turns from solved</div></div>
    <div class="stat"><div class="k">Fewest moves on a full solve</div>
      <div class="v">${bestFull ? `${bestFull.htm}<small> HTM</small>` : "—"}</div>
      <div class="d">${bestFull ? escapeHtml(bestFull.ai) : "No full solve yet"}</div></div>
    <div class="stat"><div class="k">Verified offline</div>
      <div class="v">${verifiedCount}<small> / ${models.length} models</small></div>
      <div class="d">Internet disallowed during the run</div></div>`;

  const grid = ticks(full)
    .filter((n) => n > 0 && n < full)
    .map((n) => `<div class="vc-grid" style="left:${(n / full) * 100}%"></div>`)
    .join("");
  const bars = models
    .map((model, i) => {
      const pct = full ? Math.min(100, (model.solved_turns / full) * 100) : 0;
      const lane = model.lane === "verified" ? "verified" : "open";
      const href = replayHref(model.record_id);
      const name = href
        ? `<a class="name" href="${href}" title="Replay ${escapeHtml(model.ai)}">${escapeHtml(model.ai)}</a>`
        : `<span class="name">${escapeHtml(model.ai)}</span>`;
      const value = model.reached_full
        ? `${full}<span class="check" aria-label="full scramble">✓</span> <small>full</small>`
        : `${model.solved_turns} <small>/ ${full}</small>`;
      return `
        <div class="vc-row">
          <div class="vc-label"><span class="rank">${i + 1}</span>${name}<span class="lane-chip ${lane}">${lane}</span></div>
          <div class="vc-track" data-i="${i}">
            ${grid}
            <div class="vc-target"></div>
            <div class="vc-bar ${lane}${model.reached_full ? " full" : ""}" style="--pct:${pct}%;--delay:${i * 70}ms"></div>
          </div>
          <div class="vc-value">${value}</div>
        </div>`;
    })
    .join("");
  const axis = ticks(full)
    .map((n, i, all) => {
      const cls = n === full ? "full" : all[i + 1] === full ? "near-full" : "";
      const label = n === full ? `${n}<em> · full</em>` : n;
      return `<span class="${cls}" style="left:${(n / full) * 100}%">${label}</span>`;
    })
    .join("");

  chart.hidden = false;
  chart.innerHTML = `
    <h2>How deep did each model get?</h2>
    <p class="sub">Scramble depth solved, in random turns from solved (HTM).</p>
    <div class="legend" aria-label="Legend">
      <span><i class="swatch"></i>Verified (offline)</span>
      <span><i class="swatch open"></i>Open computer-use</span>
      <span><i class="target-key"></i>Full scramble</span>
    </div>
    <div class="vc" role="img" aria-label="Scramble depth solved per model; values are in the table below.">
      ${bars}
      <div></div><div class="vc-axis">${axis}</div><div></div>
      <div class="vc-axis-title">turns from solved</div>
    </div>`;

  const tip = document.createElement("div");
  tip.className = "tip";
  tip.hidden = true;
  document.body.append(tip);
  chart.addEventListener("pointermove", (event) => {
    const track = event.target.closest(".vc-track");
    if (!track) {
      tip.hidden = true;
      return;
    }
    const m = models[Number(track.dataset.i)];
    tip.innerHTML = `<b>${escapeHtml(m.ai)}</b>
      <div class="row"><span>Lane</span><span>${laneName(m.lane)}</span></div>
      <div class="row"><span>Solved depth</span><span>${m.solved_turns} / ${full}${m.reached_full ? " ✓" : ""}</span></div>
      <div class="row"><span>Gap to full</span><span>${m.gap_turns}</span></div>
      <div class="row"><span>Moves used</span><span>${m.htm ?? "—"} HTM</span></div>`;
    tip.hidden = false;
    const pad = 14;
    const { width, height } = tip.getBoundingClientRect();
    let x = event.clientX + pad;
    let y = event.clientY + pad;
    if (x + width > innerWidth - 8) x = event.clientX - width - pad;
    if (y + height > innerHeight - 8) y = event.clientY - height - pad;
    tip.style.left = `${x}px`;
    tip.style.top = `${y}px`;
  });
  chart.addEventListener("pointerleave", () => {
    tip.hidden = true;
  });

  tableWrap.hidden = false;
  for (const model of models) {
    const tr = document.createElement("tr");
    const solved = model.reached_full ? `${model.full_turns} (full)` : String(model.solved_turns);
    tr.innerHTML = `
      <td><i class="swatch${model.lane === "verified" ? "" : " open"}"></i>${escapeHtml(model.ai)}</td>
      <td>${escapeHtml(model.lane || "")}</td>
      <td>${solved}</td>
      <td>${model.full_turns}</td>
      <td>${model.gap_turns}</td>
      <td>${model.htm ?? "—"}</td>
      <td>${replayLink(model.record_id)}</td>`;
    rows.append(tr);
  }
}
