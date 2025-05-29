
# Flask File Manager

A web-based file manager with terminal functionality built with Flask.

## Features

- Web-based file browser with upload/download capabilities
- Built-in terminal for command execution
- File editing with syntax highlighting
- Create, rename, delete files and folders
- Responsive design

## Installation

1. Install Python 3.11+ and pip
2. Install dependencies:
   ```bash
   pip3 install flask
   ```

## Running the Application

```bash
python3 app.py
```

The application will be available at `http://localhost:8082`

## For Production Deployment

Change the host and port in app.py:
```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
```

## File Structure

- `app.py` - Main Flask application
- `file_manager.py` - File management functionality
- `pyproject.toml` - Project dependencies
