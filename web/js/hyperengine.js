/** 3×3×3×3 hypercube. Keep in lockstep with src/rubix_eval/hypercube.py */

export const CELLS = ["R", "L", "U", "D", "F", "B", "I", "O"];
export const CELL_AXIS = {
  R: [0, 2],
  L: [0, 0],
  U: [1, 2],
  D: [1, 0],
  F: [2, 2],
  B: [2, 0],
  O: [3, 2],
  I: [3, 0],
};
export const AXIS_CELL = {
  "0,2": "R",
  "0,0": "L",
  "1,2": "U",
  "1,0": "D",
  "2,2": "F",
  "2,0": "B",
  "3,2": "O",
  "3,0": "I",
};

export function cellAxisOf(cell, n = 3) {
  const lo = { L: 0, D: 1, B: 2, I: 3 };
  const hi = { R: 0, U: 1, F: 2, O: 3 };
  if (cell in lo) return [lo[cell], 0];
  if (cell in hi) return [hi[cell], n - 1];
  return CELL_AXIS[cell];
}

export function axisCellOf(axis, coord, n = 3) {
  const pair = [
    ["L", "R"],
    ["D", "U"],
    ["B", "F"],
    ["I", "O"],
  ][axis];
  if (!pair) return AXIS_CELL[`${axis},${coord}`];
  if (coord === 0) return pair[0];
  if (coord === n - 1) return pair[1];
  return AXIS_CELL[`${axis},${coord}`];
}
export const CELL_COLOR = {
  R: "R",
  L: "O",
  U: "W",
  D: "Y",
  F: "G",
  B: "B",
  I: "P",
  O: "C",
};
export const COLOR_HEX = {
  // MagicCube4D DEFAULT_FACE_COLORS (cutelyaware/magiccube4d MagicCube.java).
  W: 0xffffff,
  Y: 0xffe500,
  G: 0x009e49,
  B: 0x0080ff,
  O: 0xff8d00,
  R: 0xff0000,
  P: 0x9959ff,
  C: 0xff7fff,
};
export const PLASTIC = 0x111111;
export const OPPOSITE = {
  R: "L",
  L: "R",
  U: "D",
  D: "U",
  F: "B",
  B: "F",
  I: "O",
  O: "I",
};

export function adjacentCells(cell) {
  const axis = CELL_AXIS[cell][0];
  return CELLS.filter((name) => CELL_AXIS[name][0] !== axis);
}

function permSign(seq) {
  let inv = 0;
  for (let i = 0; i < seq.length; i += 1) {
    for (let j = i + 1; j < seq.length; j += 1) if (seq[i] > seq[j]) inv += 1;
  }
  return inv % 2 ? -1 : 1;
}

export function twist90Position(pos, cell, axisCell, turns, n = 3) {
  const [cellAxis, cellExt] = cellAxisOf(cell, n);
  const [rotAxis, rotExt] = cellAxisOf(axisCell, n);
  turns = ((turns % 4) + 4) % 4;
  if (rotExt === 0) turns = (-turns + 4) % 4;
  if (cellExt === 0) turns = (-turns + 4) % 4;
  if (!turns) return pos.slice();
  const [i, j] = orientedPlane(cellAxis, rotAxis);
  const out = pos.slice();
  let ci = out[i];
  let cj = out[j];
  for (let t = 0; t < turns; t += 1) {
    const nextI = n - 1 - cj;
    const nextJ = ci;
    ci = nextI;
    cj = nextJ;
  }
  out[i] = ci;
  out[j] = cj;
  return out;
}

export function orientedPlane(cellAxis, rotAxis) {
  const others = [0, 1, 2, 3].filter((a) => a !== cellAxis && a !== rotAxis);
  let i = others[0];
  let j = others[1];
  if (permSign([cellAxis, rotAxis, i, j]) < 0) [i, j] = [j, i];
  return [i, j];
}

const PARSE_RE = /([UDLRFBIO]{2,4})(2'|2|'|3)?/y;
const TURNS_MAP = { "": 1, 2: 2, "'": 3, "2'": 2, 3: 3 };

export function parseHyperMoves(algorithm) {
  if (!algorithm || !String(algorithm).trim()) return [];
  const text = String(algorithm);
  const moves = [];
  let pos = 0;
  while (pos < text.length) {
    if (/\s|,|;/.test(text[pos])) {
      pos += 1;
      continue;
    }
    PARSE_RE.lastIndex = pos;
    const match = PARSE_RE.exec(text);
    if (!match || match.index !== pos) {
      throw new Error(`Invalid 4D move notation at ${JSON.stringify(text.slice(pos))}`);
    }
    pos = PARSE_RE.lastIndex;
    const letters = match[1];
    const turnsRaw = TURNS_MAP[match[2] || ""];
    const cell = letters[0];
    const rest = letters.slice(1).split("");
    if (rest.length === 1) {
      moves.push({ cell, axis: rest[0], turns: turnsRaw, order: 4, axisCells: rest });
    } else if (rest.length === 2) {
      moves.push({ cell, axis: rest.join(""), turns: 1, order: 2, axisCells: rest });
    } else {
      const turns = match[2] === "2" || match[2] === "'" || match[2] === "3" ? 2 : 1;
      moves.push({ cell, axis: rest.join(""), turns, order: 3, axisCells: rest });
    }
  }
  return moves;
}

