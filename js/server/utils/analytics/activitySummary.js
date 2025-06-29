function summarizeActivity(logs) {
  const activity = {};
  logs.forEach(log => {
    const user = log.user;
    if (!activity[user]) activity[user] = { edits: 0, pastes: 0, copies: 0 };
    if (log.action === 'edit') activity[user].edits += 1;
    if (log.action === 'paste') activity[user].pastes += 1;
    if (log.action === 'copy') activity[user].copies += 1;
  });
  return activity;
}
module.exports = { summarizeActivity };