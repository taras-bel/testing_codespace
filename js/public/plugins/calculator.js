document.addEventListener('DOMContentLoaded', () => {
  const output = document.getElementById('calc-output');
  document.getElementById('calc-form').addEventListener('submit', e => {
    e.preventDefault();
    try {
      const result = eval(document.getElementById('calc-input').value);
      output.textContent = 'Result: ' + result;
    } catch {
      output.textContent = 'Error';
    }
  });
});