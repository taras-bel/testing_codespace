from flask import Blueprint, render_template, request, redirect, url_for, flash, session as flask_session
from flask_login import login_required, current_user
from .. import db
from ..models.models import Session # <--- ЭТА СТРОКА ВЫЗЫВАЕТ ПРОБЛЕМУ
import uuid
from datetime import datetime, timedelta

main = Blueprint('main', __name__)

# Доступные языки и их настройки для CodeMirror
LANGUAGES = {
    'python': {'name': 'Python', 'mode': 'python'},
    'javascript': {'name': 'JavaScript', 'mode': 'javascript'},
    'java': {'name': 'Java', 'mode': 'clike'},
    'cpp': {'name': 'C++', 'mode': 'clike'},
    'text': {'name': 'Plain Text', 'mode': 'text/plain'}
}


@main.route('/')
def index():
    # Показываем только сессии, которыми владеет текущий пользователь,
    # если он аутентифицирован.
    user_sessions = []
    if current_user.is_authenticated:
        user_sessions = Session.query.filter_by(owner_id=current_user.id).all()
    return render_template('index.html', user_sessions=user_sessions)


@main.route('/create_session', methods=['POST'])
@login_required
def create_session():
    session_id = str(uuid.uuid4())
    default_code = "print('Hello, CodeShare!')" # Пример кода по умолчанию
    default_language = 'python'
    default_output = "" # Пустой вывод при создании

    # Время сессии - 60 минут по умолчанию
    timer_duration = 60 # Минут

    new_session = Session(
        id=session_id,
        owner_id=current_user.id,
        code=default_code,
        language=default_language,
        output=default_output,
        # timer_started_at остается None до запуска таймера
        timer_duration=timer_duration,
        editing_locked=False
    )
    db.session.add(new_session)
    db.session.commit()

    flash(f'Сессия "{session_id}" создана!', 'success')
    return redirect(url_for('main.editor', session_id=session_id))

@main.route('/editor/<session_id>')
@login_required
def editor(session_id):
    session_data = Session.query.get(session_id)

    if not session_data:
        flash('Сессия не найдена.', 'danger')
        return redirect(url_for('main.index'))

    # Проверяем, является ли текущий пользователь владельцем сессии,
    # или, если вы хотите разрешить всем присоединяться, просто убедитесь, что сессия существует.
    # Для целей этого проекта, мы пока что разрешим любому аутентифицированному пользователю присоединиться.
    # Если вы хотите строгую проверку владельца:
    # if session_data.owner_id != current_user.id:
    #     flash('У вас нет доступа к этой сессии.', 'danger')
    #     return redirect(url_for('main.index'))

    # Сохраняем ID сессии в сессии Flask, чтобы использовать его в SocketIO
    flask_session['session_id'] = session_id

    return render_template('editor.html', session=session_data, languages=LANGUAGES)
import os, json
from flask import request, jsonify
from datetime import datetime

@app.route('/log_activity', methods=['POST'])
def log_activity():
    data = request.json
    session_id = session.get('session_id', 'unknown')
    timestamp = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')
    os.makedirs(f'logs/sessions/{session_id}', exist_ok=True)
    with open(f'logs/sessions/{session_id}/{timestamp}.md', 'w', encoding='utf-8') as f:
        f.write(f"# Snapshot at {timestamp}\n\n")
        f.write("```python\n" + data.get("code", "") + "\n```\n\n")
        f.write("## Typing Speed (ms)\n" + ", ".join(map(str, data.get("typing_speeds", []))) + "\n\n")
        f.write("## Diff\n" + "\n".join(f"- {line}" for line in data.get("diff", [])))
    return jsonify({"status": "saved"})

@app.route('/log_copy_attempt', methods=['POST'])
def log_copy_attempt():
    data = request.json
    session_id = session.get('session_id', 'unknown')
    os.makedirs(f'logs/sessions/{session_id}', exist_ok=True)
    with open(f'logs/sessions/{session_id}/copy_log.txt', 'a', encoding='utf-8') as f:
        f.write(f"{datetime.utcnow().isoformat()} - {data.get('action') or 'unknown'}\n")
    return jsonify({"status": "logged"})

from flask import jsonify, render_template, send_file
import os
import json

@app.route("/replay/<session_id>")
@login_required
def replay(session_id):
    session = Session.query.get_or_404(session_id)
    if session.owner_id != current_user.id:
        abort(403)
    return render_template("replay.html", session=session)

@app.route("/api/replay_snapshots/<session_id>")
@login_required
def api_replay_snapshots(session_id):
    session = Session.query.get_or_404(session_id)
    if session.owner_id != current_user.id:
        abort(403)
    session_log_dir = os.path.join("logs", "sessions", session_id)
    if not os.path.exists(session_log_dir):
        return jsonify([])

    snapshots = []
    for fname in sorted(os.listdir(session_log_dir)):
        if fname.endswith(".md"):
            with open(os.path.join(session_log_dir, fname), "r", encoding="utf-8") as f:
                content = f.read()
            snapshots.append({
                "timestamp": fname.replace(".md", ""),
                "code": content
            })
    return jsonify(snapshots)