const { detectLanguage } = require('../../js/public/editor/lang/languageDetect');

const samples = ['main.py', 'script.js', 'program.cpp', 'build.gradle', 'demo.swift', 'data.sql'];

samples.forEach(file => {
  console.log(file, '->', detectLanguage(file));
});