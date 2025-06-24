import subprocess
import os
import tempfile
import shutil

def execute_swift(code):
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp()
        file_name = os.path.join(temp_dir, 'main.swift')
        exe_name = os.path.join(temp_dir, 'main')

        with open(file_name, 'w') as f:
            f.write(code)

        # Компилируем Swift код
        compile_result = subprocess.run(
            ['swiftc', file_name, '-o', exe_name],
            capture_output=True,
            text=True,
            cwd=temp_dir,
            timeout=30 # Swift компиляция может быть очень долгой
        )

        if compile_result.returncode != 0:
            return {
                'error': 'Ошибка компиляции Swift:\n' + compile_result.stderr
            }

        # Запускаем скомпилированный исполняемый файл
        run_result = subprocess.run(
            [exe_name],
            capture_output=True,
            text=True,
            timeout=10
        )

        if run_result.returncode != 0:
            return {
                'error': f'Ошибка выполнения (код: {run_result.returncode})\n{run_result.stderr}',
                'output': run_result.stdout
            }

        return {'output': run_result.stdout}
    except FileNotFoundError:
        return {'error': 'Swift компилятор (swiftc) не найден. Убедитесь, что Swift установлен и доступен в PATH.'}
    except subprocess.TimeoutExpired as e:
        return {'error': f'Операция ({e.cmd[0]}) превысила лимит времени. (Таймаут: 30с на компиляцию, 10с на выполнение)'}
    except Exception as e:
        return {'error': f'Внутренняя ошибка сервера: {e}'}
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

