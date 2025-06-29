function startScreenActivityTracking(userId) {
  if (typeof document === 'undefined') return;

  document.addEventListener('visibilitychange', () => {
    const active = !document.hidden;
    console.log(`[Screen] User ${userId} is ${active ? 'active' : 'inactive'}`);
  });
}
module.exports = { startScreenActivityTracking };