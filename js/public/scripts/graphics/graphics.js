document.addEventListener('DOMContentLoaded', () => {
  const canvas = document.getElementById('graphics-canvas');
  const ctx = canvas.getContext('2d');
  let drawing = false;

  canvas.addEventListener('mousedown', (e) => {
    drawing = true;
    ctx.beginPath();
    ctx.moveTo(e.offsetX, e.offsetY);
  });

  canvas.addEventListener('mousemove', (e) => {
    if (!drawing) return;
    ctx.lineTo(e.offsetX, e.offsetY);
    ctx.stroke();
    emitDrawing(e.offsetX, e.offsetY);
  });

  canvas.addEventListener('mouseup', () => {
    drawing = false;
  });

  const socket = io({
    auth: { token: localStorage.getItem('token') }
  });

  function emitDrawing(x, y) {
    socket.emit('graphics:draw', { x, y });
  }

  socket.on('graphics:update', ({ x, y }) => {
    ctx.lineTo(x, y);
    ctx.stroke();
  });
});