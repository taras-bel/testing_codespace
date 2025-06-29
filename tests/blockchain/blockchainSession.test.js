const { Blockchain } = require('../../js/server/utils/blockchain/blockchainSession');

const sessionChain = new Blockchain();
sessionChain.addBlock({ user: 'alice', action: 'edit', content: 'print("hi")' });
sessionChain.addBlock({ user: 'bob', action: 'paste', content: 'alert("x")' });

console.log('Valid?', sessionChain.isChainValid());
console.log('Chain:', sessionChain.chain);