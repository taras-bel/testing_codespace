document.addEventListener('DOMContentLoaded', () => {
  const canvas = document.getElementById('graph-canvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  window.drawGraph = function (points = []) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.beginPath();
    ctx.moveTo(0, canvas.height - points[0]);
    points.forEach((y, i) => {
      ctx.lineTo(i * 10, canvas.height - y);
    });
    ctx.strokeStyle = '#00cfcf';
    ctx.stroke();
  };
});