from flask import request
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room
from app import db
from app.models.models import CodeSession
from app.execution.runner import execute_code_in_docker, AVAILABLE_LANGUAGES

# Словарь для хранения информации об участниках комнат
rooms = {}

def register_socket_events(socketio):
    
    @socketio.on('join')
    def on_join(data):
        session_id = data.get('session_id')
        session = db.session.get(CodeSession, session_id)

        if not session or not current_user.is_authenticated:
            return

        join_room(session_id)
        
        # Добавляем пользователя в комнату
        if session_id not in rooms:
            rooms[session_id] = {}
        rooms[session_id][request.sid] = current_user.username

        # Отправляем новому пользователю текущее состояние
        emit('initial_state', {
            'code': session.code,
            'language': session.language,
            'output': session.output
        }, room=request.sid)
        
        # Уведомляем всех о новом участнике и отправляем обновленный список
        emit('update_participants', {'users': list(rooms[session_id].values())}, room=session_id)
        emit('user_activity', {'message': f'Пользователь {current_user.username} присоединился.'}, room=session_id)


    @socketio.on('disconnect')
    def on_disconnect():
        # Удаляем пользователя из всех комнат, в которых он был
        for session_id, participants in rooms.items():
            if request.sid in participants:
                username = participants.pop(request.sid)
                leave_room(session_id)
                # Уведомляем оставшихся и обновляем список
                emit('update_participants', {'users': list(participants.values())}, room=session_id)
                emit('user_activity', {'message': f'Пользователь {username} отключился.'}, room=session_id)
                break


    @socketio.on('code_change')
    def on_code_change(data):
        session_id = data.get('session_id')
        session = db.session.get(CodeSession, session_id)
        if session:
            session.code = data.get('code', '')
            db.session.commit()
            emit('code_update', {'code': session.code}, room=session_id, skip_sid=request.sid)

    @socketio.on('language_change')
    def on_language_change(data):
        session_id = data.get('session_id')
        new_language = data.get('language')
        session = db.session.get(CodeSession, session_id)
        if session and new_language in AVAILABLE_LANGUAGES:
            session.language = new_language
            db.session.commit()
            emit('language_update', {'language': new_language}, room=session_id)
            
    @socketio.on('cursor_move')
    def on_cursor_move(data):
        session_id = data.get('session_id')
        emit('cursor_update', {
            'user': current_user.username,
            'position': data.get('position'),
            'sid': request.sid
        }, room=session_id, skip_sid=request.sid)
        
    @socketio.on('chat_message')
    def on_chat_message(data):
        session_id = data.get('session_id')
        message = data.get('message', '')
        if message:
            emit('new_message', {
                'user': current_user.username,
                'message': message
            }, room=session_id)
            
    @socketio.on('execute_code')
    def on_execute_code(data):
        session_id = data.get('session_id')
        session = db.session.get(CodeSession, session_id)
        if not session:
            return

        def run_execution(app):
            with app.app_context():
                # Повторно получаем сессию в контексте потока
                s = db.session.get(CodeSession, session_id)
                result = execute_code_in_docker(s.language, s.code)
                output = result.get('output', '')
                error = result.get('error', '')
                final_output = output
                if error:
                    final_output += f"\n--- ОШИБКА ---\n{error}"

                s.output = final_output
                db.session.commit()
                socketio.emit('execution_result', {'output': final_output}, room=session_id)
        
        from flask import current_app
        # Передаем контекст приложения в поток
        app_context = current_app._get_current_object()
        socketio.start_background_task(run_execution, app_context)
