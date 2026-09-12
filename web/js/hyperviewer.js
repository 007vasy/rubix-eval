import * as THREE from "three";
import { OrbitControls } from "../vendor/OrbitControls.js";
import {
  AXIS_CELL,
  CELL_AXIS,
  CELL_COLOR,
  CELLS,
  COLOR_HEX,
  HyperCube,
  adjacentCells,
  formatHyperMoves,
  generateHyperScramble,
  hyperNotation,
  invertHyperMoves,
  parseHyperMoves,
  stepCost,
} from "./hyperengine.js";

const SEP = 4.4;
const PITCH = 0.78;
const CELL_ORIGIN = {
  I: [0, 0, 0],
  R: [SEP, 0, 0],
  L: [-SEP, 0, 0],
  U: [0, SEP, 0],
  D: [0, -SEP, 0],
  F: [0, 0, SEP],
  B: [0, 0, -SEP],
  O: [SEP * 1.15, -SEP * 0.15, -SEP * 1.05],
};

function localAxes(cell) {
  const cellAxis = CELL_AXIS[cell][0];
  return [0, 1, 2, 3].filter((a) => a !== cellAxis);
}

function localToOffset(cell, i, j, k) {
  const [cellAxis, cellExt] = CELL_AXIS[cell];
  const [a, b, c] = localAxes(cell);
  const v4 = [0, 0, 0, 0];
  v4[a] = (i - 1) * PITCH;
  v4[b] = (j - 1) * PITCH;
  v4[c] = (k - 1) * PITCH;
  const sign = cellExt === 2 ? 1 : -1;
  if (cellAxis === 0) return [v4[3] * sign, v4[1], v4[2]];
  if (cellAxis === 1) return [v4[0], v4[3] * sign, v4[2]];
  if (cellAxis === 2) return [v4[0], v4[1], v4[3] * sign];
  return [v4[0], v4[1], v4[2]];
}