export function hyperNotation(move) {
  if (!move.turns) return "";
  const letters = move.cell + (move.axisCells ? move.axisCells.join("") : move.axis);
  if (move.order === 4) return letters + { 1: "", 2: "2", 3: "'" }[move.turns];
  if (move.order === 3) return letters + (move.turns === 2 ? "2" : "");
  return letters;
}

export function invertHyperMoves(moves) {
  return [...moves].reverse().map((move) => {
    if (!move.turns) return { ...move };
    if (move.order === 4) return { ...move, turns: 4 - move.turns };
    if (move.order === 3) return { ...move, turns: 3 - move.turns };
    return { ...move };
  });
}

export function formatHyperMoves(moves) {
  return moves.map(hyperNotation).filter(Boolean).join(" ");
}

class LCG {
  constructor(seed = 0) {
    this.state = seed >>> 0;
  }
  nextInt(n) {
    this.state = (Math.imul(1664525, this.state) + 1013904223) >>> 0;
    return this.state % n;
  }
  choice(seq) {
    return seq[this.nextInt(seq.length)];
  }
}

export function generateHyperScramble(depth, seed = 0) {
  const rng = new LCG(seed);
  const moves = [];
  let last = null;
  for (let n = 0; n < depth; n += 1) {
    const cells = last ? CELLS.filter((c) => c !== last) : CELLS.slice();
    const cell = rng.choice(cells);
    const axis = rng.choice(adjacentCells(cell));
    const turns = rng.choice([1, 2, 3]);
    moves.push({ cell, axis, turns, order: 4, axisCells: [axis] });
    last = cell;
  }
  return moves;
}

export function stepCost(moves, scrambleDepth) {
  const htm = moves.reduce((sum, m) => sum + (m.turns ? 1 : 0), 0);
  const qtm = moves.reduce((sum, m) => {
    if (!m.turns) return sum;
    if (m.order === 4) return sum + (m.turns === 2 ? 2 : 1);
    if (m.order === 2) return sum + 2;
    return sum + 1;
  }, 0);
  const excess = htm - scrambleDepth;
  const efficiency = htm ? scrambleDepth / htm : scrambleDepth === 0 ? 1 : 0;
  return { htm, qtm, scrambleDepth, excessHtm: excess, efficiency };
}

export class HyperCube {
  constructor(state = null) {
    this.size = state && state.size ? state.size : 3;
    this.ndim = state && state.ndim ? state.ndim : 4;
    this.kind = state && state.kind ? state.kind : "4d";
    this.cubies = new Map();
    if (state && Array.isArray(state.cubies)) this.loadCubies(state.cubies);
    else if (state && state.cells) this.setCells(state.cells);
    else if (state && typeof state === "object" && state.R) this.setCells(state);
    else this.reset();
  }

  loadCubies(cubies) {
    this.cubies.clear();
    for (const row of cubies) {
      const pos = (row.pos || []).map(Number);
      this.cubies.set(this.key(pos), { pos, colors: { ...(row.colors || {}) } });
    }
  }

  key(pos) {
    return pos.join(",");
  }

  reset() {
    const n = this.size;
    this.cubies.clear();
    for (let x = 0; x < n; x += 1) {
      for (let y = 0; y < n; y += 1) {
        for (let z = 0; z < n; z += 1) {
          for (let w = 0; w < n; w += 1) {
            const pos = [x, y, z, w];
            const colors = {};
            const coords = [x, y, z, w];
            for (let axis = 0; axis < 4; axis += 1) {
              if (coords[axis] === 0 || coords[axis] === n - 1) {
                const cell = axisCellOf(axis, coords[axis], n);
                colors[cell] = CELL_COLOR[cell];
              }
            }
            if (Object.keys(colors).length) this.cubies.set(this.key(pos), { pos, colors });
          }
        }
      }
    }
  }

  apply(moves) {
    const parsed = typeof moves === "string" ? parseHyperMoves(moves) : moves;
    for (const move of parsed) this.applyMove(move);
    return parsed;
  }

  applyMove(move) {
    if (move.order === 3) {
      this.twist120(move.cell, move.axisCells, move.turns);
      return;
    }
    const turns = move.order === 2 ? (move.turns * 2) % 4 : move.turns;
    this.twist90(move.cell, move.axisCells ? move.axisCells[0] : move.axis, turns);
  }

