import * as THREE from "three";
import { OrbitControls } from "../vendor/OrbitControls.js";
import {
  AXIS_CELL,
  CELL_AXIS,
  CELL_COLOR,
  CELLS,
  COLOR_HEX,
  HyperCube,
  PLASTIC,
  adjacentCells,
  axisCellOf,
  cellAxisOf,
  formatHyperMoves,
  generateHyperScramble,
  hyperNotation,
  invertHyperMoves,
  parseHyperMoves,
  stepCost,
} from "./hyperengine.js";
import { stickerEuler } from "./sticker-pose.js";

const PITCH = 0.98;
const CUBIE = 0.58;
const STICKER = 0.5;
const SEP = 5.4;
const CELL_ORIGIN = {
  I: [0, 0, 0],
  R: [SEP, 0, 0],
  L: [-SEP, 0, 0],
  U: [0, SEP, 0],
  D: [0, -SEP, 0],
  F: [0, 0, SEP],
  B: [0, 0, -SEP],
  O: [SEP * 2, 0, 0],
};

function localAxes(cell) {
  const cellAxis = CELL_AXIS[cell][0];
  return [0, 1, 2, 3].filter((a) => a !== cellAxis);
}

function localToOffset(cell, i, j, k, n = 3) {
  const [cellAxis, cellExt] = cellAxisOf(cell, n);
  const [a, b, c] = localAxes(cell);
  const v4 = [0, 0, 0, 0];
  const mid = (n - 1) / 2;
  v4[a] = (i - mid) * PITCH;
  v4[b] = (j - mid) * PITCH;
  v4[c] = (k - mid) * PITCH;
  const sign = cellExt === 2 ? 1 : -1;
  if (cellAxis === 0) return [v4[3] * sign, v4[1], v4[2]];
  if (cellAxis === 1) return [v4[0], v4[3] * sign, v4[2]];
  if (cellAxis === 2) return [v4[0], v4[1], v4[3] * sign];
  return [v4[0], v4[1], v4[2]];
}

function pos4ToOffset(cell, pos, n = 3) {
  const [a, b, c] = localAxes(cell);
  return localToOffset(cell, pos[a], pos[b], pos[c], n);
}

function worldNormalToAxisCell(cell, nx, ny, nz, n = 3) {
  const [cellAxis, cellExt] = CELL_AXIS[cell];
  const sign = cellExt === 2 ? 1 : -1;
  let axis4;
  let positive;
  if (cellAxis === 0) {
    if (Math.abs(nx) >= Math.abs(ny) && Math.abs(nx) >= Math.abs(nz)) {
      axis4 = 3;
      positive = nx * sign > 0;
    } else if (Math.abs(ny) >= Math.abs(nz)) {
      axis4 = 1;
      positive = ny > 0;
    } else {
      axis4 = 2;
      positive = nz > 0;
    }
  } else if (cellAxis === 1) {
    if (Math.abs(ny) >= Math.abs(nx) && Math.abs(ny) >= Math.abs(nz)) {
      axis4 = 3;
      positive = ny * sign > 0;
    } else if (Math.abs(nx) >= Math.abs(nz)) {
      axis4 = 0;
      positive = nx > 0;
    } else {
      axis4 = 2;
      positive = nz > 0;
    }
  } else if (cellAxis === 2) {
    if (Math.abs(nz) >= Math.abs(nx) && Math.abs(nz) >= Math.abs(ny)) {
      axis4 = 3;
      positive = nz * sign > 0;
    } else if (Math.abs(nx) >= Math.abs(ny)) {
      axis4 = 0;
      positive = nx > 0;
    } else {
      axis4 = 1;
      positive = ny > 0;
    }
  } else if (Math.abs(nx) >= Math.abs(ny) && Math.abs(nx) >= Math.abs(nz)) {
    axis4 = 0;
    positive = nx > 0;
  } else if (Math.abs(ny) >= Math.abs(nz)) {
    axis4 = 1;
    positive = ny > 0;
  } else {
    axis4 = 2;
    positive = nz > 0;
  }
  return axisCellOf(axis4, positive ? n - 1 : 0, n) || AXIS_CELL[`${axis4},${positive ? 2 : 0}`];
}

const ARC_CACHE = new Map();
const ARC_DIRS = [];
for (const x of [-1, 0, 1]) for (const y of [-1, 0, 1]) for (const z of [-1, 0, 1]) {
  if (x || y || z) ARC_DIRS.push(new THREE.Vector3(x, y, z).normalize());
}

