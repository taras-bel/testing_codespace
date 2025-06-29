const fs = require('fs');
const path = require('path');

function logToFile(sessionId, message, type = 'actions') {
  const date = new Date().toISOString().slice(0, 10);
  const dirPath = path.join(__dirname, '../../../logs', sessionId);
  if (!fs.existsSync(dirPath)) fs.mkdirSync(dirPath, { recursive: true });

  const filePath = path.join(dirPath, `${date}.${type}.md`);
  const entry = `### ${new Date().toISOString()}\n${message}\n\n`;
  fs.appendFileSync(filePath, entry, 'utf8');
}

module.exports = { logToFile };