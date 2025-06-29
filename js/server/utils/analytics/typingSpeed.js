function calculateTypingSpeed(logs) {
  if (!logs || logs.length < 2) return 0;
  const times = logs.map(l => l.timestamp);
  const totalTime = (Math.max(...times) - Math.min(...times)) / 1000; // seconds
  const chars = logs.reduce((sum, l) => sum + (l.chars || 0), 0);
  return +(chars / (totalTime || 1) * 60).toFixed(2); // chars/min
}
module.exports = { calculateTypingSpeed };