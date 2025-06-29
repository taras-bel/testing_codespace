function notifyTeamsSessionState(sessionId, state) {
  console.log(`[Teams] State for session ${sessionId}: ${state}`);
}
module.exports = { notifyTeamsSessionState };