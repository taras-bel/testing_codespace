const express = require('express');
const router = express.Router();
const {
  createSession,
  getSessionById,
  updateSession,
  deleteSession
} = require('../controllers/sessionController');
const { requireAuth } = require('../middleware/authMiddleware');

router.post('/create', requireAuth, createSession);
router.get('/:id', requireAuth, getSessionById);
router.put('/:id', requireAuth, updateSession);
router.delete('/:id', requireAuth, deleteSession);

module.exports = router;