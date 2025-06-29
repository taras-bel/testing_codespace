function csrfProtection(req, res, next) {
  const token = req.headers['x-csrf-token'];
  if (!token || token !== process.env.CSRF_SECRET) {
    return res.status(403).json({ message: 'Invalid CSRF token' });
  }
  next();
}

module.exports = csrfProtection;