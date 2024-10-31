import argparse
import subprocess
import os
import sys
import shutil

def make_script_executable(script_path):
    if not os.access(script_path, os.X_OK):
        os.chmod(script_path, os.stat(script_path).st_mode | 0o111)

def find_script_path(script_name):
    venv_root = sys.prefix  
    script_path = os.path.join(venv_root, script_name)
    if not os.path.exists(script_path):
        raise FileNotFoundError(f"Script not found at {script_path}")
    return script_path

def initialize_patronus_directory():
    home_dir = os.path.expanduser("~")
    patronus_dir = os.path.join(home_dir, ".local", ".patronus")
    static_dir = os.path.join(patronus_dir, "static")

    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
        print(f"Created directory: {static_dir}")

        package_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
        if os.path.exists(package_static_dir):
            shutil.copytree(package_static_dir, static_dir, dirs_exist_ok=True)
            print(f"Copied static files to {static_dir}")

    return static_dir

def start_flask_server_in_tmux(static_dir):
    flask_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server.py')
    tmux_command = f"tmux new-session -d -s flask_server 'python3 {flask_script_path}'"
    subprocess.run(tmux_command, shell=True, check=True)

def run_script(script_name, args):
    if script_name == 'configure.sh':
        full_script_path = find_script_path(script_name)
    else:
        script_directory = os.path.dirname(os.path.abspath(__file__))
        full_script_path = os.path.join(script_directory, script_name)

    make_script_executable(full_script_path)
    command = [full_script_path] + args if script_name.endswith('.sh') else ['python3', full_script_path] + args
    subprocess.run(command, check=True)

def remove_gitkeep_files(static_dir):
    directories = ['redacted_full', 'full', 'splits']
    for dir_path in directories:
        full_path = os.path.join(static_dir, dir_path, '.gitkeep')
        if os.path.exists(full_path):
            os.remove(full_path)
            print(f"Removed .gitkeep from {full_path}")

def nuke_directories(static_dir):
    directories = ['full', 'redacted_full', 'splits']
    for dir_path in directories:
        full_path = os.path.join(static_dir, dir_path)
        if os.path.exists(full_path):
            for item in os.listdir(full_path):
                item_path = os.path.join(full_path, item)
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            print(f"Nuked all contents from {full_path}")

def main():
    static_dir = initialize_patronus_directory()

    parser = argparse.ArgumentParser(description="Patronus: A central command script for running multiple utility scripts.")
    parser.add_argument('mode', nargs='?', choices=['on', 'off'], help='Mode for running configuration.sh. Use "on" to run configuration.sh or "off" to run configuration.sh --undo.')
    parser.add_argument('--nuke', action='store_true', help='Erase all contents from the static directories')
    args = parser.parse_args()

    if args.mode:
        if args.mode == 'on':
            run_script('configure.sh', [])
        elif args.mode == 'off':
            run_script('configure.sh', ['--undo'])
        return

    if args.nuke:
        nuke_directories(static_dir)
        return 

    remove_gitkeep_files(static_dir)
    start_flask_server_in_tmux(static_dir)
    print("Server Started: http://127.0.0.1:8005")
    scripts_to_run = ['redact.py', 'split.py', 'edit.py']
    for script in scripts_to_run:
        run_script(script, [static_dir])

if __name__ == "__main__":
    main()
