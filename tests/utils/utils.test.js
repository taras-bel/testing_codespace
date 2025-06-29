const { writeSessionLog } = require('../../js/server/utils/general/logWriter');
const { saveFile, readFile } = require('../../js/server/utils/general/fileManager');
const { setRole, getRole, transferOwnership } = require('../../js/server/utils/general/roleManager');

writeSessionLog('testsession', 'User Alice joined session');
saveFile('testsession', 'code.js', 'console.log("Hello")');
console.log('Read code:', readFile('testsession', 'code.js'));

setRole('testsession', '1', 'owner');
setRole('testsession', '2', 'viewer');
console.log('Transfer:', transferOwnership('testsession', '1', '2'));
console.log('Role 2:', getRole('testsession', '2'));