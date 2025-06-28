from app import create_app, socketio
import os

app = create_app()

if __name__ == '__main__':
    # Получаем хост из переменной окружения или устанавливаем по умолчанию
    # Для продакшена, используйте '0.0.0.0' для доступа извне контейнера/сети
    host = os.environ.get('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_RUN_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

    print(f"Starting Flask-SocketIO app on {host}:{port} with debug={debug}")
    socketio.run(app, debug=debug, host=host, port=port, allow_unsafe_werkzeug=True) # allow_unsafe_werkzeug для dev