const express = require('express');
const router = express.Router();
const { renderGraphicsPage } = require('../controllers/graphicsController');
const { authenticate } = require('../middleware/authMiddleware');

router.get('/canvas', authenticate, renderGraphicsPage);

module.exports = router;