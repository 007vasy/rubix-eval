# Agent instructions

You are being evaluated on solving Rubik's cubes of size N×N×N, or a
3×3×3×3 hypercube when `kind` is `"4d"`, that are `scramble_depth`
random turns from solved.

**Visual / computer-use eval (default for agents):**

- Open `/eval`. Each load is a new random challenge (size 2–10, 1–10 moves
  from solved or fully scrambled). Look at the **image** of the cube. Click
  stickers. The page does not include cube JSON, the scramble, or an oracle.
  Do not read `/api/visual/boot` for state (there is none), `/api/task`, or
  the CLI.
- Left click = CW, right click = CCW, double-click = 180°. Green circle submits.

**Text eval (only if you were given `task.json`):**

- No internet. Do not fetch cube solvers, docs, or APIs.
- Read `task.json` (stdin or `/eval/task.json`).
- Output only a move string to stdout or `/eval/solution.txt`.
  3D: WCA (`R U R'`). 4D: Zhao (`RU IF' OL2`).
- Do not assume you know the scramble; invert it only if you reconstruct it
  from the state yourself.

Scoring uses HTM (each move costs 1, including 180° turns) and also reports QTM.
Each visual submit is recorded and compared to inverse-scramble, an HTM
optimal search, and Kociemba (3×3×3). You cannot see those numbers. Do not
open `/solves` or `/leaderboard`.
