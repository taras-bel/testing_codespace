# python_exec.py
import subprocess
import os
import tempfile

def execute_python(code):
    try:
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as f:
            f.write(code.encode())
            f.close()
            result = subprocess.run(
                ['python', f.name],
                capture_output=True,
                text=True,
                timeout=10
            )
            os.unlink(f.name)
            
            if result.returncode != 0:
                return {
                    'error': f'Python execution failed with return code {result.returncode}',
                    'output': result.stderr
                }
            return {'output': result.stdout}
    except subprocess.TimeoutExpired:
        return {'error': 'Execution timed out'}
    except Exception as e:
        return {'error': str(e)}