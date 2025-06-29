document.addEventListener('DOMContentLoaded', () => {
  const editor = document.getElementById('markdown-input');
  const preview = document.getElementById('markdown-preview');

  if (editor && preview) {
    editor.addEventListener('input', () => {
      preview.innerHTML = marked.parse(editor.value);
    });
  }
});