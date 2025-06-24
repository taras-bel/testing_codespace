document.addEventListener('DOMContentLoaded', () => {
    // --- Инициализация ---
    const socket = io();
    const state = {
        isUpdateFromSocket: false,
        remoteCursors: {},
    };

    // --- Настройка редактора CodeMirror ---
    CodeMirror.modeURL = "https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.15/mode/%N/%N.min.js";
    const editor = CodeMirror(document.getElementById('editor'), {
        value: INITIAL_CODE,
        lineNumbers: true,
        theme: 'dracula',
        tabSize: 4,
        indentUnit: 4,
        mode: getMode(INITIAL_LANGUAGE),
    });
    setLanguage(INITIAL_LANGUAGE);

    function getMode(lang) {
        const info = CodeMirror.findModeByName(lang);
        return info ? info.mode : 'text/plain';
    }

    function setLanguage(lang) {
        const mode = getMode(lang);
        editor.setOption('mode', mode);
        CodeMirror.autoLoadMode(editor, mode);
    }
    
    // --- Настройка изменения размера панелей ---
    const dragBar = document.getElementById('drag-bar');
    const editorPane = document.getElementById('editor-pane');
    const bottomPane = document.getElementById('bottom-pane');

    let isDragging = false;
    dragBar.addEventListener('mousedown', e => {
        e.preventDefault();
        isDragging = true;
    });
    document.addEventListener('mousemove', e => {
        if (!isDragging) return;
        const newEditorHeight = e.clientY - editorPane.offsetTop;
        const totalHeight = editorPane.parentElement.clientHeight;
        const newEditorHeightPercent = (newEditorHeight / totalHeight) * 100;

        if (newEditorHeightPercent > 20 && newEditorHeightPercent < 80) {
            editorPane.style.height = `${newEditorHeightPercent}%`;
            bottomPane.style.height = `${100 - newEditorHeightPercent}%`;
        }
    });
    document.addEventListener('mouseup', () => isDragging = false);


    // --- Элементы UI ---
    const runBtn = document.getElementById('run-code-btn');
    const langSelect = document.getElementById('languageSelect');
    const outputContent = document.getElementById('output-content');
    const userCountEl = document.getElementById('user-count');
    const userListEl = document.getElementById('user-list');
    const chatMessagesEl = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input');
    const sendChatBtn = document.getElementById('send-chat-btn');
    const copySessionIdBtn = document.getElementById('copySessionId');

    // --- Обработчики событий UI ---
    runBtn.addEventListener('click', () => {
        outputContent.textContent = 'Выполнение...';
        socket.emit('execute_code', { session_id: SESSION_ID });
    });

    langSelect.addEventListener('change', (e) => {
        const newLang = e.target.value;
        setLanguage(newLang);
        socket.emit('language_change', { session_id: SESSION_ID, language: newLang });
    });

    copySessionIdBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(SESSION_ID).then(() => {
            showToast('ID сессии скопирован!', 'success');
        });
    });
    
    // --- Логика чата ---
    const sendChatMessage = () => {
        const message = chatInput.value.trim();
        if (message) {
            socket.emit('chat_message', { session_id: SESSION_ID, message });
            chatInput.value = '';
        }
    };
    sendChatBtn.addEventListener('click', sendChatMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendChatMessage();
    });

    function addChatMessage(user, message) {
        const msgEl = document.createElement('div');
        msgEl.innerHTML = `<strong>${escapeHtml(user)}:</strong> ${escapeHtml(message)}`;
        chatMessagesEl.appendChild(msgEl);
        chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
    }
    
    function addSystemMessage(message) {
        const msgEl = document.createElement('div');
        msgEl.className = 'text-muted fst-italic small';
        msgEl.textContent = message;
        chatMessagesEl.appendChild(msgEl);
        chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
    }


    // --- Обработчики событий Socket.IO ---
    socket.on('connect', () => {
        console.log('Connected to server!');
        socket.emit('join', { session_id: SESSION_ID });
    });
    
    socket.on('initial_state', (data) => {
        state.isUpdateFromSocket = true;
        editor.setValue(data.code);
        langSelect.value = data.language;
        setLanguage(data.language);
        outputContent.textContent = data.output;
        state.isUpdateFromSocket = false;
    });

    socket.on('code_update', (data) => {
        state.isUpdateFromSocket = true;
        const cursorPos = editor.getCursor();
        editor.setValue(data.code);
        editor.setCursor(cursorPos);
        state.isUpdateFromSocket = false;
    });

    socket.on('language_update', (data) => {
        langSelect.value = data.language;
        setLanguage(data.language);
    });

    socket.on('execution_result', (data) => {
        outputContent.textContent = data.output;
    });
    
    socket.on('update_participants', (data) => {
        userCountEl.textContent = data.users.length;
        userListEl.innerHTML = '';
        data.users.forEach(user => {
            const li = document.createElement('li');
            li.className = 'list-group-item';
            li.textContent = user;
            userListEl.appendChild(li);
        });
    });

    socket.on('user_activity', (data) => {
        addSystemMessage(data.message);
        showToast(data.message, 'info');
    });
    
    socket.on('new_message', (data) => {
        addChatMessage(data.user, data.message);
    });
    
    // --- Логика многопользовательских курсоров ---
    editor.on('change', () => {
        if (!state.isUpdateFromSocket) {
            socket.emit('code_change', { session_id: SESSION_ID, code: editor.getValue() });
        }
    });

    editor.on('cursorActivity', () => {
        socket.emit('cursor_move', { session_id: SESSION_ID, position: editor.getCursor() });
    });

    socket.on('cursor_update', (data) => {
        const { user, position, sid } = data;

        if (state.remoteCursors[sid]) {
            state.remoteCursors[sid].clear();
        }

        const cursorCoords = editor.cursorCoords(position, 'local');
        const cursorEl = document.createElement('div');
        cursorEl.className = 'remote-cursor';
        cursorEl.style.backgroundColor = getUserColor(user);
        
        const labelEl = document.createElement('div');
        labelEl.className = 'remote-cursor-label';
        labelEl.textContent = user;
        labelEl.style.backgroundColor = getUserColor(user);
        cursorEl.appendChild(labelEl);
        
        state.remoteCursors[sid] = editor.addWidget(position, cursorEl, false);
    });
    
    function getUserColor(username) {
        let hash = 0;
        for (let i = 0; i < username.length; i++) {
            hash = username.charCodeAt(i) + ((hash << 5) - hash);
        }
        let color = '#';
        for (let i = 0; i < 3; i++) {
            const value = (hash >> (i * 8)) & 0xFF;
            color += ('00' + value.toString(16)).substr(-2);
        }
        return color;
    }

    // --- Вспомогательные функции ---
    function showToast(message, type = 'info', delay = 3000) {
        const toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) return;
        
        const toastEl = document.createElement('div');
        toastEl.className = `toast align-items-center text-bg-${type} border-0`;
        toastEl.setAttribute('role', 'alert');
        toastEl.setAttribute('aria-live', 'assertive');
        toastEl.setAttribute('aria-atomic', 'true');
        
        toastEl.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        toastContainer.appendChild(toastEl);
        const toast = new bootstrap.Toast(toastEl, { delay });
        toast.show();
    }
    
    function escapeHtml(unsafe) {
        return unsafe
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
    }
});
