import subprocess
import os
import tempfile
import shutil

def execute_typescript(code):
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp()
        ts_file_name = os.path.join(temp_dir, 'main.ts')
        js_file_name = os.path.join(temp_dir, 'main.js')

        with open(ts_file_name, 'w') as f:
            f.write(code)

        # Компилируем TypeScript в JavaScript с помощью tsc
        # Убедитесь, что TypeScript (tsc) установлен глобально или в PATH
        compile_result = subprocess.run(
            ['tsc', ts_file_name, '--outFile', js_file_name],
            capture_output=True,
            text=True,
            cwd=temp_dir,
            timeout=15 # Таймаут для компиляции TypeScript
        )

        if compile_result.returncode != 0:
            return {
                'error': 'Ошибка компиляции TypeScript:\n' + compile_result.stderr
            }

        # Запускаем скомпилированный JavaScript с помощью Node.js
        run_result = subprocess.run(
            ['node', js_file_name],
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
        return {'error': 'TypeScript компилятор (tsc) или Node.js не найдены. Убедитесь, что они установлены и доступны в PATH.'}
    except subprocess.TimeoutExpired as e:
        return {'error': f'Операция ({e.cmd[0]}) превысила лимит времени. (Таймаут: 15с на компиляцию, 10с на выполнение)'}
    except Exception as e:
        return {'error': f'Внутренняя ошибка сервера: {e}'}
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

