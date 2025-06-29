const integrations = require('../../js/server/integrations/integrations');

integrations.simulateTeamsStatus('alice', 'in a call');
integrations.simulateMeetStatus('bob', 'sharing screen');
integrations.simulateDiscordStatus('carol', 'muted');
console.log('Integration simulation logs sent.');