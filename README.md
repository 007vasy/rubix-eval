# rubix-eval

Offline **NxNxN Rubik’s cube** evaluation for sandboxed agents, plus an
interactive 3D cube you can spin up in a browser.

The eval parameters are:

| Parameter | Meaning |
| --- | --- |
| **size** `N` | Cube is `N×N×N` (2×2×2, 3×3×3, or any bigger cube) |
| **kind** | `3d` or `4d` (the 3×3×3×3 hypercube) |
| **scramble_depth** | How many random turns the cube is from solved |
| **step cost** | HTM (each move = 1) and QTM (`U2` = 2) |

The agent never sees the scramble sequence — only the resulting state — and
should solve **without internet**. NVIDIA OpenShell runs that constraint as a
default-deny sandbox; `https://inference.local` is still available for a local
or gateway-routed model.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

Create a puzzle that is 8 turns from solved on a 3×3×3:

```bash
rubix-eval task --size 3 --depth 8 --seed 1 -o task.json
rubix-eval show task.json
```

Grade a solution:

```bash
echo "R U R' U'" > solution.txt
rubix-eval grade task.json --solution solution.txt
```

The inverse of the withheld scramble always solves (engine check, not for agents):

```bash
rubix-eval oracle task.json
rubix-eval grade task.json --solution "$(rubix-eval oracle task.json)"
```

Run the default suite (2×2×2, 3×3×3, 4×4×4, 5×5×5, 7×7×7) against a solver
command. The solver reads task JSON on stdin and writes moves on stdout.

```bash
rubix-eval run --oracle
rubix-eval run --solver ./my_solver.sh --sizes 2,3 --depths 1,5,10 --trials 3
rubix-eval task --4d --depth 8 --seed 1 -o hyper.json
rubix-eval task --4d --size 4 --depth full --seed 1   # 4×4×4×4 on demand
rubix-eval task --ndim 5 --size 3 --depth 8           # 3^5
rubix-eval run --4d --oracle --depths 1,5,10
```

The 4D puzzle is a **3×3×3×3** (tesseract): eight cubic cells `R L U D F B I O`.
Moves are Zhao 2c clicks such as `RU` (twist the R cell 90° around U).

4D reference software (not bundled; used for records, colors, and the cheat-solve
= inverse-scramble baseline):

