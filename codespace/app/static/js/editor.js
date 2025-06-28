/**
 * CodeShare Editor v2.0
 * Complete implementation with all features
 */

class CodeShareEditor {
    constructor() {
        // Core Components
        this.editor = null;
        this.socket = null;
        
        // Session State
        this.session = {
            id: null,
            userId: null,
            username: null,
            role: 'viewer',
            isLocked: false,
            theme: 'light',
            files: {},
            currentFile: null,
            participants: {},
            permissions: {
                canEdit: false,
                canExecute: false,
                canManage: false
            }
        };

        // UI References
        this.uiElements = {
            // Editor
            editorContainer: null,
            currentFileName: null,
            languageSelect: null,
            
            // Controls
            runButton: null,
            lockButton: null,
            themeToggle: null,
            
            // Panels
            fileList: null,
            participantsList: null,
            outputPanel: null,
            chatMessages: null,
            chatInput: null,
            sendButton: null
        };

        // Utilities
        this.debounceTimers = {};
        this.cursorPositions = {};
    }

    // =====================
    // INITIALIZATION
    // =====================

    async init() {
        try {
            // 1. Load Monaco Editor
            await this.loadMonacoEditor();
            
            // 2. Initialize Socket.IO connection
            this.initSocketConnection();
            
            // 3. Setup UI components
            this.setupUI();
            
            // 4. Load session data
            this.loadSessionData();
            
            // 5. Setup event listeners
            this.setupEventListeners();
            
            console.log('[CodeShare] Editor initialized successfully');
        } catch (error) {
            console.error('[CodeShare] Initialization error:', error);
            this.showError('Failed to initialize editor. Please refresh the page.', 10000);
        }
    }

    async loadMonacoEditor() {
        return new Promise((resolve, reject) => {
            // Check if Monaco is already loaded
            if (window.monaco && window.monaco.editor) {
                this.createEditor();
                resolve();
                return;
            }

            // Load Monaco loader script
            const loaderScript = document.createElement('script');
            loaderScript.src = 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.40.0/min/vs/loader.min.js';
            loaderScript.onload = () => {
                // Configure Monaco loader
                require.config(window.monacoLoaderConfig);
                
                // Load main editor module
                require(['vs/editor/editor.main'], () => {
                    this.createEditor();
                    resolve();
                }, (error) => {
                    reject(new Error(`Monaco editor failed to load: ${error.message}`));
                });
            };
            
            loaderScript.onerror = () => {
                reject(new Error('Failed to load Monaco editor script'));
            };
            
            document.head.appendChild(loaderScript);
        });
    }

    createEditor() {
        const container = document.getElementById('editor-container');
        if (!container) {
            throw new Error('Editor container not found');
        }

        this.editor = monaco.editor.create(container, {
            value: container.dataset.initialContent || '\n// Welcome to CodeShare!\n// Start coding here...\n',
            language: container.dataset.initialLanguage || 'plaintext',
            theme: this.session.theme === 'dark' ? 'vs-dark' : 'vs',
            automaticLayout: true,
            minimap: { enabled: true },
            fontSize: 14,
            lineNumbers: 'on',
            roundedSelection: true,
            scrollBeyondLastLine: true,
            readOnly: !this.session.permissions.canEdit,
            quickSuggestions: true,
            suggestOnTriggerCharacters: true,
            tabSize: 2,
            wordWrap: 'on'
        });

        // Setup editor events
        this.editor.onDidChangeModelContent(this.handleEditorChange.bind(this));
        this.editor.onDidChangeCursorPosition(this.handleCursorPositionChange.bind(this));
        this.editor.onDidBlurEditorText(this.handleEditorBlur.bind(this));
    }

    // =====================
    // SOCKET.IO INTEGRATION
    // =====================

    initSocketConnection() {
        // Get session ID from container
        const container = document.getElementById('editor-container');
        const sessionId = container?.dataset.sessionId;
        
        if (!sessionId) {
            throw new Error('Session ID not found');
        }

        this.socket = io({
            reconnectionAttempts: 5,
            reconnectionDelay: 1000,
            transports: ['websocket'],
            query: {
                sessionId: sessionId,
                userId: this.session.userId,
                username: this.session.username
            }
        });

        // Connection events
        this.socket.on('connect', () => {
            console.log('[Socket.IO] Connected to server');
            this.updateConnectionStatus(true);
        });

        this.socket.on('disconnect', (reason) => {
            console.log('[Socket.IO] Disconnected:', reason);
            this.updateConnectionStatus(false);
        });

        this.socket.on('reconnect_failed', () => {
            this.showError('Connection lost. Please refresh the page.', 0);
        });

        // Application events
        this.setupSocketEventHandlers();
    }

