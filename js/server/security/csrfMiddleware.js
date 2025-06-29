function generateCSRFToken(req, res, next) {
  const token = Math.random().toString(36).substring(2);
  res.locals.csrfToken = token;
  res.cookie('csrfToken', token, { httpOnly: true });
  next();
}

function verifyCSRFToken(req, res, next) {
  const tokenCookie = req.cookies['csrfToken'];
  const tokenHeader = req.headers['x-csrf-token'];
  if (tokenCookie && tokenHeader && tokenCookie === tokenHeader) {
    next();
  } else {
    return res.status(403).json({ error: 'CSRF token invalid' });
  }
}

module.exports = { generateCSRFToken, verifyCSRFToken };