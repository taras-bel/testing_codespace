const fs = require('fs');
const path = require('path');

function getLogStats(sessionId, date) {
  const dir = path.join(__dirname, '../../../logs', sessionId);
  const file = path.join(dir, `${date}.actions.md`);
  if (!fs.existsSync(file)) return { count: 0, size: 0 };

  const content = fs.readFileSync(file, 'utf8');
  const count = (content.match(/^###/gm) || []).length;
  return { count, size: content.length };
}

module.exports = { getLogStats };