import json
import uuid
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sock import Sock

# --- Fake Redis (for demonstration purposes, replace with actual Redis in production) ---
class FakeRedis:
    def __init__(self):
        self.data = {} # Stores all key-value pairs

    def set(self, key, value):
        self.data[key] = value
        return True

    def get(self, key):
        return self.data.get(key)

    def hset(self, name, key, value):
        if name not in self.data:
            self.data[name] = {}
        self.data[name][key] = value
        return True

    def hmset(self, name, mapping):
        if name not in self.data:
            self.data[name] = {}
        self.data[name].update(mapping)
        return True

    def hget(self, name, key):
        return self.data.get(name, {}).get(key)

    def hgetall(self, name):
        # Decode bytes to string if necessary, assuming all values are strings
        return {k.decode('utf-8') if isinstance(k, bytes) else k: v.decode('utf-8') if isinstance(v, bytes) else v
                for k, v in self.data.get(name, {}).items()}

    def delete(self, *names):
        deleted_count = 0
        for name in names:
            if name in self.data:
                del self.data[name]
                deleted_count += 1
        return deleted_count

    def keys(self, pattern='*'):
        import re
        regex = re.compile(pattern.replace('*', '.*'))
        return [k for k in self.data.keys() if regex.fullmatch(k)]

    def exists(self, key):
        return key in self.data

redis_client = FakeRedis()
# --- End Fake Redis ---

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_super_secret_key_here' # Change this in production!
sock = Sock(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Add Jinja2 filter for datetime formatting
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d %H:%M'):
    if not value:
        return ""
    if isinstance(value, str):
        try:
            # Handle ISO format from datetime.now().isoformat()
            dt_object = datetime.fromisoformat(value)
        except ValueError:
            return value # Return original if not a valid isoformat
    else:
        dt_object = value
    return dt_object.strftime(format)

# --- User Management (Simplified for this example) ---
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = str(id) # Ensure ID is string
        self.username = username
        self.password = password

    @staticmethod
    def get(user_id):
        user_data = redis_client.hgetall(f'user:{user_id}')
        if user_data:
            return User(user_data['id'], user_data['username'], user_data['password'])
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# Pre-populate some users if they don't exist (for testing)
def create_test_users():
    if not redis_client.exists('user:1'):
        redis_client.hmset('user:1', {'id': '1', 'username': 'alice', 'password': 'password123'})
    if not redis_client.exists('user:2'):
        redis_client.hmset('user:2', {'id': '2', 'username': 'bob', 'password': 'password123'})

create_test_users()

# --- Session Management (Redis based) ---
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
        'max_participants': 100, # A reasonable default limit
        'history': json.dumps([]),
        'typing_stats': json.dumps({}), # To store typing stats per user
        'timer_end_time': None, # Timestamp when timer ends (ISO format string)
        'is_locked': False # Whether session is locked for editing
    })
    # Link user to session, marking them as owner
    redis_client.set(f'user_sessions:{owner_id}:{session_id}', 'owner')
    return session_id

def get_session(session_id):
    session_data = redis_client.hgetall(f'session:{session_id}')
    if not session_data:
        return None
    # Ensure nested JSON fields are parsed
    session_data['participants'] = json.loads(session_data['participants'])
    session_data['history'] = json.loads(session_data.get('history', '[]'))
    session_data['typing_stats'] = json.loads(session_data.get('typing_stats', '{}'))
    # Convert 'is_locked' from string 'true'/'false' to boolean
    session_data['is_locked'] = session_data.get('is_locked', 'false').lower() == 'true'
    
    return session_data

def update_session(session_id, updates):
    # Ensure nested JSON fields are stringified before storing
    if 'participants' in updates:
        updates['participants'] = json.dumps(updates['participants'])
    if 'history' in updates:
        updates['history'] = json.dumps(updates['history'])
    if 'typing_stats' in updates:
        updates['typing_stats'] = json.dumps(updates['typing_stats'])
    if 'is_locked' in updates:
        updates['is_locked'] = str(updates['is_locked']).lower() # Store boolean as string
        
    redis_client.hmset(f'session:{session_id}', updates)

def delete_session(session_id):
    session = get_session(session_id)
    if session:
        # Remove session-to-user links
        for user_id in session['participants'].keys():
            redis_client.delete(f'user_sessions:{user_id}:{session_id}')
        # Delete the session itself
        redis_client.delete(f'session:{session_id}')

