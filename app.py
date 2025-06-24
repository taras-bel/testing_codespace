import os
import secrets
import json
import threading
from datetime import datetime, timedelta

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# Импортируем модули для выполнения кода (путь к ним не меняется)
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
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['SESSION_COOKIE_SECURE'] = False # True для HTTPS, False для HTTP (локальная разработка)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)

# Настройка SQLAlchemy
# SQLite база данных будет сохранена в файле site.db в корне проекта
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Отключаем отслеживание изменений, чтобы избежать предупреждений
db = SQLAlchemy(app)

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', logger=True, engineio_logger=True)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Перенаправляем на '/login', если не авторизован

# --- Модели Базы Данных ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    # Связь с сессиями, где пользователь является владельцем
    owned_sessions = db.relationship('CodeSession', backref='owner', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"User('{self.username}', ID: {self.id})"

class CodeSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id_str = db.Column(db.String(32), unique=True, nullable=False) # Уникальный публичный ID
    code = db.Column(db.Text, nullable=False, default='')
    language = db.Column(db.String(50), nullable=False, default='python')
    output = db.Column(db.Text, nullable=False, default='')
    is_locked = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # Может быть null, если анонимно

    def __repr__(self):
        return f"CodeSession('{self.session_id_str}', Lang: '{self.language}', Locked: {self.is_locked})"

# --- Инициализация Базы Данных ---
# Создаем таблицы, если их нет
with app.app_context():
    db.create_all()

# --- Flask-Login User Loader ---
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id)) # Используем db.session.get для получения пользователя по PK

# --- Вспомогательные функции для сессий ---
def get_session_from_db(session_id_str):
    """Получает сессию из базы данных по строковому ID."""
    s = db.session.execute(db.select(CodeSession).filter_by(session_id_str=session_id_str)).scalar_one_or_none()
    if s:
        s.last_active = datetime.utcnow()
        db.session.commit()
    return s

def create_new_session_in_db(language='python', owner_id=None):
    """Создает новую сессию в базе данных."""
    new_session_id_str = secrets.token_hex(8)
    new_session = CodeSession(
        session_id_str=new_session_id_str,
        language=language,
        owner_id=owner_id,
        created_at=datetime.utcnow(),
        last_active=datetime.utcnow()
    )
    db.session.add(new_session)
    db.session.commit()
    return new_session_id_str

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

# --- Маршруты Flask ---

@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    return render_template('index.html', languages=AVAILABLE_LANGUAGES)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Проверка на существующего пользователя
        existing_user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
        if existing_user:
            flash('Имя пользователя уже занято. Выберите другое.', 'danger')
            return render_template('register.html')
        
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Вы успешно зарегистрированы! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
        
        if user and user.check_password(password):
            login_user(user, remember=True)
            return redirect(url_for('index'))
        else:
            flash('Неправильное имя пользователя или пароль', 'danger')
        return render_template('login.html')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('login'))

@app.route('/new_session', methods=['POST'])
@login_required
def new_session():
    language = request.form.get('language', 'python')
    if language not in AVAILABLE_LANGUAGES:
        language = 'python' # Дефолтный язык, если передан некорректный
    
    owner_id = current_user.id if current_user.is_authenticated else None
    session_id_str = create_new_session_in_db(language, owner_id)
    
    # ИСПРАВЛЕНО: используем session_id_str=
    return redirect(url_for('code_editor', session_id_str=session_id_str))

@app.route('/session/<session_id_str>')
@login_required
def code_editor(session_id_str):
    s = get_session_from_db(session_id_str)
    if not s:
        flash("Сессия не найдена.", 'danger')
        return redirect(url_for('index'))
    
    # Передаем статус блокировки и является ли текущий пользователь владельцем
    is_owner = current_user.is_authenticated and s.owner_id == current_user.id
    
    return render_template('editor.html', 
                           session_id=session_id_str, # Здесь передаем как session_id для использования в JS
                           initial_code=s.code, 
                           initial_language=s.language, 
                           initial_output=s.output, 
                           initial_lock_status=s.is_locked, 
                           languages=AVAILABLE_LANGUAGES,
                           is_owner=is_owner)

@app.route('/join_session', methods=['POST'])
@login_required
def join_session():
    session_id_str = request.form.get('session_id')
    s = get_session_from_db(session_id_str)
    if s:
        # ИСПРАВЛЕНО: используем session_id_str=
        return redirect(url_for('code_editor', session_id_str=session_id_str))
    flash('Сессия с таким ID не найдена.', 'danger')
    return redirect(url_for('index'))

@app.route('/toggle_lock/<session_id_str>', methods=['POST'])
@login_required
def toggle_lock_endpoint(session_id_str):
    s = get_session_from_db(session_id_str)
    if not s:
        return jsonify({'success': False, 'message': 'Сессия не найдена'}), 404
    
    # Только владелец может переключать блокировку
    if current_user.is_authenticated and s.owner_id == current_user.id:
        s.is_locked = not s.is_locked
        db.session.commit()
        lock_status = s.is_locked
        
        socketio.emit('lock_status_changed', {'is_locked': lock_status, 'session_id': session_id_str}, room=session_id_str)
        return jsonify({'success': True, 'is_locked': lock_status})
    else:
        return jsonify({'success': False, 'message': 'У вас нет прав для изменения статуса блокировки.'}), 403


