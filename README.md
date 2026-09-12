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
rubix-eval run --4d --oracle --depths 1,5,10
```

The 4D puzzle is a **3×3×3×3** (tesseract / MagicCube4D analog): eight cubic
cells `R L U D F B I O`. Moves are Zhao 2c clicks such as `RU` (twist the R
cell 90° around U).

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
