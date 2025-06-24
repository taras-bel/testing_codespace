# auth.py
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User
from . import db, login_manager

auth = Blueprint('auth', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user_id = db.hget('user_index', username)
        if not user_id:
            flash('Invalid username')
            return redirect(url_for('auth.login'))
            
        user = User.get(user_id)
        if not user or not check_password_hash(user.password_hash, password):
            flash('Invalid password')
            return redirect(url_for('auth.login'))
            
        login_user(user)
        return redirect(url_for('main.index'))
    
    return render_template('login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if db.hexists('user_index', username):
            flash('Username already exists')
            return redirect(url_for('auth.register'))
            
        user_id = str(uuid.uuid4())
        password_hash = generate_password_hash(password)
        
        db.hset(f'user:{user_id}', mapping={
            'username': username,
            'password_hash': password_hash,
            'created_at': datetime.now().isoformat()
        })
        db.hset('user_index', username, user_id)
        
        user = User(user_id, username, password_hash)
        login_user(user)
        flash('Registration successful')
        return redirect(url_for('main.index'))
    
    return render_template('register.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))