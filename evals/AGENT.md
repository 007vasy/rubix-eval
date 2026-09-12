# Agent instructions

You are being evaluated on solving Rubik's cubes of size N×N×N, or a
3×3×3×3 hypercube when `kind` is `"4d"`, that are `scramble_depth`
random turns from solved.

Rules:

- No internet. Do not fetch cube solvers, docs, or APIs.
- Read `task.json` (stdin or `/eval/task.json`).
- Output only a move string to stdout or `/eval/solution.txt`.
  3D: WCA (`R U R'`). 4D: Zhao (`RU IF' OL2`).
- Do not assume you know the scramble; invert it only if you reconstruct it
  from the state yourself.

Scoring uses HTM (each move costs 1, including 180° turns) and also reports QTM.
