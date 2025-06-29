document.addEventListener('DOMContentLoaded', () => {
  const canvas = document.getElementById('draw-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let drawing = false;

  canvas.addEventListener('mousedown', () => drawing = true);
  canvas.addEventListener('mouseup', () => drawing = false);
  canvas.addEventListener('mousemove', e => {
    if (!drawing) return;
    ctx.fillStyle = '#00cccc';
    ctx.beginPath();
    ctx.arc(e.offsetX, e.offsetY, 3, 0, 2 * Math.PI);
    ctx.fill();
  });
});