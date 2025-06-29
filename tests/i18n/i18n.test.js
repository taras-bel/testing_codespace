const i18n = require('../../js/server/middleware/i18n/i18n');
const httpMocks = require('node-mocks-http');
const fs = require('fs');

const req = httpMocks.createRequest({ query: { lang: 'ru' } });
const res = httpMocks.createResponse();

i18n(req, res, () => {
  const message = res.locals.t('welcome');
  console.log('Translation test (ru):', message);
});