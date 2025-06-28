
let editor = CodeMirror(document.getElementById('replay-editor'), {
  lineNumbers: true,
  mode: 'python',
  theme: 'default',
  readOnly: true
});

let snapshots = [];
let currentIndex = 0;

function updateEditor() {
  if (snapshots.length === 0) return;
  const snap = snapshots[currentIndex];
  editor.setValue(snap.code);
  document.getElementById("replay-info").innerText = `Снапшот ${currentIndex + 1} из ${snapshots.length} (${snap.timestamp})`;
}

document.getElementById("prev-snapshot").onclick = () => {
  if (currentIndex > 0) {
    currentIndex--;
    updateEditor();
  }
};

document.getElementById("next-snapshot").onclick = () => {
  if (currentIndex < snapshots.length - 1) {
    currentIndex++;
    updateEditor();
  }
};

fetch(`/api/replay_snapshots/${window.sessionId}`)
  .then(r => r.json())
  .then(data => {
    snapshots = data;
    updateEditor();
  });
