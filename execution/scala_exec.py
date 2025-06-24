import subprocess
import os
import tempfile
import shutil

def execute_scala(code):
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp()
        file_name = os.path.join(temp_dir, 'Main.scala')
        class_name = "Main" # Имя класса, если он обернут

        # Обернем код в объект Main, если его нет, для запуска
        scala_code_wrapped = f"""
object Main {{
  def main(args: Array[String]): Unit = {{
{code}
  }}
}}
"""
        with open(file_name, 'w') as f:
            f.write(scala_code_wrapped)

        # Компилируем Scala код
        compile_result = subprocess.run(
            ['scalac', file_name],
            capture_output=True,
            text=True,
            cwd=temp_dir,
            timeout=20 # Компиляция Scala может быть долгой
        )

        if compile_result.returncode != 0:
            return {
                'error': 'Ошибка компиляции Scala:\n' + compile_result.stderr
            }

        # Запускаем скомпилированный класс Scala
        run_result = subprocess.run(
            ['scala', class_name],
            capture_output=True,
            text=True,
            cwd=temp_dir,
            timeout=10
        )

        if run_result.returncode != 0:
            return {
                'error': f'Ошибка выполнения (код: {run_result.returncode})\n{run_result.stderr}',
                'output': run_result.stdout
            }

        return {'output': run_result.stdout}
    except FileNotFoundError:
        return {'error': 'Scala компилятор (scalac) или среда выполнения (scala) не найдены. Убедитесь, что Scala установлен и доступен в PATH.'}
    except subprocess.TimeoutExpired as e:
        return {'error': f'Операция ({e.cmd[0]}) превысила лимит времени. (Таймаут: 20с на компиляцию, 10с на выполнение)'}
    except Exception as e:
        return {'error': f'Внутренняя ошибка сервера: {e}'}
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

