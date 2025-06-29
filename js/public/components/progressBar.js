function updateProgressBar(percent) {
  const bar = document.getElementById('progress-bar');
  bar.style.width = percent + '%';
  bar.innerText = percent + '%';
}