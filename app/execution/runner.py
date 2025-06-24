import subprocess 
import os 
import tempfile 
from flask import current_app 
 
# Список доступных языков и информация для Docker 
AVAILABLE_LANGUAGES = { 
    'python': {'name': 'Python', 'extension': 'py', 'image': 
'python:3.9-slim'}, 
    'javascript': {'name': 'JavaScript', 'extension': 'js', 'image': 
'node:16-slim'}, 
    'cpp': {'name': 'C++', 'extension': 'cpp', 'image': 'gcc:latest'}, 
    'java': {'name': 'Java', 'extension': 'java', 'image': 
'openjdk:11-jre-slim'}, 
    'go': {'name': 'Go', 'extension': 'go', 'image': 
'golang:1.17-alpine'}, 
    'rust': {'name': 'Rust', 'extension': 'rs', 'image': 
'rust:latest'}, 
    'csharp': {'name': 'C#', 'extension': 'cs', 'image': 
'mcr.microsoft.com/dotnet/sdk:6.0'}, 
    # Добавьте другие языки по аналогии 
} 
 
def execute_code_in_docker(language, code): 
    """ 
    Выполняет код в изолированном Docker-контейнере. 
    """ 
    if language not in AVAILABLE_LANGUAGES: 
        return {'error': f'Язык {language} не поддерживается.'} 
         
    lang_config = AVAILABLE_LANGUAGES[language] 
    timeout = current_app.config.get('DOCKER_TIMEOUT', 10) 
 
    try: 
        with tempfile.TemporaryDirectory() as temp_dir: 
            file_path = os.path.join(temp_dir, 
f'main.{lang_config["extension"]}') 
            with open(file_path, 'w', encoding='utf-8') as f: 
                f.write(code) 
 
            # Путь к соответствующему Dockerfile 
            dockerfile_path = os.path.join( 
                os.path.dirname(__file__), 'dockerfiles', language 
            ) 
 
            # Команда для сборки и запуска Docker-контейнера 
            # --rm: удалить контейнер после выполнения 
            # -v: монтировать временную папку с кодом в контейнер 
            # -w: установить рабочую директорию внутри контейнера 
            command = [ 
                'docker', 'run', '--rm', '--network=none', 
                '-v', f'{temp_dir}:/app', 
                '-w', '/app', 
                lang_config['image'], 
                'timeout', str(timeout), 
                *get_run_command(language, 
f'main.{lang_config["extension"]}') 
            ] 
             
            # ВАЖНО: Ниже представлен вызов. Для его работы 
            # на сервере должен быть установлен Docker. 
            # Если Docker не установлен, вернется ошибка. 
            result = subprocess.run( 
                command, 
                capture_output=True, 
                text=True, 
                timeout=timeout + 2 # Таймаут для самого docker run 
            ) 
             
            if result.returncode == 124: # Код возврата `timeout` 
                 return {'error': f'Выполнение кода превысило лимит 
времени ({timeout} секунд).'} 
 
            return {'output': result.stdout, 'error': result.stderr} 
 
    except FileNotFoundError: 
        return {'error': 'Docker не найден. Для безопасного выполнения 
кода необходим установленный Docker.'} 
    except subprocess.TimeoutExpired: 
        return {'error': f'Выполнение кода превысило общий лимит 
времени.'} 
    except Exception as e: 
        return {'error': f'Произошла внутренняя ошибка сервера: 
{str(e)}'} 
 
def get_run_command(language, filename): 
    """Возвращает команду для запуска файла в зависимости от 
языка.""" 
    if language == 'python': 
        return ['python', filename] 
    if language == 'javascript': 
        return ['node', filename] 
    if language == 'cpp': 
        # Команда для компиляции и запуска 
        return ['sh', '-c', f'g++ {filename} -o main && ./main'] 
    if language == 'java': 
        class_name = filename.split('.')[0] 
        return ['sh', '-c', f'javac {filename} && java {class_name}'] 
    if language == 'go': 
        return ['go', 'run', filename] 
    if language == 'rust': 
        return ['sh', '-c', f'rustc {filename} && ./main'] 
    if language == 'csharp': 
        return ['dotnet', 'script', filename] 
    return []