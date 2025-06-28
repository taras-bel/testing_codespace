from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app.models.models import User
from app import db

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
        if user:
            flash('Это имя пользователя уже занято. Пожалуйста, выберите другое.', 'warning')
            return redirect(url_for('auth.register'))
        
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('register.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
        
        if not user or not user.check_password(password):
            flash('Неверное имя пользователя или пароль. Попробуйте снова.', 'danger')
            return redirect(url_for('auth.login'))
            
        login_user(user, remember=remember)
        return redirect(url_for('main.index'))
    
    return render_template('login.html')

@auth.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
