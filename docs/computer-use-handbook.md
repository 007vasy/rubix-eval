# Computer-use eval — human support-check handbook

Use this when you are checking **the eval as it ships today**, not when you
are the agent under test. Sit in a browser, click what an agent would click,
and mark each check pass or fail.

The computer-use path is: the model opens **this browser page**, looks at the
WebGL cube, and turns stickers with the pointer. Done submits the viewer’s
move list; the server replays those moves on the withheld scramble. There is
no server-side Puppeteer on the hosted eval.

Open (browser/agent, web on) and Verified (operator offline, internet
disallowed) are different boards.

Default origin: `http://127.0.0.1:8765` locally, or the public Cloud Run URL.

---

## 0. Two different UIs — do not mix them up

| URL | What it is | Use it for support-check? |
| --- | --- | --- |
| `/eval` | **Computer-use eval.** Full-window live WebGL cube, help card, green **Done**. | **Yes. This is the eval.** |
| `/` | Interactive playground. Size slider, keyboard moves, HUD with HTM. | No. Practice cube only. |
| `/verified` | Offline harness board (internet disallowed). | Yes, as a reader. |
| GitHub / Issues | https://github.com/007vasy/rubix-eval | Reuse the harness; file bugs. |

If you can drag a sticker on a 3D mesh and see a size slider, you are on `/`,
not `/eval`.

---

## 1. Start the eval

From the repo, with the venv:

```bash
source .venv/bin/activate
rubix-eval visual --no-open --ai "Support check"
```

You should see:

```
cube:   http://127.0.0.1:8765/eval?random=1
```

The cube draws **in this tab** (WebGL). If `/eval` is a black rectangle, the
browser blocked WebGL — try another Chrome, do not keep scoring.

Hard refresh (`Ctrl+Shift+R`) after pulling JS so you are not on a cached
`visual-eval.js`.

---

## 2. Page map

Open these as the **human checker**, not as the agent:

| Page | Role |
| --- | --- |
| `/eval` | Agent window. Image + help card + green **Done**. |
| `/eval?kind=4d` | Same window, 4D (defaults to size 3). |
| `/eval?kind=3d&size=3&depth=1` | Pin a 3×3 that is one turn from solved. |
| `/eval?ai=Support%20check` | Tag the next Done click with that name. |
| `/solves` | Every Done click, solved or not. |
| `/replay?id=<record_id>` | Replay steps and clicks. |
| `/leaderboard` | Per-puzzle board (algorithms + human WR + named AIs). |
| `/ai` | AI-only: hardest solved challenge per named model. |

Query knobs on `/eval` (all optional). After load, the address bar is rewritten
to the puzzle you actually got so you can copy it.

| Param | Effect |
| --- | --- |
| `kind` | `3d` or `4d` (aliases: `ndim=4`, `kind=4`). |
| `size` | Cube size. 3D: 2–10. 4D: 2–5. Alias: `n`. |
| `depth` | How many random turns from solved: `1`–`10` or `full`. Aliases: `turns`, `d`. |
| `ai` / `agent` / `model` | Name stored on the solve. |
| `random` | `1` draws a fresh scramble. Omit to load the **official** puzzle for that size×turns (same cube every visit). |

Examples:

```
/eval?kind=3d&size=3&depth=1
/eval?kind=3d&size=5&turns=10
/eval?kind=4d&size=3&depth=full&ai=Astra
```

The top bar (Cube / Size / Turns / Load) writes these params and reloads.

Each load of `/eval` boots a **new** session. Reloading mid-check is a new cube.

---

## 3. What the eval window must look like

Open `/eval`. Expect:

1. Dark full-window **live cube** (WebGL canvas in this tab).
2. Bottom-left help card: left click / right click / double-click / drag /
   green button.
3. Bottom-right green **Done** pill.
4. **No** scramble string, **no** move list, **no** “oracle”, **no** JSON,
   **no** size/depth HUD, **no** letter labels on faces.

