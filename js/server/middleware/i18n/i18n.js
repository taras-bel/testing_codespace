const fs = require('fs');
const path = require('path');

const supportedLangs = ['en', 'ru', 'de', 'es', 'fr'];

function i18n(req, res, next) {
  const lang = req.query.lang || req.cookies.lang || 'en';
  const language = supportedLangs.includes(lang) ? lang : 'en';
  const localePath = path.join(__dirname, '../../../locales', `${language}.json`);

  try {
    const translations = JSON.parse(fs.readFileSync(localePath, 'utf8'));
    res.locals.t = key => translations[key] || key;
  } catch {
    res.locals.t = key => key;
  }

  res.locals.lang = language;
  next();
}

module.exports = i18n;