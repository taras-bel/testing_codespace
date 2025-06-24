import secrets
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models.models import CodeSession
from app import db
from app.execution.runner import AVAILABLE_LANGUAGES

main = Blueprint('main', __name__)

@main.route('/')
@login_required
def index():
    user_sessions = current_user.sessions.order_by(CodeSession.last_active.desc()).all()
    return render_template('index.html', user_sessions=user_sessions)

@main.route('/new-session', methods=['POST'])
@login_required
def new_session():
    session_id = secrets.token_hex(8)
    new_session = CodeSession(
        id=session_id,
        owner_id=current_user.id
    )
    db.session.add(new_session)
    db.session.commit()
    flash(f'Новая сессия {session_id} создана!', 'success')
    return redirect(url_for('main.editor', session_id=session_id))

@main.route('/session/<string:session_id>')
@login_required
def editor(session_id):
    session = db.session.get(CodeSession, session_id)
    if not session:
        flash('Сессия не найдена.', 'danger')
        return redirect(url_for('main.index'))
    
    return render_template('editor.html', 
                           session=session,
                           languages=AVAILABLE_LANGUAGES)

@main.route('/join', methods=['POST'])
@login_required
def join_session():
    session_id = request.form.get('session_id')
    if not session_id:
        flash('Необходимо ввести ID сессии.', 'warning')
        return redirect(url_for('main.index'))
        
    session = db.session.get(CodeSession, session_id)
    if session:
        return redirect(url_for('main.editor', session_id=session_id))
    
    flash(f'Сессия с ID "{session_id}" не найдена.', 'danger')
    return redirect(url_for('main.index'))
