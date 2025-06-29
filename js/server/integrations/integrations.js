const log = require('../utils/general/logWriter');

function logPresence(service, user, status) {
  const sessionId = 'global-integrations';
  const message = `[${service}] ${user} is now ${status}`;
  log.writeSessionLog(sessionId, message);
}

function simulateTeamsStatus(user, status) {
  logPresence('Teams', user, status);
}

function simulateMeetStatus(user, status) {
  logPresence('Google Meet', user, status);
}

function simulateDiscordStatus(user, status) {
  logPresence('Discord', user, status);
}

module.exports = {
  simulateTeamsStatus,
  simulateMeetStatus,
  simulateDiscordStatus
};