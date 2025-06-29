document.addEventListener('DOMContentLoaded', () => {
  const preview = document.getElementById('image-preview');
  fetch('/media/<sessionId>')
    .then(res => res.json())
    .then(files => {
      files.forEach(f => {
        const img = document.createElement('img');
        img.src = '/logs/<sessionId>/images/' + f;
        img.style.maxWidth = '200px';
        img.style.margin = '5px';
        preview.appendChild(img);
      });
    });
});