/**
 * How a sticker flies from one exploded cell to another: the lowest arc (and its sideways
 * direction) that keeps every piece of the slab clear of all the other cells. In the
 * exploded layout a hop like O -> L crosses the whole puzzle, and a straight or naively
 * bulged path runs through the I and R cells. Searched once per cell pair and size.
 */
function flightArc(fromCell, toCell, n) {
  const key = `${fromCell}>${toCell}>${n}`;
  if (ARC_CACHE.has(key)) return ARC_CACHE.get(key);
  const s = new THREE.Vector3(...CELL_ORIGIN[fromCell]);
  const e = new THREE.Vector3(...CELL_ORIGIN[toCell]);
  const dir = e.clone().sub(s).normalize();
  const mid = s.clone().add(e).multiplyScalar(0.5);
  const reach = ((n - 1) / 2) * PITCH;
  const half = reach + CUBIE / 2 + 0.15;
  const offsets = [new THREE.Vector3()];
  for (const x of [-reach, reach]) for (const y of [-reach, reach]) for (const z of [-reach, reach]) {
    offsets.push(new THREE.Vector3(x, y, z));
  }
  const others = CELLS.filter((c) => c !== fromCell && c !== toCell).map((c) => new THREE.Vector3(...CELL_ORIGIN[c]));
  const p = new THREE.Vector3();
  const clears = (ctrl) => {
    for (const off of offsets) {
      for (let i = 1; i < 24; i += 1) {
        const t = i / 24;
        const u = 1 - t;
        p.copy(s).add(off).multiplyScalar(u * u)
          .addScaledVector(ctrl.clone().add(off), 2 * u * t)
          .addScaledVector(e.clone().add(off), t * t);
        for (const c of others) {
          const gap = Math.max(Math.abs(p.x - c.x), Math.abs(p.y - c.y), Math.abs(p.z - c.z)) - half;
          if (gap < 0.2) return false;
        }
      }
    }
    return true;
  };
  let found = null;
  for (let height = 0.5; height <= 12 && !found; height += 0.25) {
    for (const cand of ARC_DIRS) {
      const side = cand.clone().addScaledVector(dir, -cand.dot(dir));
      if (side.lengthSq() < 0.3) continue;
      side.normalize();
      if (clears(mid.clone().addScaledVector(side, 2 * height))) {
        found = { side, height };
        break;
      }
    }
  }
  if (!found) {
    const side = new THREE.Vector3(0, 1, 0).addScaledVector(dir, -dir.y).normalize();
    found = { side, height: 0.35 + 0.16 * s.distanceTo(e) };
  }
  ARC_CACHE.set(key, found);
  return found;
}

/** The rotation about the cell centre that carries every `from` offset onto its `target`. */
function rigidRotation(items) {
  const a1 = items.find((it) => it.from.lengthSq() > 1e-6);
  if (!a1) return new THREE.Quaternion();
  const a2 = items.find((it) => it.from.lengthSq() > 1e-6 && it.from.clone().cross(a1.from).lengthSq() > 1e-6);
  if (!a2) return new THREE.Quaternion().setFromUnitVectors(a1.from.clone().normalize(), a1.target.clone().normalize());
  const frame = (u, v) => {
    const x = u.clone().normalize();
    const z = u.clone().cross(v).normalize();
    const y = z.clone().cross(x);
    return new THREE.Matrix4().makeBasis(x, y, z);
  };
  const before = frame(a1.from, a2.from);
  const after = frame(a1.target, a2.target);
  const m = after.multiply(before.transpose());
  return new THREE.Quaternion().setFromRotationMatrix(m);
}

function makeLabel(text, hex) {
  const canvas = document.createElement("canvas");
  canvas.width = 256;
  canvas.height = 64;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = `#${hex.toString(16).padStart(6, "0")}`;
  ctx.font = "700 42px sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, 128, 32);
  const sprite = new THREE.Sprite(
    new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(canvas), transparent: true }),
  );
  sprite.scale.set(1.8, 0.45, 1);
  return sprite;
}

