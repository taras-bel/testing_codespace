const mongoose = require('mongoose');

const sessionSchema = new mongoose.Schema({
  title: { type: String, required: true },
  ownerId: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  isPrivate: { type: Boolean, default: false },
  language: { type: String, default: 'javascript' },
  content: { type: String, default: '' }
}, { timestamps: true });

module.exports = mongoose.model('Session', sessionSchema);