from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from app.config import Config
import os

from app.services.code_executor import CodeExecutor, make_celery
from .extensions import db, socketio

login_manager = LoginManager()
migrate = Migrate()

executor = CodeExecutor()
celery_app = None

login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

    migrate.init_app(app, db)

    global celery_app
    if app.config.get('CELERY_BROKER_URL'):
        celery_app = make_celery(app)
        executor.execute_code_task = celery_app.task(executor.execute_code_task)
        app.logger.info("Celery is configured and code execution tasks are routed to Celery.")
    else:
        app.logger.warning("CELERY_BROKER_URL is not set. Code execution will run in separate threads (not recommended for production).")

    from .routes.main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .routes.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .sockets import events
    events.set_code_executor(executor) # Передаем executor в sockets.events

    with app.app_context():
        from .models import models

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.models import User
        return db.session.get(User, int(user_id))

    return app