const { logToFile } = require('../../js/server/utils/logging/logToFile');
const { getLogStats } = require('../../js/server/utils/logging/analytics');

logToFile('test_session', '**User:** x123 — _pasted code_', 'clipboard');
const stats = getLogStats('test_session', new Date().toISOString().slice(0, 10));
console.log('Entries:', stats.count, 'Size:', stats.size);