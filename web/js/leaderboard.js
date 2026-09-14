const status = document.getElementById("status");
const subnav = document.getElementById("subnav");
const boards = document.getElementById("boards");
const modeTabs = [...document.querySelectorAll(".tab[data-mode]")];

function fmtTime(s) {
  if (s == null || Number.isNaN(s)) return "—";
  if (s <= 0) return "< 1 µs";
  if (s < 0.001) return `${Math.max(1, Math.round(s * 1e6))} µs`;
  if (s < 0.1) return `${(s * 1000).toFixed(2)} ms`;
  if (s < 60) return `${s.toFixed(2)} s`;
  const m = Math.floor(s / 60);
  const r = (s - m * 60).toFixed(2).padStart(5, "0");
  return `${m}:${r}`;
}

function kindLabel(kind) {
  if (kind === "human") return "Human record";
  if (kind === "algorithm") return "Known algorithm";
  if (kind === "ai") return "AI";
  return kind;
}

function scrambleTitle(label, depth) {
  if (label === "full") return `Full scramble · ${depth} random turns`;
  const n = String(label);
  return `${n} turn${n === "1" ? "" : "s"} from solved`;
}

function entryRow(row, { markBestAlg = false } = {}) {
  const wr = row.highlight || row.kind === "human";
  const badge = wr ? `<span class="badge-wr">${row.badge || "Human WR"}</span>` : "";
  const best = markBestAlg && row.kind === "algorithm" && row.rank === 1 ? " best-alg" : "";
  const replay =
    row.kind === "ai" && row.record_id
      ? `<a class="replay" href="/replay?id=${encodeURIComponent(row.record_id)}">Replay</a>`
      : "";
  const extra = [row.note || row.source || "", replay].filter(Boolean).join(" · ");
  return `<tr class="${wr ? "human-wr" : ""}${best}">
    <td>${row.rank}</td>
    <td class="kind-${row.kind}">${row.who}${badge}</td>
    <td>${kindLabel(row.kind)}</td>
    <td>${fmtTime(row.seconds)}</td>
    <td>${row.htm ?? "—"}</td>
    <td class="note">${extra}</td>
  </tr>`;
}

function rankedTable(entries) {
  if (!entries.length) {
    return `<p class="empty-row">No times yet.</p>`;
  }
  const firstAlgRank = entries.find((e) => e.kind === "algorithm")?.rank;
  const rows = entries
    .map((row) => entryRow(row, { markBestAlg: row.rank === firstAlgRank }))
    .join("");
  return `<table>
    <thead><tr><th>#</th><th>Who</th><th>Kind</th><th>Time</th><th>HTM</th><th></th></tr></thead>
    <tbody>${rows}</tbody>
  </table>`;
}

function groupBlock(title, sub, entries) {
  return `<section class="group">
    <h3>${title}</h3>
    ${sub ? `<p class="sub">${sub}</p>` : ""}
    ${rankedTable(entries)}
  </section>`;
}

let DATA = { boards: [] };
let mode = "size";
let selected = "";

function scrambleLabels(boards) {
  const seen = [];
  for (const board of boards) {
    for (const g of board.groups || []) {
      if (!seen.includes(g.depth_label)) seen.push(g.depth_label);
    }
  }
  return seen;
}

function render() {
  const boardList = DATA.boards || [];
  subnav.innerHTML = "";
  boards.innerHTML = "";
  modeTabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.mode === mode));

  if (mode === "size") {
    if (!selected || !boardList.some((b) => b.version === selected)) {
      selected = boardList[0]?.version || "";
    }
    for (const board of boardList) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = board.label;
      btn.classList.toggle("active", board.version === selected);
      btn.addEventListener("click", () => {
        selected = board.version;
        render();
      });
      subnav.append(btn);
    }
    const board = boardList.find((b) => b.version === selected);
    if (!board) return;
    const el = document.createElement("section");
    el.className = "board";
    const wr = board.human
      ? `Human WR on a full scramble: <b class="kind-human">${fmtTime(board.human.seconds)} · ${board.human.person}</b>`
      : "No competitive human record for this size.";
    const refs = (board.references || [])
      .map((r) => `<a href="${r.url}" target="_blank" rel="noreferrer">${r.name}</a> — ${r.note}`)
      .join("<br>");
    el.innerHTML = `<h2>${board.label}</h2><p class="sub">${wr}</p>${refs ? `<p class="sub refs">${refs}</p>` : ""}`;
    for (const group of board.groups || []) {
      const extra = group.full && board.human ? "Human world record is highlighted." : "";
      el.insertAdjacentHTML("beforeend", groupBlock(group.title, extra, group.entries || []));
    }
    boards.append(el);
    return;
  }

  const labels = scrambleLabels(boardList);
  if (!selected || !labels.includes(selected)) selected = labels.includes("full") ? "full" : labels[0] || "";
  for (const label of labels) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = label === "full" ? "Full scramble" : `d${label}`;
    btn.classList.toggle("active", label === selected);
    btn.addEventListener("click", () => {
      selected = label;
      render();
    });
    subnav.append(btn);
  }
  const wrap = document.createElement("div");
  const heading = selected === "full" ? "Full scramble" : scrambleTitle(selected, selected);
  wrap.innerHTML = `<section class="board"><h2>${heading}</h2>
    <p class="sub">${selected === "full" ? "Human world records are highlighted on each size." : "End-step: known algorithms only (plus any AI solves). No human WR."}</p></section>`;
  const host = wrap.firstElementChild;
  for (const board of boardList) {
    const group = (board.groups || []).find((g) => g.depth_label === selected);
    if (!group) continue;
    const extra = group.full && board.human ? `Human WR ${fmtTime(board.human.seconds)} · ${board.human.person}` : "";
    host.insertAdjacentHTML("beforeend", groupBlock(board.label, extra, group.entries || []));
  }
  boards.append(host);
}

modeTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    mode = tab.dataset.mode;
    selected = "";
    render();
  });
});

status.innerHTML = `<span class="spin">Timing local solvers…</span>`;
let data = await fetch("/api/leaderboard", { cache: "no-store" }).then((r) => r.json());
if (!data.updated_at) {
  data = await fetch("/api/leaderboard?bench=1", { cache: "no-store" }).then((r) => r.json());
}
DATA = data;
const asOf = data.human_records_as_of ? ` Human records as of ${data.human_records_as_of}.` : "";
status.textContent =
  (data.updated_at
    ? `Algorithm times cached ${String(data.updated_at).slice(0, 19).replace("T", " ")} UTC.`
    : "Algorithm times from recorded solves.") + asOf;
render();