Pass if the cube is colored stickers on dark plastic and the only controls
are the help card + Done.

Fail if you see a net, WCA letters, “8 moves from solved”, cubie coordinates,
or a size slider.

---

## 4. 3D computer-use checks

Pin an easy cube so you can see cause and effect:

`http://127.0.0.1:8765/eval?kind=3d&size=3&depth=1&ai=Support%20check`

A depth-1 3×3 is one quarter-turn from solved. One face will have a stripe
or a swapped edge.

### 4.1 Picture

- [ ] Cube is centered, three faces visible (typical: U white, F green, R red
      — colors may vary with scramble).
- [ ] Stickers have gaps (plastic shows through). Not a flat net.

### 4.2 Left click = 90° CW

- [ ] Click a **sticker** (not empty space). After ~0.5s the image refreshes.
- [ ] That layer actually turned. Consecutive frames must look different.
- [ ] Clicking empty dark background does **not** turn a layer.

### 4.3 Right click = 90° CCW (undo)

- [ ] Right-click the **same sticker**. The layer turns the other way.
- [ ] After left then right on the same sticker, the picture matches the
      picture from before the left click (turned, then turned back).

If the browser context menu appears instead of a turn, that is a fail.

### 4.4 Double-click = 180°

- [ ] Double-click a sticker. The layer jumps 180°, not 90°.
- [ ] Double-click again. It should look like the start of this pair.

### 4.5 Orbit

- [ ] Drag on empty space. The camera moves; stickers do not permute.
- [ ] After orbit, a sticker click still turns a layer (not a no-op).

### 4.6 Submit unsolved vs solved

**Unsolved:** click **Done** without finishing.

- [ ] Brief red wash; flash text `not solved`.
- [ ] Cube image is unchanged.
- [ ] A new row appears on `/solves` with solved = no.

**Solved:** on `depth=1`, undo the scramble (the odd layer) until every face
is one color, then **Done**.

- [ ] Green wash; flash text `solved`.
- [ ] `/solves` shows a solved row tagged **Support check**.
- [ ] `/ai` lists that name only if it was a real solve (unnamed / “unspecified
      AI” must **not** appear).

Repeat at least once on `size=2` and once on a bigger visual cube
(`size=5` or `size=10`) if you are signing off a release.

---

## 5. 4D computer-use checks

`http://127.0.0.1:8765/eval?kind=4d&size=3&depth=1`

### 5.1 Picture

You should see **eight exploded cells** (small cubes in a plus-shape), not
one 3D cube:

- Center cluster plus arms: roughly U (top), D (bottom), F / B / L / R,
  and I / O (inner / outer, often purple-ish).
- Each cell is a 3×3×3 of stickers with gaps.

Fail if `/eval?kind=4d` 500s, shows a 3D cube, or prints a red error at the
top of the page.

Also boot:

- `/eval?kind=4d&size=2` — smaller cells, still eight of them.
- `/eval?kind=4d&size=4` and `size=5` — denser, still drawable.

### 5.2 Click a cell sticker

- [ ] Left-click a sticker on one of the eight cells. Some stickers on that
      cell (and a neighbor) change color. Image hash / look must change.
- [ ] Right-click the same sticker. Colors return to the pre-click picture.
- [ ] Double-click does a 180° cell twist.

Clicks that miss every cell should not add a turn. Clicks on a sticker must.

### 5.3 Orbit then click

- [ ] Drag empty space so a different cell faces you.
- [ ] Click a now-visible sticker. It still turns.

### 5.4 Submit

Same as 3D: Done on an unfinished cube → `not solved`. If you actually restore
a depth-1 4D (harder to see), Done → `solved`.

---

## 6. Sizes that should draw vs sizes that should not

Visual pool (must render on `/eval`):

| kind | sizes | What you should see |
| --- | --- | --- |
| 3d | 2–10 | One N×N×N cube |
| 4d | 2–5 | Eight exploded cells of size N |

