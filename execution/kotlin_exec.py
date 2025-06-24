import subprocess
import os
import tempfile
import shutil

def execute_kotlin(code):
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp()
        file_name = os.path.join(temp_dir, 'Main.kt') # Kotlin по соглашению
        jar_name = os.path.join(temp_dir, 'main.jar')

        # Обернем код в стандартную main функцию, если ее нет
        # Это упрощенный подход, так как пользователь может ввести полный класс
        kotlin_code_wrapped = f"""
fun main() {{
{code}
}}
"""
        with open(file_name, 'w') as f:
            f.write(kotlin_code_wrapped)

        # Компилируем Kotlin код в JAR
        compile_result = subprocess.run(
            ['kotlinc', file_name, '-include-runtime', '-d', jar_name],
            capture_output=True,
            text=True,
            cwd=temp_dir,
            timeout=20 # Компиляция Kotlin может занять время
        )

        if compile_result.returncode != 0:
            return {
                'error': 'Ошибка компиляции Kotlin:\n' + compile_result.stderr
            }

        # Запускаем JAR файл
        run_result = subprocess.run(
            ['java', '-jar', jar_name],
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
        return {'error': 'Kotlin компилятор (kotlinc) или Java (java) не найдены. Убедитесь, что они установлены и доступны в PATH.'}
    except subprocess.TimeoutExpired as e:
        return {'error': f'Операция ({e.cmd[0]}) превысила лимит времени. (Таймаут: 20с на компиляцию, 10с на выполнение)'}
    except Exception as e:
        return {'error': f'Внутренняя ошибка сервера: {e}'}
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

