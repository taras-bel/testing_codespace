import os
import json
import uuid
import fnmatch
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_sock import Sock
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY') or 'dev-secret-key'
sock = Sock(app)

# --- FakeRedis Implementation ---
class FakeRedis:
    def __init__(self):
        self.data = {}
        self.expirations = {}

    def hset(self, name, key=None, value=None, mapping=None):
        if name not in self.data:
            self.data[name] = {}
        if mapping:
            self.data[name].update(mapping)
        elif key is not None and value is not None:
            self.data[name][key] = value

    def hget(self, name, key):
        return self.data.get(name, {}).get(key)

    def hgetall(self, name):
        return self.data.get(name, {}).copy()

    def hexists(self, name, key):
        return key in self.data.get(name, {})

    def hmset(self, name, mapping):
        if name not in self.data:
            self.data[name] = {}
        self.data[name].update(mapping)

    def set(self, name, value):
        self.data[name] = value

    def get(self, name):
        return self.data.get(name)

    def keys(self, pattern):
        return [k for k in self.data.keys() if fnmatch.fnmatch(k, pattern)]

    def expire(self, name, time):
        self.expirations[name] = datetime.now().timestamp() + time

    def delete(self, *names):
        for name in names:
            if name in self.data:
                del self.data[name]
            if name in self.expirations:
                del self.expirations[name]

    def __contains__(self, name):
        return name in self.data

redis_client = FakeRedis()

# --- Flask-Login Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

    @staticmethod
    def get(user_id):
        user_data = redis_client.hgetall(f'user:{user_id}')
        if not user_data:
            return None
        return User(
            id=user_id,
            username=user_data['username'],
            password_hash=user_data['password_hash']
        )

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# --- Session Management Helpers ---
def get_session(session_id):
    session_data = redis_client.hgetall(f'session:{session_id}')
    if not session_data:
        return None
    session_data['participants'] = json.loads(session_data['participants'])
    session_data['history'] = json.loads(session_data.get('history', '[]'))
    return session_data

def update_session(session_id, updates):
    redis_client.hmset(f'session:{session_id}', updates)

def create_session(owner_id):
    session_id = str(uuid.uuid4())
    redis_client.hmset(f'session:{session_id}', {
        'owner_id': owner_id,
        'code': '',
        'language': 'python',
        'created_at': datetime.now().isoformat(),
        'participants': json.dumps({owner_id: {
            'name': redis_client.hget(f'user:{owner_id}', 'username'),
            'color': f'#{hash(owner_id) % 0xFFFFFF:06x}'
        }}),
        'max_participants': 100, # Increased max participants
        'history': json.dumps([])
    })
    redis_client.set(f'user_sessions:{owner_id}:{session_id}', 'owner')
    return session_id

