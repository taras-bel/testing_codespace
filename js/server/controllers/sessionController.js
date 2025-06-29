const Session = require('../models/session');

const createSession = async (req, res) => {
  try {
    const session = await Session.create({ ownerId: req.user.id, ...req.body });
    res.status(201).json(session);
  } catch (err) {
    res.status(500).json({ message: 'Failed to create session', error: err.message });
  }
};

const getSessionById = async (req, res) => {
  try {
    const session = await Session.findById(req.params.id);
    if (!session) return res.status(404).json({ message: 'Session not found' });
    res.json(session);
  } catch (err) {
    res.status(500).json({ message: 'Failed to retrieve session', error: err.message });
  }
};

const updateSession = async (req, res) => {
  try {
    const session = await Session.findByIdAndUpdate(req.params.id, req.body, { new: true });
    res.json(session);
  } catch (err) {
    res.status(500).json({ message: 'Failed to update session', error: err.message });
  }
};

const deleteSession = async (req, res) => {
  try {
    await Session.findByIdAndDelete(req.params.id);
    res.status(204).send();
  } catch (err) {
    res.status(500).json({ message: 'Failed to delete session', error: err.message });
  }
};

module.exports = { createSession, getSessionById, updateSession, deleteSession };