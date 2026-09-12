---
name: rubiks-eval
description: Solve a scrambled cube by looking at it and clicking stickers. Visual only. Computer use.
---

# Visual cube eval (computer use)

You are solving a scrambled Rubik's cube **by looking at it**. You do not get
the scramble, a net, JSON, or move names.

There is no internet. Do not call external APIs. If you need a model, use
`https://inference.local` only.

## What you may do

1. Open the cube window (the page at `/eval`, usually `http://127.0.0.1:8765/eval`).
2. Look at the colored stickers.
3. Turn the cube with the pointer:
   - **Left click** a sticker = 90° clockwise on that layer/cell
   - **Right click** a sticker = 90° counter-clockwise
   - **Double-click** a sticker = 180°
   - **Drag empty space** to orbit / look around
4. When every side is a single color, click the **green circle** in the
   bottom-right to submit.

On the 4D puzzle you will see several colored cubes (cells of a tesseract).
Click stickers on those cells the same way. There are no letter labels.

## What you must not do

- Do not open `/eval/task.json`, `task.json`, or any JSON.
- Do not run `rubix-eval show`, `oracle`, or `grade`.
- Do not read the page source, network responses, or DevTools.
- Do not type face letters as a substitute for looking at the stickers.
- Do not fetch `/api/task` (that endpoint is for humans, not this eval).

If a terminal is available, ignore it for this task. Use the display.

## Scoring (you cannot see these numbers)

Solved, move count (HTM/QTM), and extra moves vs scramble depth.
Shorter correct solutions score better.