export class HyperViewer {
  constructor(canvas, onChange, options = {}) {
    this.canvas = canvas;
    this.onChange = onChange;
    this.showLabels = options.showLabels !== false;
    this.cube = new HyperCube();
    this.history = [];
    this.scramble = [];
    this.queue = [];
    this.animating = false;
    this.modifier = 1;
    this._stopped = false;
    this._press = null;
    this._pendingClick = null;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0b0d10);
    this.camera = new THREE.PerspectiveCamera(42, 1, 0.1, 200);
    this.camera.position.set(16, 11, 18);

    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.enablePan = false;
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.minDistance = 10;
    this.controls.maxDistance = 48;
    this.controls.target.set(SEP * 0.7, 0, 0);
    this.controls.mouseButtons.RIGHT = -1;

    this.root = new THREE.Group();
    this.scene.add(this.root);
    this.scene.add(new THREE.HemisphereLight(0xc8c8c8, 0x1a1a1a, 0.85));
    const key = new THREE.DirectionalLight(0xffffff, 0.75);
    key.position.set(10, 14, 12);
    this.scene.add(key);

    this.raycaster = new THREE.Raycaster();
    this.pointer = new THREE.Vector2();
    this.stickerMeshes = [];

    this.onDown = this.handlePointerDown.bind(this);
    this.onMove = this.handlePointerMove.bind(this);
    this.onUp = this.handlePointerUp.bind(this);
    this.onResize = () => this.resize();
    this.onContext = (event) => event.preventDefault();
    canvas.addEventListener("pointerdown", this.onDown);
    window.addEventListener("pointermove", this.onMove);
    window.addEventListener("pointerup", this.onUp);
    canvas.addEventListener("contextmenu", this.onContext);
    window.addEventListener("resize", this.onResize);

