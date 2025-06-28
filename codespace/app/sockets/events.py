from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
from flask import request, current_app
from app.extensions import socketio, db # Импортируем из extensions
from app.models.models import Session, File, CollaborationRole, User
from app.services.session_manager import SessionManager
import json
import difflib # Для создания патчей
from datetime import datetime # Добавлен импорт datetime

code_executor = None

def set_code_executor(executor_instance):
    global code_executor
    code_executor = executor_instance

# Хранилище для отслеживания последних известных состояний файлов
# Это нужно для создания патчей (deltas)
last_known_file_content = {} # {file_id: "content"}

# Хранилище для отслеживания подключенных пользователей в сессиях
# {session_id: {user_id: {username: ..., sid: ..., role: ..., current_file_id: ...}}}
session_users = {}

@socketio.on('connect')
def handle_connect():
    # Отладочная информация
    current_app.logger.info(f"Client connected: {request.sid}")
    if current_user.is_authenticated:
        current_app.logger.info(f"User {current_user.username} connected with SID {request.sid}")
    else:
        current_app.logger.warning(f"Unauthenticated client connected with SID {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    current_app.logger.info(f"Client disconnected: {request.sid}")
    disconnected_user_id = None
    disconnected_username = "Неизвестный пользователь"
    disconnected_session_id = None

    # Находим пользователя и сессию, из которой он отключился
    for s_id, users_in_session in session_users.items():
        for u_id, user_data in users_in_session.items():
            if user_data['sid'] == request.sid:
                disconnected_user_id = u_id
                disconnected_username = user_data['username']
                disconnected_session_id = s_id
                break
        if disconnected_session_id:
            break

    if disconnected_session_id and disconnected_user_id:
        with current_app.app_context():
            session_data = SessionManager.get_session(disconnected_session_id)
            if session_data:
                # Удаляем пользователя из списка активных пользователей сессии
                if disconnected_user_id in session_users[disconnected_session_id]:
                    del session_users[disconnected_session_id][disconnected_user_id]
                    current_app.logger.info(f"User {disconnected_username} (ID: {disconnected_user_id}) left session {disconnected_session_id}")

                    # Отправляем обновление списка участников всем в сессии
                    # Использование broadcast_participants_update для унификации
                    broadcast_participants_update(disconnected_session_id)

                    # Удаляем курсор пользователя
                    emit('cursor_update', {
                        'userId': disconnected_user_id,
                        'username': disconnected_username,
                        'position': None, # Отправляем None, чтобы удалить курсор
                        'fileId': None
                    }, room=disconnected_session_id)
                
                # Если в сессии никого не осталось, можно очистить ее из last_known_file_content и session_users
                if not session_users[disconnected_session_id]:
                    if disconnected_session_id in last_known_file_content:
                        del last_known_file_content[disconnected_session_id]
                        current_app.logger.info(f"Cleaned up last_known_file_content for empty session {disconnected_session_id}")
                    del session_users[disconnected_session_id]
    
    current_app.logger.info(f"Client disconnected, SID: {request.sid}")


@socketio.on('join')
def handle_join(data):
    session_id = data.get('sessionId')
    user_id = data.get('userId')
    username = data.get('username')
    
    if not current_user.is_authenticated or current_user.id != user_id:
        current_app.logger.warning(f"Attempted join by unauthenticated or mismatched user_id: {user_id} with SID {request.sid}")
        return # Отклоняем, если пользователь не аутентифицирован или ID не совпадает

    with current_app.app_context():
        session_data = SessionManager.get_session(session_id)
        if not session_data:
            current_app.logger.warning(f"Attempted join to non-existent session: {session_id}")
            emit('error', {'message': 'Сессия не найдена.'})
            return

        user_role = SessionManager.get_user_role_in_session(session_id, user_id)
        if not user_role and session_data.visibility == 'private':
            current_app.logger.warning(f"User {username} (ID: {user_id}) attempted to join private session {session_id} without permission.")
            emit('error', {'message': 'У вас нет доступа к этой приватной сессии.'})
            return
        
        if not user_role and session_data.visibility == 'public':
            # Если публичная сессия и пользователь не участник, добавляем как viewer
            SessionManager.add_collaborator(session_id, user_id, 'viewer')
            user_role = 'viewer'
            current_app.logger.info(f"User {username} (ID: {user_id}) auto-added as viewer to public session {session_id}.")


        join_room(session_id)
        current_app.logger.info(f"User {username} (ID: {user_id}) joined room: {session_id} with role: {user_role}")

        # Добавляем пользователя в список активных участников сессии
        if session_id not in session_users:
            session_users[session_id] = {}
        session_users[session_id][user_id] = {
            'username': username,
            'sid': request.sid,
            'role': user_role,
            'current_file_id': None # Пока не выбран файл
        }

        # Отправляем текущее состояние сессии и файла только что присоединившемуся пользователю
        main_file = db.session.query(File).filter_by(session_id=session_id, is_main=True).first()
        if not main_file:
            # Если основного файла нет, берем первый доступный
            main_file = db.session.query(File).filter_by(session_id=session_id).first()
        
        if main_file:
            last_known_file_content[main_file.id] = main_file.content # Убедимся, что контент в кэше
            emit('load_file_content', {
                'fileId': main_file.id,
                'content': main_file.content,
                'language': main_file.language,
                'fileName': main_file.name # Добавлен fileName
            }, room=request.sid) # Отправляем только присоединившемуся
            session_users[session_id][user_id]['current_file_id'] = main_file.id # Обновляем активный файл
            current_app.logger.info(f"User {username} loaded main file {main_file.name} (ID: {main_file.id}).")
        else:
            emit('load_file_content', {
                'fileId': None,
                'fileName': 'Новый файл', # Добавлен fileName
                'content': '// Сессия пуста. Добавьте файлы.',
                'language': 'plaintext'
            }, room=request.sid)
            current_app.logger.warning(f"No files found for session {session_id}.")


        # Отправляем роль и статус блокировки редактору
        emit('session_config', {
            'current_user_role': user_role,
            'editing_locked': session_data.editing_locked,
            'session_id': session_id,
            'owner_id': session_data.owner_id
        }, room=request.sid)

        # Отправляем обновленный список участников всем в сессии
        broadcast_participants_update(session_id)


@socketio.on('leave')
def handle_leave(data):
    session_id = data.get('sessionId')
    user_id = data.get('userId')
    
    if not current_user.is_authenticated or current_user.id != user_id:
        current_app.logger.warning(f"Attempted leave by unauthenticated or mismatched user_id: {user_id} with SID {request.sid}")
        return

    leave_room(session_id)
    current_app.logger.info(f"User {current_user.username} (ID: {user_id}) left room: {session_id}")

    if session_id in session_users and user_id in session_users[session_id]:
        del session_users[session_id][user_id]
        current_app.logger.info(f"Removed user {current_user.username} from session_users for session {session_id}")

        # Отправляем обновленный список участников всем в сессии
        broadcast_participants_update(session_id)

        # Удаляем курсор пользователя
        emit('cursor_update', {
            'userId': user_id,
            'username': current_user.username,
            'position': None, # Отправляем None, чтобы удалить курсор
            'fileId': None
        }, room=session_id)

        if not session_users[session_id]:
            if session_id in last_known_file_content:
                del last_known_file_content[session_id]
                current_app.logger.info(f"Cleaned up last_known_file_content for empty session {session_id}")
            del session_users[session_id]


@socketio.on('code_change')
def handle_code_change(data):
    session_id = data.get('sessionId')
    file_id = data.get('fileId')
    change = data.get('change') # Это Monaco delta change event
    current_content = data.get('currentContent') # Клиент отправляет текущий полный контент

    if not current_user.is_authenticated:
        return

    with current_app.app_context():
        session_data = SessionManager.get_session(session_id)
        if not session_data:
            return
        
        user_role = SessionManager.get_user_role_in_session(session_id, current_user.id)
        if user_role not in ['owner', 'editor'] or session_data.editing_locked:
            # Отклоняем изменение, если у пользователя нет прав или сессия заблокирована
            emit('editor_revert', {'fileId': file_id, 'content': last_known_file_content.get(file_id, "")}, room=request.sid)
            return

        file_to_update = db.session.get(File, file_id)
        if not file_to_update or file_to_update.session_id != session_id:
            return

        # Обновляем контент файла в БД
        file_to_update.content = current_content
        db.session.commit()
        current_app.logger.debug(f"File {file_id} content updated in DB.")

        # Обновляем последнее известное состояние файла на сервере
        last_known_file_content[file_id] = current_content
        current_app.logger.debug(f"File {file_id} last_known_content updated in cache.")

        # Отправляем изменение всем, кроме отправителя
        # Отправляем именно delta-изменение, а не полный контент, для эффективности
        # current_content используется для синхронизации, если дельта не сработает
        emit('code_update', {
            'fileId': file_id,
            'change': change, # Передаем дельту
            'currentContent': current_content # На случай рассинхронизации
        }, room=session_id, skip_sid=request.sid)
        current_app.logger.debug(f"Emitted code_update for session {session_id}, file {file_id}")


@socketio.on('cursor_move')
def handle_cursor_move(data):
    session_id = data.get('sessionId')
    file_id = data.get('fileId')
    position = data.get('position') # {lineNumber: X, column: Y}

    if not current_user.is_authenticated:
        return

    # Обновляем активный файл пользователя в session_users
    if session_id in session_users and current_user.id in session_users[session_id]:
        session_users[session_id][current_user.id]['current_file_id'] = file_id

    # Отправляем позицию курсора всем, кроме отправителя
    emit('cursor_update', {
        'userId': current_user.id,
        'username': current_user.username,
        'position': position,
        'fileId': file_id
    }, room=session_id, skip_sid=request.sid)

    # Если позиция курсора None (например, при переключении файла), нужно обновить участников
    # чтобы убрать старую позицию курсора. broadcast_participants_update уже делает это.
    if position is None: # Проверим, если клиент отправил None, то это значит, что курсор ушел с файла
        current_app.logger.debug(f"User {current_user.username} (ID: {current_user.id}) set cursor to None in file {file_id}. Broadcasting participant update.")
        broadcast_participants_update(session_id) # Это обновит UI для всех


@socketio.on('switch_file')
def handle_switch_file(data):
    session_id = data.get('sessionId')
    file_id = data.get('fileId')

    if not current_user.is_authenticated:
        return

    with current_app.app_context():
        file_to_load = db.session.get(File, file_id)
        if not file_to_load or file_to_load.session_id != session_id:
            current_app.logger.warning(f"User {current_user.username} tried to switch to non-existent or wrong file {file_id} in session {session_id}")
            return
        
        # Обновляем last_known_file_content для нового файла
        last_known_file_content[file_id] = file_to_load.content

        # Отправляем новому активному файлу, его контент
        emit('load_file_content', {
            'fileId': file_to_load.id,
            'content': file_to_load.content,
            'language': file_to_load.language,
            'fileName': file_to_load.name # Добавлен fileName
        }, room=request.sid)

        # Обновляем активный файл пользователя в session_users
        if session_id in session_users and current_user.id in session_users[session_id]:
            session_users[session_id][current_user.id]['current_file_id'] = file_id
        
        # Обновляем список участников для всех, чтобы показать, кто какой файл смотрит
        broadcast_participants_update(session_id)
        current_app.logger.info(f"User {current_user.username} switched to file {file_to_load.name} (ID: {file_to_load.id}) in session {session_id}.")


@socketio.on('chat_message')
def handle_chat_message(data):
    session_id = data.get('sessionId')
    message = data.get('message')
    user = current_user.username
    timestamp = datetime.now().isoformat()

    # Отправляем сообщение всем в комнате
    emit('new_message', {
        'user': user,
        'message': message,
        'timestamp': timestamp
    }, room=session_id)
    current_app.logger.info(f"Chat message from {user} in {session_id}: {message}")


@socketio.on('execute_code')
def handle_execute_code(data):
    session_id = data.get('sessionId')
    file_id = data.get('fileId') # ID файла для выполнения

    if not current_user.is_authenticated:
        return

    with current_app.app_context():
        session_data = SessionManager.get_session(session_id)
        if not session_data:
            emit('error', {'message': 'Сессия не найдена.'})
            return
        
        user_role = SessionManager.get_user_role_in_session(session_id, current_user.id)
        if user_role not in ['owner', 'editor']:
            emit('error', {'message': 'У вас нет прав для выполнения кода.'})
            return

        if code_executor:
            # Выполнение кода может занять время, запускаем асинхронно
            # Вместо Thread используем socketio.start_background_task для совместимости с eventlet/gevent
            file_obj = db.session.get(File, file_id) # Получаем объект файла внутри контекста
            if not file_obj or file_obj.session_id != session_id:
                emit('execution_result', {'output': 'Файл не найден или не принадлежит этой сессии.'}, room=request.sid)
                current_app.logger.warning(f"File {file_id} not found or doesn't belong to session {session_id}.")
                return

            emit('execution_started', {'message': 'Выполнение кода начато...'}, room=session_id)
            current_app.logger.info(f"Code execution started for session {session_id}, file {file_id} by {current_user.username}.")
            
            socketio.start_background_task(SessionManager.execute_code_in_session, file_obj.id, file_obj.language, file_obj.content, session_id)
        else:
            emit('error', {'message': 'Исполнитель кода недоступен.'}, room=session_id)
            current_app.logger.error("CodeExecutor is not set.")

@socketio.on('set_main_file_socket')
def handle_set_main_file_socket(data):
    session_id = data['sessionId']
    file_id = data['fileId']
    user_id = current_user.id

    with current_app.app_context():
        session_obj = Session.query.get(session_id)
        if not session_obj:
            return

        user_role_entry = CollaborationRole.query.filter_by(session_id=session_id, user_id=user_id).first()
        if not user_role_entry or user_role_entry.role not in ['owner', 'editor']:
            emit('error', {'message': 'У вас нет прав для изменения основного файла.'}, room=request.sid)
            return
        
        target_file = db.session.get(File, file_id)
        if not target_file or target_file.session_id != session_id:
            emit('error', {'message': 'Файл не найден или не принадлежит этой сессии.'}, room=request.sid)
            return

        # Сброс is_main для всех файлов в сессии
        for f in session_obj.files:
            f.is_main = False
        
        target_file.is_main = True
        target_file_lang = target_file.language
        db.session.commit()
        current_app.logger.info(f"Main file set to {file_id} for session {session_id}.")

        # Уведомляем всех в сессии об изменении основного файла
        emit('main_file_changed', {
            'fileId': file_id,
            'newLanguage': target_file_lang # Передаем новый язык основного файла
        }, room=session_id)
        # Обновляем UI файлов на всех клиентах
        # Вместо SessionManager.notify_file_list_update(session_id)
        # Мы просто пересылаем обновленные данные списка файлов напрямую
        files_data = SessionManager.get_session_files_data_for_json(session_id) # Предполагается, что SessionManager имеет такой метод
        emit('file_list_update', {'files': files_data}, room=session_id)


@socketio.on('delete_file_socket')
def handle_delete_file_socket(data):
    session_id = data['sessionId']
    file_id = data['fileId']
    user_id = current_user.id

    with current_app.app_context():
        session_obj = Session.query.get(session_id)
        if not session_obj:
            return

        user_role_entry = CollaborationRole.query.filter_by(session_id=session_id, user_id=user_id).first()
        if not user_role_entry or user_role_entry.role not in ['owner', 'editor']:
            emit('error', {'message': 'У вас нет прав для удаления файлов.'}, room=request.sid)
            return

        file_to_delete = db.session.get(File, file_id)
        if not file_to_delete or file_to_delete.session_id != session_id:
            emit('error', {'message': 'Файл не найден или не принадлежит этой сессии.'}, room=request.sid)
            return
        
        if len(session_obj.files) == 1:
            emit('error', {'message': 'Нельзя удалить последний файл в сессии.'}, room=request.sid)
            return

        # Если удаляется основной файл, устанавливаем другой файл основным
        if file_to_delete.is_main:
            other_files = [f for f in session_obj.files if f.id != file_id]
            if other_files:
                other_files[0].is_main = True
                db.session.add(other_files[0]) # Убедиться, что изменения в других_файлах сохранятся
            # else: Если сюда дошли, это ошибка, т.к. "Нельзя удалить последний файл"
            
        db.session.delete(file_to_delete)
        db.session.commit()
        current_app.logger.info(f"File {file_id} deleted from session {session_id}.")

        emit('file_deleted', {'fileId': file_id}, room=session_id)
        # Обновляем UI файлов на всех клиентах
        files_data = SessionManager.get_session_files_data_for_json(session_id)
        emit('file_list_update', {'files': files_data}, room=session_id)


# Вспомогательная функция для широковещательной рассылки списка участников
def broadcast_participants_update(session_id):
    participants = []
    
    # Получаем актуальный список участников из нашего словаря session_users
    if session_id in session_users:
        for user_id, user_data in session_users[session_id].items():
            # Проверяем, что пользователь все еще существует в БД
            user_obj = User.query.get(user_id)
            if user_obj:
                participants.append({
                    'id': user_id,
                    'username': user_data['username'],
                    'role': user_data['role'],
                    'current_file_id': user_data.get('current_file_id') # Добавляем текущий файл
                })
            else:
                # Если пользователя нет в БД, удаляем его из session_users
                current_app.logger.warning(f"User {user_id} in session_users but not in DB. Removing.")
                del session_users[session_id][user_id]
    
    emit('participants_update', {'participants': participants}, room=session_id)
    current_app.logger.info(f"Broadcasted participants update for session {session_id}. Participants count: {len(participants)}")

# Добавлен новый обработчик для обновления языка файла.
@socketio.on('update_file_language')
def handle_update_file_language(data):
    session_id = data.get('sessionId')
    file_id = data.get('fileId')
    new_language = data.get('language')
    user_id = current_user.id

    if not current_user.is_authenticated:
        return

    with current_app.app_context():
        session_obj = Session.query.get(session_id)
        if not session_obj:
            return

        user_role = SessionManager.get_user_role_in_session(session_id, user_id)
        if user_role not in ['owner', 'editor']:
            emit('error', {'message': 'У вас нет прав для изменения языка файла.'}, room=request.sid)
            return
        
        file_to_update = db.session.get(File, file_id)
        if not file_to_update or file_to_update.session_id != session_id:
            emit('error', {'message': 'Файл не найден или не принадлежит этой сессии.'}, room=request.sid)
            return
        
        file_to_update.language = new_language
        db.session.commit()
        current_app.logger.info(f"File {file_id} language updated to {new_language} by user {user_id}.")

        # Уведомляем всех в сессии об изменении языка файла
        emit('file_language_updated', {
            'fileId': file_id,
            'newLanguage': new_language
        }, room=session_id)
        # Возможно, также обновить список файлов, если язык отображается там
        files_data = SessionManager.get_session_files_data_for_json(session_id)
        emit('file_list_update', {'files': files_data}, room=session_id)

