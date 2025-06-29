const sessionRoles = {};

function setRole(sessionId, userId, role) {
  if (!sessionRoles[sessionId]) sessionRoles[sessionId] = {};
  sessionRoles[sessionId][userId] = role;
}

function getRole(sessionId, userId) {
  return sessionRoles[sessionId]?.[userId] || 'viewer';
}

function transferOwnership(sessionId, oldOwnerId, newOwnerId) {
  if (getRole(sessionId, oldOwnerId) !== 'owner') return false;
  setRole(sessionId, newOwnerId, 'owner');
  setRole(sessionId, oldOwnerId, 'editor');
  return true;
}

module.exports = { setRole, getRole, transferOwnership };