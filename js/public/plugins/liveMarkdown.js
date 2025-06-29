document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('md-input');
  const preview = document.getElementById('md-preview');
  if (!input || !preview) return;
  input.addEventListener('input', () => {
    const md = input.value
      .replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
      .replace(/\_(.*?)\_/g, '<i>$1</i>');
    preview.innerHTML = md;
  });
});