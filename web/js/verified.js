const empty = document.getElementById("empty");
const board = document.getElementById("board");
const rows = document.getElementById("rows");
const detail = document.getElementById("detail");
const puzzles = document.getElementById("puzzles");

function esc(value) {
  return String(value).replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]);
}

// One card per verified puzzle: the best verified and the best open run, side by side.
async function renderPuzzles() {
  const charts = ["3d", "4d", "4d3"];
  const all = await Promise.all(
    charts.map((k) => fetch(`/api/verified/depth?kind=${k}`, { cache: "no-store" }).then((r) => r.json())),
  );
  const best = (models, lane) =>
    models
      .filter((m) => m.lane === lane && m.solved_turns > 0)
      .sort((a, b) => b.solved_turns - a.solved_turns || (a.htm ?? 1e9) - (b.htm ?? 1e9))[0];
  puzzles.innerHTML = all
    .map((d) => {
      const line = (lane, label) => {
        const m = best(d.models || [], lane);
        const pct = m ? Math.min(100, (m.solved_turns / d.full_turns) * 100) : 0;
        const depth = m ? (m.reached_full ? `full ✓` : `${m.solved_turns}/${d.full_turns}`) : "—";
        return `<div class="lane-line"><span class="lane-chip ${lane}">${label}</span>
          <span class="who">${m ? esc(m.ai) : "no run yet"}</span><span class="depth">${depth}</span></div>
          <div class="mini ${lane}"><i style="width:${pct}%"></i></div>`;
      };
      return `<a class="puzzle-card" href="/verified/${d.slug}">
        <h3>${esc(d.title)}</h3>
        <div class="meta">${d.ndim}D · full scramble ${d.full_turns} turns · ${(d.models || []).length} model runs</div>
        ${line("verified", "verified")}
        ${line("open", "open")}
        <span class="go">Open chart →</span>
      </a>`;
    })
    .join("");
}
renderPuzzles();

function fmtTime(s) {
  if (s == null || Number.isNaN(s)) return "—";
  if (s < 0.1) return `${(s * 1000).toFixed(1)} ms`;
  if (s < 60) return `${s.toFixed(2)} s`;
  const m = Math.floor(s / 60);
  const r = (s - m * 60).toFixed(2).padStart(5, "0");
  return `${m}:${r}`;
}

function solvesBar(n) {
  const max = Math.max(1, ...ais.map((a) => a.solves || 0));
  return `<div class="tbar sm"><div class="tbar-track"><span class="tbar-fill" style="--w:${Math.max(3, (n / max) * 100)}%"></span></div><span class="tbar-val">${n}</span></div>`;
}

function replayLink(id) {
  if (!id) return "";
  return `<a class="replay" href="/replay?id=${encodeURIComponent(id)}">Replay</a>`;
}

const data = await fetch("/api/leaderboard/ai?lane=verified", { cache: "no-store" }).then((r) => r.json());
const ais = data.ais || [];
if (!ais.length) {
  empty.hidden = false;
} else {
  board.hidden = false;
  for (const row of ais) {
    const h = row.hardest || {};
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.rank}</td>
      <td class="kind-algorithm"><b>${row.ai}</b></td>
      <td>${h.puzzle || "—"}</td>
      <td>${h.htm ?? "—"}</td>
      <td>${h.step_count ?? "—"}</td>
      <td>${fmtTime(h.elapsed_sec)}</td>
      <td>${solvesBar(row.solves)}</td>
      <td>${replayLink(h.record_id)}</td>
    `;
    rows.append(tr);
  }
}

rows.addEventListener("click", (event) => {
  const btn = event.target.closest("button[data-ai]");
  if (!btn) return;
  const name = decodeURIComponent(btn.dataset.ai);
  const row = ais.find((a) => a.ai === name);
  if (!row) return;
  const list = (row.solved || [])
    .map(
      (s) => `<div class="alg"><b>${s.puzzle}</b><span>HTM ${s.htm ?? "—"}</span>${replayLink(s.record_id)}</div>`,
    )
    .join("");
  detail.hidden = false;
  detail.innerHTML = `<h2>${row.ai}</h2><div class="algs">${list}</div>`;
});
