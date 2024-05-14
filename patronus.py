import argparse
import subprocess
import os

def check_and_install_asciinema():
    try:
        subprocess.run(['asciinema', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except FileNotFoundError:
        print('\033[91mAsciinema is not installed. Installing...\033[0m')
        subprocess.run(['sudo', 'apt', 'install', '-y', 'asciinema'])
        print('\033[92mAsciinema installed successfully.\033[0m')


def run_script(script_name, args):
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

def remove_gitkeep_files():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    directories = ['static/redacted_full', 'static/full', 'static/splits']
    for dir_path in directories:
        full_path = os.path.join(base_dir, dir_path, '.gitkeep')
        if os.path.exists(full_path):
            os.remove(full_path)
            #print(f"Removed .gitkeep from {full_path}")

def nuke_directories():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    directories = ['static/full', 'static/redacted_full', 'static/splits']
    for dir_path in directories:
        full_path = os.path.join(base_dir, dir_path)
        for item in os.listdir(full_path):
            item_path = os.path.join(full_path, item)
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        print(f"Nuked all contents from {full_path}")

def main():
    parser = argparse.ArgumentParser(description="Patronus: A central command script for running multiple utility scripts.")
    parser.add_argument('mode', nargs='?', choices=['on', 'off'],
                        help='Mode for running configuration.sh. Use "on" to run configuration.sh or "off" to run configuration.sh --undo.')
    parser.add_argument('--nuke', action='store_true', help='Erase all contents from the static directories')

    args = parser.parse_args()

    if args.mode:
        if args.mode == 'on':
            check_and_install_asciinema()
        run_script('configure.sh', ['--undo'] if args.mode == 'off' else [])
        return

    if args.nuke:
        nuke_directories()
        return 

    remove_gitkeep_files()

    scripts_to_run = ['redact.py', 'split.py', 'edit.py', 'server.py']
    for script in scripts_to_run:
        run_script(script, [])

if __name__ == "__main__":
    main()
