const fs = require('fs');
const path = require('path');

const logToFile = (sessionId, data) => {
  const dir = path.join(__dirname, '../../logs', sessionId);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

  const filePath = path.join(dir, `${new Date().toISOString().split('T')[0]}.md`);
  const log = `\n### ${new Date().toLocaleString()}\n${data}\n`;
  fs.appendFileSync(filePath, log, 'utf8');
};

module.exports = { logToFile };