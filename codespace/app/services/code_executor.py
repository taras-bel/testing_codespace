import docker
import os
import tempfile
import shutil
from flask import current_app
from celery import Celery
from app.models.models import Session, File
from app.extensions import db, socketio

def make_celery(app_instance):
    celery = Celery(
        app_instance.import_name,
        broker=app_instance.config['CELERY_BROKER_URL'],
        backend=app_instance.config['CELERY_RESULT_BACKEND']
    )
    celery.conf.update(app_instance.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app_instance.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

class CodeExecutor:
    AVAILABLE_LANGUAGES = {
        'python': {'name': 'Python', 'extension': 'py', 'image': 'python:3.9-slim', 'cmd': ['python', 'main.py']},
        'javascript': {'name': 'JavaScript', 'extension': 'js', 'image': 'node:16-slim', 'cmd': ['node', 'main.js']},
        'cpp': {'name': 'C++', 'extension': 'cpp', 'image': 'gcc:latest', 'cmd': ['sh', '-c', 'g++ main.cpp -o main && ./main']},
        'java': {'name': 'Java', 'extension': 'java', 'image': 'openjdk:11-jre-slim', 'cmd': ['sh', '-c', 'javac Main.java && java Main']},
        'go': {'name': 'Go', 'extension': 'go', 'image': 'golang:1.17-alpine', 'cmd': ['go', 'run', 'main.go']},
        'rust': {'name': 'Rust', 'extension': 'rs', 'image': 'rust:latest', 'cmd': ['sh', '-c', 'rustc main.rs && ./main']},
        'csharp': {'name': 'C#', 'extension': 'cs', 'image': 'mcr.microsoft.com/dotnet/sdk:6.0', 'cmd': ['dotnet', 'run', '--project', '/app']},
    }

    def __init__(self):
        self.client = None

    def _initialize_docker_client(self):
        if self.client is None:
            try:
                self.client = docker.from_env()
                current_app.logger.info("Docker client initialized successfully.")
            except docker.errors.DockerException as e:
                current_app.logger.error(f"Docker client initialization error: {e}")
                self.client = None
                return False
        return self.client is not None

    def execute_code_task(self, session_id, file_id):
        if not self._initialize_docker_client():
            output = "Ошибка: Docker не запущен или недоступен на сервере."
            self._update_session_output_and_emit(session_id, output)
            return

        if not self.client:
            output = "Ошибка: Docker не запущен или недоступен на сервере."
            self._update_session_output_and_emit(session_id, output)
            return

        with current_app.app_context():
            session_data = db.session.get(Session, session_id)
            if not session_data:
                current_app.logger.error(f"Session {session_id} not found for execution.")
                return

            main_file = None
            if file_id:
                main_file = db.session.get(File, file_id)
                if main_file and main_file.session_id != session_id:
                    main_file = None
            
            if not main_file:
                main_file = db.session.query(File).filter_by(session_id=session_id, is_main=True).first()

            if not main_file:
                current_app.logger.error(f"No main file found for session {session_id} to execute.")
                output = "Ошибка выполнения: Не удалось найти основной файл для выполнения."
                self._update_session_output_and_emit(session_id, output)
                return

            language = main_file.language
            code_content = main_file.content

            lang_config = self.AVAILABLE_LANGUAGES.get(language)
            if not lang_config:
                output = f'Язык {language} не поддерживается для выполнения.'
                current_app.logger.warning(output)
                self._update_session_output_and_emit(session_id, output)
                return

            timeout = current_app.config.get('DOCKER_TIMEOUT', 15)
            output = ""
            stderr = ""

            temp_dir = None
            try:
                temp_dir = tempfile.mkdtemp()
                for file_obj in session_data.files:
                    file_path = os.path.join(temp_dir, file_obj.name)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(file_obj.content)

                if language == 'csharp':
                    cs_file_name = next((f.name for f in session_data.files if f.language == 'csharp' and f.is_main), 'Program.cs')
                    project_name = os.path.splitext(cs_file_name)[0]
                    csproj_content = f"""
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net6.0</TargetFramework>
    <StartupObject>{project_name}.Program</StartupObject>
  </PropertyGroup>
  <ItemGroup>
    <Compile Include="{cs_file_name}" />
  </ItemGroup>
</Project>
                    """
                    with open(os.path.join(temp_dir, f'{project_name}.csproj'), 'w', encoding='utf-8') as f:
                        f.write(csproj_content.strip())
                
                container_command = ['timeout', str(timeout)] + lang_config['cmd']

                container = self.client.containers.run(
                    lang_config['image'],
                    command=container_command,
                    volumes={temp_dir: {'bind': '/app', 'mode': 'rw'}},
                    working_dir='/app',
                    detach=True,
                    network_disabled=True,
                    mem_limit='128m',
                    cpu_period=100000,
                    cpu_quota=50000,
                )

                result = container.wait(timeout=timeout + 5)

                output = container.logs().decode('utf-8')

                if result['StatusCode'] == 124:
                    output = f'Выполнение кода превысило лимит времени ({timeout} секунд).\n' + output
                elif result['StatusCode'] != 0:
                    output = f"Ошибка выполнения (код {result['StatusCode']}):\n{output}"
                
                container.remove()

            except docker.errors.ContainerError as e:
                output = f"Ошибка выполнения в контейнере:\n{e.stderr.decode('utf-8') if e.stderr else str(e)}"
                current_app.logger.error(f"Container error for session {session_id}: {e}")
            except docker.errors.ImageNotFound:
                output = f"Ошибка: Docker образ '{lang_config['image']}' не найден. Пожалуйста, убедитесь, что он установлен."
                current_app.logger.error(f"Docker image not found: {lang_config['image']}")
            except docker.errors.APIError as e:
                output = f"Ошибка API Docker: {str(e)}"
                current_app.logger.error(f"Docker API error for session {session_id}: {e}")
            except Exception as e:
                output = f"Произошла внутренняя ошибка сервера: {str(e)}"
                current_app.logger.exception(f"Unexpected error during code execution for session {session_id}")
            finally:
                if temp_dir and os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    current_app.logger.info(f"Cleaned up temporary directory: {temp_dir}")

            self._update_session_output_and_emit(session_id, output)

    def _update_session_output_and_emit(self, session_id, output):
        with current_app.app_context():
            session_data = db.session.get(Session, session_id)
            if session_data:
                session_data.output = output
                db.session.commit()
                socketio.emit('execution_result', {'output': output}, room=session_id)
            else:
                current_app.logger.error(f"Session {session_id} not found when trying to update output.")