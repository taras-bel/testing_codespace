const crypto = require('crypto');

class Block {
  constructor(index, timestamp, data, prevHash = '') {
    this.index = index;
    this.timestamp = timestamp;
    this.data = data;
    this.prevHash = prevHash;
    this.hash = this.calculateHash();
  }

  calculateHash() {
    const raw = this.index + this.timestamp + JSON.stringify(this.data) + this.prevHash;
    return crypto.createHash('sha256').update(raw).digest('hex');
  }
}

class Blockchain {
  constructor() {
    this.chain = [this.createGenesisBlock()];
  }

  createGenesisBlock() {
    return new Block(0, Date.now(), "Genesis Block", "0");
  }

  getLatestBlock() {
    return this.chain[this.chain.length - 1];
  }

  addBlock(data) {
    const latest = this.getLatestBlock();
    const newBlock = new Block(this.chain.length, Date.now(), data, latest.hash);
    this.chain.push(newBlock);
    return newBlock;
  }

  isChainValid() {
    for (let i = 1; i < this.chain.length; i++) {
      const current = this.chain[i];
      const prev = this.chain[i - 1];

      if (current.hash !== current.calculateHash()) return false;
      if (current.prevHash !== prev.hash) return false;
    }
    return true;
  }

  exportChain() {
    return this.chain.map(b => ({
      index: b.index,
      timestamp: b.timestamp,
      data: b.data,
      hash: b.hash,
      prevHash: b.prevHash
    }));
  }
}

module.exports = { Blockchain };