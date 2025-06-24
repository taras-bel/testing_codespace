import os
import secrets
import json
import threading
from datetime import datetime, timedelta

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

# Импортируем модули для выполнения кода
from execution.python_exec import execute_python
from execution.cpp_exec import execute_cpp
from execution.csharp_exec import execute_csharp
from execution.java_exec import execute_java
from execution.javascript_exec import execute_javascript
from execution.go_exec import execute_go
from execution.ruby_exec import execute_ruby
from execution.rust_exec import execute_rust
from execution.php_exec import execute_php
from execution.swift_exec import execute_swift
from execution.kotlin_exec import execute_kotlin
from execution.scala_exec import execute_scala
from execution.haskell_exec import execute_haskell
from execution.perl_exec import execute_perl
from execution.r_exec import execute_r
from execution.bash_exec import execute_bash
from execution.typescript_exec import execute_typescript
from execution.lua_exec import execute_lua
from execution.dart_exec import execute_dart
from execution.julia_exec import execute_julia

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16) # Устанавливаем секретный ключ
app.config['SESSION_COOKIE_SECURE'] = True # Рекомендуется для HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30) # Для flask_login

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', logger=True, engineio_logger=True) # Разрешаем CORS для всех источников во время разработки

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Имитация базы данных пользователей
users = {
    "user1": {"password": "password1", "id": "1"},
    "user2": {"password": "password2", "id": "2"},
}

class User(UserMixin):
    def __init__(self, id):
        self.id = id

    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    return User(user_id) if user_id in users else None

# In-memory хранилище сессий. В продакшене использовать Redis, базу данных и т.д.
# { session_id: { 'code': '...', 'language': '...', 'output': '...', 'is_locked': False, 'created_at': datetime.now(), 'last_active': datetime.now() } }
sessions = {}
session_lock = threading.Lock() # Для обеспечения атомарности операций с сессиями

# Список доступных языков и их исполнителей
AVAILABLE_LANGUAGES = {
    'python': {'name': 'Python', 'executor': execute_python},
    'cpp': {'name': 'C++', 'executor': execute_cpp},
    'csharp': {'name': 'C#', 'executor': execute_csharp},
    'java': {'name': 'Java', 'executor': execute_java},
    'javascript': {'name': 'JavaScript', 'executor': execute_javascript},
    'go': {'name': 'Go', 'executor': execute_go},
    'ruby': {'name': 'Ruby', 'executor': execute_ruby},
    'rust': {'name': 'Rust', 'executor': execute_rust},
    'php': {'name': 'PHP', 'executor': execute_php},
    'swift': {'name': 'Swift', 'executor': execute_swift},
    'kotlin': {'name': 'Kotlin', 'executor': execute_kotlin},
    'scala': {'name': 'Scala', 'executor': execute_scala},
    'haskell': {'name': 'Haskell', 'executor': execute_haskell},
    'perl': {'name': 'Perl', 'executor': execute_perl},
    'r': {'name': 'R', 'executor': execute_r},
    'bash': {'name': 'Bash', 'executor': execute_bash},
    'typescript': {'name': 'TypeScript', 'executor': execute_typescript},
    'lua': {'name': 'Lua', 'executor': execute_lua},
    'dart': {'name': 'Dart', 'executor': execute_dart},
    'julia': {'name': 'Julia', 'executor': execute_julia},
}

def get_session(session_id):
    with session_lock:
        session_data = sessions.get(session_id)
        if session_data:
            # Обновляем время последней активности
            session_data['last_active'] = datetime.now()
            # Убедимся, что 'is_locked' всегда булево
            current_is_locked = session_data.get('is_locked')
            if not isinstance(current_is_locked, bool):
                # Если это не булево, пытаемся преобразовать из строки или устанавливаем False
                session_data['is_locked'] = str(current_is_locked).lower() == 'true' if isinstance(current_is_locked, str) else False
            return session_data
        return None

def create_new_session(language='python'):
    new_session_id = secrets.token_hex(8)
    with session_lock:
        sessions[new_session_id] = {
            'code': '',
            'language': language,
            'output': '',
            'is_locked': False,
            'created_at': datetime.now(),
            'last_active': datetime.now()
        }
    return new_session_id

# --- Маршруты Flask ---

@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username]['password'] == password:
            user = User(users[username]['id'])
            login_user(user, remember=True) # Сохраняем пользователя в сессии
            return redirect(url_for('index'))
        return render_template('login.html', error='Неправильное имя пользователя или пароль')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/new_session', methods=['POST'])
@login_required
def new_session():
    language = request.form.get('language', 'python')
    if language not in AVAILABLE_LANGUAGES:
        language = 'python' # Дефолтный язык, если передан некорректный
    
    session_id = create_new_session(language)
    return redirect(url_for('code_editor', session_id=session_id))

@app.route('/session/<session_id>')
@login_required
def code_editor(session_id):
    s = get_session(session_id)
    if not s:
        return "Сессия не найдена", 404
    return render_template('editor.html', session_id=session_id, initial_code=s['code'], initial_language=s['language'], initial_output=s['output'], initial_lock_status=s['is_locked'], languages=AVAILABLE_LANGUAGES)

@app.route('/join_session', methods=['POST'])
@login_required
def join_session():
    session_id = request.form.get('session_id')
    session_data = get_session(session_id)
    if session_data:
        return redirect(url_for('code_editor', session_id=session_id))
    return render_template('index.html', error_message='Сессия с таким ID не найдена.')

