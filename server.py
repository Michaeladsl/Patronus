from flask import Flask, render_template_string, request, jsonify
import subprocess
import os
import shutil
import psutil
import json

app = Flask(__name__)

from flask import request

def get_cast_files():
    static_dir = os.path.join(app.root_path, 'static', 'splits')
    files = [f for f in os.listdir(static_dir) if f.endswith('.cast')]
    
    mappings_file = os.path.join(static_dir, 'file_timestamp_mapping.json')
    timestamps = {}
    with open(mappings_file, 'r') as f:
        mappings = json.load(f)
        timestamps = {file_path: timestamp for file_path, timestamp in mappings.items() if timestamp is not None}
    
    if request.path.startswith('/command/'):
        sorted_files = sorted(files, key=lambda x: timestamps.get(os.path.join(static_dir, x), ''))
    else:
        sorted_files = sorted(files)

    tools = sorted(set(f.split('_')[0] for f in sorted_files))
    files_dict = {tool: [f for f in sorted_files if f.split('_')[0] == tool] for tool in tools}
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
        total_size = sum(os.path.getsize(os.path.join(dirpath, filename)) for dirpath, _, filenames in os.walk(path) for filename in filenames)
        return total_size / (1024 ** 3)

    recordings_size = (
        get_directory_size(os.path.join(app.root_path, "static", "splits")) +
        get_directory_size(os.path.join(app.root_path, "static", "redacted_full")) +
        get_directory_size(os.path.join(app.root_path, "static", "full"))
    )
    return total_free_gb, recordings_size

def load_favorites():
    favorites_file = os.path.join(app.root_path, 'favorites.txt')
    favorites = {}
    if os.path.exists(favorites_file):
        with open(favorites_file, 'r') as f:
            for line in f:
                filename = line.strip()
                favorites[filename] = True
    return favorites

def save_favorites(favorites):
    favorites_file = os.path.join(app.root_path, 'favorites.txt')
    with open(favorites_file, 'w') as f:
        for filename in favorites:
            f.write(filename + '\n')

favorites = load_favorites()

@app.route('/')
def index():
    tools, files_dict = get_cast_files()
    free_gb, recordings_size = get_disk_usage()
    return render_template_string(HTML_TEMPLATE, tools=tools, files_dict=files_dict, free_gb=free_gb, recordings_size=recordings_size, favorites=favorites)

@app.route('/command/<command>')
def command_page(command):
    _, files_dict = get_cast_files()
    command_files = files_dict.get(command, [])
    return render_template_string(COMMAND_TEMPLATE, command=command, command_files=command_files, favorites=favorites)

@app.route('/favorites')
def favorites_page():
    _, files_dict = get_cast_files()
    favorites_files = [file for file in favorites if file in sum(files_dict.values(), [])]
    return render_template_string(COMMAND_TEMPLATE, command="Favorites", command_files=favorites_files, favorites=favorites)

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

@app.route('/edit', methods=['POST'])
def edit_file_name():
    data = request.get_json()
    old_file_name = data['old_file']
    new_file_name = data['new_file']
    old_file_path = os.path.join(app.root_path, 'static', 'splits', old_file_name)
    new_file_path = os.path.join(app.root_path, 'static', 'splits', new_file_name)
    try:
        os.rename(old_file_path, new_file_path)
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

