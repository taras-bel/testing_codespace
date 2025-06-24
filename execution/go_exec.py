import subprocess
import os
import tempfile
import shutil

def execute_go(code):
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp()
        file_name = os.path.join(temp_dir, 'main.go')
        exe_name = os.path.join(temp_dir, 'main') # Для скомпилированного исполняемого файла

        with open(file_name, 'w') as f:
            f.write(code)

        # Компилируем Go код
        compile_result = subprocess.run(
            ['go', 'build', '-o', exe_name, file_name],
            capture_output=True,
            text=True,
            cwd=temp_dir, # Компилируем во временной директории
            timeout=10
        )

        if compile_result.returncode != 0:
            return {
                'error': 'Ошибка компиляции Go:\n' + compile_result.stderr
            }

        # Запускаем скомпилированный исполняемый файл
        run_result = subprocess.run(
            [exe_name],
            capture_output=True,
            text=True,
            timeout=10 # 10-секундный таймаут
        )

        if run_result.returncode != 0:
            return {
                'error': f'Ошибка выполнения (код: {run_result.returncode})\n{run_result.stderr}',
                'output': run_result.stdout
            }

        return {'output': run_result.stdout}
    except FileNotFoundError:
        return {'error': 'Go компилятор не найден. Убедитесь, что Go установлен и доступен в PATH.'}
    except subprocess.TimeoutExpired as e:
        return {'error': f'Операция ({e.cmd[0]}) превысила лимит времени. (Таймаут: 10с на компиляцию/выполнение)'}
    except Exception as e:
        return {'error': f'Внутренняя ошибка сервера: {e}'}
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