function axisWorldDir(cell, axisCell) {
  const dummy = localToOffset(cell, 1, 1, 1);
  const [cellAxis] = CELL_AXIS[cell];
  const rotAxis = CELL_AXIS[axisCell][0];
  const [a, b, c] = localAxes(cell);
  const i = a === rotAxis ? 2 : 1;
  const j = b === rotAxis ? 2 : 1;
  const k = c === rotAxis ? 2 : 1;
  const tip = localToOffset(cell, i, j, k);
  return new THREE.Vector3(tip[0] - dummy[0], tip[1] - dummy[1], tip[2] - dummy[2]).normalize();
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
    this._lastClickAt = 0;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0b0d10);
    this.camera = new THREE.PerspectiveCamera(42, 1, 0.1, 200);
    this.camera.position.set(8.5, 6.5, 12);

    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.enablePan = false;
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.minDistance = 8;
    this.controls.maxDistance = 40;
    this.controls.mouseButtons.RIGHT = -1;

    this.root = new THREE.Group();
    this.scene.add(this.root);
    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x1a1a1a, 1.1));
    const key = new THREE.DirectionalLight(0xffffff, 1.0);
    key.position.set(8, 12, 10);
    this.scene.add(key);

    this.raycaster = new THREE.Raycaster();
    this.pointer = new THREE.Vector2();
    this.stickerMeshes = [];

    this.onClick = this.handleClick.bind(this);
    this.onResize = () => this.resize();
    this.onContext = (event) => event.preventDefault();
    canvas.addEventListener("pointerdown", this.onClick);
    canvas.addEventListener("contextmenu", this.onContext);
    window.addEventListener("resize", this.onResize);

    this.resize();
    this.rebuild();
    this.loop();
  }

  dispose() {
    this._stopped = true;
    this.canvas.removeEventListener("pointerdown", this.onClick);
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
    if (this.animating || !this.history.length) return;
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
    const geo = new THREE.BoxGeometry(0.7, 0.7, 0.7);
    for (const cell of CELLS) {
      const group = new THREE.Group();
      group.position.set(...CELL_ORIGIN[cell]);
      group.userData.cell = cell;
      const [cellAxis, cellExt] = CELL_AXIS[cell];
      const [a, b, c] = localAxes(cell);
      for (let i = 0; i < 3; i += 1) {
        for (let j = 0; j < 3; j += 1) {
          for (let k = 0; k < 3; k += 1) {
            const pos = [0, 0, 0, 0];
            pos[cellAxis] = cellExt;
            pos[a] = i;
            pos[b] = j;
            pos[c] = k;
            const cubie = this.cube.cubies.get(pos.join(","));
            const color = cubie.colors[cell];
            const mat = new THREE.MeshStandardMaterial({
              color: COLOR_HEX[color],
              roughness: 0.35,
              metalness: 0.04,
            });
            const mesh = new THREE.Mesh(geo, mat);
            const off = localToOffset(cell, i, j, k);
            mesh.position.set(...off);
            mesh.userData = { cell, i, j, k };
            group.add(mesh);
            this.stickerMeshes.push(mesh);
          }
        }
      }
      if (this.showLabels) {
        const label = makeLabel(cell, COLOR_HEX[CELL_COLOR[cell]]);
        label.position.set(0, 1.55, 0);
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
    const axis = move.order === 4 && axisCell ? axisWorldDir(move.cell, axisCell) : new THREE.Vector3(0, 1, 0);
    let radians = Math.PI / 2;
    if (move.order === 4) {
      const q = ((move.turns % 4) + 4) % 4;
      radians = q === 1 ? Math.PI / 2 : q === 2 ? Math.PI : q === 3 ? -Math.PI / 2 : 0;
      if (CELL_AXIS[move.cell][1] === 0) radians = -radians;
      if (CELL_AXIS[axisCell][1] === 0) radians = -radians;
    } else if (move.order === 2) radians = Math.PI;
    else radians = ((move.turns % 3) * 2 * Math.PI) / 3;

    const start = performance.now();
    const duration = 200;
    const tick = (now) => {
      if (this._stopped) return;
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - (1 - t) ** 3;
      if (group && move.order === 4) {
        group.setRotationFromAxisAngle(axis, radians * eased);
      }
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

  handleClick(event) {
    if (this.animating || (event.button !== 0 && event.button !== 2)) return;
    const rect = this.canvas.getBoundingClientRect();
    this.pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const hit = this.raycaster.intersectObjects(this.stickerMeshes, false)[0];
    if (!hit) return;
    this.controls.enabled = false;
    const now = performance.now();
    const dbl = event.button === 0 && now - this._lastClickAt < 320;
    this._lastClickAt = now;
    const prev = this.modifier;
    if (event.button === 2) this.modifier = 3;
    else if (dbl) this.modifier = 2;
    const move = this.stickerToMove(hit.object.userData);
    this.modifier = prev;
    if (move) this.enqueue(move);
    setTimeout(() => {
      this.controls.enabled = true;
    }, 40);
  }

  stickerToMove(data) {
    const { cell, i, j, k } = data;
    const axes = localAxes(cell);
    const coords = [i, j, k];
    const extremes = [];
    coords.forEach((v, idx) => {
      if (v === 0 || v === 2) {
        extremes.push(AXIS_CELL[`${axes[idx]},${v}`]);
      }
    });
    if (extremes.length === 1) {
      return {
        cell,
        axis: extremes[0],
        turns: this.modifier,
        order: 4,
        axisCells: extremes,
      };
    }
    if (extremes.length === 2) {
      return { cell, axis: extremes.join(""), turns: 1, order: 2, axisCells: extremes };
    }
    if (extremes.length === 3) {
      const turns = this.modifier === 3 ? 2 : 1;
      return { cell, axis: extremes.join(""), turns, order: 3, axisCells: extremes };
    }
    return null;
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