@app.route('/toggle_favorite', methods=['POST'])
def toggle_favorite():
    data = request.json
    file = data['file']
    if file in favorites:
        favorites.pop(file)
    else:
        favorites[file] = True
    save_favorites(favorites)
    return jsonify(success=True)



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
            margin: 0 auto 20px;
            width: 95%;
            text-align: center;
        }
        .favorite {
            float: right;
            margin-right: 20px;
            cursor: pointer;
            font-size: 24px;
        }
        .favorites-button {
            background-color: #4ecca3;
            border: none;
            color: white;
            padding: 10px;
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
        .favorites-button:hover {
            background-color: #3ba888;
        }
    </style>
</head>
<body>
    <div class="disk-meter">
        Free Space: {{ free_gb|round(2) }} GB, Recordings Size: {{ recordings_size|round(2) }} GB
    </div>
    <a class="favorites-button" href="/favorites">Favorites</a>
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
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 18px;
            margin: 10px auto;
            cursor: pointer;
            border-radius: 5px;
            width: 95%;
            box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
            transition: 0.3s;
        }
        .edit-icon, .save-btn, .exit-btn {
            margin-left: 5px;
            cursor: pointer;
            visibility: hidden; /* Initially hidden */
        }
        .file-name:hover .edit-icon {
            visibility: visible;
        }
        .favorite {
            margin-left: 35px;
            cursor: pointer;
            font-size: 28px;
        }
        .dropdown-content {
            display: none;
            width: 95%;
            margin: 10px auto;
            background-color: #16213e;
            color: white;
            padding: 15px;
            border: 1px solid #4ecca3;
            border-radius: 5px;
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

        .file-name:hover {
            box-shadow: 0 8px 16px 0 rgba(0,0,0,0.3);
        }
        .redact-controls, .delete-controls, .edit-controls {
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
        .delete-button, .edit-button {
            background-color: #E94560; /* Red color */
            padding: 10px 15px;
            margin-top: 5px;
        }
        .delete-button:hover, .edit-button:hover {
            background-color: #D8315B; /* Slightly darker red on hover */
        }
        
        .exit-btn:hover {
            background-color: #E94560;
        }
    
        .editing span {
            outline: 2px solid #4ecca3;
        }
        .save-btn {
            color: green;
            font-size: 28px;
            margin-right: 5px;
        }

        .exit-btn {
            color: red;
        }
    </style>
</head>
<body>
    {% for file in command_files %}
    <div class="file-name" id="file-{{ loop.index }}" onclick="toggleDisplay('{{ file }}', event)">
        <span id="name-{{ file }}">{{ file.split('.cast')[0] }}</span>.cast
        <i class="edit-icon" onclick="enableEdit('{{ file }}', event)">🖊️</i>
        <i class="save-btn" onclick="confirmSave('{{ file }}', event)" style="visibility: hidden;">&#10004;</i>
        <i class="exit-btn" onclick="exitEditMode('{{ file }}', event)" style="visibility: hidden;">&#10006;</i>
        {% if file in favorites %}
            <span class="favorite" onclick="toggleFavorite('{{ file }}', event)">&#9733;</span>
        {% else %}
            <span class="favorite" onclick="toggleFavorite('{{ file }}', event)">&#9734;</span>
        {% endif %}
    </div>
    <div id="demo-{{ file }}" class="dropdown-content">
        <div class="redact-controls">
            <input type="text" id="redact-word-{{ file }}" placeholder="Word to Redact">
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
                
                // Get current timestamp
                var timestamp = new Date().getTime();
                
                // Use timestamp in URL to ensure fresh content
                AsciinemaPlayer.create('/static/splits/' + filename + '?_=' + timestamp, player);
            }
        }

        
        function enableEdit(file, event) {
            event.stopPropagation();
            var nameSpan = document.getElementById('name-' + file);
            nameSpan.contentEditable = true;
            nameSpan.focus();
            var parentDiv = nameSpan.closest('.file-name');
            var editIcon = parentDiv.querySelector('.edit-icon');
            var saveIcon = parentDiv.querySelector('.save-btn');
            var exitIcon = parentDiv.querySelector('.exit-btn'); // New exit button
            editIcon.style.visibility = 'hidden'; // Hide edit button
            saveIcon.style.visibility = 'visible'; // Show save button
            exitIcon.style.visibility = 'visible'; // Show exit button
        }

        function confirmSave(file, event) {
            event.stopPropagation();
            if (confirm("Are you sure you want to save the changes?")) {
                saveEdit(file, event);
            }
        }

        function saveEdit(file, event) {
            var nameSpan = document.getElementById('name-' + file);
            var newName = nameSpan.textContent + '.cast'; // Append the extension
            fetch('/edit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({old_file: file, new_file: newName})
            }).then(response => {
                if (response.ok) {
                    return response.json();
                }
                throw new Error('Failed to edit file name.');
            }).then(data => {
                if (data.success) {
                    nameSpan.contentEditable = false;
                    var saveBtn = document.querySelector('.save-btn');
                    saveBtn.style.visibility = 'hidden'; // Hide save button after save
                    alert('File name updated successfully!');
                } else {
                    alert('Failed to edit the file name.');
                }
            }).catch(error => {
                console.error('Error:', error);
                alert(error.message);
            });
        }

        function exitEditMode(file, event) {
            event.stopPropagation();
            var nameSpan = document.getElementById('name-' + file);
            nameSpan.contentEditable = false;
            var parentDiv = nameSpan.closest('.file-name');
            var editIcon = parentDiv.querySelector('.edit-icon');
            var saveIcon = parentDiv.querySelector('.save-btn');
            var exitIcon = parentDiv.querySelector('.exit-btn'); // New exit button
            editIcon.style.visibility = 'visible'; // Show edit button
            saveIcon.style.visibility = 'hidden'; // Hide save button
            exitIcon.style.visibility = 'hidden'; // Hide exit button
            nameSpan.textContent = file.split('.cast')[0];
        }

        function toggleFavorite(file) {
            fetch('/toggle_favorite', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({file: file})
            }).then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.location.reload(); // Reload the page to reflect changes
                } else {
                    console.error('Failed to toggle favorite status');
                }
            }).catch(error => {
                console.error('Error:', error);
            });
        }

        function redactAndReload(filename) {
            var wordInput = document.getElementById('redact-word-' + filename);
            var word = wordInput.value;
            fetch('/redact', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({word: word, file: filename})
            }).then(response => response.json())
            .then(data => {
                if (data.success) {
                    var timestamp = new Date().getTime(); // Get current timestamp
                    var playerContainer = document.getElementById('demo-' + filename);
                    playerContainer.innerHTML = ''; // Clear existing content
                    wordInput.value = '';

                    // Recreate the player with a new URL including the timestamp
                    setTimeout(() => {
                        playerContainer.style.display = 'block';
                        AsciinemaPlayer.create('/static/splits/' + filename + '?_=' + timestamp, playerContainer);
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
