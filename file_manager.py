
import os
import shutil
import mimetypes
import stat
from datetime import datetime
from flask import jsonify
import json

class FileManager:
    def __init__(self):
        self.allowed_operations = ['read', 'write', 'delete', 'rename', 'move', 'copy']
    
    def get_directory_contents(self, path):
        """Get contents of a directory"""
        try:
            if not os.path.exists(path):
                return {'error': 'Directory does not exist'}
            
            if not os.path.isdir(path):
                return {'error': 'Path is not a directory'}
            
            items = []
            try:
                for item_name in sorted(os.listdir(path)):
                    if item_name.startswith('.'):
                        continue  # Skip hidden files for now
                    
                    item_path = os.path.join(path, item_name)
                    item_stat = os.stat(item_path)
                    
                    item_info = {
                        'name': item_name,
                        'path': item_path,
                        'type': 'directory' if os.path.isdir(item_path) else 'file',
                        'size': item_stat.st_size,
                        'modified': datetime.fromtimestamp(item_stat.st_mtime).isoformat(),
                        'permissions': oct(item_stat.st_mode)[-3:],
                        'mime_type': mimetypes.guess_type(item_path)[0] if os.path.isfile(item_path) else None
                    }
                    items.append(item_info)
                
                return {
                    'path': path,
                    'items': items,
                    'parent': os.path.dirname(path) if path != '/' else None
                }
            except PermissionError:
                return {'error': 'Permission denied'}
        except Exception as e:
            return {'error': str(e)}
    
    def read_file(self, file_path):
        """Read file contents"""
        try:
            if not os.path.exists(file_path):
                return {'error': 'File does not exist'}
            
            if not os.path.isfile(file_path):
                return {'error': 'Path is not a file'}
            
            # Check file size (limit to 1MB for text files)
            file_size = os.path.getsize(file_path)
            if file_size > 1024 * 1024:
                return {'error': 'File too large to display'}
            
            # Try to read as text
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return {
                    'path': file_path,
                    'content': content,
                    'type': 'text',
                    'size': file_size
                }
            except UnicodeDecodeError:
                return {'error': 'Binary file cannot be displayed as text'}
        
        except PermissionError:
            return {'error': 'Permission denied'}
        except Exception as e:
            return {'error': str(e)}
    
    def write_file(self, file_path, content):
        """Write content to file"""
        try:
            # Create directory if it doesn't exist
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {'success': True, 'path': file_path}
        
        except PermissionError:
            return {'error': 'Permission denied'}
        except Exception as e:
            return {'error': str(e)}
    
    def create_directory(self, dir_path):
        """Create a new directory"""
        try:
            if os.path.exists(dir_path):
                return {'error': 'Directory already exists'}
            
            os.makedirs(dir_path)
            return {'success': True, 'path': dir_path}
        
        except PermissionError:
            return {'error': 'Permission denied'}
        except Exception as e:
            return {'error': str(e)}
    
    def delete_item(self, item_path):
        """Delete file or directory"""
        try:
            if not os.path.exists(item_path):
                return {'error': 'Item does not exist'}
            
            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
            
            return {'success': True, 'path': item_path}
        
        except PermissionError:
            return {'error': 'Permission denied'}
        except Exception as e:
            return {'error': str(e)}
    
    def rename_item(self, old_path, new_name):
        """Rename file or directory"""
        try:
            if not os.path.exists(old_path):
                return {'error': 'Item does not exist'}
            
            directory = os.path.dirname(old_path)
            new_path = os.path.join(directory, new_name)
            
            if os.path.exists(new_path):
                return {'error': 'An item with that name already exists'}
            
            os.rename(old_path, new_path)
            return {'success': True, 'old_path': old_path, 'new_path': new_path}
        
        except PermissionError:
            return {'error': 'Permission denied'}
        except Exception as e:
            return {'error': str(e)}
    
    def move_item(self, source_path, destination_path):
        """Move file or directory"""
        try:
            if not os.path.exists(source_path):
                return {'error': 'Source item does not exist'}
            
            # If destination is a directory, move into it
            if os.path.isdir(destination_path):
                destination_path = os.path.join(destination_path, os.path.basename(source_path))
            
            if os.path.exists(destination_path):
                return {'error': 'Destination already exists'}
            
            shutil.move(source_path, destination_path)
            return {'success': True, 'source': source_path, 'destination': destination_path}
        
        except PermissionError:
            return {'error': 'Permission denied'}
        except Exception as e:
            return {'error': str(e)}
    
    def copy_item(self, source_path, destination_path):
        """Copy file or directory"""
        try:
            if not os.path.exists(source_path):
                return {'error': 'Source item does not exist'}
            
            # If destination is a directory, copy into it
            if os.path.isdir(destination_path):
                destination_path = os.path.join(destination_path, os.path.basename(source_path))
            
            if os.path.exists(destination_path):
                return {'error': 'Destination already exists'}
            
            if os.path.isfile(source_path):
                shutil.copy2(source_path, destination_path)
            elif os.path.isdir(source_path):
                shutil.copytree(source_path, destination_path)
            
            return {'success': True, 'source': source_path, 'destination': destination_path}
        
        except PermissionError:
            return {'error': 'Permission denied'}
        except Exception as e:
            return {'error': str(e)}
    
    def get_file_tree(self, root_path, max_depth=3):
        """Get file tree structure"""
        def build_tree(path, current_depth=0):
            if current_depth >= max_depth:
                return []
            
            try:
                items = []
                if os.path.isdir(path):
                    # Limit the number of items to prevent timeout
                    dir_items = sorted(os.listdir(path))[:50]  # Limit to 50 items
                    for item_name in dir_items:
                        if item_name.startswith('.'):
                            continue
                        
                        item_path = os.path.join(path, item_name)
                        try:
                            is_dir = os.path.isdir(item_path)
                            item_info = {
                                'name': item_name,
                                'path': item_path,
                                'type': 'directory' if is_dir else 'file'
                            }
                            
                            if is_dir and current_depth < max_depth - 1:
                                item_info['children'] = build_tree(item_path, current_depth + 1)
                            
                            items.append(item_info)
                        except (PermissionError, OSError):
                            continue
                
                return items
            except (PermissionError, OSError):
                return []
        
        try:
            return {
                'path': root_path,
                'tree': build_tree(root_path)
            }
        except Exception as e:
            return {'error': str(e)}

# Global file manager instance
file_manager = FileManager()
