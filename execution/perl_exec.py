import subprocess
import os
import tempfile

def execute_perl(code):
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pl') as temp_file:
            temp_file.write(code)
            temp_file_name = temp_file.name

        result = subprocess.run(
            ['perl', temp_file_name],
            capture_output=True,
            text=True,
            timeout=10 # 10-секундный таймаут
        )
        os.unlink(temp_file_name)

        if result.returncode != 0:
            return {'error': f'Ошибка выполнения Perl:\n{result.stderr}', 'output': result.stdout}
        return {'output': result.stdout}
    except FileNotFoundError:
        return {'error': 'Perl интерпретатор не найден. Убедитесь, что Perl установлен и доступен в PATH.'}
    except subprocess.TimeoutExpired:
        if 'temp_file_name' in locals() and os.path.exists(temp_file_name):
            os.unlink(temp_file_name)
        return {'error': 'Выполнение кода превысило лимит времени (10 секунд).'}
    except Exception as e:
        if 'temp_file_name' in locals() and os.path.exists(temp_file_name):
            os.unlink(temp_file_name)
        return {'error': f'Внутренняя ошибка сервера: {e}'}