# --- WebSocket Management ---
active_connections = {} # Stores {connection_id: {'ws': ws_object, 'session_id': 'xyz', 'user_id': 'abc'}}

def broadcast(session_id, message, exclude_connection_id=None):
    message_json = json.dumps(message)
    for conn_id, conn_data in list(active_connections.items()):
        if conn_data['session_id'] == session_id and conn_id != exclude_connection_id:
            try:
                conn_data['ws'].send(message_json)
            except Exception as e:
                print(f"Error sending message to {conn_id}: {e}")
                # Potentially remove broken connection here
                del active_connections[conn_id]

# --- Background task for checking timers (simplified) ---
# In a real application, use APScheduler, Celery, or a dedicated threading.Timer
# to periodically run this, not on every request/websocket message.
def check_and_lock_session(session_id):
    session = get_session(session_id)
    if not session:
        return

    # Only lock if there's an end time and it's not already locked
    if session['timer_end_time'] and not session['is_locked']:
        end_time = datetime.fromisoformat(session['timer_end_time'])
        if datetime.now() >= end_time:
            update_session(session_id, {'is_locked': True})
            broadcast(session_id, {
                'type': 'session_locked',
                'ownerId': session['owner_id']
            })
            print(f"Session {session_id} has been locked.")

# --- Routes ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # In a real app, hash and salt passwords
        # For this example, we just iterate through our fake users
        user_found = False
        for user_id_key in redis_client.keys('user:*'):
            user_data = redis_client.hgetall(user_id_key)
            if user_data.get('username') == username and user_data.get('password') == password:
                user = User(user_data['id'], user_data['username'], user_data['password'])
                login_user(user)
                user_found = True
                flash('Успешный вход!', 'success')
                return redirect(url_for('index'))
        
        if not user_found:
            flash('Неверное имя пользователя или пароль.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    user_sessions_keys = redis_client.keys(f'user_sessions:{current_user.id}:*')
    
    user_sessions = []
    for key in user_sessions_keys:
        session_id = key.split(':')[-1]
        session_data = get_session(session_id)
        if session_data:
            # Determine if current user is owner or guest for display
            is_owner = session_data['owner_id'] == str(current_user.id)
            owner_username = redis_client.hget(f'user:{session_data['owner_id']}', 'username')
            user_sessions.append({
                'id': session_id,
                'owner_name': owner_username if owner_username else 'Неизвестно',
                'is_owner': is_owner,
                'num_participants': len(session_data['participants']),
                'created_at': session_data['created_at']
            })
    
    # Sort sessions by creation date (most recent first)
    user_sessions.sort(key=lambda x: x['created_at'], reverse=True)

    return render_template('sessions.html', user_sessions=user_sessions)

@app.route('/create_new_session', methods=['POST'])
@login_required
def create_new_session_route():
    session_id = create_session(str(current_user.id))
    flash('Новая сессия успешно создана!', 'success')
    return redirect(url_for('join_session', session_id=session_id))

@app.route('/session/<session_id>')
@login_required
def join_session(session_id):
    session = get_session(session_id)
    if not session:
        flash("Сессия не найдена.", 'danger')
        return redirect(url_for('index'))
        
    user_id_str = str(current_user.id)
    session_owner_id = session['owner_id'] # Get owner ID
    
    # Add participant if not already in session
    if user_id_str not in session['participants']:
        if len(session['participants']) >= session['max_participants']:
            flash("Сессия заполнена. Невозможно присоединиться.", 'warning')
            return redirect(url_for('index'))
            
        participants = session['participants']
        participants[user_id_str] = {
            'name': current_user.username,
            'color': f'#{hash(user_id_str) % 0xFFFFFF:06x}' # Simple hash-based color
        }
        update_session(session_id, {
            'participants': participants
        })
        # Link user to session, marking them as guest
        redis_client.set(f'user_sessions:{current_user.id}:{session_id}', 'guest')
        
        # Notify others about new participant
        broadcast(session_id, {
            'type': 'participant_joined',
            'userId': user_id_str,
            'participant': participants[user_id_str]
        })
    
    return render_template('index.html', session_id=session_id, session_owner_id=session_owner_id)

@app.route('/session/<session_id>/leave', methods=['POST'])
@login_required
def leave_session(session_id):
    user_id_str = str(current_user.id)
    session = get_session(session_id)

    if not session:
        flash("Сессия не найдена.", 'danger')
        return redirect(url_for('index'))

    # Owner cannot "leave" this way (they close the session by deleting it or just disconnecting)
    if user_id_str == session['owner_id']:
        flash("Владелец сессии не может покинуть ее таким образом. Пожалуйста, закройте вкладку или создайте новую сессию.", 'warning')
        return redirect(url_for('join_session', session_id=session_id)) # Stay on the session page

    if user_id_str in session['participants']:
        # Remove from session participants
        participants = session['participants']
        del participants[user_id_str]
        update_session(session_id, {'participants': participants})

        # Remove user's session entry
        redis_client.delete(f'user_sessions:{user_id_str}:{session_id}')

        # Notify others via WebSocket
        broadcast(session_id, {
            'type': 'participant_left',
            'userId': user_id_str
        })
        flash("Вы покинули сессию.", 'info')
    else:
        flash("Вы не являетесь участником этой сессии.", 'warning')
        
    return redirect(url_for('index')) # Redirect to the sessions list


@app.route('/session/<session_id>/set_timer', methods=['POST'])
@login_required
def set_session_timer(session_id):
    session = get_session(session_id)
    if not session:
        return jsonify({'error': 'Сессия не найдена.'}), 404

    if str(current_user.id) != session['owner_id']:
        return jsonify({'error': 'Доступ запрещен. Только владелец сессии может устанавливать таймер.'}), 403

    duration_minutes = request.json.get('duration_minutes')
    if not isinstance(duration_minutes, int) or duration_minutes <= 0:
        return jsonify({'error': 'Неверная длительность таймера.'}), 400

    end_time = datetime.now() + timedelta(minutes=duration_minutes)
    
    update_session(session_id, {
        'timer_end_time': end_time.isoformat(),
        'is_locked': False # Ensure it's not locked if setting a new timer
    })
    
    broadcast(session_id, {
        'type': 'timer_set',
        'endTime': end_time.isoformat(),
        'ownerId': str(current_user.id)
    })
    
    return jsonify({'success': True, 'endTime': end_time.isoformat()})

@app.route('/execute', methods=['POST'])
@login_required
def execute():
    data = request.get_json()
    language = data['language']
    code = data['code']
    session_id = data.get('sessionId') # Get session ID from client

    session = get_session(session_id)
    if not session or str(current_user.id) not in session['participants']:
        return jsonify({'error': 'Доступ запрещен'}), 403

    # Check if session is locked and user is not owner
    if session['is_locked'] and str(current_user.id) != session['owner_id']:
        return jsonify({'error': 'Сессия заблокирована для редактирования и выполнения.'}), 403
    
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
        elif language == 'go':
            from execution.go_exec import execute_go
            result = execute_go(code)
        elif language == 'ruby':
            from execution.ruby_exec import execute_ruby
            result = execute_ruby(code)
        elif language == 'rust':
            from execution.rust_exec import execute_rust
            result = execute_rust(code)
        elif language == 'php':
            from execution.php_exec import execute_php
            result = execute_php(code)
        elif language == 'swift':
            from execution.swift_exec import execute_swift
            result = execute_swift(code)
        elif language == 'kotlin':
            from execution.kotlin_exec import execute_kotlin
            result = execute_kotlin(code)
        elif language == 'scala':
            from execution.scala_exec import execute_scala
            result = execute_scala(code)
        elif language == 'haskell':
            from execution.haskell_exec import execute_haskell
            result = execute_haskell(code)
        elif language == 'perl':
            from execution.perl_exec import execute_perl
            result = execute_perl(code)
        elif language == 'r':
            from execution.r_exec import execute_r
            result = execute_r(code)
        elif language == 'bash':
            from execution.bash_exec import execute_bash
            result = execute_bash(code)
        elif language == 'typescript':
            from execution.typescript_exec import execute_typescript
            result = execute_typescript(code)
        elif language == 'lua':
            from execution.lua_exec import execute_lua
            result = execute_lua(code)
        elif language == 'dart':
            from execution.dart_exec import execute_dart
            result = execute_dart(code)
        elif language == 'julia':
            from execution.julia_exec import execute_julia
            result = execute_julia(code)
        else:
            return jsonify({'error': 'Неподдерживаемый язык'}), 400
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f"Ошибка выполнения: {e}"}), 500

