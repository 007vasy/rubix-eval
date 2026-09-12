---
name: rubiks-eval
description: Solve an NxNxN Rubik's cube eval task without network access.
---

# Rubik's cube eval

You are solving a scrambled NxNxN cube, or a 3×3×3×3 (4D) hypercube when
`kind` is `"4d"`. There is no internet. Do not call external APIs. If you
need a model, use `https://inference.local` only.

## Task files

- `/eval/task.json` is the puzzle. It has `size`, `scramble_depth`, and `state`.
- The scramble sequence is withheld on purpose. Invert-guessing it is cheating
  only if it appears in the file; it will not.
- Write your solution to `/eval/solution.txt` as WCA moves, space-separated.

## CLI

```bash
rubix-eval show /eval/task.json --no-color
rubix-eval apply /eval/task.json "R U R'"
# When finished:
# echo "R U R' U'" > /eval/solution.txt
# rubix-eval grade /eval/task.json --solution /eval/solution.txt
```

## Notation (3D)

- Faces: `U D L R F B`
- `'` is counter-clockwise, `2` is a half turn
- Inner slices on big cubes: `2R`, `3U`
- Wide turns: `Rw`, `3Uw`

## Notation (4D, `kind: "4d"`)

A 3×3×3×3 has eight cubic cells: `R L U D F B I` (inside) `O` (outside).
`RU` twists the R cell 90° around U (2c click). `RU'` and `RU2` as usual.
The task JSON `state.cells` is an 8-cell map of 3×3×3 sticker tensors.

## Scoring

You are graded on:

1. `solved` — every face one color
2. `htm` — number of moves (half-turn metric)
3. `qtm` — quarter-turn metric (`U2` costs 2)
4. `excess_htm` — `htm - scramble_depth` (lower is better; negative means a shorter path than the scramble)
5. Stay under `max_moves`

Prefer a short correct solution over a long one.
