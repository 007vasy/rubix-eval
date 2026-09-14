const empty = document.getElementById("empty");
const controls = document.getElementById("controls");
const subnav = document.getElementById("subnav");
const boards = document.getElementById("boards");
const detail = document.getElementById("detail");
const modeTabs = [...document.querySelectorAll(".tab[data-mode]")];

function sizeKey(row) {
  return row.kind === "4d" ? "3x3x3x3" : `${row.size}x${row.size}x${row.size}`;
}

function sizeLabel(row) {
  return row.kind === "4d" ? "3×3×3×3 (4D)" : `${row.size}×${row.size}×${row.size}`;
}

function scrambleKey(row) {
  if (row.depth_label) return String(row.depth_label);
  return String(row.scramble_depth ?? "");
}

function scrambleLabel(row) {
  const key = scrambleKey(row);
  if (key === "full") return `Full scramble · ${row.scramble_depth} turns`;
  return `${key} turn${key === "1" ? "" : "s"} from solved`;
}

function ratio(row) {
  if (row.optimality_ratio == null) return "—";
  return `${Math.round(row.optimality_ratio * 100)}%`;
}

function bestFirst(a, b) {
  const as = a.solved ? 0 : 1;
  const bs = b.solved ? 0 : 1;
  if (as !== bs) return as - bs;
  const ah = a.ai_htm == null ? 1e9 : a.ai_htm;
  const bh = b.ai_htm == null ? 1e9 : b.ai_htm;
  if (ah !== bh) return ah - bh;
  const ae = a.elapsed_sec == null ? 1e9 : a.elapsed_sec;
  const be = b.elapsed_sec == null ? 1e9 : b.elapsed_sec;
  return ae - be;
}

function rowHtml(row) {
  const solved = row.solved ? (row.optimal ? "optimal" : "solved") : "unsolved";
  return `<tr>
    <td>${(row.recorded_at || "").replace("T", " ").slice(0, 19)}</td>
    <td>${row.ai || "unspecified AI"}</td>
    <td>${row.ai_htm ?? "—"}</td>
    <td>${row.step_count ?? "—"}</td>
    <td>${row.click_count ?? "—"}</td>
    <td>${row.tokens_used != null ? Number(row.tokens_used).toLocaleString() : "—"}</td>
    <td>${row.best_htm ?? "—"}</td>
    <td>${ratio(row)}</td>
    <td>${row.excess_vs_best ?? "—"}</td>
    <td>${row.best_algorithm || "—"}</td>
    <td><a class="replay" href="/replay?id=${encodeURIComponent(row.record_id)}">Replay</a>
      <button class="row ${row.solved ? "ok" : "bad"}" data-id="${row.record_id}">${solved}</button></td>
  </tr>`;
}

function tableFor(rows) {
  if (!rows.length) return `<p class="empty-row">No attempts in this category.</p>`;
  return `<table>
    <thead><tr>
      <th>When</th><th>AI</th><th>HTM</th><th>Steps</th><th>Clicks</th><th>Tokens</th><th>Best known</th><th>Ratio</th><th>Excess</th><th>Algorithm</th><th></th>
    </tr></thead>
    <tbody>${rows.map(rowHtml).join("")}</tbody>
  </table>`;
}

let ROWS = [];
let mode = "size";
let selected = "";

function unique(values) {
  const out = [];
  for (const v of values) if (v !== "" && !out.includes(v)) out.push(v);
  return out;
}

