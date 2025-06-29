const { notifyDiscordSessionStart } = require('../../js/server/integrations/discord');
const { checkGoogleMeetActivity } = require('../../js/server/integrations/googleMeet');
const { notifyTeamsSessionState } = require('../../js/server/integrations/teams');

notifyDiscordSessionStart('abc123', 'alice');
console.log('In Google Meet:', checkGoogleMeetActivity('bob'));
notifyTeamsSessionState('abc123', 'editing');