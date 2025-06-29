const crypto = require('crypto');
const blocks = {};

function calculateHash(block) {
  const { index, timestamp, userId, action, content, prevHash } = block;
  const data = `${index}${timestamp}${userId}${action}${content}${prevHash}`;
  return crypto.createHash('sha256').update(data).digest('hex');
}

function createBlock(sessionId, userId, action, content) {
  if (!blocks[sessionId]) blocks[sessionId] = [];
  const chain = blocks[sessionId];
  const prevHash = chain.length > 0 ? chain[chain.length - 1].hash : 'GENESIS';
  const newBlock = {
    index: chain.length,
    timestamp: new Date().toISOString(),
    userId,
    action,
    content,
    prevHash,
  };
  newBlock.hash = calculateHash(newBlock);
  chain.push(newBlock);
  return newBlock;
}

function verifyChain(sessionId) {
  const chain = blocks[sessionId] || [];
  for (let i = 1; i < chain.length; i++) {
    if (chain[i].prevHash !== chain[i - 1].hash) return false;
    if (calculateHash(chain[i]) !== chain[i].hash) return false;
  }
  return true;
}

function getSessionChain(sessionId) {
  return blocks[sessionId] || [];
}

module.exports = { createBlock, verifyChain, getSessionChain };