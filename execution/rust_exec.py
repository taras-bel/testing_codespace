import subprocess
import os
import tempfile
import shutil

def execute_rust(code):
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp()
        file_name = os.path.join(temp_dir, 'main.rs')
        exe_name = os.path.join(temp_dir, 'main') # Исполняемый файл по умолчанию

        with open(file_name, 'w') as f:
            f.write(code)

        # Компилируем Rust код
        compile_result = subprocess.run(
            ['rustc', file_name, '-o', exe_name],
            capture_output=True,
            text=True,
            cwd=temp_dir,
            timeout=20 # Rust компиляция может быть долгой
        )

        if compile_result.returncode != 0:
            return {
                'error': 'Ошибка компиляции Rust:\n' + compile_result.stderr
            }

        # Запускаем скомпилированный исполняемый файл
        run_result = subprocess.run(
            [exe_name],
            capture_output=True,
            text=True,
            timeout=10 # Таймаут для выполнения
        )

        if run_result.returncode != 0:
            return {
                'error': f'Ошибка выполнения (код: {run_result.returncode})\n{run_result.stderr}',
                'output': run_result.stdout
            }

        return {'output': run_result.stdout}
    except FileNotFoundError:
        return {'error': 'Rust компилятор (rustc) не найден. Убедитесь, что Rust установлен и доступен в PATH.'}
    except subprocess.TimeoutExpired as e:
        return {'error': f'Операция ({e.cmd[0]}) превысила лимит времени. (Таймаут: 20с на компиляцию, 10с на выполнение)'}
    except Exception as e:
        return {'error': f'Внутренняя ошибка сервера: {e}'}
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

