#!/usr/bin/env python3
"""
Standalone Telegram Remote System Administration Bot
Complete implementation in a single file with all features
"""

import os
import sys
import subprocess
import requests
import json
import time
import logging
import tempfile
import shutil
import hashlib
import re
import threading
from pathlib import Path
from typing import Dict, Tuple, Optional, List

# Bot Configuration - You'll need to update this with your bot token
BOT_TOKEN = os.getenv("BOT_TOKEN", "7814902912:AAHlmK87m7cp_7gJj2a3aPInyEVvAWpO9EI")
TELEGRAM_BASE_URL = "https://api.telegram.org/bot"

# Configuration Constants
MAX_UPLOAD_SIZE = 2000 * 1024 * 1024  # 20MB
MAX_DOWNLOAD_SIZE = 5000 * 1024 * 1024  # 50MB
COMMAND_TIMEOUT = 600  # 10 minutes
MAX_MESSAGE_LENGTH = 4000

# Emojis for better UX
EMOJIS = {
    'robot': '🤖', 'folder': '📁', 'file': '📄', 'upload': '📤',
    'download': '📥', 'success': '✅', 'error': '❌', 'warning': '⚠️',
    'info': 'ℹ️', 'rocket': '🚀', 'gear': '⚙️', 'terminal': '💻'
}

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.api_url = f"{TELEGRAM_BASE_URL}{token}"
        self.user_directories = {}
        self.upload_directories = {}
        self.running_bots = {}
        self.command_history = {}
        
        # Setup logging
        self._setup_logging()
        
        # Create necessary directories
        self._ensure_directories()
        
        # Install dependencies
        self._install_dependencies()
        
    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)
        
    def _ensure_directories(self):
        """Ensure necessary directories exist"""
        dirs = ['downloads', 'uploads', 'logs', 'scripts']
        for directory in dirs:
            os.makedirs(directory, exist_ok=True)
            
    def _install_dependencies(self):
        """Install required dependencies"""
        required_packages = ['requests']
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                self.logger.info(f"Installing {package}...")
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])

    def escape_markdown(self, text: str) -> str:
        """Escape special characters for Telegram markdown formatting"""
        escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
        return text

    def send_message(self, chat_id: int, text: str, parse_mode: str = 'Markdown', 
                    reply_to_message_id: Optional[int] = None) -> Optional[dict]:
        """Send message to Telegram chat"""
        try:
            if len(text) > MAX_MESSAGE_LENGTH:
                return self._send_long_message(chat_id, text, parse_mode, reply_to_message_id)
            
            payload = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': parse_mode
            }
            
            if reply_to_message_id:
                payload['reply_to_message_id'] = reply_to_message_id
            
            response = requests.post(f"{self.api_url}/sendMessage", data=payload, timeout=30)
            return response.json() if response.status_code == 200 else None
            
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            return None

    def _send_long_message(self, chat_id: int, text: str, parse_mode: str, 
                          reply_to_message_id: Optional[int] = None):
        """Send long message in chunks"""
        chunks = [text[i:i+MAX_MESSAGE_LENGTH] for i in range(0, len(text), MAX_MESSAGE_LENGTH)]
        
        for i, chunk in enumerate(chunks):
            if i == 0 and reply_to_message_id:
                self.send_message(chat_id, chunk, parse_mode, reply_to_message_id)
            else:
                self.send_message(chat_id, chunk, parse_mode)
            time.sleep(0.5)  # Avoid rate limiting

    def send_document(self, chat_id: int, file_path: str, caption: Optional[str] = None) -> Optional[dict]:
        """Send document to Telegram chat"""
        try:
            if not os.path.exists(file_path):
                return None
            
            if os.path.getsize(file_path) > MAX_DOWNLOAD_SIZE:
                self.send_message(chat_id, f"{EMOJIS['error']} File too large (max {MAX_DOWNLOAD_SIZE//1024//1024}MB)")
                return None
            
            with open(file_path, 'rb') as file:
                files = {'document': file}
                data = {'chat_id': chat_id}
                
                if caption:
                    data['caption'] = caption
                
                response = requests.post(f"{self.api_url}/sendDocument", files=files, data=data, timeout=120)
                return response.json() if response.status_code == 200 else None
                
        except Exception as e:
            self.logger.error(f"Failed to send document: {e}")
            return None

    def download_file(self, file_id: str, download_path: str) -> tuple:
        """Download file from Telegram"""
        try:
            # Get file info
            response = requests.get(f"{self.api_url}/getFile?file_id={file_id}", timeout=30)
            
            if response.status_code != 200:
                return False, "Failed to get file information"
            
            file_info = response.json()
            if not file_info.get('ok'):
                return False, "Invalid file information"
            
            file_path = file_info['result']['file_path']
            file_size = file_info['result'].get('file_size', 0)
            
            if file_size > MAX_UPLOAD_SIZE:
                return False, f"File too large (max {MAX_UPLOAD_SIZE//1024//1024}MB)"
            
            # Download file
            file_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
            file_response = requests.get(file_url, timeout=120)
            
            if file_response.status_code == 200:
                with open(download_path, 'wb') as f:
                    f.write(file_response.content)
                return True, "File downloaded successfully"
            else:
                return False, "Failed to download file"
                
        except Exception as e:
            return False, f"Download error: {str(e)}"

    def get_updates(self, offset: Optional[int] = None) -> Optional[dict]:
        """Get updates from Telegram"""
        try:
            params = {'timeout': 30}
            if offset:
                params['offset'] = offset
            
            response = requests.get(f"{self.api_url}/getUpdates", params=params, timeout=35)
            return response.json() if response.status_code == 200 else None
            
        except Exception as e:
            self.logger.error(f"Failed to get updates: {e}")
            return None

    def get_user_directory(self, user_id: int) -> str:
        """Get current directory for user"""
        return self.user_directories.get(user_id, os.getcwd())

    def set_user_directory(self, user_id: int, directory: str):
        """Set current directory for user"""
        self.user_directories[user_id] = directory

    def is_safe_command(self, command: str) -> tuple:
        """Check if command is safe to execute"""
        dangerous_commands = [
           'kill -9 -1'
        ]
        
        command_lower = command.lower().strip()
        
        for dangerous in dangerous_commands:
            if dangerous in command_lower:
                return False, f"{EMOJIS['error']} Dangerous command blocked: `{dangerous}`"
        
        # Block commands with certain patterns
        if re.search(r'rm\s+-rf\s+[/*]', command_lower):
            return False, f"{EMOJIS['error']} Dangerous rm command blocked"
        
        if re.search(r'sudo\s+(rm|mv|cp|chmod|chown)', command_lower):
            return False, f"{EMOJIS['error']} Dangerous sudo command blocked"
        
        return True, "Command is safe"

    def execute_command(self, command: str, current_dir: str, user_id: int) -> Tuple[bool, str]:
        """Execute shell command with safety checks"""
        # Safety check
        is_safe, safety_message = self.is_safe_command(command)
        if not is_safe:
            return False, safety_message
        
        # Handle background commands
        if command.strip().endswith('&'):
            return self._execute_background_command(command, current_dir, user_id)
        
        try:
            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                cwd=current_dir,
                capture_output=True,
                text=True,
                timeout=COMMAND_TIMEOUT,
                env=dict(os.environ, PYTHONPATH=current_dir)
            )
            
            # Combine stdout and stderr with backslash suppression
            output = ""
            if result.stdout:
                # Apply backslash escaping for output suppression
                cleaned_stdout = result.stdout.replace('\\', '\\\\')
                output += cleaned_stdout
            if result.stderr:
                # Apply backslash escaping for stderr suppression  
                cleaned_stderr = result.stderr.replace('\\', '\\\\')
                output += f"\nSTDERR:\n{cleaned_stderr}"
            
            if not output:
                output = f"{EMOJIS['success']} Command executed successfully (no output)"
            
            # Update command history
            if user_id not in self.command_history:
                self.command_history[user_id] = []
            self.command_history[user_id].append({
                'command': command,
                'directory': current_dir,
                'timestamp': time.time(),
                'success': result.returncode == 0
            })
            
            return True, output[:8000]  # Limit output length
            
        except subprocess.TimeoutExpired:
            return False, f"{EMOJIS['error']} Command timed out after {COMMAND_TIMEOUT} seconds"
        except Exception as e:
            return False, f"{EMOJIS['error']} Command failed: {str(e)}"

    def _execute_background_command(self, command: str, current_dir: str, user_id: int) -> Tuple[bool, str]:
        """Execute command in background"""
        try:
            command = command.rstrip('&').strip()
            
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=current_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Store process info
            process_id = f"bg_{user_id}_{int(time.time())}"
            self.running_bots[process_id] = {
                'process': process,
                'command': command,
                'started': time.time(),
                'user_id': user_id
            }
            
            return True, f"{EMOJIS['rocket']} Command started in background: `{process_id}`"
            
        except Exception as e:
            return False, f"{EMOJIS['error']} Failed to start background process: {str(e)}"

    def handle_cd_command(self, chat_id: int, user_id: int, path: str):
        """Handle directory change command"""
        current_dir = self.get_user_directory(user_id)
        
        if not path:
            path = os.path.expanduser("~")
        elif path == "..":
            path = os.path.dirname(current_dir)
        elif not path.startswith('/'):
            path = os.path.join(current_dir, path)
        
        path = os.path.abspath(path)
        
        if os.path.isdir(path):
            self.set_user_directory(user_id, path)
            self.send_message(chat_id, f"{EMOJIS['folder']} Changed directory to: `{path}`")
        else:
            self.send_message(chat_id, f"{EMOJIS['error']} Directory not found: `{path}`")

    def handle_file_upload(self, chat_id: int, user_id: int, file_info: dict, message_id: int):
        """Handle file uploads from users"""
        try:
            file_name = file_info.get('file_name', 'unknown_file')
            file_id = file_info['file_id']
            file_size = file_info.get('file_size', 0)
            
            if file_size > MAX_UPLOAD_SIZE:
                self.send_message(
                    chat_id, 
                    f"{EMOJIS['error']} File too large: {file_size//1024//1024}MB (max {MAX_UPLOAD_SIZE//1024//1024}MB)",
                    reply_to_message_id=message_id
                )
                return
            
            # Get upload directory
            current_dir = self.get_user_directory(user_id)
            upload_path = os.path.join(current_dir, file_name)
            
            # Download file
            success, message = self.download_file(file_id, upload_path)
            
            if success:
                self.send_message(
                    chat_id,
                    f"{EMOJIS['upload']} File uploaded successfully!\n📄 *File:* `{file_name}`\n📁 *Location:* `{upload_path}`",
                    reply_to_message_id=message_id
                )
            else:
                self.send_message(
                    chat_id,
                    f"{EMOJIS['error']} Upload failed: {message}",
                    reply_to_message_id=message_id
                )
                
        except Exception as e:
            self.send_message(
                chat_id,
                f"{EMOJIS['error']} Upload error: {str(e)}",
                reply_to_message_id=message_id
            )

    def handle_download_command(self, chat_id: int, user_id: int, file_path: str):
        """Handle file download command"""
        current_dir = self.get_user_directory(user_id)
        
        if not file_path.startswith('/'):
            full_path = os.path.join(current_dir, file_path)
        else:
            full_path = file_path
        
        if not os.path.exists(full_path):
            self.send_message(chat_id, f"{EMOJIS['error']} File not found: `{file_path}`")
            return
        
        if os.path.isdir(full_path):
            self.send_message(chat_id, f"{EMOJIS['error']} Cannot download directory: `{file_path}`")
            return
        
        file_size = os.path.getsize(full_path)
        if file_size > MAX_DOWNLOAD_SIZE:
            self.send_message(
                chat_id, 
                f"{EMOJIS['error']} File too large: {file_size//1024//1024}MB (max {MAX_DOWNLOAD_SIZE//1024//1024}MB)"
            )
            return
        
        # Send file
        result = self.send_document(chat_id, full_path, f"📥 Downloaded: {os.path.basename(file_path)}")
        
        if result:
            self.send_message(chat_id, f"{EMOJIS['download']} File sent successfully: `{file_path}`")
        else:
            self.send_message(chat_id, f"{EMOJIS['error']} Failed to send file: `{file_path}`")

    def add_bot_script(self, script_content: str, script_name: str = None) -> Tuple[bool, str]:
        """Add a new bot script"""
        try:
            if not script_name:
                script_name = f"bot_script_{int(time.time())}.py"
            
            if not script_name.endswith('.py'):
                script_name += '.py'
            
            script_path = os.path.join('scripts', script_name)
            
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            # Make script executable
            os.chmod(script_path, 0o755)
            
            return True, f"{EMOJIS['success']} Bot script saved: `{script_name}`"
            
        except Exception as e:
            return False, f"{EMOJIS['error']} Failed to save script: {str(e)}"

    def run_bot_script(self, script_name: str, bot_token: str = None) -> Tuple[bool, str]:
        """Run a bot script"""
        try:
            script_path = os.path.join('scripts', script_name)
            
            if not os.path.exists(script_path):
                return False, f"{EMOJIS['error']} Script not found: `{script_name}`"
            
            # Create environment
            env = os.environ.copy()
            if bot_token:
                env['BOT_TOKEN'] = bot_token
            
            # Start script
            process = subprocess.Popen(
                [sys.executable, script_path],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Store process info
            bot_id = f"bot_{int(time.time())}"
            self.running_bots[bot_id] = {
                'process': process,
                'script_name': script_name,
                'started': time.time()
            }
            
            return True, f"{EMOJIS['rocket']} Bot script started!\n🤖 *Bot ID:* `{bot_id}`\n📝 *Script:* `{script_name}`"
            
        except Exception as e:
            return False, f"{EMOJIS['error']} Failed to run script: {str(e)}"

    def handle_addbot_command(self, chat_id: int, user_id: int, script_content: str):
        """Handle add bot command"""
        # Save script
        success, message = self.add_bot_script(script_content)
        self.send_message(chat_id, message)
        
        if success:
            # Extract script name from message
            script_match = re.search(r'`([^`]+\.py)`', message)
            if script_match:
                script_name = script_match.group(1)
                success, run_message = self.run_bot_script(script_name, self.token)
                self.send_message(chat_id, run_message)

    def list_bots(self) -> str:
        """List all running bots"""
        if not self.running_bots:
            return f"{EMOJIS['info']} No bots currently running"
        
        bot_list = [f"{EMOJIS['robot']} *Running Bots:*\n"]
        
        for bot_id, info in self.running_bots.items():
            runtime = int(time.time() - info['started'])
            status = "Running" if info['process'].poll() is None else "Stopped"
            
            bot_list.append(
                f"🤖 *Bot ID:* `{bot_id}`\n"
                f"📝 *Script:* `{info.get('script_name', 'Background Command')}`\n"
                f"⏱️ *Runtime:* {runtime}s\n"
                f"📊 *Status:* {status}\n"
            )
        
        return '\n'.join(bot_list)

    def stop_bot(self, bot_id: str) -> Tuple[bool, str]:
        """Stop a running bot"""
        try:
            if bot_id not in self.running_bots:
                return False, f"{EMOJIS['error']} Bot ID not found: `{bot_id}`"
            
            bot_info = self.running_bots[bot_id]
            process = bot_info['process']
            
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            
            del self.running_bots[bot_id]
            
            return True, f"{EMOJIS['success']} Bot stopped: `{bot_id}`"
            
        except Exception as e:
            return False, f"{EMOJIS['error']} Failed to stop bot: {str(e)}"

    def get_system_info(self) -> dict:
        """Get system information"""
        try:
            import platform
            import psutil
            
            info = {
                'OS': platform.system(),
                'Platform': platform.platform(),
                'Architecture': platform.architecture()[0],
                'Processor': platform.processor(),
                'Python Version': platform.python_version(),
                'CPU Count': psutil.cpu_count(),
                'Memory Total': f"{psutil.virtual_memory().total // 1024 // 1024} MB",
                'Memory Available': f"{psutil.virtual_memory().available // 1024 // 1024} MB",
                'Disk Usage': f"{psutil.disk_usage('/').percent}%"
            }
            
            return info
            
        except ImportError:
            # Fallback without psutil
            import platform
            return {
                'OS': platform.system(),
                'Platform': platform.platform(),
                'Architecture': platform.architecture()[0],
                'Python Version': platform.python_version()
            }
        except Exception:
            return None

    def install_package(self, package_name: str) -> Tuple[bool, str]:
        """Install package"""
        try:
            # Try pip first
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', package_name],
                capture_output=True, text=True, timeout=300
            )
            
            if result.returncode == 0:
                return True, f"{EMOJIS['success']} Package installed successfully: {package_name}"
            else:
                # Try apt if pip fails
                try:
                    apt_result = subprocess.run(
                        ['sudo', 'apt', 'install', '-y', package_name],
                        capture_output=True, text=True, timeout=300
                    )
                    if apt_result.returncode == 0:
                        return True, f"{EMOJIS['success']} System package installed: {package_name}"
                except:
                    pass
                
                error_output = result.stderr or result.stdout or "Unknown error"
                return False, f"{EMOJIS['error']} Package installation failed: {error_output}"
                
        except subprocess.TimeoutExpired:
            return False, f"{EMOJIS['error']} Package installation timed out"
        except Exception as e:
            return False, f"{EMOJIS['error']} Package installation failed: {str(e)}"

    def handle_start_command(self, chat_id: int):
        """Handle /start command"""
        msg = (
            f"{EMOJIS['robot']} *Overpower Bot by @Kecee_Pyrite* is now active!\n\n"
            f"{EMOJIS['folder']} Current directory: /home/runner\n"
            f"{EMOJIS['rocket']} *Getting Started:*\n"
            "• `ls` — list files\n"
            "• Type any shell command to execute\n\n"
            f"{EMOJIS['terminal']} *Available Commands:*\n"
            "• `/start` — show this message\n"
            "• `/help` — show help information\n"
            "• `/download <file_path>` — download file\n"
            "• `/upload <path>` — set upload directory\n"
            "• `/addbot <script>` — add and run bot script\n"
            "• `/listbots` — list running bots\n"
            "• `/stopbot <id>` — stop running bot\n"
            "• `/install <package>` — install package\n"
            "• `/sysinfo` — show system information\n"
            "• `pwd` — show current directory\n"
            "• `cd <path>` — change directory\n\n"
            f"{EMOJIS['upload']} *File Operations:*\n"
            "• Send any file to upload to current directory\n"
            "• Use `/download filename` to download files\n\n"
            f"{EMOJIS['warning']} *Note:* Commands timeout after 10 minutes\n"
            f"{EMOJIS['info']} *Limits:* Upload max 20MB, Download max 50MB"
        )
        self.send_message(chat_id, msg)

    def handle_help_command(self, chat_id: int):
        """Handle /help command"""
        help_msg = (
            f"{EMOJIS['info']} *Bot Help & Usage*\n\n"
            f"{EMOJIS['terminal']} *Shell Commands:*\n"
            "• Execute any Linux command directly\n"
            "• Use `&` at the end for background processes\n"
            "• Commands are executed with safety checks\n\n"
            f"{EMOJIS['folder']} *Navigation:*\n"
            "• `pwd` — show current directory\n"
            "• `cd <path>` — change directory\n"
            "• `ls` — list directory contents\n\n"
            f"{EMOJIS['upload']} *File Management:*\n"
            "• Send files directly to upload\n"
            "• `/download <file>` — download files\n"
            "• `/upload [path]` — set upload directory\n\n"
            f"{EMOJIS['robot']} *Bot Management:*\n"
            "• `/addbot <script>` — add Python bot script\n"
            "• `/listbots` — show running bots\n"
            "• `/stopbot <id>` — stop bot by ID\n\n"
            f"{EMOJIS['gear']} *System:*\n"
            "• `/install <package>` — install packages\n"
            "• `/sysinfo` — system information\n\n"
            f"{EMOJIS['warning']} *Safety Features:*\n"
            "• Dangerous commands are blocked\n"
            "• File size limits enforced\n"
            "• Command timeout after 10 minutes\n"
            "• Safe execution environment\n\n"
            f"{EMOJIS['info']} *Tips:*\n"
            "• Each user has their own working directory\n"
            "• Commands run in isolated environment\n"
            "• Use absolute paths for system-wide access\n"
            "• Background processes tracked automatically\n\n"
            f"{EMOJIS['warning']} Interactive commands may not work properly"
        )
        self.send_message(chat_id, help_msg)

    def process_message(self, message: dict):
        """Process incoming message"""
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        message_id = message['message_id']
        
        # Handle file uploads
        if 'document' in message:
            self.handle_file_upload(chat_id, user_id, message['document'], message_id)
            return
        
        # Handle text messages
        if 'text' not in message:
            return
            
        text = message['text'].strip()
        
        # Handle commands
        if text.startswith('/start'):
            self.handle_start_command(chat_id)
        elif text.startswith('/help'):
            self.handle_help_command(chat_id)
        elif text.startswith('/download '):
            file_path = text[10:].strip()
            self.handle_download_command(chat_id, user_id, file_path)
        elif text.startswith('/upload'):
            path = text[7:].strip() if len(text) > 7 else ""
            current_dir = self.get_user_directory(user_id)
            if path:
                if not path.startswith('/'):
                    full_path = os.path.join(current_dir, path)
                else:
                    full_path = path
                if os.path.isdir(full_path):
                    self.set_user_directory(user_id, full_path)
                    self.send_message(chat_id, f"{EMOJIS['success']} Upload directory set to: `{full_path}`")
                else:
                    self.send_message(chat_id, f"{EMOJIS['error']} Directory not found: `{path}`")
            else:
                self.send_message(chat_id, f"{EMOJIS['folder']} Current upload directory: `{current_dir}`")
        elif text.startswith('/addbot '):
            script_content = text[8:].strip()
            self.handle_addbot_command(chat_id, user_id, script_content)
        elif text.startswith('/listbots'):
            bot_list = self.list_bots()
            self.send_message(chat_id, bot_list)
        elif text.startswith('/stopbot '):
            bot_id = text[9:].strip()
            success, message_text = self.stop_bot(bot_id)
            self.send_message(chat_id, message_text)
        elif text.startswith('/install '):
            package_name = text[9:].strip()
            success, message_text = self.install_package(package_name)
            self.send_message(chat_id, message_text)
        elif text.startswith('/sysinfo'):
            info = self.get_system_info()
            if info:
                formatted_info = f"{EMOJIS['terminal']} *System Information:*\n\n"
                for key, value in info.items():
                    formatted_info += f"• *{key}:* `{value}`\n"
                self.send_message(chat_id, formatted_info)
            else:
                self.send_message(chat_id, f"{EMOJIS['error']} Failed to get system information")
        elif text.startswith('cd '):
            path = text[3:].strip()
            self.handle_cd_command(chat_id, user_id, path)
        elif text == 'pwd':
            current_dir = self.get_user_directory(user_id)
            self.send_message(chat_id, f"```\n{current_dir}\n```")
        else:
            # Handle regular shell commands
            current_dir = self.get_user_directory(user_id)
            success, output = self.execute_command(text, current_dir, user_id)
            
            if success:
                escaped_output = self.escape_markdown(output)
                self.send_message(chat_id, f"```\n{escaped_output}\n```")
            else:
                self.send_message(chat_id, output)

    def run(self):
        """Main bot loop"""
        self.logger.info("🤖 Telegram Remote System Administration Bot is running...")
        self.logger.info(f"📁 Working directory: {os.getcwd()}")
        self.logger.info("💻 Send /start to begin")
        
        offset = None
        
        while True:
            try:
                # Get updates from Telegram
                updates = self.get_updates(offset)
                
                if not updates or not updates.get('ok'):
                    time.sleep(1)
                    continue
                
                for update in updates.get('result', []):
                    offset = update['update_id'] + 1
                    
                    if 'message' not in update:
                        continue
                    
                    message = update['message']
                    self.process_message(message)
                    
            except KeyboardInterrupt:
                self.logger.info("Bot stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                time.sleep(5)


def main():
    """Main function to start the bot"""
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Please set your BOT_TOKEN in the environment or update the code")
        print("💡 You can get a bot token from @BotFather on Telegram")
        return
    
    try:
        bot = TelegramBot(BOT_TOKEN)
        bot.run()
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")


if __name__ == "__main__":
    main()