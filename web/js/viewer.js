import * as THREE from "three";
import { OrbitControls } from "../vendor/OrbitControls.js";
import {
  COLOR_HEX,
  Cube,
  PLASTIC,
  axisOf,
  formatMoves,
  invertMoves,
  moveLayers,
  notation,
  parseMoves,
  sliceIndex,
} from "./engine.js";

const FACE_NORMALS = {
  R: [1, 0, 0],
  L: [-1, 0, 0],
  U: [0, 1, 0],
  D: [0, -1, 0],
  F: [0, 0, 1],
  B: [0, 0, -1],
};

function shortestRadians(quarterTurns) {
  const q = ((quarterTurns % 4) + 4) % 4;
  if (q === 1) return Math.PI / 2;
  if (q === 2) return Math.PI;
  if (q === 3) return -Math.PI / 2;
  return 0;
}

function faceDir(face) {
  return { R: -1, L: 1, U: -1, D: 1, F: -1, B: 1 }[face];
}

export class CubeViewer {
  constructor(canvas, onChange) {
    this.canvas = canvas;
    this.onChange = onChange;
    this.cube = new Cube(3);
    this.history = [];
    this.scramble = [];
    this.queue = [];
    this.animating = false;
    this.pitch = 1.08;
    this.drag = null;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0b0d10);
    this.camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
    this.camera.position.set(4.6, 3.8, 6.2);

    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.enablePan = false;
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.minDistance = 4;
    this.controls.maxDistance = 28;
    this.controls.target.set(0, 0, 0);

    this.pivot = new THREE.Group();
    this.scene.add(this.pivot);
    this.root = new THREE.Group();
    this.scene.add(this.root);

    const hemi = new THREE.HemisphereLight(0xffffff, 0x1a1a1a, 1.15);
    this.scene.add(hemi);
    const key = new THREE.DirectionalLight(0xffffff, 1.05);
    key.position.set(6, 10, 8);
    this.scene.add(key);
    const fill = new THREE.DirectionalLight(0x88aacc, 0.35);
    fill.position.set(-8, -4, -6);
    this.scene.add(fill);

    this.raycaster = new THREE.Raycaster();
    this.pointer = new THREE.Vector2();
    this.stickerMeshes = [];

    this.boundPointerDown = this.onPointerDown.bind(this);
    this.boundPointerMove = this.onPointerMove.bind(this);
    this.boundPointerUp = this.onPointerUp.bind(this);
    canvas.addEventListener("pointerdown", this.boundPointerDown);
    window.addEventListener("pointermove", this.boundPointerMove);
    window.addEventListener("pointerup", this.boundPointerUp);

