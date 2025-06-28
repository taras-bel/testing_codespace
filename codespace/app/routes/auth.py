from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app.models.models import User, CollaborationRole, Session
from app import db

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard')) # Перенаправляем на дашборд
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')

        if not username or not email or not password or not password_confirm:
            flash('Пожалуйста, заполните все поля.', 'danger')
            return redirect(url_for('auth.register'))

        if password != password_confirm:
            flash('Пароли не совпадают.', 'danger')
            return redirect(url_for('auth.register'))

        user_exists = db.session.execute(db.select(User).filter(
            (User.username == username) | (User.email == email)
        )).scalar_one_or_none()

        if user_exists:
            flash('Пользователь с таким именем или email уже существует.', 'warning')
            return redirect(url_for('auth.register'))

        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = db.session.execute(db.select(User).filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        )).scalar_one_or_none()

        if not user or not user.check_password(password):
            flash('Неверное имя пользователя/email или пароль. Попробуйте снова.', 'danger')
            return redirect(url_for('auth.login'))

        login_user(user, remember=remember)
        flash(f'Добро пожаловать, {user.username}!', 'success')
        return redirect(url_for('main.dashboard')) # Перенаправляем на дашборд

    return render_template('login.html')

@auth.route('/logout')
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('auth.login'))