# --- SocketIO Обработчики ---

@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    print(f'Client disconnected: {request.sid}')

@socketio.on('join')
def on_join(data):
    session_id_str = data.get('session_id')
    if not session_id_str:
        emit('error', {'message': 'Session ID is missing.'})
        return

    s = get_session_from_db(session_id_str)
    if not s:
        emit('error', {'message': 'Session not found.'})
        return

    join_room(session_id_str)
    
    # Проверка владельца для правильного отображения кнопок блокировки на клиенте
    is_owner = current_user.is_authenticated and s.owner_id == current_user.id

    emit('initial_state', { # Изменено на initial_state для комплексного обновления
        'code': s.code, 
        'language': s.language, 
        'output': s.output, 
        'is_locked': s.is_locked,
        'is_owner': is_owner # Передаем информацию о владельце
    }, room=request.sid)
    print(f'{request.sid} joined room {session_id_str}')

@socketio.on('leave')
def on_leave(data):
    session_id_str = data.get('session_id')
    if session_id_str:
        leave_room(session_id_str)
        print(f'{request.sid} left room {session_id_str}')

@socketio.on('code_change')
def handle_code_change(data):
    session_id_str = data.get('session_id')
    new_code = data.get('code')
    
    if not session_id_str or new_code is None:
        return

    s = get_session_from_db(session_id_str)
    if not s:
        return

    # Проверяем статус блокировки. Только владелец может менять код, если заблокировано.
    if s.is_locked and (not current_user.is_authenticated or s.owner_id != current_user.id):
        # Если заблокировано, и это не владелец, не обновляем код
        # и отправляем текущий код обратно клиенту, который пытался изменить
        emit('code_update', {'code': s.code, 'session_id': session_id_str}, room=request.sid)
        return

    s.code = new_code
    s.last_active = datetime.utcnow()
    db.session.commit()
    
    emit('code_update', {'code': new_code, 'session_id': session_id_str}, room=session_id_str, skip_sid=request.sid)


@socketio.on('language_change')
def handle_language_change(data):
    session_id_str = data.get('session_id')
    new_language = data.get('language')

    if not session_id_str or new_language not in AVAILABLE_LANGUAGES:
        return

    s = get_session_from_db(session_id_str)
    if not s:
        return

    # Проверяем статус блокировки
    if s.is_locked and (not current_user.is_authenticated or s.owner_id != current_user.id):
        emit('language_update', {'language': s.language, 'session_id': session_id_str}, room=request.sid)
        return

    s.language = new_language
    s.last_active = datetime.utcnow()
    db.session.commit()
    
    emit('language_update', {'language': new_language, 'session_id': session_id_str}, room=session_id_str)


@socketio.on('execute_code')
def handle_execute_code(data):
    session_id_str = data.get('session_id')
    
    s = get_session_from_db(session_id_str)
    if not s:
        emit('execution_result', {'output': 'Ошибка: Сессия не найдена.', 'session_id': session_id_str}, room=request.sid)
        return

    code_to_execute = s.code
    language = s.language

    executor_info = AVAILABLE_LANGUAGES.get(language)
    if not executor_info:
        emit('execution_result', {'output': f'Ошибка: Исполнитель для языка "{language}" не найден.', 'session_id': session_id_str}, room=request.sid)
        return

    executor_func = executor_info['executor']
    
    def run_execution():
        print(f"Executing code for session {session_id_str} ({language})...")
        result = executor_func(code_to_execute)
        
        output = result.get('output', '')
        error = result.get('error', '')
        
        final_output = output + (f"\n\nОшибка:\n{error}" if error else "")

        # Важно: В новом потоке нужно получить свежую сессию из БД
        # или использовать app.app_context() для работы с db.session
        with app.app_context(): 
            s_in_thread = db.session.execute(db.select(CodeSession).filter_by(session_id_str=session_id_str)).scalar_one_or_none()
            if s_in_thread: # Убедимся, что сессия все еще существует
                s_in_thread.output = final_output
                s_in_thread.last_active = datetime.utcnow()
                db.session.commit() # Сохраняем изменения в базе данных
                
            socketio.emit('execution_result', {'output': final_output, 'session_id': session_id_str}, room=session_id_str)
            print(f"Execution finished for session {session_id_str}. Output length: {len(final_output)}")

    threading.Thread(target=run_execution).start()

# --- Логика очистки старых сессий ---
def cleanup_old_sessions():
    """Удаляет старые сессии из базы данных, которые неактивны более 1 часа."""
    with app.app_context(): # Необходимо для доступа к db.session
        while True:
            current_time = datetime.utcnow()
            # Удаляем сессии, которые неактивны более 1 часа
            old_sessions = db.session.execute(
                db.select(CodeSession).filter(CodeSession.last_active < current_time - timedelta(hours=1))
            ).scalars().all()
            
            for s in old_sessions:
                db.session.delete(s)
                print(f"Сессия {s.session_id_str} удалена из-за неактивности.")
            db.session.commit()
            
            threading.Event().wait(1800) # Проверяем каждые 30 минут

cleanup_thread = threading.Thread(target=cleanup_old_sessions)
cleanup_thread.daemon = True 
cleanup_thread.start()


if __name__ == '__main__':
    print("Starting Flask-SocketIO server...")
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)

