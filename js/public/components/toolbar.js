document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.toolbar button').forEach(btn => {
    btn.addEventListener('click', () => {
      console.log('Toolbar action:', btn.dataset.action);
    });
  });
});