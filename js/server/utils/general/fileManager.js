const fs = require('fs');
const path = require('path');

function saveFile(sessionId, filename, content) {
  const sessionPath = path.join(__dirname, '..', '..', '..', '..', 'logs', sessionId);
  if (!fs.existsSync(sessionPath)) fs.mkdirSync(sessionPath, { recursive: true });
  fs.writeFileSync(path.join(sessionPath, filename), content, 'utf-8');
}

function readFile(sessionId, filename) {
  const filePath = path.join(__dirname, '..', '..', '..', '..', 'logs', sessionId, filename);
  if (!fs.existsSync(filePath)) return null;
  return fs.readFileSync(filePath, 'utf-8');
}

module.exports = { saveFile, readFile };