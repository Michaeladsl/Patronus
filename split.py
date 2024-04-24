import re
import sys
import json
import pyte
import os

def split_file(input_dir, output_dir):
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.cast'):
                process_cast_file(os.path.join(root, file), output_dir)

def process_cast_file(input_file_path, output_dir):
    trivial_commands = {'cd', 'ls', 'ls -la', 'nano', 'vi'}
    try:
        with open(input_file_path, 'r') as file:
            lines = file.readlines()
    except IOError as e:
        print(f"Error: Could not read file '{input_file_path}'. {e}")
        return
    regex_pattern = r';[\w,\d,-,_,\.]+@[\w,-.\d]+:'
    command_prompt_regex = r'└─\$'
    screen = pyte.Screen(80, 24)
    stream = pyte.Stream(screen)
    json_line = lines[0].strip()
    try:
        json_data = json.loads(json_line)
    except json.JSONDecodeError:
        print(f"Error: The first line is not valid JSON in file '{input_file_path}'")
        return
    part_index = 0
    current_file_content = []
    start_time = None
    command_name = None
    for line in lines[1:]:
        data = json.loads(line.strip())
        stream.feed(data[2])
        current_display = "\n".join(screen.display)
        if re.search(regex_pattern, line):
            if current_file_content and command_name:
                if not is_trivial_command(command_name, trivial_commands):
                    filename = os.path.join(output_dir, generate_filename(clean_filename(command_name), part_index))
                    write_segment(filename, [json_line] + current_file_content)
                    part_index += 1
                current_file_content = []
                command_name = None
            start_time = None
        adjusted_line = adjust_time(line, start_time)
        if adjusted_line:
            if start_time is None:
                start_time = adjusted_line[0]
            current_file_content.append(json.dumps([adjusted_line[0] - start_time, data[1], data[2]]))
        if re.search(command_prompt_regex, current_display):
            command_name = extract_command(current_display)
    if current_file_content and command_name and not is_trivial_command(command_name, trivial_commands):
        filename = os.path.join(output_dir, generate_filename(clean_filename(command_name), part_index))
        write_segment(filename, [json_line] + current_file_content)

def adjust_time(line, start_time):
    parts = json.loads(line.strip())
    original_time = float(parts[0])
    return original_time, parts[1], parts[2]

def write_segment(filename, content):
    with open(filename, 'w') as new_file:
        new_file.write('\n'.join(content))
    print(f"Created file: {filename}")

def extract_command(display):
    lines = display.split('\n')
    for line in lines[::-1]:
        if '└─$' in line:
            command = line.split('└─$')[-1].strip()
            return command.replace(' ', '_')
    return "initial"

def clean_filename(command_name):
    command_name = re.sub(r'(-u_\S+|-p_\S+|-H_\S+)', '', command_name)
    command_name = re.sub(r'[^a-zA-Z0-9_]', '_', command_name)
    return command_name

def generate_filename(command_name, part_index):
    base_name = f"{command_name}.cast"
    if len(base_name) > 255:
        base_name = base_name[:250] + ".cast"
    return base_name

def is_trivial_command(command, trivial_commands):
    return command.split('_')[0] in trivial_commands

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(script_dir, 'static', 'redacted_full')
    output_dir = os.path.join(script_dir, 'static', 'splits')
    split_file(input_dir, output_dir)
