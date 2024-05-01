from flask import Flask, render_template_string, request, jsonify
import subprocess
import os
import shutil
import psutil


app = Flask(__name__)

def get_cast_files():
    static_dir = os.path.join(app.root_path, 'static', 'splits')
    files = [f for f in os.listdir(static_dir) if f.endswith('.cast')]
    tools = sorted(set(f.split('_')[0] for f in files))
    files_dict = {tool: [f for f in files if f.split('_')[0] == tool] for tool in tools}
    return tools, files_dict

def get_disk_usage():
    partitions = psutil.disk_partitions(all=True)

    total_free_gb = 0
    total_recordings_size = 0

    for partition in partitions:
        try:
            disk_usage = psutil.disk_usage(partition.mountpoint)
            free_gb = disk_usage.free / (1024 ** 3)
            total_free_gb += free_gb
        except PermissionError:
            pass

    def get_directory_size(path):
        total_size = sum(
            os.path.getsize(os.path.join(dirpath, filename))
            for dirpath, _, filenames in os.walk(path)
            for filename in filenames
        )
        return total_size / (1024 ** 3)

    recordings_size = (
        get_directory_size(os.path.join(app.root_path, "static", "splits"))
        + get_directory_size(os.path.join(app.root_path, "static", "redacted_full"))
        + get_directory_size(os.path.join(app.root_path, "static", "full"))
    )

    return total_free_gb, recordings_size

@app.route('/')
def index():
    tools, files_dict = get_cast_files()
    free_gb, recordings_size = get_disk_usage()
    return render_template_string(HTML_TEMPLATE, tools=tools, files_dict=files_dict, free_gb=free_gb, recordings_size=recordings_size)

@app.route('/command/<command>')
def command_page(command):
    _, files_dict = get_cast_files()
    command_files = files_dict.get(command, [])
    return render_template_string(COMMAND_TEMPLATE, command=command, command_files=command_files)

@app.route('/redact', methods=['POST'])
def redact_text():
    data = request.json
    word = data['word']
    file_to_redact = os.path.join(app.root_path, 'static', 'splits', data['file'])
    subprocess.run(['python3', 'redact.py', '-w', word, '-f', file_to_redact])
    return jsonify(success=True)

