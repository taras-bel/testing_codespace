document.addEventListener('DOMContentLoaded', () => {
  require.config({ paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs' } });
  require(['vs/editor/editor.main'], () => {
    const editor = monaco.editor.create(document.getElementById('editor'), {
      value: '',
      language: 'javascript',
      theme: 'vs-light',
      automaticLayout: true
    });

    const socket = io({
      auth: { token: localStorage.getItem('token') }
    });

    editor.onDidChangeModelContent((e) => {
      const content = editor.getValue();
      socket.emit('editor:change', { content });
    });

    socket.on('editor:update', ({ content }) => {
      const current = editor.getValue();
      if (current !== content) editor.setValue(content);
    });

    document.addEventListener('copy', (e) => {
      e.preventDefault();
      alert('Copy is disabled in this session.');
    });

    document.addEventListener('paste', (e) => {
      e.preventDefault();
      alert('Paste is disabled in this session.');
    });
  });
});