    this.resize();
    this.rebuild();
    this.loop();
  }

  dispose() {
    this._stopped = true;
    if (this._pendingClick) clearTimeout(this._pendingClick.timer);
    this.canvas.removeEventListener("pointerdown", this.onDown);
    window.removeEventListener("pointermove", this.onMove);
    window.removeEventListener("pointerup", this.onUp);
    this.canvas.removeEventListener("contextmenu", this.onContext);
    window.removeEventListener("resize", this.onResize);
    this.controls.dispose();
    this.renderer.dispose();
  }

  reset() {
    this.cube.reset();
    this.history = [];
    this.scramble = [];
    this.rebuild();
    this.notify();
  }

  loadState(state) {
    this.cube = new HyperCube(state);
    this.history = [];
    this.scramble = [];
    this.rebuild();
    this.notify();
  }

  applyScramble(moves) {
    this.cube.reset();
    this.scramble = moves.slice();
    this.cube.apply(moves);
    this.history = [];
    this.rebuild();
    this.notify();
  }

  enqueue(move) {
    this.queue.push(move);
    if (!this.animating) this.playNext();
  }

  applyText(text) {
    for (const move of parseHyperMoves(text)) this.enqueue(move);
  }

  undo() {
    if (!this.history.length) return;
    const last = this.history.pop();
    this.enqueue({ ...last, turns: last.order === 4 ? 4 - last.turns : last.turns, _undo: true });
  }

  solveByReverse() {
    const path = invertHyperMoves([...this.scramble, ...this.history]);
    for (const move of path) this.enqueue(move);
  }

  rebuild() {
    while (this.root.children.length) this.root.remove(this.root.children[0]);
    this.stickerMeshes = [];
    const bodyGeo = new THREE.BoxGeometry(CUBIE, CUBIE, CUBIE);
    const stickerGeo = new THREE.PlaneGeometry(STICKER, STICKER);
    const plastic = new THREE.MeshStandardMaterial({
      color: PLASTIC,
      roughness: 0.55,
      metalness: 0.08,
    });
    const faceDirs = [
      [1, 0, 0],
      [-1, 0, 0],
      [0, 1, 0],
      [0, -1, 0],
      [0, 0, 1],
      [0, 0, -1],
    ];
    for (const cell of CELLS) {
      const group = new THREE.Group();
      group.position.set(...CELL_ORIGIN[cell]);
      group.userData.cell = cell;
      const n = this.cube.size;
      const [cellAxis, cellExt] = cellAxisOf(cell, n);
      const [a, b, c] = localAxes(cell);
      for (let i = 0; i < n; i += 1) {
        for (let j = 0; j < n; j += 1) {
          for (let k = 0; k < n; k += 1) {
            const pos = [0, 0, 0, 0];
            pos[cellAxis] = cellExt;
            pos[a] = i;
            pos[b] = j;
            pos[c] = k;
            const cubie = this.cube.cubies.get(pos.join(","));
            if (!cubie || !cubie.colors) continue;
            const color = cubie.colors[cell];
            if (color == null) continue;
            const piece = new THREE.Group();
            const off = localToOffset(cell, i, j, k, n);
            piece.position.set(...off);
            piece.userData.pos = pos.slice();
            piece.userData.cell = cell;
            piece.add(new THREE.Mesh(bodyGeo, plastic));
            const stickerMat = new THREE.MeshStandardMaterial({
              color: COLOR_HEX[color] ?? 0x444444,
              roughness: 0.4,
              metalness: 0.02,
            });
            const z = CUBIE / 2 + 0.004;
            for (const [nx, ny, nz] of faceDirs) {
              const sticker = new THREE.Mesh(stickerGeo, stickerMat);
              sticker.position.set(nx * z, ny * z, nz * z);
              const [rx, ry, rz] = stickerEuler(nx, ny, nz);
              sticker.rotation.set(rx, ry, rz);
              sticker.userData = { cell, i, j, k, nx, ny, nz };
              piece.add(sticker);
              this.stickerMeshes.push(sticker);
            }
            group.add(piece);
          }
        }
      }
      if (this.showLabels) {
        const label = makeLabel(cell, COLOR_HEX[CELL_COLOR[cell]]);
        label.position.set(0, 1.7, 0);
        group.add(label);
      }
      this.root.add(group);
    }
  }

  /** Where each displayed sticker ("pos|cell") lands after `move`, straight from the engine. */
  stickerDestinations(move) {
    const probe = Object.assign(Object.create(Object.getPrototypeOf(this.cube)), this.cube);
    probe.cubies = new Map();
    for (const [key, cubie] of this.cube.cubies) {
      const colors = {};
      for (const cell of Object.keys(cubie.colors || {})) colors[cell] = `${cubie.pos.join(",")}|${cell}`;
      probe.cubies.set(key, { pos: cubie.pos.slice(), colors });
    }
    probe.applyMove(move);
    const out = new Map();
    for (const cubie of probe.cubies.values()) {
      for (const [cell, id] of Object.entries(cubie.colors)) {
        if (id !== `${cubie.pos.join(",")}|${cell}`) out.set(id, { cell, pos: cubie.pos });
      }
    }
    return out;
  }

  playNext() {
    if (!this.queue.length) {
      this.animating = false;
      return;
    }
    this.animating = true;
    const move = this.queue.shift();
    const n = this.cube.size;
    const dest = this.stickerDestinations(move);
    const pivots = [];
    const flights = [];
    for (const group of [...this.root.children]) {
      const displayCell = group.userData.cell;
      if (!displayCell) continue;
      const staying = [];
      for (const piece of [...group.children]) {
        const pos = piece.userData && piece.userData.pos;
        if (!pos) continue;
        const to = dest.get(`${pos.join(",")}|${displayCell}`);
        if (!to) continue;
        const from = new THREE.Vector3(...pos4ToOffset(displayCell, pos, n));
        const target = new THREE.Vector3(...pos4ToOffset(to.cell, to.pos, n));
        if (to.cell === displayCell) {
          if (from.distanceToSquared(target) > 1e-6) staying.push({ piece, from, target });
          continue;
        }
        // The twist carries this sticker into another cell: fly it there through the gap.
        const start = new THREE.Vector3(...CELL_ORIGIN[displayCell]).add(from);
        const end = new THREE.Vector3(...CELL_ORIGIN[to.cell]).add(target);
        // Arc around the other cells instead of through them (see flightArc).
        const arc = flightArc(displayCell, to.cell, n);
        const control = start.clone().add(end).multiplyScalar(0.5).addScaledVector(arc.side, 2 * arc.height);
        this.root.attach(piece);
        flights.push({ piece, start, control, end });
      }
      if (!staying.length) continue;
      // Stickers that stay in this cell turn together as one rigid block about the cell centre.
      const q = rigidRotation(staying);
      const pivot = new THREE.Group();
      group.add(pivot);
      for (const item of staying) pivot.attach(item.piece);
      pivots.push({ pivot, q });
    }

    const finish = () => {
      if (!move._undo) {
        this.history.push({
          cell: move.cell,
          axis: move.axis,
          turns: move.turns,
          order: move.order,
          axisCells: move.axisCells,
        });
      }
      this.cube.applyMove(move);
      this.rebuild();
      this.notify();
      this.playNext();
    };
    if (!pivots.length && !flights.length) {
      finish();
      return;
    }

    const start = performance.now();
    const duration = (move.turns === 2 || move.order === 2 ? 460 : 360) * (flights.length ? 1.15 : 1);
    const identity = new THREE.Quaternion();
    const p = new THREE.Vector3();
    const tick = (now) => {
      if (this._stopped) return;
      const t = Math.min(1, (now - start) / duration);
      const eased = t * t * (3 - 2 * t);
      for (const item of pivots) item.pivot.quaternion.slerpQuaternions(identity, item.q, eased);
      for (const f of flights) {
        const u = 1 - eased;
        p.copy(f.start).multiplyScalar(u * u)
          .addScaledVector(f.control, 2 * u * eased)
          .addScaledVector(f.end, eased * eased);
        f.piece.position.copy(p);
        f.piece.scale.setScalar(1 - 0.18 * Math.sin(Math.PI * eased));
      }
      if (t < 1) {
        requestAnimationFrame(tick);
        return;
      }
      finish();
    };
    requestAnimationFrame(tick);
  }

  pointerNDC(event) {
    const rect = this.canvas.getBoundingClientRect();
    this.pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  }

  hitSticker(event) {
    this.pointerNDC(event);
    this.raycaster.setFromCamera(this.pointer, this.camera);
    return this.raycaster.intersectObjects(this.stickerMeshes, false)[0] || null;
  }

  handlePointerDown(event) {
    if (event.button !== 0 && event.button !== 2) return;
    const hit = this.hitSticker(event);
    this._press = {
      x: event.clientX,
      y: event.clientY,
      button: event.button,
      hit,
      dragged: false,
    };
    if (hit) this.controls.enabled = false;
  }

  handlePointerMove(event) {
    if (!this._press) return;
    if (Math.hypot(event.clientX - this._press.x, event.clientY - this._press.y) > 12) {
      this._press.dragged = true;
      this.controls.enabled = true;
    }
  }

  handlePointerUp(event) {
    const press = this._press;
    this._press = null;
    this.controls.enabled = true;
    if (!press || press.dragged || !press.hit) return;
    const data = press.hit.object.userData;
    const cell = data.cell;
    const nx = data.nx ?? 0;
    const ny = data.ny ?? 1;
    const nz = data.nz ?? 0;
    let axis = worldNormalToAxisCell(cell, nx, ny, nz, this.cube.size);
    if (!axis || axis === cell || (CELL_AXIS[axis] && CELL_AXIS[axis][0] === CELL_AXIS[cell][0])) {
      const neighbors = adjacentCells(cell).filter((name) => name !== cell);
      axis = neighbors[0];
    }
    if (!axis) return;
    const spec = { cell, axis, order: 4, axisCells: [axis] };
    if (press.button === 2) {
      if (this._pendingClick) clearTimeout(this._pendingClick.timer);
      this._pendingClick = null;
      this.enqueue({ ...spec, turns: 3 });
    } else if (this._pendingClick && this._pendingClick.cell === cell && this._pendingClick.axis === axis) {
      clearTimeout(this._pendingClick.timer);
      this._pendingClick = null;
      this.enqueue({ ...spec, turns: 2 });
    } else {
      if (this._pendingClick) clearTimeout(this._pendingClick.timer);
      const timer = setTimeout(() => {
        this._pendingClick = null;
        this.enqueue({ ...spec, turns: 1 });
      }, 280);
      this._pendingClick = { timer, cell, axis };
    }
  }

  notify() {
    if (!this.onChange) return;
    this.onChange({
      cube: this.cube,
      history: this.history,
      scramble: this.scramble,
      solved: this.cube.isSolved(),
      moves: formatHyperMoves(this.history),
      scrambleText: formatHyperMoves(this.scramble),
      kind: "4d",
    });
  }

  resize() {
    const wrap = this.canvas.parentElement;
    const width = wrap.clientWidth || 800;
    const height = wrap.clientHeight || 600;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height, false);
  }

  loop() {
    if (this._stopped) return;
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
    requestAnimationFrame(() => this.loop());
  }
}

export { adjacentCells, formatHyperMoves, generateHyperScramble, hyperNotation, invertHyperMoves, parseHyperMoves, stepCost };
