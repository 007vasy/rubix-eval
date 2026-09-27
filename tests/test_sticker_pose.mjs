import assert from "node:assert/strict";
import * as THREE from "../web/vendor/three.module.js";
import { stickerEuler } from "../web/js/sticker-pose.js";

const faces = [
  [1, 0, 0],
  [-1, 0, 0],
  [0, 1, 0],
  [0, -1, 0],
  [0, 0, 1],
  [0, 0, -1],
];

for (const [nx, ny, nz] of faces) {
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(1, 1));
  const [rx, ry, rz] = stickerEuler(nx, ny, nz);
  mesh.rotation.set(rx, ry, rz);
  const facing = new THREE.Vector3(0, 0, 1).applyQuaternion(mesh.quaternion);
  const normal = new THREE.Vector3(nx, ny, nz);
  assert.ok(
    facing.distanceTo(normal) < 1e-6,
    `sticker +Z ${facing.toArray()} != normal ${normal.toArray()}`,
  );
}

console.log("sticker planes face outward");
