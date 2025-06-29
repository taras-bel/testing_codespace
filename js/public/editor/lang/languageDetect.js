const extensionMap = {
  '.js': 'javascript',
  '.ts': 'typescript',
  '.py': 'python',
  '.java': 'java',
  '.c': 'c',
  '.cpp': 'cpp',
  '.cs': 'csharp',
  '.go': 'go',
  '.rb': 'ruby',
  '.php': 'php',
  '.rs': 'rust',
  '.swift': 'swift',
  '.kt': 'kotlin',
  '.pl': 'perl',
  '.scala': 'scala',
  '.hs': 'haskell',
  '.sql': 'sql',
  '.sh': 'shell',
  '.dart': 'dart',
  '.json': 'json'
};

function detectLanguage(filename) {
  const ext = filename.slice(filename.lastIndexOf('.'));
  return extensionMap[ext] || 'plaintext';
}

module.exports = { detectLanguage };