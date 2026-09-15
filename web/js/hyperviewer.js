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
  twist90Position,
} from "./hyperengine.js";

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

function pos4ToOffset(cell, pos) {
  const [a, b, c] = localAxes(cell);
  return localToOffset(cell, pos[a], pos[b], pos[c]);
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

function twistWorldRotation(cell, axisCell, turns) {
  const [cellAxis, cellExt] = CELL_AXIS[cell];
  const rotAxis = CELL_AXIS[axisCell][0];
  const pos = [1, 1, 1, 1];
  pos[cellAxis] = cellExt;
  pos[rotAxis] = 2;
  const plane = [0, 1, 2, 3].find((a) => a !== cellAxis && a !== rotAxis);
  pos[plane] = 2;
  const before = new THREE.Vector3(...pos4ToOffset(cell, pos));
  const after = new THREE.Vector3(...pos4ToOffset(cell, twist90Position(pos, cell, axisCell, turns)));
  if (before.lengthSq() < 1e-8 || after.lengthSq() < 1e-8) {
    return { axis: new THREE.Vector3(0, 1, 0), angle: 0 };
  }
  const axis = new THREE.Vector3().crossVectors(before, after);
  if (axis.lengthSq() < 1e-8) {
    const q = ((turns % 4) + 4) % 4;
    const angle = q === 2 ? Math.PI : 0;
    const fallback = before.clone().normalize();
    const helper = Math.abs(fallback.y) < 0.9 ? new THREE.Vector3(0, 1, 0) : new THREE.Vector3(1, 0, 0);
    return { axis: new THREE.Vector3().crossVectors(fallback, helper).normalize(), angle };
  }
  axis.normalize();
  return { axis, angle: before.angleTo(after) };
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
    if (this._pendingClick) clearTimeout(this._pendingClick);
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
              sticker.lookAt(sticker.position.clone().add(new THREE.Vector3(nx, ny, nz)));
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

  playNext() {
    if (!this.queue.length) {
      this.animating = false;
      return;
    }
    this.animating = true;
    const move = this.queue.shift();
    const group = this.root.children.find((g) => g.userData.cell === move.cell);
    const axisCell = move.axisCells ? move.axisCells[0] : move.axis;
    let axis = new THREE.Vector3(0, 1, 0);
    let angle = 0;
    if (move.order === 4 && axisCell && CELL_AXIS[axisCell]) {
      const rot = twistWorldRotation(move.cell, axisCell, move.turns);
      axis = rot.axis;
      angle = rot.angle;
    } else if (move.order === 2) {
      angle = Math.PI;
    }

    const start = performance.now();
    const duration = move.turns === 2 ? 280 : 200;
    const tick = (now) => {
      if (this._stopped) return;
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - (1 - t) ** 3;
      if (group && angle) group.setRotationFromAxisAngle(axis, angle * eased);
      if (t < 1) {
        requestAnimationFrame(tick);
        return;
      }
      if (group) group.rotation.set(0, 0, 0);
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
    const now = performance.now();
    const dbl = press.button === 0 && now - (this._lastClickAt || 0) < 320;
    this._lastClickAt = now;
    let turns = press.button === 2 ? 3 : 1;
    if (dbl) turns = 2;
    this.enqueue({ cell, axis, turns, order: 4, axisCells: [axis] });
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
