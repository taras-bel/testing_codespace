document.addEventListener('DOMContentLoaded', () => {
  const output = document.getElementById('output-panel');
  window.renderOutput = function (content) {
    output.innerText = content;
    output.classList.add('visible');
  };
});