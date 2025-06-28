import os
import secrets
from datetime import timedelta

class Config:
    # Базовые настройки
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32)) # Увеличена длина для безопасности
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    TESTING = False

    # Настройка SQLAlchemy
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///site.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False # Отключает отслеживание изменений, которое потребляет много памяти

    # Настройки сессий Flask
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true' # True для HTTPS в продакшене
    SESSION_COOKIE_HTTPONLY = True # Запрещает доступ к куки через JavaScript
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    PERMANENT_SESSION_LIFETIME = timedelta(days=7) # Срок жизни постоянной сессии

    # Настройки для выполнения кода
    DOCKER_TIMEOUT = int(os.environ.get('DOCKER_TIMEOUT', 15)) # Максимальное время выполнения кода в секундах
    DOCKER_IMAGE_PREFIX = 'codeshare_executor_' # Префикс для Docker-образов
    DOCKER_NETWORK = 'none' # Изоляция сети для контейнеров выполнения кода

    # Настройки для Celery (если будете использовать)
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')