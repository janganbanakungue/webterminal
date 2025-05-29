
from flask import Flask, request, jsonify, render_template_string
import os
from file_manager import file_manager

app = Flask(__name__)

# HTML template for the file manager interface
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>File Manager</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .path-bar { background: #f5f5f5; padding: 10px; border-radius: 5px; margin-bottom: 20px; }
        .file-list { border: 1px solid #ddd; border-radius: 5px; }
        .file-item { padding: 10px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
        .file-item:hover { background: #f9f9f9; }
        .file-name { font-weight: bold; color: #333; cursor: pointer; }
        .file-info { color: #666; font-size: 0.9em; }
        .directory { color: #0066cc; }
        .file { color: #333; }
        .actions { display: flex; gap: 10px; }
        .btn { padding: 5px 10px; border: none; border-radius: 3px; cursor: pointer; font-size: 0.8em; }
        .btn-primary { background: #007bff; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-secondary { background: #6c757d; color: white; }
        .editor { margin-top: 20px; }
        .editor textarea { width: 100%; height: 400px; font-family: monospace; }
        .hidden { display: none; }
        .toolbar { margin-bottom: 20px; }
        .toolbar button { margin-right: 10px; }
        .terminal { 
            margin-top: 20px; 
            background: #0d1117; 
            color: #c9d1d9; 
            font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', 'Consolas', monospace; 
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid #21262d;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
        }
        .terminal-header { 
            background: #161b22; 
            padding: 12px 16px; 
            border-bottom: 1px solid #21262d; 
            display: flex; 
            justify-content: space-between; 
            align-items: center;
            font-size: 14px;
            font-weight: 600;
        }
        .terminal-title {
            color: #f0f6fc;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .terminal-controls {
            display: flex;
            gap: 8px;
        }
        .terminal-output { 
            height: 400px; 
            overflow-y: auto; 
            padding: 12px 16px; 
            white-space: pre-wrap;
            font-size: 13px;
            line-height: 1.45;
            background: #0d1117;
        }
        .terminal-input { 
            display: flex; 
            padding: 12px 16px; 
            background: #0d1117; 
            border-top: 1px solid #21262d;
            align-items: center;
        }
        .terminal-prompt { 
            color: #58a6ff; 
            margin-right: 8px; 
            font-weight: 600;
            user-select: none;
        }
        .terminal-command { 
            flex: 1; 
            background: transparent; 
            border: none; 
            color: #c9d1d9; 
            font-family: inherit; 
            font-size: 13px; 
            outline: none;
            line-height: 1.45;
        }
        .terminal-command::placeholder {
            color: #6e7681;
        }
        .terminal-line { 
            margin-bottom: 2px; 
            word-wrap: break-word;
        }
        .terminal-command-line { 
            color: #58a6ff; 
            font-weight: 600;
        }
        .terminal-output-line { 
            color: #c9d1d9; 
        }
        .terminal-error-line { 
            color: #f85149; 
        }
        .terminal-success-line {
            color: #56d364;
        }
        .terminal-warning-line {
            color: #e3b341;
        }
        .terminal-directory {
            color: #79c0ff;
            font-weight: 600;
        }
        .terminal-file {
            color: #c9d1d9;
        }
        .terminal-executable {
            color: #56d364;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>File Manager</h1>
        
        <div class="toolbar">
            <button class="btn btn-primary" onclick="createDirectory()">New Folder</button>
            <button class="btn btn-primary" onclick="createFile()">New File</button>
            <button class="btn btn-secondary" onclick="refresh()">Refresh</button>
            <button class="btn btn-secondary" onclick="toggleTerminal()">Terminal</button>
        </div>
        
        <div class="path-bar">
            <strong>Current Path:</strong> <span id="current-path">/</span>
            <button class="btn btn-secondary" onclick="goUp()" id="up-btn">↑ Up</button>
        </div>
        
        <div class="file-list" id="file-list">
            Loading...
        </div>
        
        <div class="editor hidden" id="editor">
            <h3>Edit File: <span id="edit-filename"></span></h3>
            <textarea id="file-content"></textarea>
            <br>
            <button class="btn btn-primary" onclick="saveFile()">Save</button>
            <button class="btn btn-secondary" onclick="closeEditor()">Cancel</button>
        </div>
        
        <div class="terminal hidden" id="terminal">
            <div class="terminal-header">
                <div class="terminal-title">
                    <span>🖥️ Shell</span>
                    <span id="terminal-path" style="color: #6e7681; font-weight: normal; font-size: 12px;"></span>
                </div>
                <div class="terminal-controls">
                    <button class="btn btn-secondary" onclick="clearTerminal()">Clear</button>
                    <button class="btn btn-secondary" onclick="toggleTerminal()">✕</button>
                </div>
            </div>
            <div class="terminal-output" id="terminal-output">
                <div class="terminal-line terminal-success-line">Welcome to Replit Shell</div>
                <div class="terminal-line" style="color: #6e7681;">Type commands to interact with your environment</div>
                <div class="terminal-line"></div>
            </div>
            <div class="terminal-input">
                <span class="terminal-prompt" id="terminal-prompt">~$</span>
                <input type="text" class="terminal-command" id="terminal-command" placeholder="Type a command..." autocomplete="off">
            </div>
        </div>
    </div>

    <script>
        let currentPath = '.';
        
        function loadDirectory(path = '.') {
            currentPath = path;
            document.getElementById('current-path').textContent = path;
            document.getElementById('up-btn').style.display = path === '.' ? 'none' : 'inline-block';
            
            fetch('/api/directory', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({path: path})
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    document.getElementById('file-list').innerHTML = `<div class="file-item">Error: ${data.error}</div>`;
                    return;
                }
                
                let html = '';
                data.items.forEach(item => {
                    const icon = item.type === 'directory' ? '📁' : '📄';
                    const className = item.type === 'directory' ? 'directory' : 'file';
                    const size = item.type === 'file' ? `(${formatSize(item.size)})` : '';
                    
                    html += `
                        <div class="file-item">
                            <div onclick="${item.type === 'directory' ? `loadDirectory('${item.path}')` : `editFile('${item.path}')`}">
                                <span class="file-name ${className}">${icon} ${item.name}</span>
                                <div class="file-info">${item.type} ${size} - Modified: ${new Date(item.modified).toLocaleString()}</div>
                            </div>
                            <div class="actions">
                                <button class="btn btn-secondary" onclick="renameItem('${item.path}', '${item.name}')">Rename</button>
                                <button class="btn btn-danger" onclick="deleteItem('${item.path}')">Delete</button>
                            </div>
                        </div>
                    `;
                });
                
                document.getElementById('file-list').innerHTML = html || '<div class="file-item">Empty directory</div>';
            })
            .catch(error => {
                document.getElementById('file-list').innerHTML = `<div class="file-item">Error: ${error.message}</div>`;
            });
        }
        
        function editFile(filePath) {
            fetch('/api/file/read', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({path: filePath})
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert('Error: ' + data.error);
                    return;
                }
                
                document.getElementById('edit-filename').textContent = filePath;
                document.getElementById('file-content').value = data.content;
                document.getElementById('editor').classList.remove('hidden');
            });
        }
        
        function saveFile() {
            const filePath = document.getElementById('edit-filename').textContent;
            const content = document.getElementById('file-content').value;
            
            fetch('/api/file/write', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({path: filePath, content: content})
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert('Error: ' + data.error);
                } else {
                    alert('File saved successfully');
                    closeEditor();
                    refresh();
                }
            });
        }
        
        function closeEditor() {
            document.getElementById('editor').classList.add('hidden');
        }
        
        function deleteItem(path) {
            if (confirm('Are you sure you want to delete this item?')) {
                fetch('/api/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({path: path})
                })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        alert('Error: ' + data.error);
                    } else {
                        refresh();
                    }
                });
            }
        }
        
        function renameItem(path, currentName) {
            const newName = prompt('Enter new name:', currentName);
            if (newName && newName !== currentName) {
                fetch('/api/rename', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({path: path, new_name: newName})
                })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        alert('Error: ' + data.error);
                    } else {
                        refresh();
                    }
                });
            }
        }
        
        function createDirectory() {
            const name = prompt('Enter directory name:');
            if (name) {
                const path = currentPath === '.' ? name : `${currentPath}/${name}`;
                fetch('/api/directory/create', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({path: path})
                })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        alert('Error: ' + data.error);
                    } else {
                        refresh();
                    }
                });
            }
        }
        
        function createFile() {
            const name = prompt('Enter file name:');
            if (name) {
                const path = currentPath === '.' ? name : `${currentPath}/${name}`;
                fetch('/api/file/write', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({path: path, content: ''})
                })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        alert('Error: ' + data.error);
                    } else {
                        refresh();
                    }
                });
            }
        }
        
        function goUp() {
            const parentPath = currentPath.split('/').slice(0, -1).join('/') || '.';
            loadDirectory(parentPath);
        }
        
        function refresh() {
            loadDirectory(currentPath);
        }
        
        function formatSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
        
        function toggleTerminal() {
            const terminal = document.getElementById('terminal');
            const isHidden = terminal.classList.contains('hidden');
            
            if (isHidden) {
                terminal.classList.remove('hidden');
                document.getElementById('terminal-command').focus();
            } else {
                terminal.classList.add('hidden');
            }
        }
        
        let commandHistory = [];
        let historyIndex = -1;
        let currentWorkingDir = '.';
        
        function addTerminalLine(content, type = 'output') {
            const output = document.getElementById('terminal-output');
            const line = document.createElement('div');
            line.className = `terminal-line terminal-${type}-line`;
            
            // Handle special formatting for different content types
            if (type === 'output' && content) {
                // Color directories, files, etc.
                const formattedContent = formatTerminalOutput(content);
                line.innerHTML = formattedContent;
            } else {
                line.textContent = content;
            }
            
            output.appendChild(line);
            output.scrollTop = output.scrollHeight;
        }
        
        function formatTerminalOutput(content) {
            // Simple formatting for common outputs
            return content
                .replace(/^d[rwx-]{9}/gm, '<span class="terminal-directory">$&</span>')
                .replace(/^-[rwx-]{9}/gm, '<span class="terminal-file">$&</span>')
                .replace(/\b([a-zA-Z_][a-zA-Z0-9_]*\.py)\b/g, '<span class="terminal-file">$1</span>')
                .replace(/\b([a-zA-Z_][a-zA-Z0-9_]*\/)\b/g, '<span class="terminal-directory">$1</span>');
        }
        
        function updateTerminalPrompt() {
            const prompt = document.getElementById('terminal-prompt');
            const pathDisplay = document.getElementById('terminal-path');
            const shortPath = currentWorkingDir === '.' ? '~' : currentWorkingDir.split('/').pop() || '~';
            prompt.textContent = `${shortPath}$`;
            pathDisplay.textContent = currentWorkingDir === '.' ? '~' : currentWorkingDir;
        }
        
        function executeCommand(command) {
            if (!command.trim()) return;
            
            // Add to history
            commandHistory.push(command);
            historyIndex = commandHistory.length;
            
            // Display the command with current prompt
            const prompt = document.getElementById('terminal-prompt').textContent;
            addTerminalLine(`${prompt} ${command}`, 'command');
            
            // Handle built-in commands
            if (command.trim() === 'clear') {
                clearTerminal();
                return;
            }
            
            if (command.trim().startsWith('cd ')) {
                handleCdCommand(command.trim().substring(3));
                return;
            }
            
            fetch('/api/execute', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    command: command,
                    cwd: currentWorkingDir
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    addTerminalLine(data.error, 'error');
                } else {
                    if (data.output && data.output.trim()) {
                        addTerminalLine(data.output, 'output');
                    }
                    if (data.stderr && data.stderr.trim()) {
                        addTerminalLine(data.stderr, 'error');
                    }
                    if (data.return_code !== 0 && data.return_code !== undefined) {
                        addTerminalLine(`Process exited with code ${data.return_code}`, 'warning');
                    }
                    // Update working directory if pwd command was run
                    if (command.trim() === 'pwd' && data.output) {
                        currentWorkingDir = data.output.trim();
                        updateTerminalPrompt();
                    }
                }
            })
            .catch(error => {
                addTerminalLine(`Error: ${error.message}`, 'error');
            });
        }
        
        function handleCdCommand(path) {
            if (!path) path = '.';
            
            fetch('/api/execute', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    command: `cd "${path}" && pwd`,
                    cwd: currentWorkingDir
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    addTerminalLine(data.error, 'error');
                } else if (data.output) {
                    currentWorkingDir = data.output.trim();
                    updateTerminalPrompt();
                    // Also update the file manager if we're in the same directory
                    if (currentWorkingDir === currentPath || 
                        (currentWorkingDir.endsWith(currentPath) && currentPath !== '.')) {
                        refresh();
                    }
                }
            })
            .catch(error => {
                addTerminalLine(`Error: ${error.message}`, 'error');
            });
        }
        
        function clearTerminal() {
            document.getElementById('terminal-output').innerHTML = '';
        }
        
        // Terminal command input handler
        document.addEventListener('DOMContentLoaded', function() {
            const terminalCommand = document.getElementById('terminal-command');
            if (terminalCommand) {
                terminalCommand.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        const command = this.value.trim();
                        if (command) {
                            executeCommand(command);
                            this.value = '';
                        }
                    } else if (e.key === 'ArrowUp') {
                        e.preventDefault();
                        if (historyIndex > 0) {
                            historyIndex--;
                            this.value = commandHistory[historyIndex] || '';
                        }
                    } else if (e.key === 'ArrowDown') {
                        e.preventDefault();
                        if (historyIndex < commandHistory.length - 1) {
                            historyIndex++;
                            this.value = commandHistory[historyIndex] || '';
                        } else {
                            historyIndex = commandHistory.length;
                            this.value = '';
                        }
                    } else if (e.key === 'Tab') {
                        e.preventDefault();
                        // Simple tab completion for common commands
                        const value = this.value;
                        const commonCommands = ['ls', 'cd', 'pwd', 'mkdir', 'touch', 'rm', 'cp', 'mv', 'cat', 'echo', 'grep', 'find', 'python', 'python3', 'node', 'npm', 'git'];
                        const matches = commonCommands.filter(cmd => cmd.startsWith(value));
                        if (matches.length === 1) {
                            this.value = matches[0] + ' ';
                        }
                    } else if (e.ctrlKey && e.key === 'c') {
                        e.preventDefault();
                        addTerminalLine('^C', 'warning');
                        this.value = '';
                    } else if (e.ctrlKey && e.key === 'l') {
                        e.preventDefault();
                        clearTerminal();
                    }
                });
                
                // Focus terminal when clicked
                document.getElementById('terminal').addEventListener('click', function() {
                    terminalCommand.focus();
                });
            }
            
            // Initialize terminal
            updateTerminalPrompt();
        });
        
        // Load initial directory
        loadDirectory('.');
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/directory', methods=['POST'])
def get_directory():
    data = request.get_json()
    path = data.get('path', '.')
    result = file_manager.get_directory_contents(path)
    return jsonify(result)