Engine-only (JSON / ASCII / inverse tests). Booting them on `/eval` **as-is**:

| kind | sizes | As-is behavior |
| --- | --- | --- |
| 3d | 40 | Heavy but a cube may appear |
| 3d | 100 | Blank dark PNG |
| 4d | 6, 7 | Still draws (catalog marks `visual: false`) |
| 5d / 6d / 7d | listed n^d | **Blank dark PNG**, HTTP 200, no crash |

Mark 5D+ blank as **known**, not a regression, unless the server 500s.

---

## 7. Anti-cheat checks (you may use DevTools; the agent must not)

Do these on a fresh `/eval?kind=3d&size=3&depth=8` tab.

### 7.1 Boot payload

DevTools → Network → `/api/visual/boot`.

The JSON must include `id`, `kind`, `size`, and `state` (needed to draw).
Fail if you see `oracle` or `seed`. `state` on the open eval is expected
(the cube draws in the visitor’s browser). Verified runs do not use this page.

### 7.2 Frame

Hosted `/eval` does not use `/api/visual/frame`. A 404 here is fine.

### 7.3 Page globals

Console:

```js
window.__rubixEval
```

Allowed keys: `id`, `kind`, `usage`, `setUsage`, `input`.
Fail if cubies, history, or an oracle string are sitting on `window`.

### 7.4 Fake history

In the console, after the cube has loaded (do **not** solve it):

```js
await fetch("/api/visual/submit", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    id: window.__rubixEval.id,
    history: "R U R' U' F2",
    solved: true,
  }),
}).then((r) => r.json())
```

Pass: `solved` is false (unless you lucked into a solved cube) and `htm` is
**not** 5 from the fake string. The server must ignore client `history` once
it owns the cube.

### 7.5 Same-origin side doors (known, as-is)

These URLs exist on the same host. A cheating agent *could* open them. They
do **not** contain **this session’s** scramble (seed is not on boot), but they
are still leaks of *a* cube:

- `GET /api/task?size=3&depth=8&seed=1` — full `state`, no oracle.
- `GET /api/challenge?size=3&depth=1` — full `state` + seed.

`GET /api/visual/input` click responses may include `pick.cell` and mesh
counts. Submit JSON may include `algorithms[].moves` (inverse scramble).
Record those as **known holes** if you are scoring hardening, not as
“the visual page itself dumped the oracle.”

### 7.6 What the agent instructions forbid

`evals/AGENT.md` and `openshell/skills/rubiks-eval/SKILL.md` tell the agent
not to read `/api/task`, page source, or `/solves`. Verified OpenShell runs
also **block public internet** (`openshell/policy.yaml`): Chromium may load
local `:8766/eval` only; agent CLIs cannot curl cube JSON. See
[openshell/README.md](../openshell/README.md).

---

## 8. After Done — solves, replay, boards

### 8.1 `/solves`

- [ ] Your attempt is listed (solved or not).
- [ ] Stats: clicks, steps, time. Tokens only if you passed `?tokens=`.
- [ ] No oracle / scramble in the on-screen detail.

### 8.2 Replay

From a row with a replay link, or `/replay?id=<record_id>`:

- [ ] 3D and 4D records draw the cube and step through history.
- [ ] **Reset / Prev / Play / Next** move the cube.
- [ ] Click list matches what you did (left / right / double / orbit).
- [ ] 5D+ records may say the puzzle is not drawn; the move list should
      still be there.

### 8.3 `/leaderboard`

- [ ] Grouped by cube size and by scramble depth.
- [ ] Human WR highlighted on **full** scrambles only (not on d1–d10).
- [ ] Named AI rows can link to replay.

### 8.4 `/ai`

- [ ] Only **named** models. No “unspecified AI”.
- [ ] Rank = hardest solved challenge (dimension, then size, then full vs
      shallow, then depth).
- [ ] An unsolved Done must **not** become that model’s hardest solve.

---

## 9. Controls cheat-sheet (what you are checking)

