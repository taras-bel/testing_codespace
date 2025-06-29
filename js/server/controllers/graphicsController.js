const path = require('path');

const renderGraphicsPage = (req, res) => {
  res.render('graphics/graphics', {
    user: req.user,
    title: 'Canvas Session'
  });
};

module.exports = { renderGraphicsPage };