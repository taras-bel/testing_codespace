const fs = require('fs');
const path = require('path');

function writeSessionLog(sessionId, entry) {
  const folderPath = path.join(__dirname, '..', '..', '..', '..', 'logs', sessionId);
  if (!fs.existsSync(folderPath)) fs.mkdirSync(folderPath, { recursive: true });

  const logFile = path.join(folderPath, 'session.md');
  const line = `- [${new Date().toISOString()}] ${entry}\n`;
  fs.appendFileSync(logFile, line);
}

module.exports = { writeSessionLog };