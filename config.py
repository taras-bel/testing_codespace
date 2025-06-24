import os
import secrets
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(16))
    
    # Настройка SQLAlchemy
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///site.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Настройки сессий Flask
    SESSION_COOKIE_SECURE = False  # Установите True для HTTPS в продакшене
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    
    # Настройки для выполнения кода
    DOCKER_TIMEOUT = 10  # Максимальное время выполнения кода в секундах
