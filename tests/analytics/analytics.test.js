const { calculateTypingSpeed } = require('../../js/server/utils/analytics/typingSpeed');
const { summarizeActivity } = require('../../js/server/utils/analytics/activitySummary');

const sampleLogs = [
  { user: 'alice', action: 'edit', timestamp: 1000, chars: 20 },
  { user: 'alice', action: 'edit', timestamp: 2000, chars: 30 },
  { user: 'bob', action: 'copy', timestamp: 3000 },
  { user: 'bob', action: 'paste', timestamp: 4000 }
];

console.log('Typing speed:', calculateTypingSpeed(sampleLogs));
console.log('Activity summary:', summarizeActivity(sampleLogs));