@app.route('/api/file/read', methods=['POST'])
def read_file():
    data = request.get_json()
    path = data.get('path')
    if not path:
        return jsonify({'error': 'Path is required'})
    
    result = file_manager.read_file(path)
    return jsonify(result)

@app.route('/api/file/write', methods=['POST'])
def write_file():
    data = request.get_json()
    path = data.get('path')
    content = data.get('content', '')
    
    if not path:
        return jsonify({'error': 'Path is required'})
    
    result = file_manager.write_file(path, content)
    return jsonify(result)

@app.route('/api/directory/create', methods=['POST'])
def create_directory():
    data = request.get_json()
    path = data.get('path')
    
    if not path:
        return jsonify({'error': 'Path is required'})
    
    result = file_manager.create_directory(path)
    return jsonify(result)

@app.route('/api/delete', methods=['POST'])
def delete_item():
    data = request.get_json()
    path = data.get('path')
    
    if not path:
        return jsonify({'error': 'Path is required'})
    
    result = file_manager.delete_item(path)
    return jsonify(result)

@app.route('/api/rename', methods=['POST'])
def rename_item():
    data = request.get_json()
    path = data.get('path')
    new_name = data.get('new_name')
    
    if not path or not new_name:
        return jsonify({'error': 'Path and new name are required'})
    
    result = file_manager.rename_item(path, new_name)
    return jsonify(result)

