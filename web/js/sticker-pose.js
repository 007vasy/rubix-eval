/** PlaneGeometry faces +Z. XYZ Euler that lays +Z along the face normal. */
export function stickerEuler(nx, ny, nz) {
  if (nx === 1) return [0, Math.PI / 2, 0];
  if (nx === -1) return [0, -Math.PI / 2, 0];
  if (ny === 1) return [-Math.PI / 2, 0, 0];
  if (ny === -1) return [Math.PI / 2, 0, 0];
  if (nz === -1) return [0, Math.PI, 0];
  return [0, 0, 0];
}
