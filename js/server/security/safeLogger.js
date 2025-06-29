const fs = require('fs');
const path = require('path');

function writeSecureLog(sessionId, message) {
  const logDir = path.join(__dirname, '..', '..', '..', '..', 'logs', sessionId);
  if (!fs.existsSync(logDir)) fs.mkdirSync(logDir, { recursive: true });
  const safeMessage = message.replace(/[<>]/g, '');
  const logPath = path.join(logDir, 'secure.log.md');
  fs.appendFileSync(logPath, `- ${new Date().toISOString()} — ${safeMessage}\n`);
}

module.exports = { writeSecureLog };