| Input | Eval `/eval` | Playground `/` |
| --- | --- | --- |
| Left click sticker | 90° CW, server-side | Live WebGL turn |
| Right click sticker | 90° CCW | Live WebGL turn |
| Double-click sticker | 180° | 180° |
| Drag empty space | Orbit (live) | Orbit (live) |
| Green **Done** | Grade + write `solves/` | Not present |
| Keyboard U/R/F… | **None** (fail if it works) | Yes, on `/` |

HTM: every recorded turn costs 1, including 180°. QTM counts 180° as 2.

---

## 10. Suggested 20-minute pass (sign-off)

Do these in order. Stop on the first unexpected fail.

1. Start `rubix-eval visual --no-open --ai "Support check"`.
2. Open `/eval`. Confirm live cube + help + Done + GitHub/Issues. No oracle.
3. Network: boot JSON has `id, kind, size, state` and no `oracle` / `seed`.
4. `/eval?kind=3d&size=3&depth=1` — left click changes the picture; right
   click restores it; double-click is 180°; drag orbits.
5. Done while unsolved → `not solved` + `/solves` row.
6. Undo the depth-1 scramble, Done → `solved` + named row on `/ai`.
7. Open that replay; Play steps through your clicks.
8. `/eval?kind=4d&size=3&depth=1` — eight cells; click + right-click restore.
9. `/eval?kind=4d` with no size still draws 3⁴ (not a 500).
10. Console fake-history submit is ignored.
11. `/eval?kind=5d&size=2` should not 500 (drawing may be empty).

---

## 11. As-is limitations (do not file these as “eval is broken”)

- **5D–7D** and **100³** visual boots return 200 and a black PNG. They are
  JSON/engine puzzles, not computer-use drawing.
- **4D 6⁴ / 7⁴** are marked non-visual in the catalog but still draw if you
  force `?kind=4d&size=6`.
- Inspect **text** tasks (`inspect eval …@rubix`) give the model ASCII + JSON
  on purpose. That is not the browser computer-use eval. Browser CU is `/eval`.
  Inspect visual (`@rubix_visual`) is `look()` / `twist()` tools, no PNG.
- Default `pip install -e .` does not install Inspect. Use
  `pip install -e ".[inspect]"`.
- Same-origin `/api/task` and `/api/challenge` still serve cubie JSON for
  **other** puzzles. Submit may echo algorithm move strings. See §7.5.
- There is no `submit()` Inspect tool; the visual Inspect scorer reads the
  `twist()` history.

---

## 12. Pass / fail sheet

Copy and tick.

```
Date:
Commit:
Server: rubix-eval visual on :8765

[ ] /eval is the computer-use cube (help + Done), not the playground slider
[ ] Boot JSON has no oracle / state / scramble
[ ] 3×3×3 depth-1: left click turns
[ ] Same sticker right click restores
[ ] Double-click is 180°
[ ] Drag empty space orbits
[ ] Done unsolved → "not solved"
[ ] Done solved → "solved" and a named /solves row
[ ] Replay plays the clicks
[ ] /ai has the name, not "unspecified AI"
[ ] /eval?kind=4d shows eight cells
[ ] 4D left click turns; right click restores
[ ] Fake history POST does not count as a solve
[ ] Keyboard letters do nothing on /eval
[ ] 5D boot does not 500

Known holes noted: [ ] /api/task  [ ] algorithms on submit  [ ] pick.cell
```

---

## 13. If something fails

1. Hard refresh `/eval`.
2. Confirm the process is `python -m rubix_eval visual` (not `rubix-eval view`).
3. Confirm you are on `/eval`, not `/`.
4. Restart the visual server so Puppeteer reloads `web/js/renderer.js`.
5. `pytest -q` — engine and boot-hiding tests. A green suite does **not**
   prove clicks; that is this handbook.

Related agent text (do not follow it as the checker): `evals/AGENT.md`.
Related product README: visual-only section in `README.md`.