- [MagicCube4D](https://github.com/cutelyaware/magiccube4d) — Melinda Green,
  Don Hatch, Jay Berkenbilt, Roice Nelson. Canonical 3⁴ UI and
  [Hall of Fame](https://superliminal.com/cube/halloffame.htm).
- [MPUlt](https://github.com/cutelyaware/MPUlt) — Andrey Astrelin, Magic Puzzle
  Ultimate, higher-dimensional twisty puzzles.

Bigger cubes and higher dimensions are created on demand (`--size`, `--ndim`
4–7). There does not need to be a solver — inverse scramble always exists.
Every n^d that has a published human record (MC4D / MPUlt / Hyperspeedcube /
MC7D) is on the leaderboard so an AI computer-use run can beat it.

The 3⁴ speed WR follows
[Hypercubing records](https://hypercubing.xyz/leaderboards/records/) (MC4D
lineage). Shortest human 3⁴ is 191 twists (Charles Doan, 2021).

## Challenges

Each time a model **requests a challenge**, a new instance is drawn:

- **Sizes:** 2×2×2, 3×3×3, …, 10×10×10, plus 40×40×40 and 100×100×100
- **Distance from solved:** 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 random turns, or **fully scrambled** (WCA-length: 11 / 25 / 45 / … / 1200 depending on N)
- **Seed:** new on every request, so the same size×depth pair is never the same scramble twice

```bash
rubix-eval challenge              # random size, depth, seed
rubix-eval challenge --size 3     # random depth + seed on a 3×3×3
rubix-eval challenge --depth 1    # random size, one move from solved
rubix-eval challenge --depth full --size 4
rubix-eval challenge --list       # print the catalog
```

HTTP (no oracle, scramble withheld):

```
GET /api/challenge
GET /api/challenge?size=5&depth=10
GET /api/challenges
```

The visual page draws a **new random challenge on every load** (browser-safe sizes 2–10). Giant cubes (40, 100) are text/API challenges only.

## Visual-only eval (computer use)

The agent should **only look at the cube** and turn it with the pointer. No
JSON, no ASCII net, no scramble, no move names on screen.

```bash
rubix-eval visual                 # random challenge on every load
rubix-eval visual --ai "Grok 4.6" # tag recorded solves with this AI
rubix-eval visual --size 3        # random depth on a 3×3×3
rubix-eval visual --4d            # random 3×3×3×3 hypercube
rubix-eval visual --size 3 --depth 8 --seed 1
```

Opens `http://127.0.0.1:8765/eval`:

- Left click a sticker = 90° clockwise
- Right click = 90° counter-clockwise
- Double-click = 180°
- Drag empty space to orbit
- Green circle = submit

The harness grades at `http://127.0.0.1:8765/api/visual/grade` after submit.
Every **Done** click is written under `solves/` and scored against known
algorithms (the agent-facing `/eval` page does not show these numbers).
Pass `--ai "Grok 4.6"` (or `?ai=` / `RUBIX_AI`) so the log and leaderboard
name which AI solved it.

| Algorithm | What it is |
| --- | --- |
| Inverse scramble | Exact inverse of the withheld generating sequence |
| God's algorithm | Optimal HTM search (bidirectional BFS on the eval move set) |
| Kociemba two-phase | Standard 3×3×3 solver (near-optimal, always a solution) |

`optimality_ratio` is `best_htm / ai_htm` (1.0 means the AI matched the best
known length). Review the log at `http://127.0.0.1:8765/solves` or:

```bash
rubix-eval solves
rubix-eval solves <record-id>
```

A per-version **leaderboard** lives at `http://127.0.0.1:8765/leaderboard`:

- **Full scramble** (WCA-length): how fast the local solvers produce a
  solution, plus the human world-record single (WCA for 2×2–7×7; unofficial
  for 8×8–10×10 and 3×3×3×3).
- **End-step** (1–10 turns from solved): algorithm time only — there is no
  human record for a cube that is already almost solved.

```bash
rubix-eval leaderboard
rubix-eval leaderboard --bench   # time the solvers and cache the result
rubix-eval leaderboard --ai      # AI-only: hardest challenge each model solved
```

A separate **AI leaderboard** at `http://127.0.0.1:8765/ai` ranks models by the
hardest challenge they have actually solved (higher dimension, then bigger
cube, then full scramble, then more turns from solved).

The boot API does not include the scramble or oracle. Point a computer-use
agent at that window (screenshot + click). Inference stays on
`inference.local` inside NVIDIA OpenShell; the cube UI is this local page.

## 3D cube in the browser

```bash
rubix-eval view
# open http://127.0.0.1:8765/
```

Or serve the `web/` folder as static files. Drag a sticker to turn that layer,
drag empty space to orbit, use `U D L R F B` (shift for `'`). Size goes from
2×2×2 through 7×7×7. Toggle **4D 3³×3** for the exploded eight-cell hypercube
and click a sticker to twist that cell. The HUD reports HTM / QTM versus
scramble depth.

## OpenShell (no internet)

```bash
curl -LsSf https://raw.githubusercontent.com/NVIDIA/OpenShell/main/install.sh | sh

openshell sandbox create \
  --name rubix-eval \
  --from . \
  --policy ./openshell/policy.yaml \
  --no-auto-providers
```

`openshell/policy.yaml` has an empty `network_policies` map, so the agent cannot
reach the public internet. Configure a local model with OpenShell inference
routing if the agent needs a LLM.

Inside the sandbox:

```bash
rubix-eval task --size 3 --depth 8 --seed 1 -o /eval/task.json
# agent writes /eval/solution.txt
rubix-eval grade /eval/task.json --solution /eval/solution.txt
```

## Notation

WCA face turns: `R`, `U'`, `F2`. Inner slices on big cubes: `2R`, `3Uw`.
Wide turns: `Rw`. Metric is HTM unless you read the `qtm` field.

## License

MIT