@app.route('/toggle_lock/<session_id>', methods=['POST'])
@login_required
def toggle_lock_endpoint(session_id):
    s = get_session(session_id)
    if not s:
        return jsonify({'success': False, 'message': 'Сессия не найдена'}), 404
    
    with session_lock:
        s['is_locked'] = not s['is_locked']
        lock_status = s['is_locked']
    
    socketio.emit('lock_status_changed', {'is_locked': lock_status, 'session_id': session_id}, room=session_id)
    return jsonify({'success': True, 'is_locked': lock_status})


# --- SocketIO Обработчики ---

@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    print(f'Client disconnected: {request.sid}')
    # Логика очистки, если пользователь был единственным в комнате
    for session_id, s_data in sessions.items():
        # Это неидеальный способ отслеживать пользователей в комнате,
        # но для простоты мы можем проверять, пуста ли комната после дисконнекта
        pass

@socketio.on('join')
def on_join(data):
    session_id = data.get('session_id')
    if not session_id:
        emit('error', {'message': 'Session ID is missing.'})
        return

    s = get_session(session_id)
    if not s:
        emit('error', {'message': 'Session not found.'})
        return

    join_room(session_id)
    # Отправляем текущее состояние сессии новому клиенту
    emit('initial_code', {'code': s['code'], 'language': s['language'], 'output': s['output'], 'is_locked': s['is_locked']}, room=request.sid)
    print(f'{request.sid} joined room {session_id}')

@socketio.on('leave')
def on_leave(data):
    session_id = data.get('session_id')
    if session_id:
        leave_room(session_id)
        print(f'{request.sid} left room {session_id}')

@socketio.on('code_change')
def handle_code_change(data):
    session_id = data.get('session_id')
    new_code = data.get('code')
    
    if not session_id or new_code is None:
        return

    s = get_session(session_id)
    if not s:
        return # Сессия не найдена

    # Проверяем статус блокировки
    if s['is_locked'] and current_user.get_id() != s.get('owner_id'): # Предполагаем, что owner_id устанавливается при создании сессии
        # Если заблокировано, и это не владелец, не обновляем код
        # и отправляем текущий код обратно клиенту, который пытался изменить
        emit('code_update', {'code': s['code'], 'session_id': session_id}, room=request.sid)
        return

    # Обновляем код в хранилище
    with session_lock:
        s['code'] = new_code
    
    # Отправляем обновленный код всем клиентам в комнате, кроме отправителя
    # Это важно для предотвращения "ряби" и цикличных обновлений
    emit('code_update', {'code': new_code, 'session_id': session_id}, room=session_id, skip_sid=request.sid)


@socketio.on('language_change')
def handle_language_change(data):
    session_id = data.get('session_id')
    new_language = data.get('language')

    if not session_id or new_language not in AVAILABLE_LANGUAGES:
        return

    s = get_session(session_id)
    if not s:
        return

    # Проверяем статус блокировки
    if s['is_locked'] and current_user.get_id() != s.get('owner_id'):
        emit('language_update', {'language': s['language'], 'session_id': session_id}, room=request.sid)
        return

    with session_lock:
        s['language'] = new_language
    
    emit('language_update', {'language': new_language, 'session_id': session_id}, room=session_id)


@socketio.on('execute_code')
def handle_execute_code(data):
    session_id = data.get('session_id')
    
    s = get_session(session_id)
    if not s:
        emit('execution_result', {'output': 'Ошибка: Сессия не найдена.', 'session_id': session_id}, room=request.sid)
        return

    code_to_execute = s['code']
    language = s['language']

    executor_info = AVAILABLE_LANGUAGES.get(language)
    if not executor_info:
        emit('execution_result', {'output': f'Ошибка: Исполнитель для языка "{language}" не найден.', 'session_id': session_id}, room=request.sid)
        return

    executor_func = executor_info['executor']
    
    # Запускаем выполнение в отдельном потоке, чтобы не блокировать SocketIO
    def run_execution():
        print(f"Executing code for session {session_id} ({language})...")
        result = executor_func(code_to_execute)
        
        output = result.get('output', '')
        error = result.get('error', '')
        
        final_output = output + (f"\n\nОшибка:\n{error}" if error else "")

        with session_lock:
            s['output'] = final_output # Сохраняем результат выполнения в сессии

        # Отправляем результат всем клиентам в комнате
        socketio.emit('execution_result', {'output': final_output, 'session_id': session_id}, room=session_id)
        print(f"Execution finished for session {session_id}. Output length: {len(final_output)}")

    threading.Thread(target=run_execution).start()

# --- Логика очистки старых сессий ---
def cleanup_old_sessions():
    """Удаляет старые сессии, которые неактивны более 1 часа."""
    while True:
        current_time = datetime.now()
        sessions_to_delete = []
        with session_lock:
            for session_id, session_data in sessions.items():
                if current_time - session_data['last_active'] > timedelta(hours=1):
                    sessions_to_delete.append(session_id)
            
            for session_id in sessions_to_delete:
                del sessions[session_id]
                print(f"Сессия {session_id} удалена из-за неактивности.")
        
        # Проверяем каждые 30 минут
        threading.Event().wait(1800) 

# Запускаем поток для очистки сессий
cleanup_thread = threading.Thread(target=cleanup_old_sessions)
cleanup_thread.daemon = True # Поток завершится при завершении основного приложения
cleanup_thread.start()


if __name__ == '__main__':
    # В продакшене используйте gunicorn или другой WSGI-сервер
    # socketio.run(app, debug=True, host='0.0.0.0', port=5000)
    print("Starting Flask-SocketIO server...")
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True) # allow_unsafe_werkzeug=True для dev сервера на Flask 3+