@app.route('/api/move', methods=['POST'])
def move_item():
    data = request.get_json()
    source = data.get('source')
    destination = data.get('destination')
    
    if not source or not destination:
        return jsonify({'error': 'Source and destination are required'})
    
    result = file_manager.move_item(source, destination)
    return jsonify(result)

@app.route('/api/copy', methods=['POST'])
def copy_item():
    data = request.get_json()
    source = data.get('source')
    destination = data.get('destination')
    
    if not source or not destination:
        return jsonify({'error': 'Source and destination are required'})
    
    result = file_manager.copy_item(source, destination)
    return jsonify(result)

@app.route('/api/tree', methods=['POST'])
def get_file_tree():
    data = request.get_json()
    path = data.get('path', '.')
    max_depth = data.get('max_depth', 3)
    
    result = file_manager.get_file_tree(path, max_depth)
    return jsonify(result)

@app.route('/api/execute', methods=['POST'])
def execute_command():
    import subprocess
    
    data = request.get_json()
    command = data.get('command', '')
    cwd = data.get('cwd', '.')
    
    if not command.strip():
        return jsonify({'error': 'Command cannot be empty'})
    
    # Normalize working directory
    if cwd == '.' or not cwd:
        cwd = os.getcwd()
    
    try:
        # Execute command and capture output
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=300,
            cwd=cwd,
            env=dict(os.environ, PYTHONUNBUFFERED='1')
        )
        
        output = result.stdout
        stderr = result.stderr
        return_code = result.returncode
        
        return jsonify({
            'output': output,
            'stderr': stderr,
            'return_code': return_code,
            'command': command,
            'cwd': cwd
        })
    
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Command timed out after 300 seconds'})
    except FileNotFoundError:
        return jsonify({'error': f'Directory not found: {cwd}'})
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8082, debug=True)
