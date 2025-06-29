const { sanitizeInput } = require('../../js/server/security/xssFilter');
const { writeSecureLog } = require('../../js/server/security/safeLogger');

const dirty = '<script>alert("xss")</script>';
console.log('Sanitized:', sanitizeInput(dirty));
writeSecureLog('test-session', 'Malicious attempt: ' + dirty);