from flask import Flask, render_template_string, request, jsonify
import subprocess
import os
import shutil
import psutil
import json
import re


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


def strip_ansi_sequences(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
        return re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', content)

def create_text_versions():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    static_dir = os.path.join(script_dir, 'static')
    text_dir = os.path.join(static_dir, 'text')

    os.makedirs(text_dir, exist_ok=True)

    splits_dir = os.path.join(static_dir, 'splits')
    for file in os.listdir(splits_dir):
        if file.endswith('.cast'):
            file_path = os.path.join(splits_dir, file)
            text_content = strip_ansi_sequences(file_path)
            text_file_path = os.path.join(text_dir, file + '.txt')
            with open(text_file_path, 'w') as f:
                f.write(text_content)

create_text_versions()



def search_index(query):
    text_dir = os.path.join(app.root_path, 'static', 'text')
    results = []
    for text_file in os.listdir(text_dir):
        if text_file.endswith('.txt'):
            with open(os.path.join(text_dir, text_file), 'r') as f:
                content = f.read()
                if query.lower() in content.lower():
                    results.append(text_file.replace('.txt', ''))
    return results


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
        get_directory_size(os.path.join(app.root_path, "static", "full")) +
        get_directory_size(os.path.join(app.root_path, "static", "text"))
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
    
    # Initialize variables for date grouping
    current_date = None
    files_with_dates = []

    # Loop through command files to group them by date
    for file in command_files:
        file_path = os.path.join(app.root_path, 'static', 'splits', file)
        timestamp = get_timestamp(file_path)
        date = timestamp.split()[0] if timestamp else None
        
        # Add date separator if new date is encountered
        if date != current_date:
            current_date = date
            files_with_dates.append(date)

        files_with_dates.append(file)

    return render_template_string(COMMAND_TEMPLATE, command=command, command_files=files_with_dates, favorites=favorites)

def get_timestamp(file_path):
    mappings_file = os.path.join(app.root_path, 'static', 'splits', 'file_timestamp_mapping.json')
    with open(mappings_file, 'r') as f:
        mappings = json.load(f)
        timestamp = mappings.get(file_path)
        return timestamp



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

@app.route('/search')
def search_files():
    query = request.args.get('q', '')
    results = search_index(query)
    return jsonify(results)


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
            margin: 10px auto; 
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
        body { background-color: #000000; color: white; }
        input[type="text"] {
            padding: 8px;
            width: 94%; 
            margin: 10px auto;
            display: block;
            background-color: #16213e;
            border: 1px solid #4ecca3;
            color: white;
            font-size: 16px;
            border-radius: 5px;
        }
        .search-results {
            background-color: #333;
            border: 1px solid #4ecca3;
            color: white;
            position: center;
            width: 94%;
            margin: 0 auto;
            display: none;
            z-index: 1000;
        }
        .search-result {
            padding: 10px;
            text-align: center;
            border-bottom: 1px solid #4ecca3;
            cursor: pointer;
        }
        .search-result:last-child {
            border-bottom: none;
        }
        .search-result:hover {
            background-color: #4ecca3;
        }
    </style>
</head>
<body>
    <div class="disk-meter">
        Free Space: {{ free_gb|round(2) }} GB, Recordings Size: {{ recordings_size|round(2) }} GB
    </div>
    <input type="text" id="searchInput" placeholder="Search for commands..." oninput="performSearch()">
    <div id="searchResults" class="search-results"></div>
    <a class="favorites-button" href="/favorites">Favorites</a>
    {% for tool, count in files_dict.items() %}
    <div class="button" onclick="window.location.href='/command/{{ tool }}'">{{ tool }} ({{ count|length }})</div>
    {% endfor %}
    <script>
        function performSearch() {
            let input = document.getElementById('searchInput');
            let dropdown = document.getElementById('searchResults');

            if (input.value.length < 1) {
                dropdown.style.display = 'none';
                return;
            }

            fetch(`/search?q=${encodeURIComponent(input.value)}`)
            .then(response => response.json())
            .then(data => {
                if (data.length) {
                    dropdown.innerHTML = data.map(item => `<div class="search-result" onclick="location.href='/command/${item.split('_')[0]}?open=${item}'">${item}</div>`).join('');
                    dropdown.style.display = 'block';
                } else {
                    dropdown.innerHTML = '<div class="search-result">No results found</div>';
                    dropdown.style.display = 'block';
                }
            })
            .catch(error => console.error('Error:', error));
        }
        document.addEventListener('click', function(event) {
            var searchInput = document.getElementById('searchInput');
            var searchResults = document.getElementById('searchResults');

            if (event.target !== searchInput && !searchResults.contains(event.target)) {
                searchResults.style.display = 'none'; 
            }
        });

    </script>
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
            visibility: hidden; 
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
            box-sizing: border-box;
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
            background-color: #E94560;
            padding: 10px 15px;
            margin-top: 5px;
        }
        .delete-button:hover, .edit-button:hover {
            background-color: #D8315B;
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
        .file-date {
            color: white;
            font-size: 20px;
            margin: 20px auto 10px;
            text-align: left;
            width: 95%;
        }
        .file-actions {
            display: flex;
            align-items: center;
            margin-left: 10px;
        }
    </style>
</head>
<body>
    {% set current_date = None %}
    {% for item in command_files %}
        {% if item.endswith('.cast') %}
            <div class="file-name" id="file-{{ loop.index }}" onclick="toggleDisplay('{{ item }}', event)">
                <span id="name-{{ item }}" class="file-text">{{ item.split('.cast')[0] }}</span>
                <i class="edit-icon" onclick="enableEdit('{{ item }}', event)">🖊️</i>
                <i class="save-btn" onclick="confirmSave('{{ item }}', event)" style="visibility: hidden;">&#10004;</i>
                <i class="exit-btn" onclick="exitEditMode('{{ item }}', event)" style="visibility: hidden;">&#10006;</i>
                {% if item in favorites %}
                    <span class="favorite" onclick="toggleFavorite('{{ item }}', event)">&#9733;</span>
                {% else %}
                    <span class="favorite" onclick="toggleFavorite('{{ item }}', event)">&#9734;</span>
                {% endif %}
                
            </div>
            <div id="demo-{{ item }}" class="dropdown-content">
                <div class="redact-controls">
                    <input type="text" id="redact-word-{{ item }}" placeholder="Word to Redact">
                    <button onclick="redactAndReload('{{ item }}')">Redact and Reload</button>
                </div>
                <div class="delete-controls">
                    <button class="delete-button" onclick="deleteFile('{{ item }}')">Delete File</button>
                </div>
            </div>
        {% else %}
            <div class="file-date">{{ item }}</div>
        {% endif %}
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
                
                var timestamp = new Date().getTime();
                
                AsciinemaPlayer.create('/static/splits/' + filename + '?_=' + timestamp, player);
            }
        }
        window.onload = function() {
            const params = new URLSearchParams(window.location.search);
            const openFile = params.get('open');
            if (openFile) {
                const player = document.getElementById('demo-' + openFile);
                if (player) {
                    player.style.display = 'block';
                    AsciinemaPlayer.create('/static/splits/' + openFile + '?_=' + new Date().getTime(), player);
                }
            }
        };

        
        function enableEdit(file, event) {
            event.stopPropagation();
            var nameSpan = document.getElementById('name-' + file);
            nameSpan.contentEditable = true;
            nameSpan.focus();

            nameSpan.onclick = function(event) {
                event.stopPropagation();  
            };

            var fileDiv = nameSpan.closest('.file-name');
            fileDiv.querySelector('.edit-icon').style.visibility = 'hidden';
            fileDiv.querySelector('.save-btn').style.visibility = 'visible';
            fileDiv.querySelector('.exit-btn').style.visibility = 'visible';
        }



        function confirmSave(file, event) {
            event.stopPropagation(); 
            if (confirm("Are you sure you want to save the changes?")) {
                saveEdit(file, event);
            }
        }

        function saveEdit(file, event) {
            event.stopPropagation();
            var nameSpan = document.getElementById('name-' + file);
            var newName = nameSpan.textContent.trim();

            fetch('/edit', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({old_file: file, new_file: newName + '.cast'})
            }).then(response => response.json())
            .then(data => {
                if (data.success) {
                    nameSpan.contentEditable = false;
                    alert('File name updated successfully!');

                    var fileDiv = nameSpan.closest('.file-name');
                    fileDiv.querySelector('.edit-icon').style.visibility = 'visible';
                    fileDiv.querySelector('.save-btn').style.visibility = 'hidden';
                    fileDiv.querySelector('.exit-btn').style.visibility = 'hidden';
                } else {
                    alert('Failed to edit the file name.');
                }
            }).catch(error => {
                console.error('Error:', error);
                alert('Error saving the file name: ' + error.message);
            });
        }


        function exitEditMode(file, event) {
            event.stopPropagation();
            var nameSpan = document.getElementById('name-' + file);
            nameSpan.contentEditable = false;
            var parentDiv = nameSpan.closest('.file-name');
            var editIcon = parentDiv.querySelector('.edit-icon');
            var saveIcon = parentDiv.querySelector('.save-btn');
            var exitIcon = parentDiv.querySelector('.exit-btn'); 
            editIcon.style.visibility = 'visible'; 
            saveIcon.style.visibility = 'hidden';
            exitIcon.style.visibility = 'hidden'; 
            nameSpan.textContent = file.split('.cast')[0];
        }

        function toggleFavorite(file) {
            event.stopPropagation();
            fetch('/toggle_favorite', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({file: file})
            }).then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.location.reload();
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
                    var timestamp = new Date().getTime();
                    var playerContainer = document.getElementById('demo-' + filename);
                    playerContainer.innerHTML = ''; 
                    wordInput.value = '';

                    setTimeout(() => {
                        playerContainer.style.display = 'block';
                        AsciinemaPlayer.create('/static/splits/' + filename + '?_=' + timestamp, playerContainer);
                    }, 1000);
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

