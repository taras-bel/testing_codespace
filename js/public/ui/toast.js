function showToast(msg, duration = 3000) {
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = msg;
  toast.style.cssText = 'position:fixed;bottom:20px;right:20px;padding:10px;background:#00cccc;color:white;border-radius:5px;';
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), duration);
}