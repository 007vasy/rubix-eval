/** NxNxN cube engine. Keep in lockstep with src/rubix_eval/cube.py and scramble.py. */

export const FACES = ["U", "D", "F", "B", "L", "R"];
export const FACE_COLOR = { U: "W", D: "Y", F: "G", B: "B", L: "O", R: "R" };
export const COLOR_HEX = {
  W: 0xf4f1ea,
  Y: 0xf1c40f,
  G: 0x27ae60,
  B: 0x2e86de,
  O: 0xe67e22,
  R: 0xe74c3c,
};
export const PLASTIC = 0x111111;

const FACE_AXIS = { R: 0, L: 0, U: 1, D: 1, F: 2, B: 2 };
const FACE_FROM_ZERO = { L: true, D: true, B: true, R: false, U: false, F: false };
const FACE_DIR = { R: -1, L: 1, U: -1, D: 1, F: -1, B: 1 };
const COLOR_CYCLE = {
  0: ["U", "F", "D", "B"],
  1: ["R", "B", "L", "F"],
  2: ["R", "U", "L", "D"],
};
const TURNS_MAP = { "": 1, 2: 2, "'": 3, "2'": 2, 3: 3 };
const LOWER_WIDE = { u: "U", d: "D", l: "L", r: "R", f: "F", b: "B" };

const PARSE_RE =
  /(?:(\d+)?([UDLRFBudlrfb])(w)?(2'|2|'|3)?|([xyzXYZ])(2'|2|'|3)?|([MESmes])(2'|2|'|3)?)/y;

function isOuter(x, y, z, n) {
  return x === 0 || x === n - 1 || y === 0 || y === n - 1 || z === 0 || z === n - 1;
}

function rotatePosition(x, y, z, n, axis, turns) {
  turns = ((turns % 4) + 4) % 4;
  for (let i = 0; i < turns; i += 1) {
    if (axis === 0) {
      const ny = n - 1 - z;
      const nz = y;
      y = ny;
      z = nz;
    } else if (axis === 1) {
      const nx = z;
      const nz = n - 1 - x;
      x = nx;
      z = nz;
    } else {
      const nx = n - 1 - y;
      const ny = x;
      x = nx;
      y = ny;
    }
  }
  return [x, y, z];
}

function rotateColors(colors, axis, turns) {
  turns = ((turns % 4) + 4) % 4;
  if (turns === 0) return { ...colors };
  const cycle = COLOR_CYCLE[axis];
  const mapping = {};
  for (let i = 0; i < 4; i += 1) mapping[cycle[i]] = cycle[(i + turns) % 4];
  const out = {};
  for (const [face, color] of Object.entries(colors)) {
    out[mapping[face] || face] = color;
  }
  return out;
}

export function parseMoves(algorithm) {
  if (!algorithm || !String(algorithm).trim()) return [];
  const text = String(algorithm);
  const moves = [];
  let pos = 0;
  while (pos < text.length) {
    const ch = text[pos];
    if (/\s|,|;/.test(ch)) {
      pos += 1;
      continue;
    }
    PARSE_RE.lastIndex = pos;
    const match = PARSE_RE.exec(text);
    if (!match || match.index !== pos) {
      throw new Error(`Invalid move notation at ${JSON.stringify(text.slice(pos))}`);
    }
    pos = PARSE_RE.lastIndex;
    if (match[5]) throw new Error("Whole-cube rotations (x/y/z) are not allowed during eval");
    if (match[7]) {
      const sliceFace = match[7].toUpperCase();
      const face = { M: "L", E: "D", S: "F" }[sliceFace];
      const turns = TURNS_MAP[match[8] || ""];
      moves.push({ face, layer: 2, wide: false, turns });
      continue;
    }
    const rawFace = match[2];
    let wide = Boolean(match[3]);
    const depth = match[1] ? Number(match[1]) : 0;
    const turns = TURNS_MAP[match[4] || ""];
    let face;
    let layer;
    if (LOWER_WIDE[rawFace]) {
      face = LOWER_WIDE[rawFace];
      wide = true;
      layer = depth || 2;
    } else {
      face = rawFace;
      if (wide) layer = depth || 2;
      else if (depth) layer = depth;
      else layer = 1;
    }
    moves.push({ face, layer, wide, turns });
  }
  return moves;
}

