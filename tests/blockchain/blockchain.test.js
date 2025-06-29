const { Blockchain } = require('../../js/server/utils/blockchain/blockchain');

const sessionChain = new Blockchain();

sessionChain.addBlock({ user: 'alice', action: 'edit', content: 'let x = 1;' });
sessionChain.addBlock({ user: 'bob', action: 'copy' });
sessionChain.addBlock({ user: 'alice', action: 'paste', content: 'console.log(x)' });

console.log('Chain valid:', sessionChain.isChainValid());
console.log('Chain:', sessionChain.exportChain());