function render() {
  boards.innerHTML = "";
  subnav.innerHTML = "";
  modeTabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.mode === mode));
  if (!ROWS.length) return;

  if (mode === "size") {
    const keys = unique(ROWS.map(sizeKey));
    if (!selected || !keys.includes(selected)) selected = keys[0];
    for (const key of keys) {
      const sample = ROWS.find((r) => sizeKey(r) === key);
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = sample ? sizeLabel(sample) : key;
      btn.classList.toggle("active", key === selected);
      btn.addEventListener("click", () => {
        selected = key;
        render();
      });
      subnav.append(btn);
    }
    const subset = ROWS.filter((r) => sizeKey(r) === selected);
    const depths = unique(subset.map(scrambleKey));
    const el = document.createElement("section");
    el.className = "board";
    const sample = subset[0];
    el.innerHTML = `<h2>${sample ? sizeLabel(sample) : selected}</h2>`;
    for (const depth of depths) {
      const group = subset.filter((r) => scrambleKey(r) === depth).slice().sort(bestFirst);
      const title = group[0] ? scrambleLabel(group[0]) : depth;
      el.insertAdjacentHTML(
        "beforeend",
        `<section class="group"><h3>${title}</h3>${tableFor(group)}</section>`,
      );
    }
    boards.append(el);
    return;
  }

  const keys = unique(ROWS.map(scrambleKey));
  if (!selected || !keys.includes(selected)) selected = keys[0];
  for (const key of keys) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = key === "full" ? "Full scramble" : `d${key}`;
    btn.classList.toggle("active", key === selected);
    btn.addEventListener("click", () => {
      selected = key;
      render();
    });
    subnav.append(btn);
  }
  const subset = ROWS.filter((r) => scrambleKey(r) === selected);
  const el = document.createElement("section");
  el.className = "board";
  el.innerHTML = `<h2>${subset[0] ? scrambleLabel(subset[0]) : selected}</h2>`;
  const sizes = unique(subset.map(sizeKey));
  for (const key of sizes) {
    const group = subset.filter((r) => sizeKey(r) === key).slice().sort(bestFirst);
    const title = group[0] ? sizeLabel(group[0]) : key;
    el.insertAdjacentHTML(
      "beforeend",
      `<section class="group"><h3>${title}</h3>${tableFor(group)}</section>`,
    );
  }
  boards.append(el);
}

modeTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    mode = tab.dataset.mode;
    selected = "";
    render();
  });
});

boards.addEventListener("click", async (event) => {
  const btn = event.target.closest("button[data-id]");
  if (!btn) return;
  const rec = await fetch(`/api/solves?id=${encodeURIComponent(btn.dataset.id)}`).then((r) => r.json());
  const algs = (rec.algorithms || [])
    .map(
      (a) => `<div class="alg"><b>${a.label}</b><span>HTM ${a.htm ?? "—"}</span><span>${a.solved ? "solves" : a.error || "fail"}</span><code>${a.moves || ""}</code></div>`,
    )
    .join("");
  const opt = rec.optimality || {};
  const att = rec.attempt || {};
  const who = rec.ai || att.ai || "unspecified AI";
  detail.hidden = false;
  detail.innerHTML = `
    <h2>${rec.record_id}</h2>
    <p><b>${who}</b> ${att.solved ? "solved" : "did not solve"} in <b>${att.htm}</b> HTM.
       ${att.step_count ?? "—"} steps · ${att.click_count ?? "—"} clicks ·
       ${att.tokens_used != null ? Number(att.tokens_used).toLocaleString() : "—"} tokens
       ${att.token_cost_usd != null ? `· $${Number(att.token_cost_usd).toFixed(2)}` : ""}.
       Best known: <b>${opt.best_htm ?? "—"}</b> (${opt.best_label || "—"}).
       Ratio ${opt.optimality_ratio ?? "—"} · excess ${opt.excess_vs_best ?? "—"}.</p>
    <p><a class="replay" href="/replay?id=${encodeURIComponent(rec.record_id)}">Replay this attempt</a></p>
    <div class="algs">${algs}</div>
    <pre>${att.moves || "(no move history)"}</pre>
  `;
});

const data = await fetch("/api/solves", { cache: "no-store" }).then((r) => r.json());
ROWS = data.solves || [];
if (!ROWS.length) {
  empty.hidden = false;
} else {
  controls.hidden = false;
  render();
}
