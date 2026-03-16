import argparse
import subprocess
import os
import shutil

def make_script_executable(script_path):
    if not os.access(script_path, os.X_OK):
        os.chmod(script_path, os.stat(script_path).st_mode | 0o111)

def check_and_install_asciinema():
    try:
        subprocess.run(['asciinema', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except FileNotFoundError:
        print('\033[91mAsciinema is not installed. Installing...\033[0m')
        subprocess.run(['sudo', 'apt', 'install', '-y', 'asciinema'])
        print('\033[92mAsciinema installed successfully.\033[0m')

def start_flask_server_in_tmux():
    script_directory = os.path.dirname(os.path.abspath(__file__))
    flask_script_path = os.path.join(script_directory, 'server.py')

    check_session_command = "tmux has-session -t flask_server 2>/dev/null"
    result = subprocess.run(check_session_command, shell=True)
    # FIX: original didn't check if session already existed — would crash on re-run
    if result.returncode == 0:
        print("flask_server tmux session already active")
        return

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
            item_path = os.path.join(full_path, item)
            # FIX: original used os.remove(item) / shutil.rmtree(item) — missing full path,
            # which would cause FileNotFoundError unless run from that exact directory
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        print(f"Nuked all contents from {full_path}")

# FIX: README claims `python3 patronus.py redact,split,server,config` works,
# but the old argparse only accepted 'on'/'off' — anything else raised an error.
# Implemented properly as a --run flag with comma-separated component names.
VALID_COMPONENTS = {
    'redact': 'redact.py',
    'split':  'split.py',
    'server': None,   # handled specially
    'edit':   'edit.py',
    'config': 'configure.sh',
}

def run_components(components_str):
    import sys
    requested = [c.strip().lower() for c in components_str.split(',')]
    unknown = [c for c in requested if c not in VALID_COMPONENTS]
    if unknown:
        print(f"[patronus] Unknown component(s): {', '.join(unknown)}")
        print(f"[patronus] Valid options: {', '.join(VALID_COMPONENTS.keys())}")
        sys.exit(1)
    for component in requested:
        script = VALID_COMPONENTS[component]
        if component == 'server':
            print("[patronus] Starting Flask server in tmux…")
            start_flask_server_in_tmux()
            print("Server started: http://127.0.0.1:8005")
        elif script:
            print(f"[patronus] Running {component}…")
            run_script(script, [])


def main():
    parser = argparse.ArgumentParser(
        description="Patronus: capture, redact, and review pentest terminal recordings.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 patronus.py on                          # Start recording
  python3 patronus.py off                         # Stop recording
  python3 patronus.py                             # Process + launch web UI
  python3 patronus.py --run redact,split,server   # Run specific components
  python3 patronus.py --run server                # Just restart the server
  python3 patronus.py --nuke                      # Wipe all recording data
        """
    )
    parser.add_argument(
        'mode',
        nargs='?',
        choices=['on', 'off'],
        help='Turn recording on or off'
    )
    parser.add_argument(
        '--run',
        metavar='COMPONENTS',
        help=(
            'Comma-separated list of components: redact, split, server, edit, config. '
            'Example: --run redact,split,server'
        )
    )
    parser.add_argument(
        '--nuke',
        action='store_true',
        help='Erase all contents from the recording directories'
    )
    args = parser.parse_args()

    if args.mode:
        if args.mode == 'on':
            check_and_install_asciinema()
        run_script('configure.sh', ['--undo'] if args.mode == 'off' else [])
        return

    if args.nuke:
        confirm = input("This will delete ALL recordings. Type 'yes' to confirm: ")
        if confirm.strip().lower() == 'yes':
            nuke_directories()
        else:
            print("Aborted.")
        return

    if args.run:
        remove_gitkeep_files()
        run_components(args.run)
        return

    # Default: run everything
    remove_gitkeep_files()
    start_flask_server_in_tmux()
    print("Server started: http://127.0.0.1:8005")
    for script in ['redact.py', 'split.py', 'edit.py']:
        run_script(script, [])


if __name__ == "__main__":
    main()
