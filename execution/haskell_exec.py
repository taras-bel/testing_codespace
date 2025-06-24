import subprocess
import os
import tempfile
import shutil

def execute_haskell(code):
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp()
        file_name = os.path.join(temp_dir, 'main.hs')
        exe_name = os.path.join(temp_dir, 'main')

        with open(file_name, 'w') as f:
            f.write(code)

        # Компилируем Haskell код с GHC
        compile_result = subprocess.run(
            ['ghc', file_name, '-o', exe_name],
            capture_output=True,
            text=True,
            cwd=temp_dir,
            timeout=20 # Компиляция Haskell может быть долгой
        )

        if compile_result.returncode != 0:
            return {
                'error': 'Ошибка компиляции Haskell:\n' + compile_result.stderr
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
        return {'error': 'Haskell компилятор (ghc) не найден. Убедитесь, что Haskell установлен и доступен в PATH.'}
    except subprocess.TimeoutExpired as e:
        return {'error': f'Операция ({e.cmd[0]}) превысила лимит времени. (Таймаут: 20с на компиляцию, 10с на выполнение)'}
    except Exception as e:
        return {'error': f'Внутренняя ошибка сервера: {e}'}
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

