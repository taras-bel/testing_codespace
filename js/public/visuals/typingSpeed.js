function plotTypingSpeed(containerId, data) {
  const ctx = document.getElementById(containerId).getContext('2d');
  new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.map(e => e.time),
      datasets: [{
        label: 'Typing Speed (chars/min)',
        data: data.map(e => e.speed),
        fill: false,
        borderColor: '#00cccc',
        tension: 0.1
      }]
    }
  });
}