export function notation(move) {
  if (!move.turns) return "";
  const suffix = { 1: "", 2: "2", 3: "'" }[move.turns];
  if (move.wide) {
    if (move.layer === 2) return `${move.face}w${suffix}`;
    return `${move.layer}${move.face}w${suffix}`;
  }
  if (move.layer === 1) return `${move.face}${suffix}`;
  return `${move.layer}${move.face}${suffix}`;
}

export function invertMoves(moves) {
  return [...moves].reverse().map((move) => ({
    ...move,
    turns: move.turns === 0 ? 0 : 4 - move.turns,
  }));
}

export function formatMoves(moves) {
  return moves.map(notation).filter(Boolean).join(" ");
}

export function moveLayers(move, size) {
  if (move.wide) {
    const layers = [];
    for (let i = 1; i <= move.layer; i += 1) layers.push(i);
    return layers;
  }
  return [move.layer];
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
  randint(lo, hi) {
    return lo + this.nextInt(hi - lo + 1);
  }
}

export function generateScramble(size, depth, seed = 0, innerSlices = null) {
  if (innerSlices == null) innerSlices = size >= 4;
  const rng = new LCG(seed);
  let maxLayer = innerSlices ? size : 1;
  maxLayer = size > 2 ? Math.min(maxLayer, size - 1) : 1;
  const facesAll = ["U", "D", "L", "R", "F", "B"];
  const opposite = { U: "D", D: "U", L: "R", R: "L", F: "B", B: "F" };
  const moves = [];
  let lastFace = null;
  let lastAxisFace = null;
  for (let i = 0; i < depth; i += 1) {
    let faces = facesAll.slice();
    if (lastFace) {
      faces = faces.filter((f) => f !== lastFace);
      if (lastAxisFace && faces.includes(lastAxisFace) && faces.length > 1) {
        if (!innerSlices || size <= 3) {
          const filtered = faces.filter((f) => f !== lastAxisFace);
          if (filtered.length) faces = filtered;
        }
      }
    }
    const face = rng.choice(faces);
    const layer = maxLayer <= 1 ? 1 : rng.randint(1, maxLayer);
    const turns = rng.choice([1, 2, 3]);
    moves.push({ face, layer, wide: false, turns });
    if (lastFace && opposite[face] === lastFace) lastAxisFace = face;
    else lastAxisFace = null;
    lastFace = face;
  }
  return moves;
}

export class Cube {
  constructor(size = 3, state = null) {
    if (size < 2) throw new Error("Cube size must be >= 2");
    this.size = size;
    this.cubies = new Map();
    if (state) this.setFaces(state.faces || state);
    else this.reset();
  }

  key(x, y, z) {
    return `${x},${y},${z}`;
  }

  reset() {
    const n = this.size;
    this.cubies.clear();
    for (let x = 0; x < n; x += 1) {
      for (let y = 0; y < n; y += 1) {
        for (let z = 0; z < n; z += 1) {
          if (!isOuter(x, y, z, n)) continue;
          const colors = {};
          if (x === 0) colors.L = FACE_COLOR.L;
          if (x === n - 1) colors.R = FACE_COLOR.R;
          if (y === 0) colors.D = FACE_COLOR.D;
          if (y === n - 1) colors.U = FACE_COLOR.U;
          if (z === 0) colors.B = FACE_COLOR.B;
          if (z === n - 1) colors.F = FACE_COLOR.F;
          this.cubies.set(this.key(x, y, z), { x, y, z, colors });
        }
      }
    }
  }

  copy() {
    const clone = new Cube(this.size);
    clone.cubies = new Map();
    for (const [k, cubie] of this.cubies) {
      clone.cubies.set(k, { x: cubie.x, y: cubie.y, z: cubie.z, colors: { ...cubie.colors } });
    }
    return clone;
  }

  apply(moves) {
    const parsed = typeof moves === "string" ? parseMoves(moves) : moves;
    for (const move of parsed) this.applyMove(move);
    return parsed;
  }