  twist90(cell, axisCell, turns) {
    const n = this.size;
    const [cellAxis, cellExt] = cellAxisOf(cell, n);
    const [rotAxis, rotExt] = cellAxisOf(axisCell, n);
    turns = ((turns % 4) + 4) % 4;
    if (rotExt === 0) turns = (-turns + 4) % 4;
    if (cellExt === 0) turns = (-turns + 4) % 4;
    if (!turns) return;
    const [i, j] = orientedPlane(cellAxis, rotAxis);
    const cycle = [
      axisCellOf(i, n - 1, n),
      axisCellOf(j, n - 1, n),
      axisCellOf(i, 0, n),
      axisCellOf(j, 0, n),
    ];
    const mapping = {};
    for (let k = 0; k < 4; k += 1) mapping[cycle[k]] = cycle[(k + turns) % 4];
    const moving = [];
    for (const cubie of this.cubies.values()) {
      if (cubie.pos[cellAxis] === cellExt) moving.push(cubie);
    }
    for (const cubie of moving) this.cubies.delete(this.key(cubie.pos));
    for (const cubie of moving) {
      const pos = cubie.pos.slice();
      let ci = pos[i];
      let cj = pos[j];
      for (let t = 0; t < turns; t += 1) {
        const nextI = n - 1 - cj;
        const nextJ = ci;
        ci = nextI;
        cj = nextJ;
      }
      pos[i] = ci;
      pos[j] = cj;
      const colors = {};
      for (const [face, color] of Object.entries(cubie.colors)) {
        colors[mapping[face] || face] = color;
      }
      this.cubies.set(this.key(pos), { pos, colors });
    }
  }

  twist120(cell, axisCells, turns) {
    const [cellAxis, cellExt] = CELL_AXIS[cell];
    turns = ((turns % 3) + 3) % 3;
    if (cellExt === 0) turns = (-turns + 3) % 3;
    if (!turns) return;
    const cellAxes = axisCells.map((name) => CELL_AXIS[name][0]);
    const [a, b, c] = cellAxes;
    const names = axisCells.slice();
    const nameCycle = {};
    for (let k = 0; k < 3; k += 1) nameCycle[names[k]] = names[(k + turns) % 3];
    const opp = names.map((n) => OPPOSITE[n]);
    for (let k = 0; k < 3; k += 1) nameCycle[opp[k]] = opp[(k + turns) % 3];
    const moving = [];
    for (const cubie of this.cubies.values()) {
      if (cubie.pos[cellAxis] === cellExt) moving.push(cubie);
    }
    for (const cubie of moving) this.cubies.delete(this.key(cubie.pos));
    for (const cubie of moving) {
      const pos = cubie.pos.slice();
      let coords = [pos[a], pos[b], pos[c]];
      for (let t = 0; t < turns; t += 1) coords = [coords[2], coords[0], coords[1]];
      pos[a] = coords[0];
      pos[b] = coords[1];
      pos[c] = coords[2];
      const colors = {};
      for (const [face, color] of Object.entries(cubie.colors)) {
        colors[nameCycle[face] || face] = color;
      }
      this.cubies.set(this.key(pos), { pos, colors });
    }
  }

  cellLocalAxes(cell) {
    const cellAxis = CELL_AXIS[cell][0];
    return [0, 1, 2, 3].filter((a) => a !== cellAxis);
  }

  cellStickers(cell) {
    const n = this.size;
    const [cellAxis, cellExt] = cellAxisOf(cell, n);
    const [a, b, c] = this.cellLocalAxes(cell);
    const grid = [];
    for (let k = 0; k < n; k += 1) {
      const layer = [];
      for (let j = 0; j < n; j += 1) {
        const row = [];
        for (let i = 0; i < n; i += 1) {
          const pos = [0, 0, 0, 0];
          pos[cellAxis] = cellExt;
          pos[a] = i;
          pos[b] = j;
          pos[c] = k;
          const cubie = this.cubies.get(this.key(pos));
          row.push(cubie && cubie.colors ? cubie.colors[cell] : "");
        }
        layer.push(row);
      }
      grid.push(layer);
    }
    return grid;
  }

  isSolved() {
    for (const cell of CELLS) {
      const expected = CELL_COLOR[cell];
      for (const layer of this.cellStickers(cell)) {
        for (const row of layer) {
          if (row.some((s) => s !== expected)) return false;
        }
      }
    }
    return true;
  }

  misplacedStickers() {
    let count = 0;
    for (const cell of CELLS) {
      const expected = CELL_COLOR[cell];
      for (const layer of this.cellStickers(cell)) {
        for (const row of layer) {
          for (const s of row) if (s !== expected) count += 1;
        }
      }
    }
    return count;
  }

  toDict() {
    const cells = {};
    for (const cell of CELLS) cells[cell] = this.cellStickers(cell);
    return { kind: "4d", size: 3, ndim: 4, cells };
  }

  setCells(cells) {
    const n = this.size;
    this.cubies.clear();
    for (const [cell, grid] of Object.entries(cells)) {
      const [cellAxis, cellExt] = cellAxisOf(cell, n);
      const [a, b, c] = this.cellLocalAxes(cell);
      for (let k = 0; k < n; k += 1) {
        for (let j = 0; j < n; j += 1) {
          for (let i = 0; i < n; i += 1) {
            const pos = [0, 0, 0, 0];
            pos[cellAxis] = cellExt;
            pos[a] = i;
            pos[b] = j;
            pos[c] = k;
            const key = this.key(pos);
            if (!this.cubies.has(key)) this.cubies.set(key, { pos: pos.slice(), colors: {} });
            this.cubies.get(key).colors[cell] = String(grid[k][j][i]);
          }
        }
      }
    }
  }
}
