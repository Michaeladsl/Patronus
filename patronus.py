import argparse
import subprocess
import os

def make_script_executable(script_path):
    if not os.access(script_path, os.X_OK):
        os.chmod(script_path, os.stat(script_path).st_mode | 0o111)

#def check_and_install_asciinema():
 #   try:
  #      subprocess.run(['asciinema', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
   # except FileNotFoundError:
    #    print('\033[91mAsciinema is not installed. Installing...\033[0m')
     #   subprocess.run(['sudo', 'apt', 'install', '-y', 'asciinema'])
      #  print('\033[92mAsciinema installed successfully.\033[0m')

def start_flask_server_in_tmux():
    script_directory = os.path.dirname(os.path.abspath(__file__))
    flask_script_path = os.path.join(script_directory, 'server.py')
    tmux_command = f"tmux new-session -d -s flask_server 'python3 {flask_script_path}'"
    subprocess.run(tmux_command, shell=True, check=True)

def run_script(script_name, args):
    script_directory = os.path.dirname(os.path.abspath(__file__))
    full_script_path = os.path.join(script_directory, script_name)
    make_script_executable(full_script_path)
    command = [full_script_path] + args if script_name.endswith('.sh') else ['python3', full_script_path] + args
    subprocess.run(command, check=True)
    
def remove_gitkeep_files():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    directories = ['static/redacted_full', 'static/full', 'static/splits']
    for dir_path in directories:
        full_path = os.path.join(base_dir, dir_path, '.gitkeep')
        if os.path.exists(full_path):
            os.remove(full_path)

def nuke_directories():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    directories = ['static/full', 'static/redacted_full', 'static/splits']
    for dir_path in directories:
        full_path = os.path.join(base_dir, dir_path)
        for item in os.listdir(full_path):
            if os.path.isfile(item) or os.path.islink(item):
                os.remove(item)
            elif os.path.isdir(item):
                shutil.rmtree(item)
        print(f"Nuked all contents from {full_path}")

def main():
    parser = argparse.ArgumentParser(description="Patronus: A central command script for running multiple utility scripts.")
    parser.add_argument('mode', nargs='?', choices=['on', 'off'], help='Mode for running configuration.sh. Use "on" to run configuration.sh or "off" to run configuration.sh --undo.')
    parser.add_argument('--nuke', action='store_true', help='Erase all contents from the static directories')
    args = parser.parse_args()

    if args.mode:
        if args.mode == 'on':
            #check_and_install_asciinema()
        run_script('configure.sh', ['--undo'] if args.mode == 'off' else [])
        return

    if args.nuke:
        nuke_directories()
        return 

    remove_gitkeep_files()
    start_flask_server_in_tmux()
    print("Server Started: http://127.0.0.1:8005")
    scripts_to_run = ['redact.py', 'split.py', 'edit.py']
    for script in scripts_to_run:
        run_script(script, [])

if __name__ == "__main__":
    main()
