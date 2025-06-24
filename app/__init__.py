from flask import Flask 
from flask_sqlalchemy import SQLAlchemy 
from flask_login import LoginManager 
from flask_socketio import SocketIO 
from config import Config 
 
db = SQLAlchemy() 
login_manager = LoginManager() 
socketio = SocketIO() 
 
def create_app(config_class=Config): 
    app = Flask(__name__) 
    app.config.from_object(config_class) 
 
    # Инициализация расширений 
    db.init_app(app) 
    login_manager.init_app(app) 
    socketio.init_app(app, cors_allowed_origins="*", 
async_mode='threading') 
 
    # Настройки для Flask-Login 
    login_manager.login_view = 'auth.login' 
    login_manager.login_message = 'Пожалуйста, войдите, чтобы получить доступ к этой странице.' 
    login_manager.login_message_category = 'info' 
 
    # Регистрация Blueprints 
    from app.main.routes import main 
    from app.auth.routes import auth 
    app.register_blueprint(main) 
    app.register_blueprint(auth) 
     
    # Регистрация обработчиков Socket.IO 
    from app.sockets.events import register_socket_events 
    register_socket_events(socketio) 
 
    with app.app_context(): 
        db.create_all() 
 
    return app