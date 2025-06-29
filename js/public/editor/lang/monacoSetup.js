require.config({ paths: { 'vs': 'https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs' } });
require(['vs/editor/editor.main'], function() {
  window.monacoInstance = monaco.editor.create(document.getElementById('editor'), {
    value: '',
    language: 'plaintext',
    theme: 'vs-light',
    automaticLayout: true
  });
});