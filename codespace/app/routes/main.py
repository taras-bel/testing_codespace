from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.services.session_manager import SessionManager
from app.models.models import Session, File, User, CollaborationRole
from app.extensions import db
import json

main = Blueprint('main', __name__)

# Available languages for Monaco Editor (kept here for create_session.html dropdown)
LANGUAGES = {
    'python': {'name': 'Python', 'mode': 'python', 'file_extension': 'py'},
    'javascript': {'name': 'JavaScript', 'mode': 'javascript', 'file_extension': 'js'},
    'java': {'name': 'Java', 'mode': 'java', 'file_extension': 'java'},
    'cpp': {'name': 'C++', 'mode': 'clike', 'file_extension': 'cpp'},
    'csharp': {'name': 'C#', 'extension': 'cs', 'mode': 'csharp', 'file_extension': 'cs'},
    'go': {'name': 'Go', 'mode': 'go', 'file_extension': 'go'},
    'rust': {'name': 'Rust', 'mode': 'rust', 'file_extension': 'rs'},
    'plaintext': {'name': 'Plain Text', 'mode': 'plaintext', 'file_extension': 'txt'}
}


@main.route('/')
@login_required
def index():
    # Перенаправляем на дашборд, если пользователь авторизован
    return redirect(url_for('main.dashboard'))

@main.route('/dashboard')
@login_required
def dashboard():
    # Получаем все сессии, где пользователь является владельцем или коллаборатором
    owned_sessions = Session.query.filter_by(owner_id=current_user.id).order_by(Session.last_accessed.desc()).all()
    collaborator_roles = CollaborationRole.query.filter_by(user_id=current_user.id).all()
    
    collaborated_sessions = []
    for role in collaborator_roles:
        if role.session.owner_id != current_user.id: # Исключаем сессии, где пользователь уже владелец
            collaborated_sessions.append(role.session)

    return render_template('dashboard.html', 
                           owned_sessions=owned_sessions, 
                           collaborated_sessions=collaborated_sessions)

@main.route('/create_session', methods=['GET', 'POST'])
@login_required
def create_session():
    if request.method == 'POST':
        title = request.form.get('title', 'Новая сессия')
        description = request.form.get('description', '')
        visibility = request.form.get('visibility', 'private')
        initial_language = request.form.get('language', 'python')

        if not title or not initial_language:
            flash('Название сессии и начальный язык обязательны.', 'danger')
            return render_template('create_session.html', languages=LANGUAGES)

        if initial_language not in LANGUAGES:
            flash('Выбран неподдерживаемый язык.', 'danger')
            return render_template('create_session.html', languages=LANGUAGES)

        session_id = SessionManager.create_session(
            owner_id=current_user.id,
            title=title,
            description=description,
            visibility=visibility,
            initial_language=initial_language
        )

        if session_id:
            flash(f'Сессия "{title}" создана успешно!', 'success')
            return redirect(url_for('main.session', session_id=session_id))
        else:
            flash('Не удалось создать сессию.', 'danger')
            return render_template('create_session.html', languages=LANGUAGES)
            
    return render_template('create_session.html', languages=LANGUAGES)


