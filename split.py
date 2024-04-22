import os
import pyte
import json
import re
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))

input_dir = os.path.join(script_dir, 'static', 'redacted_full')
output_dir = os.path.join(script_dir, 'static', 'splits')

def load_cast_file(filename):
    with open(filename, 'r') as file:
        first_line = file.readline().strip()
        try:
            header = json.loads(first_line)
        except json.JSONDecodeError:
            raise ValueError(f"Error decoding JSON from the header in file {filename}")
        
        events = []
        for line in file:
            stripped_line = line.strip()
            if stripped_line: 
                try:
                    event = json.loads(stripped_line)
                    events.append(event)
                except json.JSONDecodeError:
                    continue  
    if not isinstance(header, dict):
        raise TypeError(f"Expected header to be a dictionary, got {type(header)} in file {filename}")

    return header, events

def extract_ansi_and_text(text):
    ansi_escape = re.compile(r'(\x1b\[[0-9;]*[mKDHCUJ])|(\x1b\[?\?\d+l\x1b>)|(\x1b\[?\?\d+l\r\r\n)')
    parts = ansi_escape.split(text)
    ansi_positions = []
    clean_text = ""
    last_pos = 0

    for part in parts:
        if part is not None and ansi_escape.match(part):
            ansi_positions.append((last_pos, part))
        elif part is not None:
            clean_text += part
            last_pos += len(part)

    return clean_text, ansi_positions

def remove_ansi(text):
    ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', text)


def find_splits(events, debug=False):
    split_indices = []
    pattern = re.compile(r'\r\r(?:\\u001b\]0;.*)?$')
    
    for i, event in enumerate(events):
        if event[1] == "o":
            clean_text, _ = extract_ansi_and_text(event[2])
            if pattern.search(clean_text):
                split_indices.append(i)

    return split_indices

def extract_command(screen):
    for line in screen.display:
        cleaned_line, _ = extract_ansi_and_text(line)
        if '└─$' in cleaned_line:
            command_part = cleaned_line.split('└─$', 1)[1].strip()
            if command_part:
                command_part = remove_ansi(command_part).replace(' ', '_')
                command_part = re.sub(r'(-u_\S+|-p_\S+|-H_\S+)', '', command_part)
                return command_part
    return "unknown"

def check_content_trivial(screen):
    return all('└─$' not in line for line in screen.display)

def write_new_cast_file(header, events, filename, screen, debug=False):
    if check_content_trivial(screen):
        if debug:
            print(f"Skipping writing trivial file: {filename}")
        return False

    with open(filename, 'w') as file:
        json.dump(header, file)
        file.write('\n')
        for event in events:
            json.dump(event, file)
            file.write('\n')
    if debug:
        print(f"File written: {filename}")
    return True

def adjust_timestamps_and_header(events, original_start_time):
    if not events:
        return [], None
    
    adjusted_events = []
    start_time = events[0][0]
    for event in events:
        adjusted_time = event[0] - start_time
        adjusted_events.append([adjusted_time] + event[1:])

    new_header = {
        "version": 2,
        "width": 236,
        "height": 50,
        "timestamp": start_time,
        "env": {"SHELL": "/usr/bin/zsh", "TERM": "xterm-256color"}
    }
    return adjusted_events, new_header

def split_cast_file(directory, debug=False):
    files = os.listdir(directory)
    for file in files:
        original_file = os.path.join(directory, file)
        header, events = load_cast_file(original_file)
        splits = find_splits(events, debug)
        original_start_time = header['timestamp']
        last_index = 0

        for i, split_index in enumerate(splits + [len(events)]):
            segment_events = events[last_index:split_index]
            screen = pyte.Screen(80, 24)
            stream = pyte.Stream(screen)
            for event in segment_events:
                if event[1] == "o":
                    stream.feed(event[2])

            if check_content_trivial(screen):
                last_index = split_index
                continue

            adjusted_segment_events, new_header = adjust_timestamps_and_header(segment_events, original_start_time)
            command_name = extract_command(screen)
            filename_safe_command = re.sub(r'[^\w\-_\. ]', '_', command_name)[:50]
            new_filename = os.path.join(output_dir, f"{filename_safe_command}_{i+1}.cast")
            write_new_cast_file(new_header, adjusted_segment_events, new_filename, screen, debug)
            last_index = split_index

if __name__ == "__main__":
    debug_flag = '--debug' in sys.argv
    split_cast_file(input_dir, debug=debug_flag)