@sock.route('/ws/<session_id>')
@login_required
def websocket(ws, session_id):
    user_id_str = str(current_user.id)
    
    session = get_session(session_id)
    if not session or user_id_str not in session['participants']:
        ws.close()
        return

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
            'history': session['history'],
            'timer_end_time': session.get('timer_end_time'), # NEW
            'is_locked': session.get('is_locked'), # NEW
            'ownerId': session['owner_id'] # NEW: Pass owner ID
        }))

        while True:
            data = ws.receive()
            if data is None: # Connection closed
                break
            
            message = json.loads(data)
            
            # Periodically check and lock session if timer expired (simple approach)
            check_and_lock_session(session_id) 

            session = get_session(session_id) # Reload session to get latest lock status
            if not session: # Session might have been deleted by owner during connection
                break

            # If session is locked and the sender is not the owner, prevent changes
            if session['is_locked'] and user_id_str != session['owner_id']:
                # Optionally send a message back to the client: "Session is locked"
                ws.send(json.dumps({
                    'type': 'error',
                    'message': 'Сессия заблокирована для редактирования.'
                }))
                continue # Skip processing this message

            if message['type'] == 'code_change':
                new_code = message['code']
                cursor_pos = message.get('cursor', None)
                
                # Update code and add to history
                update_session(session_id, {'code': new_code})

                history = session['history']
                history.append({
                    'timestamp': datetime.now().isoformat(),
                    'userId': user_id_str,
                    'change': 'code_update' # Simplified change description
                })
                # Keep history size manageable (e.g., last 100 entries)
                if len(history) > 100:
                    history = history[-100:]
                update_session(session_id, {'history': history})

                # Broadcast code change and cursor to other participants
                broadcast(session_id, {
                    'type': 'code_update',
                    'code': new_code,
                    'userId': user_id_str,
                    'cursor': cursor_pos
                }, exclude_connection_id=connection_id)

            elif message['type'] == 'language_change':
                new_language = message['language']
                update_session(session_id, {'language': new_language})
                broadcast(session_id, {
                    'type': 'language_update',
                    'language': new_language,
                    'userId': user_id_str
                }, exclude_connection_id=connection_id)

            elif message['type'] == 'cursor_update':
                # Broadcast cursor position to other participants
                broadcast(session_id, {
                    'type': 'cursor_update',
                    'userId': user_id_str,
                    'cursor': message['cursor']
                }, exclude_connection_id=connection_id)

            elif message['type'] == 'history_request':
                # Client requested full history (e.g., on reconnect)
                ws.send(json.dumps({
                    'type': 'history_response',
                    'history': session['history']
                }))
            
            elif message['type'] == 'typing_data':
                # This data is *not* broadcasted to other clients for privacy/performance
                # Only stored server-side.
                typing_stats = session['typing_stats']
                user_stats = typing_stats.get(user_id_str, {'typing_speed': [], 'thinking_times': []})
                
                # Append new data
                if 'speed' in message:
                    user_stats['typing_speed'].append({
                        'timestamp': datetime.now().isoformat(),
                        'cpm': message['speed']
                    })
                if 'thinkingTime' in message:
                    user_stats['thinking_times'].append({
                        'timestamp': datetime.now().isoformat(),
                        'duration_ms': message['thinkingTime']
                    })
                
                typing_stats[user_id_str] = user_stats
                update_session(session_id, {
                    'typing_stats': typing_stats
                })

    except Exception as e:
        print(f"WebSocket error for user {user_id_str} in session {session_id}: {e}")
    finally:
        # Clean up connection
        if connection_id in active_connections:
            del active_connections[connection_id]
            # If the owner leaves and no one else is in session, delete the session
            # (Simplified logic, consider more robust session management)
            session = get_session(session_id)
            if session and user_id_str == session['owner_id'] and not session['participants']:
                 delete_session(session_id) # Only delete if owner leaves and no other participants
                 print(f"Session {session_id} deleted as owner left and no participants.")
            elif session and user_id_str in session['participants']:
                # If a regular participant leaves, notify others
                broadcast(session_id, {
                    'type': 'participant_left',
                    'userId': user_id_str
                })
            elif session and user_id_str == session['owner_id']: # Owner left, but participants remain (edge case for owner leaving not via leave_session)
                 # Reassign owner or mark as ownerless? For now, ownerless state handled by session['owner_id']
                 pass # For now, just keep session
            print(f"Connection {connection_id} closed.")


if __name__ == '__main__':
    # You might want to run with `flask run` or a production WSGI server like Gunicorn
    # For development, this is fine:
    app.run(debug=True, port=5000)

