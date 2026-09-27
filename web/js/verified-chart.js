const SLUGS = { "3d": "3d", "4d": "4d", "3x3x3x3": "4d3" };
const slug = location.pathname.replace(/\/$/, "").split("/").pop();
const kind = SLUGS[slug] || "3d";
const title = document.getElementById("title");
const subtitle = document.getElementById("subtitle");
const blurb = document.getElementById("blurb");
const empty = document.getElementById("empty");
const stats = document.getElementById("stats");
const chart = document.getElementById("chart");
const tableWrap = document.getElementById("table-wrap");
const rows = document.getElementById("rows");
for (const a of document.querySelectorAll("header nav a, #puzzle-switch a")) {
  if (a.getAttribute("href").replace(/\/$/, "") === location.pathname.replace(/\/$/, "")) a.setAttribute("aria-current", "page");
}

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
document.title = `rubix-eval — verified ${data.title}`;
title.textContent = `Verified ${data.title}`;
subtitle.textContent = `Deepest official scramble solved · full scramble = ${full} turns`;
blurb.textContent =
  `Each bar is one model: how many random turns deep the hardest official ${data.title} scramble it solved was. ` +
  `The line at the right edge is a full scramble (${full} turns); ties go to fewer moves (HTM). ` +
  `Verified runs were made offline with the internet disallowed. Open runs used a browser with web access ` +
  `and are ranked separately below.`;

// Rank inside each lane: deepest first, then fewer moves.
const byDepth = (a, b) => b.solved_turns - a.solved_turns || (a.htm ?? Infinity) - (b.htm ?? Infinity);
const all = data.models || [];
const lanes = [
  {
    key: "verified",
    title: "Verified · offline",
    note: "OpenShell sandbox, internet disallowed, attested",
    models: all.filter((m) => m.lane === "verified").sort(byDepth),
  },
  {
    key: "open",
    title: "Open · computer-use",
    note: "Browser runs with web access — not verified",
    models: all.filter((m) => m.lane !== "verified").sort(byDepth),
  },
];
const models = lanes.flatMap((l) => l.models);

if (!models.length) {
  empty.hidden = false;
} else {
  const bestOf = (list) => list.filter((m) => m.reached_full).reduce((b, m) => (b && b.htm <= m.htm ? b : m), null);
  const [ver, open] = lanes;
  const bestVer = bestOf(ver.models);
  const bestOpen = bestOf(open.models);
  stats.hidden = false;
  stats.innerHTML = `
    <div class="stat verified"><div class="k">Verified · full scramble</div>
      <div class="v">${ver.models.filter((m) => m.reached_full).length}<small> / ${ver.models.length} models</small></div>
      <div class="d">${bestVer ? `Best: ${escapeHtml(bestVer.ai)} · ${bestVer.htm} HTM` : "No verified full solve yet"}</div></div>
    <div class="stat open"><div class="k">Open · full scramble</div>
      <div class="v">${open.models.filter((m) => m.reached_full).length}<small> / ${open.models.length} models</small></div>
      <div class="d">${bestOpen ? `Best: ${escapeHtml(bestOpen.ai)} · ${bestOpen.htm} HTM` : "No open full solve yet"}</div></div>
    <div class="stat"><div class="k">Full scramble</div>
      <div class="v">${full}<small> random turns</small></div>
      <div class="d">${data.ndim}D puzzle · ${escapeHtml(data.title)}</div></div>`;

  const grid = ticks(full)
    .filter((n) => n > 0 && n < full)
    .map((n) => `<div class="vc-grid" style="left:${(n / full) * 100}%"></div>`)
    .join("");
  let i = 0;
  const bar = (model, rank) => {
    const k = i++;
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
        <div class="vc-label"><span class="rank">${rank}</span>${name}</div>
        <div class="vc-track" data-i="${k}">
          ${grid}
          <div class="vc-target"></div>
          <div class="vc-bar ${lane}${model.reached_full ? " full" : ""}" style="--pct:${pct}%;--delay:${k * 70}ms"></div>
        </div>
        <div class="vc-value">${value}</div>
      </div>`;
  };
  const groups = lanes
    .map((lane) => {
      const head = `
        <div class="vc-group ${lane.key}">
          <span class="lane-chip ${lane.key}">${lane.key}</span>
          <b>${lane.title}</b><span class="vc-group-note">${lane.note}</span>
          <span class="vc-group-count">${lane.models.length} model${lane.models.length === 1 ? "" : "s"}</span>
        </div>`;
      const body = lane.models.length
        ? lane.models.map((m, r) => bar(m, r + 1)).join("")
        : `<div class="vc-none">No ${lane.key === "verified" ? "verified offline" : "open"} run on this puzzle yet.</div>`;
      return head + body;
    })
    .join("");
  const axis = ticks(full)
    .map((n, j, marks) => {
      const cls = n === full ? "full" : marks[j + 1] === full ? "near-full" : "";
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
    <div class="vc" role="img" aria-label="Scramble depth solved per model, verified and open runs ranked separately; values are in the table below.">
      ${groups}
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
  for (const lane of lanes) {
    if (!lane.models.length) continue;
    const head = document.createElement("tr");
    head.className = `lane-row ${lane.key}`;
    head.innerHTML = `<td colspan="7"><span class="lane-chip ${lane.key}">${lane.key}</span> ${lane.title}</td>`;
    rows.append(head);
    for (const model of lane.models) {
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
}