  applyMove(move) {
    const n = this.size;
    const axis = FACE_AXIS[move.face];
    const fromZero = FACE_FROM_ZERO[move.face];
    const layers = moveLayers(move, n);
    const sliceIndices = layers.map((layer) => (fromZero ? layer - 1 : n - layer));
    const direction = (((FACE_DIR[move.face] * move.turns) % 4) + 4) % 4;
    if (direction === 0) return;
    this.rotateSlices(axis, sliceIndices, direction);
  }

  rotateSlices(axis, sliceIndices, turns) {
    const n = this.size;
    const moving = [];
    for (const cubie of this.cubies.values()) {
      const pos = [cubie.x, cubie.y, cubie.z];
      if (sliceIndices.includes(pos[axis])) moving.push(cubie);
    }
    for (const cubie of moving) this.cubies.delete(this.key(cubie.x, cubie.y, cubie.z));
    for (const cubie of moving) {
      const [x, y, z] = rotatePosition(cubie.x, cubie.y, cubie.z, n, axis, turns);
      const colors = rotateColors(cubie.colors, axis, turns);
      this.cubies.set(this.key(x, y, z), { x, y, z, colors });
    }
  }

  faceCoords(face, row, col) {
    const n = this.size;
    if (face === "U") return [col, n - 1, row];
    if (face === "D") return [col, 0, n - 1 - row];
    if (face === "F") return [col, n - 1 - row, n - 1];
    if (face === "B") return [n - 1 - col, n - 1 - row, 0];
    if (face === "L") return [0, n - 1 - row, col];
    if (face === "R") return [n - 1, n - 1 - row, n - 1 - col];
    throw new Error(`Unknown face ${face}`);
  }

  faceGrid(face) {
    const n = this.size;
    const grid = [];
    for (let r = 0; r < n; r += 1) {
      const row = [];
      for (let c = 0; c < n; c += 1) {
        const [x, y, z] = this.faceCoords(face, r, c);
        row.push(this.cubies.get(this.key(x, y, z)).colors[face]);
      }
      grid.push(row);
    }
    return grid;
  }

  faces() {
    const out = {};
    for (const face of FACES) out[face] = this.faceGrid(face);
    return out;
  }

  setFaces(faces) {
    const n = this.size;
    this.cubies.clear();
    for (const [face, grid] of Object.entries(faces)) {
      for (let r = 0; r < n; r += 1) {
        for (let c = 0; c < n; c += 1) {
          const [x, y, z] = this.faceCoords(face, r, c);
          const key = this.key(x, y, z);
          if (!this.cubies.has(key)) this.cubies.set(key, { x, y, z, colors: {} });
          this.cubies.get(key).colors[face] = grid[r][c];
        }
      }
    }
  }

  isSolved() {
    for (const face of FACES) {
      const expected = FACE_COLOR[face];
      for (const row of this.faceGrid(face)) {
        if (row.some((sticker) => sticker !== expected)) return false;
      }
    }
    return true;
  }

  misplacedStickers() {
    let count = 0;
    for (const face of FACES) {
      const expected = FACE_COLOR[face];
      for (const row of this.faceGrid(face)) {
        for (const sticker of row) if (sticker !== expected) count += 1;
      }
    }
    return count;
  }

  toDict() {
    return { size: this.size, faces: this.faces() };
  }

  static fromDict(data) {
    return new Cube(data.size, data);
  }
}

export function stepCost(moves, scrambleDepth) {
  const htm = moves.reduce((sum, m) => sum + (m.turns ? 1 : 0), 0);
  const qtm = moves.reduce((sum, m) => sum + (m.turns === 2 ? 2 : m.turns ? 1 : 0), 0);
  const excess = htm - scrambleDepth;
  const efficiency = htm ? scrambleDepth / htm : scrambleDepth === 0 ? 1 : 0;
  return { htm, qtm, scrambleDepth, excessHtm: excess, efficiency };
}

export function axisOf(face) {
  return FACE_AXIS[face];
}

export function sliceIndex(face, layer, size) {
  return FACE_FROM_ZERO[face] ? layer - 1 : size - layer;
}

export function turnSign(face, turns) {
  return FACE_DIR[face] * (turns === 3 ? -1 : turns === 2 ? 2 : 1);
}
