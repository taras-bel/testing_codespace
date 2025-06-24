import subprocess
import os
import tempfile

def execute_javascript(code):
    try:
        with tempfile.NamedTemporaryFile(suffix='.js', delete=False) as f:
            f.write(code.encode())
            f.close()
            result = subprocess.run(
                ['node', f.name],
                capture_output=True,
                text=True,
                timeout=10
            )
            os.unlink(f.name)
            
            if result.returncode != 0:
                return {
                    'error': f'JavaScript execution failed with return code {result.returncode}',
                    'output': result.stderr
                }
            return {'output': result.stdout}
    except subprocess.TimeoutExpired:
        return {'error': 'Execution timed out'}
    except Exception as e:
        return {'error': str(e)}