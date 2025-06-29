document.addEventListener('DOMContentLoaded', () => {
  const canvas = document.getElementById('typing-speed-chart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  window.renderTypingSpeedChart = function (dataPoints) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.beginPath();
    ctx.moveTo(0, 150);
    dataPoints.forEach((val, i) => ctx.lineTo(i * 10, 150 - val));
    ctx.strokeStyle = '#00cfcf';
    ctx.lineWidth = 2;
    ctx.stroke();
  };
});