    this.resize();
    window.addEventListener("resize", () => this.resize());
    this.rebuild();
    this.loop();
  }

  setSize(size) {
    this.cube = new Cube(size);
    this.history = [];
    this.scramble = [];
    this.rebuild();
    this.notify();
  }

  loadState(state) {
    this.cube = Cube.fromDict(state);
    this.history = [];
    this.rebuild();
    this.notify();
  }

  reset() {
    this.cube.reset();
    this.history = [];
    this.scramble = [];
    this.rebuild();
    this.notify();
  }

  applyScramble(moves) {
    this.reset();
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
    for (const move of parseMoves(text)) this.enqueue(move);
  }

  undo() {
    if (this.animating || !this.history.length) return;
    const last = this.history.pop();
    this.enqueue({ ...last, turns: last.turns === 2 ? 2 : 4 - last.turns, _undo: true });
  }

  solveByReverse() {
    const path = invertMoves([...this.scramble, ...this.history]);
    for (const move of path) this.enqueue(move);
  }

  worldFromIndex(i, n) {
    return (i - (n - 1) / 2) * this.pitch;
  }

  indexFromWorld(value, n) {
    return Math.round(value / this.pitch + (n - 1) / 2);
  }

  rebuild() {
    while (this.root.children.length) {
      const obj = this.root.children[0];
      this.root.remove(obj);
    }
    this.stickerMeshes = [];
    const n = this.cube.size;
    const cubieSize = 1;
    const sticker = cubieSize * 0.86;
    const stickerZ = cubieSize / 2 + 0.001;
    const geo = new THREE.BoxGeometry(cubieSize, cubieSize, cubieSize);
    const stickerGeo = new THREE.PlaneGeometry(sticker, sticker);
    const plastic = new THREE.MeshStandardMaterial({
      color: PLASTIC,
      roughness: 0.45,
      metalness: 0.12,
    });

    for (const cubie of this.cube.cubies.values()) {
      const group = new THREE.Group();
      group.position.set(
        this.worldFromIndex(cubie.x, n),
        this.worldFromIndex(cubie.y, n),
        this.worldFromIndex(cubie.z, n),
      );
      group.userData = { x: cubie.x, y: cubie.y, z: cubie.z };
      const body = new THREE.Mesh(geo, plastic);
      group.add(body);
      for (const [face, color] of Object.entries(cubie.colors)) {
        const mat = new THREE.MeshStandardMaterial({
          color: COLOR_HEX[color],
          roughness: 0.35,
          metalness: 0.04,
        });
        const mesh = new THREE.Mesh(stickerGeo, mat);
        const [nx, ny, nz] = FACE_NORMALS[face];
        mesh.position.set(nx * stickerZ, ny * stickerZ, nz * stickerZ);
        mesh.lookAt(mesh.position.clone().add(new THREE.Vector3(nx, ny, nz)));
        mesh.userData = { face, cubie: group.userData, color };
        group.add(mesh);
        this.stickerMeshes.push(mesh);
      }
      this.root.add(group);
    }
    const span = n * this.pitch + 1.5;
    this.controls.minDistance = span * 0.7;
    this.controls.maxDistance = span * 3.5;
    const dist = Math.max(6, span * 1.55);
    const current = this.camera.position.length();
    if (!this._framed || current < dist * 0.9) {
      const dir = this.camera.position.clone().normalize();
      if (!this._framed || dir.lengthSq() === 0) {
        this.camera.position.set(dist * 0.72, dist * 0.58, dist);
      } else {
        this.camera.position.copy(dir.multiplyScalar(dist));
      }
      this._framed = true;
    }
  }

  playNext() {
    if (!this.queue.length) {
      this.animating = false;
      return;
    }
    this.animating = true;
    const move = this.queue.shift();
    const n = this.cube.size;
    const axis = axisOf(move.face);
    const layers = moveLayers(move, n);
    const indices = new Set(layers.map((layer) => sliceIndex(move.face, layer, n)));
    const direction = (((faceDir(move.face) * move.turns) % 4) + 4) % 4;
    const radians = shortestRadians(direction);
    const axisVec = [new THREE.Vector3(1, 0, 0), new THREE.Vector3(0, 1, 0), new THREE.Vector3(0, 0, 1)][axis];

    while (this.pivot.children.length) this.root.attach(this.pivot.children[0]);
    this.pivot.rotation.set(0, 0, 0);
    for (const child of [...this.root.children]) {
      const { x, y, z } = child.userData;
      const coord = [x, y, z][axis];
      if (indices.has(coord)) this.pivot.attach(child);
    }

    const duration = move.turns === 2 ? 280 : 200;
    const start = performance.now();
    const tick = (now) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - (1 - t) ** 3;
      this.pivot.setRotationFromAxisAngle(axisVec, radians * eased);
      if (t < 1) {
        this._anim = requestAnimationFrame(tick);
        return;
      }
      while (this.pivot.children.length) this.root.attach(this.pivot.children[0]);
      this.pivot.rotation.set(0, 0, 0);
      if (!move._undo) this.history.push({ face: move.face, layer: move.layer, wide: move.wide, turns: move.turns });
      this.cube.applyMove({ face: move.face, layer: move.layer, wide: move.wide, turns: move.turns });
      this.rebuild();
      this.notify();
      this.playNext();
    };
    this._anim = requestAnimationFrame(tick);
  }

  pointerNDC(event) {
    const rect = this.canvas.getBoundingClientRect();
    this.pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  }

  hitSticker(event) {
    this.pointerNDC(event);
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const hits = this.raycaster.intersectObjects(this.stickerMeshes, false);
    return hits[0] || null;
  }

  onPointerDown(event) {
    if (this.animating || event.button !== 0) return;
    const hit = this.hitSticker(event);
    if (!hit) return;
    this.controls.enabled = false;
    this.drag = {
      startX: event.clientX,
      startY: event.clientY,
      cubie: hit.object.userData.cubie,
      face: hit.object.userData.face,
      committed: false,
    };
  }

  onPointerMove(event) {
    if (!this.drag || this.drag.committed) return;
    const dx = event.clientX - this.drag.startX;
    const dy = event.clientY - this.drag.startY;
    if (Math.hypot(dx, dy) < 18) return;
    const move = this.dragToMove(this.drag, dx, dy);
    if (!move) return;
    this.drag.committed = true;
    this.controls.enabled = true;
    this.enqueue(move);
  }

  onPointerUp() {
    this.drag = null;
    this.controls.enabled = true;
  }

  dragToMove(drag, dx, dy) {
    const n = this.cube.size;
    const normal = new THREE.Vector3(...FACE_NORMALS[drag.face]);
    const camRight = new THREE.Vector3();
    const camUp = new THREE.Vector3();
    this.camera.matrixWorld.extractBasis(camRight, camUp, new THREE.Vector3());
    const screen = camRight.multiplyScalar(dx).add(camUp.multiplyScalar(-dy)).normalize();
    const axisVec = new THREE.Vector3().crossVectors(normal, screen);
    const abs = [Math.abs(axisVec.x), Math.abs(axisVec.y), Math.abs(axisVec.z)];
    const axis = abs[0] >= abs[1] && abs[0] >= abs[2] ? 0 : abs[1] >= abs[2] ? 1 : 2;
    const sign = Math.sign(axisVec.getComponent(axis)) || 1;
    const coord = [drag.cubie.x, drag.cubie.y, drag.cubie.z][axis];
    const face = axis === 0 ? (coord > (n - 1) / 2 ? "R" : "L") : axis === 1 ? (coord > (n - 1) / 2 ? "U" : "D") : coord > (n - 1) / 2 ? "F" : "B";
    const layer = FACE_NORMALS[face][axis] > 0 ? n - coord : coord + 1;
    const dir = faceDir(face);
    // Engine applies dir * turns +RH quarter turns. We want visual rotation `sign` on +axis.
    // shortestRadians(dir * turns) should have the same sign as `sign` around +axis.
    let turns = 1;
    const quarter = (((dir * turns) % 4) + 4) % 4;
    const visual = Math.sign(shortestRadians(quarter)) || 1;
    if (visual !== sign) turns = 3;
    return { face, layer, wide: false, turns };
  }

  notify() {
    if (this.onChange) {
      this.onChange({
        cube: this.cube,
        history: this.history,
        scramble: this.scramble,
        solved: this.cube.isSolved(),
        moves: formatMoves(this.history),
        scrambleText: formatMoves(this.scramble),
      });
    }
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
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
    requestAnimationFrame(() => this.loop());
  }
}

export { formatMoves, invertMoves, notation, parseMoves };