@main.route('/session/<session_id>')
@login_required
def session(session_id):
    session_data = SessionManager.get_session(session_id)
    if not session_data:
        flash('Сессия не найдена.', 'danger')
        return redirect(url_for('main.dashboard'))

    user_role = SessionManager.get_user_role_in_session(session_id, current_user.id)
    if not user_role and session_data.visibility == 'private':
        flash('У вас нет доступа к этой приватной сессии.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Если это публичная сессия и пользователь не участник, добавить как viewer
    if not user_role and session_data.visibility == 'public':
        SessionManager.add_collaborator(session_id, current_user.id, 'viewer')
        user_role = 'viewer' # Обновляем роль после добавления

    if not user_role: # Если все еще нет роли (например, приватная и не добавлен)
        flash('У вас нет доступа к этой сессии.', 'danger')
        return redirect(url_for('main.dashboard'))

    # Получаем все файлы для текущей сессии
    files = SessionManager.get_session_files(session_id)
    # Определяем текущий активный файл (по умолчанию первый или основной)
    active_file = None
    if files:
        active_file = next((f for f in files if f.is_main), files[0])
    
    return render_template('session.html', 
                           session=session_data, 
                           current_user_role=user_role,
                           files=files,
                           active_file=active_file,
                           languages=LANGUAGES) # Передаем LANGUAGES в шаблон session.html


@main.route('/delete_session/<session_id>', methods=['POST'])
@login_required
def delete_session(session_id):
    session_data = SessionManager.get_session(session_id)
    if not session_data or session_data.owner_id != current_user.id:
        flash('У вас нет прав для удаления этой сессии.', 'danger')
        return redirect(url_for('main.dashboard'))

    if SessionManager.delete_session(session_id):
        flash('Сессия успешно удалена.', 'success')
    else:
        flash('Ошибка при удалении сессии.', 'danger')
    return redirect(url_for('main.dashboard'))

@main.route('/session/<session_id>/add_file', methods=['POST'])
@login_required
def add_file(session_id):
    session_data = SessionManager.get_session(session_id)
    if not session_data:
        flash('Сессия не найдена.', 'danger')
        return redirect(url_for('main.dashboard'))

    user_role = SessionManager.get_user_role_in_session(session_id, current_user.id)
    if user_role not in ['owner', 'editor']:
        flash('У вас нет прав для добавления файлов в эту сессию.', 'danger')
        return redirect(url_for('main.session', session_id=session_id))

    file_name = request.form.get('file_name')
    file_language = request.form.get('file_language')

    if not file_name or not file_language:
        flash('Имя файла и язык обязательны.', 'danger')
        return redirect(url_for('main.session', session_id=session_id))
    
    # Проверка на существование файла с таким именем
    existing_file = File.query.filter_by(session_id=session_id, name=file_name).first()
    if existing_file:
        flash('Файл с таким именем уже существует в этой сессии.', 'danger')
        return redirect(url_for('main.session', session_id=session_id))

    new_file = File(
        session_id=session_id,
        name=file_name,
        content=SessionManager.get_default_code(file_language),
        language=file_language,
        is_main=False # По умолчанию новый файл не основной
    )
    db.session.add(new_file)
    try:
        db.session.commit()
        flash('Файл успешно добавлен.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при добавлении файла: {e}', 'danger')

    return redirect(url_for('main.session', session_id=session_id))

@main.route('/session/<session_id>/delete_file/<int:file_id>', methods=['POST'])
@login_required
def delete_file(session_id, file_id):
    session_data = SessionManager.get_session(session_id)
    if not session_data:
        flash('Сессия не найдена.', 'danger')
        return redirect(url_for('main.dashboard'))

    user_role = SessionManager.get_user_role_in_session(session_id, current_user.id)
    if user_role not in ['owner', 'editor']:
        flash('У вас нет прав для удаления файлов из этой сессии.', 'danger')
        return redirect(url_for('main.session', session_id=session_id))

    file_to_delete = db.session.get(File, file_id)
    if not file_to_delete or file_to_delete.session_id != session_id:
        flash('Файл не найден в этой сессии.', 'danger')
        return redirect(url_for('main.session', session_id=session_id))
    
    if len(session_data.files) == 1:
        flash('Нельзя удалить последний файл в сессии.', 'warning')
        return redirect(url_for('main.session', session_id=session_id))

    db.session.delete(file_to_delete)
    try:
        db.session.commit()
        flash('Файл успешно удален.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении файла: {e}', 'danger')
    
    return redirect(url_for('main.session', session_id=session_id))

@main.route('/session/<session_id>/set_main_file/<int:file_id>', methods=['POST'])
@login_required
def set_main_file(session_id, file_id):
    session_data = SessionManager.get_session(session_id)
    if not session_data:
        flash('Сессия не найдена.', 'danger')
        return redirect(url_for('main.dashboard'))

    user_role = SessionManager.get_user_role_in_session(session_id, current_user.id)
    if user_role not in ['owner', 'editor']:
        flash('У вас нет прав для изменения основного файла.', 'danger')
        return redirect(url_for('main.session', session_id=session_id))

    file_to_set_main = db.session.get(File, file_id)
    if not file_to_set_main or file_to_set_main.session_id != session_id:
        flash('Файл не найден в этой сессии.', 'danger')
        return redirect(url_for('main.session', session_id=session_id))
    
    # Сбрасываем флаг is_main для всех файлов в сессии
    for f in session_data.files:
        f.is_main = False
    
    # Устанавливаем is_main для выбранного файла
    file_to_set_main.is_main = True

    try:
        db.session.commit()
        flash(f'Файл "{file_to_set_main.name}" установлен как основной.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при установке основного файла: {e}', 'danger')
    
    return redirect(url_for('main.session', session_id=session_id))

@main.route('/session/<session_id>/change_file/<int:file_id>', methods=['GET'])
@login_required
def change_file(session_id, file_id):
    session_data = SessionManager.get_session(session_id)
    if not session_data:
        flash('Сессия не найдена.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    user_role = SessionManager.get_user_role_in_session(session_id, current_user.id)
    if not user_role and session_data.visibility == 'private':
        flash('У вас нет доступа к этой приватной сессии.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    if not user_role and session_data.visibility == 'public':
        SessionManager.add_collaborator(session_id, current_user.id, 'viewer')
        user_role = 'viewer'

    file_to_open = db.session.get(File, file_id)
    if not file_to_open or file_to_open.session_id != session_id:
        flash('Файл не найден в этой сессии.', 'danger')
        return redirect(url_for('main.session', session_id=session_id))
    
    files = SessionManager.get_session_files(session_id)

    # Принудительно устанавливаем новый активный файл для рендеринга
    return render_template('session.html', 
                           session=session_data, 
                           current_user_role=user_role,
                           files=files,
                           active_file=file_to_open,
                           languages=LANGUAGES)


@main.route('/session/<session_id>/lock_editing', methods=['POST'])
@login_required
def lock_editing(session_id):
    session_data = SessionManager.get_session(session_id)
    if not session_data or session_data.owner_id != current_user.id:
        flash('У вас нет прав для изменения настроек блокировки.', 'danger')
        return redirect(url_for('main.session', session_id=session_id))

    session_data.editing_locked = True
    db.session.commit()
    flash('Редактирование сессии заблокировано.', 'info')
    return redirect(url_for('main.session', session_id=session_id))

@main.route('/session/<session_id>/unlock_editing', methods=['POST'])
@login_required
def unlock_editing(session_id):
    session_data = SessionManager.get_session(session_id)
    if not session_data or session_data.owner_id != current_user.id:
        flash('У вас нет прав для изменения настроек блокировки.', 'danger')
        return redirect(url_for('main.session', session_id=session_id))

    session_data.editing_locked = False
    db.session.commit()
    flash('Редактирование сессии разблокировано.', 'info')
    return redirect(url_for('main.session', session_id=session_id))

@main.route('/session/<session_id>/manage_collaborators', methods=['GET', 'POST'])
@login_required
def manage_collaborators(session_id):
    session_data = SessionManager.get_session(session_id)
    if not session_data or session_data.owner_id != current_user.id:
        flash('У вас нет прав для управления коллабораторами этой сессии.', 'danger')
        return redirect(url_for('main.dashboard'))

    collaborators_data = SessionManager.get_session_collaborators_with_users(session_id)
    
    # Фильтруем владельца, он всегда есть и его роль нельзя изменить или удалить через этот интерфейс
    collaborators_for_display = [
        (role_entry, user_obj) for role_entry, user_obj in collaborators_data 
        if role_entry.role != 'owner'
    ]

    if request.method == 'POST':
        action = request.form.get('action')
        target_user_id = request.form.get('user_id')
        
        if target_user_id:
            target_user_id = int(target_user_id) # Конвертируем обратно в int

        if action == 'update_role':
            new_role = request.form.get('new_role')
            if target_user_id and new_role:
                # Проверка, что владелец не пытается изменить свою роль
                if target_user_id == current_user.id:
                    flash('Вы не можете изменить свою собственную роль.', 'danger')
                elif SessionManager.update_collaborator_role(session_id, target_user_id, new_role):
                    flash(f'Роль пользователя успешно обновлена до "{new_role}".', 'success')
                else:
                    flash('Ошибка при обновлении роли пользователя.', 'danger')
            else:
                flash('Недостаточно данных для обновления роли.', 'danger')
        elif action == 'remove_collaborator':
            if target_user_id:
                # Проверка, что владелец не пытается удалить себя
                if target_user_id == current_user.id:
                    flash('Вы не можете удалить себя из сессии через этот интерфейс.', 'danger')
                elif SessionManager.remove_collaborator(session_id, target_user_id):
                    flash('Коллаборатор успешно удален.', 'success')
                else:
                    flash('Ошибка при удалении коллаборатора.', 'danger')
            else:
                flash('Недостаточно данных для удаления коллаборатора.', 'danger')
        elif action == 'add_collaborator':
            username_to_add = request.form.get('username_to_add')
            role_to_add = request.form.get('role_to_add', 'viewer')
            if username_to_add:
                user_to_add = User.query.filter_by(username=username_to_add).first()
                if user_to_add:
                    if SessionManager.add_collaborator(session_id, user_to_add.id, role_to_add):
                        flash(f'Пользователь {username_to_add} успешно добавлен как {role_to_add}.', 'success')
                    else:
                        flash(f'Пользователь {username_to_add} уже является коллаборатором или произошла ошибка.', 'warning')
                else:
                    flash(f'Пользователь с именем "{username_to_add}" не найден.', 'danger')
            else:
                flash('Имя пользователя для добавления не может быть пустым.', 'danger')

        # После POST запроса, перенаправляем на GET, чтобы обновить страницу и избежать повторной отправки
        return redirect(url_for('main.manage_collaborators', session_id=session_id))

    return render_template(
        'manage_collaborators.html',
        session=session_data,
        collaborators=collaborators_for_display # Передаем отфильтрованных коллабораторов
    )


from flask import request, jsonify
import os


@main.route("/log_activity", methods=["POST"])
def log_activity():
    data = request.get_json()
    code = data.get("code", "")
    speeds = data.get("speeds", [])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = session.get("session_id", "unknown")
    username = session.get("username", "anonymous")

    log_dir = os.path.join("logs", "sessions", session_id)
    os.makedirs(log_dir, exist_ok=True)
    base_path = os.path.join(log_dir, f"{timestamp}_{username}.md")
    
    # Определим путь к файлу с последним снапшотом
    latest_path = os.path.join(log_dir, f"latest_snapshot_{username}.txt")
    diff_text = ""

    if os.path.exists(latest_path):
        with open(latest_path, "r", encoding="utf-8") as prev:
            old_code = prev.read().splitlines()
            new_code = code.splitlines()
            import difflib
            diff = difflib.unified_diff(old_code, new_code, lineterm="")
            diff_text = "\n".join(diff)

    with open(base_path, "w", encoding="utf-8") as f:
        f.write(f"# Snapshot: {timestamp}\n")
        f.write("```python\n")
        f.write(code)
        f.write("\n```\n\n")
        f.write("## Typing Speed (ms between keys):\n")
        f.write(", ".join(map(str, speeds)) + "\n\n")
        if diff_text:
            f.write("## Changes since last snapshot:\n")
            f.write("```diff\n" + diff_text + "\n```\n")

    # Обновим последний снапшот
    with open(latest_path, "w", encoding="utf-8") as f:
        f.write(code)
    
    return jsonify({"status": "saved"}), 200



@main.route("/log_copy_attempt", methods=["POST"])
def log_copy_attempt():
    data = request.get_json()
    type = data.get("type", "unknown")
    timestamp = data.get("timestamp", "unknown")
    session_id = session.get("session_id", "unknown")
    username = session.get("username", "anonymous")

    log_dir = os.path.join("logs", "sessions", session_id)
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"copy_attempts_{username}.md")

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"- {timestamp}: {username} attempted {type}\n")
    
    return jsonify({"status": "logged"}), 200
