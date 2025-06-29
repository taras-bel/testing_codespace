const validateEmail = require('../../js/server/validators/validateEmail');
const validateSessionId = require('../../js/server/validators/validateSessionId');

console.assert(validateEmail('user@example.com') === true);
console.assert(validateEmail('bad-email') === false);
console.assert(validateSessionId('507f1f77bcf86cd799439011') === true);
console.assert(validateSessionId('not-valid') === false);
console.log('Security validation tests passed.');