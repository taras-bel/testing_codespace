function checkGoogleMeetActivity(userId) {
  console.log(`[GoogleMeet] Checking if ${userId} is in a meeting...`);
  return Math.random() > 0.5; // mock presence
}
module.exports = { checkGoogleMeetActivity };