import subprocess
import os
import tempfile

def execute_python(code):
    try:
        # Создаем временный файл для записи кода
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as temp_file:
            temp_file.write(code)
            temp_file_name = temp_file.name

        # Выполняем Python код с использованием subprocess
        # Добавляем таймаут, чтобы предотвратить бесконечные циклы
        result = subprocess.run(
            ['python', temp_file_name],
            capture_output=True,
            text=True,
            timeout=10  # 10-секундный таймаут
        )

        # Удаляем временный файл
        os.unlink(temp_file_name)

        if result.returncode != 0:
            return {
                'error': f'Ошибка выполнения (код: {result.returncode})\n{result.stderr}',
                'output': result.stdout # Иногда stdout может быть даже при ошибке
            }
        else:
            return {'output': result.stdout}
    except subprocess.TimeoutExpired:
        if 'temp_file_name' in locals() and os.path.exists(temp_file_name):
            os.unlink(temp_file_name)
        return {'error': 'Выполнение кода превысило лимит времени (10 секунд).'}
    except Exception as e:
        if 'temp_file_name' in locals() and os.path.exists(temp_file_name):
            os.unlink(temp_file_name)
        return {'error': f'Внутренняя ошибка сервера: {e}'}

