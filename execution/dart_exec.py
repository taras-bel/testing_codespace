import subprocess
import os
import tempfile
import shutil

def execute_dart(code):
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp()
        file_name = os.path.join(temp_dir, 'main.dart')
        
        with open(file_name, 'w') as f:
            f.write(code)

        # Выполняем Dart код с использованием dart run
        # Или можно использовать dart compile exe для создания исполняемого файла
        result = subprocess.run(
            ['dart', 'run', file_name],
            capture_output=True,
            text=True,
            cwd=temp_dir,
            timeout=15 # Таймаут для выполнения Dart
        )

        if result.returncode != 0:
            return {
                'error': f'Ошибка выполнения Dart (код: {result.returncode})\n{result.stderr}',
                'output': result.stdout
            }

        return {'output': result.stdout}
    except FileNotFoundError:
        return {'error': 'Dart SDK не найден. Убедитесь, что Dart установлен и доступен в PATH.'}
    except subprocess.TimeoutExpired as e:
        return {'error': f'Выполнение кода Dart превысило лимит времени (15 секунд).'}
    except Exception as e:
        return {'error': f'Внутренняя ошибка сервера: {e}'}
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