@app.route('/delete', methods=['POST'])
def delete_file():
    data = request.json
    file_path = os.path.join(app.root_path, 'static', 'splits', data['file'])
    try:
        os.remove(file_path)
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Command Selection</title>
    <style>
        body { background-color: #000000; color: white; }
        .button {
            background-color: #16213e;
            border: 1px solid #4ecca3;
            color: white;
            padding: 15px;
            text-align: center;
            text-decoration: none;
            display: block;
            font-size: 18px;
            margin: 10px auto;  /* Centering the buttons */
            cursor: pointer;
            border-radius: 5px;
            width: 95%;
            box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
            transition: 0.3s;
        }
        .button:hover {
            box-shadow: 0 8px 16px 0 rgba(0,0,0,0.3);
        }
        .disk-meter {
            background-color: rgba(22, 33, 62, 0.8);
            color: white;
            padding: 10px;
            border-radius: 5px;
            font-size: 14px;
            margin: 0 auto 20px; /* Centering the disk meter and add space below */
            width: 95%;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="disk-meter">
        Free Space: {{ free_gb|round(2) }} GB, Recordings Size: {{ recordings_size|round(2) }} GB
    </div>
    {% for tool, count in files_dict.items() %}
    <div class="button" onclick="window.location.href='/command/{{ tool }}'">{{ tool }} ({{ count|length }})</div>
    {% endfor %}
</body>
</html>
'''

COMMAND_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Command Files - {{ command }}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='asciinema-player.css') }}">
    <style>
        body { background-color: #000000; color: white; }
        .file-name {
            background-color: #16213e;
            border: 1px solid #4ecca3;
            color: white;
            padding: 15px;
            text-align: center;
            text-decoration: none;
            display: block;
            font-size: 18px;
            margin: 10px auto;
            cursor: pointer;
            border-radius: 5px;
            width: 95%;
            box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
            transition: 0.3s;
        }
        
        .file-name, .dropdown-content {
            box-sizing: border-box; /* Include padding and border in the element's total width and height */
            width: 95%; /* Set the same width for both */
            margin: 10px auto; /* Center both elements with auto margins */
            background-color: #16213e;
            color: white;
            padding: 15px;
            border: 1px solid #4ecca3;
            border-radius: 5px;
            box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
            transition: 0.3s;
        }

        .file-name {
            cursor: pointer;
            display: block;
            font-size: 18px;
        }

        .dropdown-content {
            display: none; /* Initially hidden */
        }

        .file-name:hover {
            box-shadow: 0 8px 16px 0 rgba(0,0,0,0.3);
        }
        .redact-controls, .delete-controls {
            padding: 10px;
            display: block;
        }
        input[type="text"], button {
            padding: 5px;
            margin-right: 10px;
        }
        button {
            background-color: #4ecca3;
            border: none;
            cursor: pointer;
        }
        button:hover {
            background-color: #3ba888;
        }
        .delete-button {
            background-color: #E94560; /* Red color */
            padding: 10px 15px;
            margin-top: 5px;
        }
        .delete-button:hover {
            background-color: #D8315B; /* Slightly darker red on hover */
        }
    </style>
</head>
<body>
    {% for file in command_files %}
    <div class="file-name" onclick="toggleDisplay('{{ file }}')">{{ file }}</div>
    <div id="demo-{{ file }}" class="dropdown-content">
        <div class="redact-controls">
            <input type="text" id="redact-word-{{ file }}" placeholder="Word to redact">
            <button onclick="redactAndReload('{{ file }}')">Redact and Reload</button>
        </div>
        <div class="delete-controls">
            <button class="delete-button" onclick="deleteFile('{{ file }}')">Delete File</button>
        </div>
    </div>
    {% endfor %}
    <script src="{{ url_for('static', filename='asciinema-player.min.js') }}"></script>
    <script>
        function toggleDisplay(filename) {
            var player = document.getElementById('demo-' + filename);
            if (player.style.display === 'block') {
                player.style.display = 'none';
            } else {
                var allPlayers = document.getElementsByClassName('dropdown-content');
                for (var i = 0; i < allPlayers.length; i++) {
                    allPlayers[i].style.display = 'none';
                }
                player.style.display = 'block';
                AsciinemaPlayer.create('{{ url_for('static', filename='splits/') }}' + filename, player);
            }
        }
        function redactAndReload(filename) {
            var wordInput = document.getElementById('redact-word-' + filename);
            var word = wordInput.value;
            var redactButton = document.getElementById('redact-button-' + filename); // Assuming you have an ID for the button
            fetch('/redact', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({word: word, file: filename})
            }).then(response => response.json())
            .then(data => {
                if (data.success) {
                    
                    var timestamp = new Date().getTime();
                    var playerContainer = document.getElementById('demo-' + filename);
                    playerContainer.innerHTML = ''; // Clear existing content

                    
                    wordInput.value = '';
                    if (redactButton) redactButton.disabled = true;

                    
                    setTimeout(() => {
                        playerContainer.style.display = 'block';
                        AsciinemaPlayer.create('/static/splits/' + filename + '?_=' + timestamp, playerContainer);
                        if (redactButton) redactButton.disabled = false;
                    }, 1000); // Adjust the delay as needed
                }
            }).catch(error => {
                console.error('Error:', error);
            });
        }
        function deleteFile(filename) {
            if (confirm('Are you sure you want to delete this file?')) {
                fetch('/delete', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({file: filename})
                }).then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Reload the page to reflect changes
                        window.location.reload();
                    } else {
                        alert('Failed to delete the file.');
                    }
                }).catch(error => {
                    console.error('Error:', error);
                    alert('Error deleting the file.');
                });
            }
        }
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=False)
