import subprocess
import os
import tempfile

def execute_csharp(code):
    try:
        temp_dir = tempfile.mkdtemp()
        file_name = os.path.join(temp_dir, 'Program.cs')
        exe_name = os.path.join(temp_dir, 'program')
        
        with open(file_name, 'w') as f:
            f.write(code)
        
        compile_result = subprocess.run(
            ['mcs', file_name, '-out:' + exe_name],
            capture_output=True,
            text=True
        )
        
        if compile_result.returncode != 0:
            return {
                'error': 'Compilation failed',
                'output': compile_result.stderr
            }
        
        run_result = subprocess.run(
            ['mono', exe_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if run_result.returncode != 0:
            return {
                'error': f'Execution failed with return code {run_result.returncode}',
                'output': run_result.stderr
            }
            
        return {'output': run_result.stdout}
    except subprocess.TimeoutExpired:
        return {'error': 'Execution timed out'}
    except Exception as e:
        return {'error': str(e)}
    finally:
        if 'temp_dir' in locals():
            for file in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, file))
            os.rmdir(temp_dir)