# --- Routes ---
@app.route('/')
@login_required
def index():
    user_sessions = redis_client.keys(f'user_sessions:{current_user.id}:*')
    session_id = None
    if not user_sessions:
        # If no active session, create one
        session_id = create_session(current_user.id)
        flash('New session created for you!', 'info')
    else:
        # Attempt to rejoin an existing session
        # For simplicity, just pick the first one found.
        # In a real app, you might list them or allow user to choose.
        session_key = user_sessions[0]
        session_id = session_key.split(':')[-1]
        flash('Rejoining your active session!', 'info')
        
    return redirect(url_for('join_session', session_id=session_id))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if redis_client.hexists('user_index', username):
            flash('Имя пользователя уже существует. Пожалуйста, выберите другое.', 'danger')
            return redirect(url_for('register'))
            
        user_id = str(uuid.uuid4())
        password_hash = generate_password_hash(password)
        
        redis_client.hmset(f'user:{user_id}', {
            'username': username,
            'password_hash': password_hash,
            'created_at': datetime.now().isoformat()
        })
        
        redis_client.hset('user_index', username, user_id)
        
        user = User(user_id, username, password_hash)
        login_user(user)
        flash('Регистрация прошла успешно!', 'success')
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user_id = redis_client.hget('user_index', username)
        if not user_id:
            flash('Неверное имя пользователя.', 'danger')
            return redirect(url_for('login'))
            
        user = User.get(user_id)
        if not user or not check_password_hash(user.password_hash, password):
            flash('Неверный пароль.', 'danger')
            return redirect(url_for('login'))
            
        login_user(user)
        flash('Вход выполнен успешно!', 'success')
        return redirect(url_for('index'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('login'))

@app.route('/session/<session_id>')
@login_required
def join_session(session_id):
    session = get_session(session_id)
    if not session:
        flash("Сессия не найдена.", 'danger')
        return redirect(url_for('index'))
        
    user_id_str = str(current_user.id)
    
    if user_id_str not in session['participants']:
        # Check if session is full, though with 100 participants it's less likely.
        if len(session['participants']) >= session['max_participants']:
            flash("Сессия заполнена. Невозможно присоединиться.", 'warning')
            return redirect(url_for('index'))
            
        participants = session['participants']
        participants[user_id_str] = {
            'name': current_user.username,
            'color': f'#{hash(user_id_str) % 0xFFFFFF:06x}'
        }
        update_session(session_id, {
            'participants': json.dumps(participants)
        })
        redis_client.set(f'user_sessions:{current_user.id}:{session_id}', 'guest')
        
        # Broadcast that a new participant joined
        broadcast(session_id, {
            'type': 'participant_joined',
            'userId': user_id_str,
            'participant': participants[user_id_str]
        })
    
    return render_template('index.html', session_id=session_id)

# --- WebSocket Handling ---
active_connections = {}

@sock.route('/ws/<session_id>')
@login_required
def websocket(ws, session_id):
    user_id_str = str(current_user.id)
    
    session = get_session(session_id)
    if not session or user_id_str not in session['participants']:
        ws.close()
        return

    # Generate a unique ID for this specific websocket connection
    connection_id = str(uuid.uuid4())
    active_connections[connection_id] = {
        'ws': ws,
        'session_id': session_id,
        'user_id': user_id_str
    }
    
    try:
        # Send initial state to the new client
        ws.send(json.dumps({
            'type': 'init',
            'code': session.get('code', ''),
            'language': session.get('language', 'python'),
            'participants': session['participants'],
            'userId': user_id_str,
            'isOwner': user_id_str == session['owner_id'],
            'history': session['history']
        }))
        
        # Keep connection open and listen for messages
        while True:
            message = ws.receive()
            if message is None: # Client disconnected
                break
                
            try:
                data = json.loads(message)
                handle_ws_message(session_id, data, connection_id)
            except json.JSONDecodeError:
                print(f"Invalid JSON received: {message}")
            except Exception as e:
                print(f"Error handling WS message: {e}")
                
    finally:
        # Cleanup: Remove connection and update participant list
        if connection_id in active_connections:
            del active_connections[connection_id]
        
        # Check if the user has any other active connections to this session
        user_still_connected = False
        for conn in active_connections.values():
            if conn['session_id'] == session_id and conn['user_id'] == user_id_str:
                user_still_connected = True
                break
        
        if not user_still_connected:
            session = get_session(session_id)
            if session and user_id_str in session['participants']:
                participants = session['participants']
                del participants[user_id_str]
                update_session(session_id, {
                    'participants': json.dumps(participants)
                })
                redis_client.delete(f'user_sessions:{user_id_str}:{session_id}') # Clean up user's session entry
                broadcast(session_id, {
                    'type': 'participant_left',
                    'userId': user_id_str
                })

def handle_ws_message(session_id, data, connection_id):
    session = get_session(session_id)
    if not session:
        return
    
    user_id_str = active_connections[connection_id]['user_id']
        
    if data['type'] == 'code_change':
        # Limit history to 50 entries
        history = session['history']
        history.append({
            'timestamp': datetime.now().isoformat(),
            'userId': user_id_str,
            'code': data['code']
        })
        history = history[-50:] # Keep only the last 50 entries
            
        update_session(session_id, {
            'code': data['code'],
            'history': json.dumps(history)
        })
        broadcast(session_id, {
            'type': 'code_update',
            'code': data['code'],
            'userId': user_id_str
        }, exclude_user_connection_id=connection_id) # Exclude the sender
        
    elif data['type'] == 'language_change':
        if user_id_str != session['owner_id']: # Only owner can change language (optional)
            # You might want to flash an error or ignore if not owner
            print(f"User {user_id_str} tried to change language but is not owner.")
            return

        update_session(session_id, {
            'language': data['language']
        })
        broadcast(session_id, {
            'type': 'language_update',
            'language': data['language'],
            'userId': user_id_str
        })
        
    elif data['type'] == 'cursor_update':
        broadcast(session_id, {
            'type': 'cursor_update',
            'userId': user_id_str,
            'position': data['position']
        }, exclude_user_connection_id=connection_id) # Exclude the sender
        
    elif data['type'] == 'history_request':
        session = get_session(session_id)
        if session:
            # Send history only to the requesting connection
            active_connections[connection_id]['ws'].send(json.dumps({
                'type': 'history_response',
                'history': session['history']
            }))

def broadcast(session_id, message, exclude_user_connection_id=None):
    for conn_id, conn in list(active_connections.items()):
        if conn['session_id'] == session_id:
            if exclude_user_connection_id and conn_id == exclude_user_connection_id:
                continue
            try:
                conn['ws'].send(json.dumps(message))
            except Exception as e:
                print(f"Error broadcasting to connection {conn_id}: {e}. Removing connection.")
                del active_connections[conn_id]

# --- Code Execution Route ---
# The execution module imports remain the same. Ensure you have the `execution` directory
# with `python_exec.py`, `cpp_exec.py`, etc.
@app.route('/execute', methods=['POST'])
@login_required
def execute():
    data = request.get_json()
    language = data['language']
    code = data['code']
    session_id = data.get('sessionId')
    
    session = get_session(session_id)
    if not session or str(current_user.id) not in session['participants']:
        return jsonify({'error': 'Доступ запрещен'}), 403
    
    try:
        result = {'output': '', 'error': ''}
        if language == 'python':
            from execution.python_exec import execute_python
            result = execute_python(code)
        elif language == 'cpp':
            from execution.cpp_exec import execute_cpp
            result = execute_cpp(code)
        elif language == 'csharp':
            from execution.csharp_exec import execute_csharp
            result = execute_csharp(code)
        elif language == 'java':
            from execution.java_exec import execute_java
            result = execute_java(code)
        elif language == 'javascript':
            from execution.javascript_exec import execute_javascript
            result = execute_javascript(code)
        else:
            return jsonify({'error': 'Неподдерживаемый язык'}), 400
        
        history = session['history']
        history.append({
            'timestamp': datetime.now().isoformat(),
            'userId': str(current_user.id),
            'action': 'execution',
            'language': language,
            'output': result.get('output', ''),
            'error': result.get('error', '')
        })
        update_session(session_id, {
            'history': json.dumps(history[-50:])
        })
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/error')
def error():
    error_msg = request.args.get('msg', 'Произошла ошибка')
    return render_template('error.html', error=error_msg)

if __name__ == '__main__':
    app.run(debug=True)

