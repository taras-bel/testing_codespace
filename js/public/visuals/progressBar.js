function renderProgressBar(containerId, value) {
  const el = document.getElementById(containerId);
  el.innerHTML = '';
  const bar = document.createElement('div');
  bar.style.width = value + '%';
  bar.style.height = '20px';
  bar.style.backgroundColor = '#00cccc';
  el.appendChild(bar);
}