    setupSocketEventHandlers() {
        const handlers = {
            // Session events
            'session_data': (data) => {
                this.session = { ...this.session, ...data };
                this.updatePermissions();
                this.updateUI();
            },
            
            // File events
            'file_content': (data) => {
                if (this.session.currentFile?.id === data.fileId) {
                    this.loadFileContent(data.content, data.language);
                }
            },
            
            // Code collaboration
            'code_update': (data) => {
                if (data.userId !== this.session.userId && 
                    this.session.currentFile?.id === data.fileId) {
                    this.applyRemoteUpdate(data.content);
                }
            },
            
            // Participant events
            'participant_joined': (participant) => {
                this.session.participants[participant.id] = participant;
                this.updateParticipantsList();
            },
            
            'participant_left': (userId) => {
                delete this.session.participants[userId];
                this.updateParticipantsList();
                this.removeCursorMarker(userId);
            },
            
            // Cursor position
            'cursor_position': (data) => {
                if (data.userId !== this.session.userId && 
                    data.fileId === this.session.currentFile?.id) {
                    this.updateRemoteCursor(data.userId, data.position);
                }
            },
            
            // Execution results
            'execution_result': (result) => {
                this.showExecutionResult(result);
            },
            
            // Chat messages
            'chat_message': (message) => {
                this.addChatMessage(message);
            },
            
            // Error handling
            'error': (error) => {
                this.showError(error.message);
            }
        };

        // Register all handlers
        Object.entries(handlers).forEach(([event, handler]) => {
            this.socket.on(event, handler);
        });
    }

    // =====================
    // FILE MANAGEMENT
    // =====================

    loadFile(fileId) {
        if (!fileId || !this.session.files[fileId]) return;

        // Save current file content before switching
        if (this.session.currentFile) {
            this.saveCurrentFile();
        }

        // Update current file reference
        this.session.currentFile = this.session.files[fileId];
        
        // Request file content from server
        this.socket.emit('request_file', { fileId });
        
        // Update UI
        this.updateFileSelection();
        this.updateCurrentFileDisplay();
    }

    saveCurrentFile() {
        if (!this.session.currentFile || !this.editor) return;
        
        const content = this.editor.getValue();
        this.socket.emit('save_file', {
            fileId: this.session.currentFile.id,
            content: content
        });
    }

    createNewFile(name, language) {
        return new Promise((resolve, reject) => {
            this.socket.emit('create_file', { name, language }, (response) => {
                if (response.success) {
                    this.session.files[response.file.id] = response.file;
                    this.updateFileList();
                    resolve(response.file);
                } else {
                    reject(new Error(response.error));
                }
            });
        });
    }

    // =====================
    // UI MANAGEMENT
    // =====================

    setupUI() {
        // Cache UI elements
        this.uiElements = {
            editorContainer: document.getElementById('editor-container'),
            currentFileName: document.getElementById('current-file-name'),
            languageSelect: document.getElementById('language-select'),
            runButton: document.getElementById('run-code-btn'),
            lockButton: document.getElementById('toggle-lock-btn'),
            themeToggle: document.getElementById('theme-toggle'),
            fileList: document.getElementById('file-list'),
            participantsList: document.getElementById('participants-list'),
            outputPanel: document.getElementById('output-panel'),
            chatMessages: document.getElementById('chat-messages'),
            chatInput: document.getElementById('chat-input'),
            sendButton: document.getElementById('send-message-btn')
        };

        // Initialize UI state
        this.updateUI();
    }

    updateUI() {
        this.updatePermissions();
        this.updateEditorState();
        this.updateFileList();
        this.updateParticipantsList();
        this.updateCurrentFileDisplay();
        this.updateTheme();
    }

    updatePermissions() {
        this.session.permissions = {
            canEdit: ['owner', 'editor'].includes(this.session.role) && !this.session.isLocked,
            canExecute: ['owner', 'editor'].includes(this.session.role),
            canManage: this.session.role === 'owner'
        };
    }

    // ... (другие методы реализации)

    // =====================
    // UTILITIES
    // =====================

    showError(message, duration = 5000) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger position-fixed top-0 end-0 m-3';
        errorDiv.style.zIndex = '9999';
        errorDiv.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas fa-exclamation-circle me-2"></i>
                <div>${message}</div>
            </div>
        `;
        
        document.body.appendChild(errorDiv);
        
        if (duration > 0) {
            setTimeout(() => {
                errorDiv.classList.add('fade');
                setTimeout(() => errorDiv.remove(), 300);
            }, duration);
        }
    }

    debounce(func, delay, key = 'default') {
        clearTimeout(this.debounceTimers[key]);
        this.debounceTimers[key] = setTimeout(func, delay);
    }
}

// Initialize editor when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Create editor instance
    const editor = new CodeShareEditor();
    
    // Make available globally for debugging
    window.codeShareEditor = editor;
    
    // Initialize
    editor.init();
});