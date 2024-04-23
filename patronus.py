import argparse
import subprocess
import os

def run_script(script_name, args):
    """Run the specified script with additional arguments."""
    script_directory = os.path.dirname(os.path.abspath(__file__))
    full_script_path = os.path.join(script_directory, script_name)
    
    if script_name.endswith('.sh'):
        if not os.access(full_script_path, os.X_OK):
            os.chmod(full_script_path, os.stat(full_script_path).st_mode | 0o111)
        command = [full_script_path] + args
    else:
        command = ['python3', full_script_path] + args
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_name}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Patronus: A central command script for running multiple utility scripts.")
    parser.add_argument('tools', nargs='?', default='redact,split,server',
                        help='Comma-separated list of tools to run (redact, split, server, config). Defaults to running redact.py, split.py, and server.py in that order.')
    parser.add_argument('args', nargs=argparse.REMAINDER, help='Additional arguments to pass to the scripts')

    args = parser.parse_args()
    tools_to_run = args.tools.split(',')

    script_map = {
        'redact': 'redact.py',
        'split': 'split.py',
        'server': 'server.py',
        'config': 'configure.sh'
    }

    for tool in tools_to_run:
        script = script_map.get(tool.strip())
        if script:
            print(f"Running {script} with arguments {args.args}")
            run_script(script, args.args)
        else:
            print(f"Warning: No script found for tool '{tool}'")

if __name__ == "__main__":
    main()
