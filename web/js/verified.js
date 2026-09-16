const empty = document.getElementById("empty");
const board = document.getElementById("board");
const rows = document.getElementById("rows");
const detail = document.getElementById("detail");

function fmtTime(s) {
  if (s == null || Number.isNaN(s)) return "—";
  if (s < 0.1) return `${(s * 1000).toFixed(1)} ms`;
  if (s < 60) return `${s.toFixed(2)} s`;
  const m = Math.floor(s / 60);
  const r = (s - m * 60).toFixed(2).padStart(5, "0");
  return `${m}:${r}`;
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
      <td class="kind-ai">${row.ai}</td>
      <td>${h.puzzle || "—"}</td>
      <td>${h.htm ?? "—"}</td>
      <td>${h.step_count ?? "—"}</td>
      <td>${fmtTime(h.elapsed_sec)}</td>
      <td>${row.solves}</td>
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
