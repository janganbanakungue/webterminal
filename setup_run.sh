
#!/bin/bash

# Open Directory and Make Directory
cd /workspace/code
mkdir -p web
cd /workspace/code/web

# Auto Setup and Run Script for File Manager Project
echo "🚀 Starting File Manager Project Setup..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python3 is not installed!"
    exit 1
fi

print_success "Python3 is available"

# Check if we're in a Replit environment
if [ -f ".replit" ]; then
    print_status "Detected Replit environment"
    
    # Install Python dependencies using uv (Replit's package manager)
    if command -v uv &> /dev/null; then
        print_status "Installing dependencies with uv..."
        uv sync
        if [ $? -eq 0 ]; then
            print_success "Dependencies installed successfully with uv"
        else
            print_warning "uv sync failed, trying pip..."
            python3 -m pip install flask
        fi
    else
        print_status "Installing dependencies with pip..."
        python3 -m pip install flask
    fi
else
    print_status "Standard environment detected"
    
    # Install dependencies with pip
    print_status "Installing Python dependencies (Flask, Requests, and Delete Blinker..."
    sudo rm -rf /usr/lib/python3/dist-packages/blinker* 
    sudo rm -rf /usr/local/lib/python3.*/dist-packages/blinker* 
    ssudo rm -rf /usr/lib/python3.*/dist-packages/blinker* 
    sudo pip3 install --upgrade setuptools pip 
    sudo python3 -m pip install --upgrade pip
    python3 -m pip3 install flask requests
    
    if [ $? -eq 0 ]; then
        print_success "Flask and Requests installed successfully"
    else
        print_error "Failed to install Flask"
        exit 1
    fi
fi

# Check if required files exist
if [ ! -f "app.py" ]; then
    print_error "app.py not found!"
    exit 1
fi

if [ ! -f "file_manager.py" ]; then
    print_error "file_manager.py not found!"
    exit 1
fi

print_success "All required files found"

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p uploads downloads logs scripts code

# Set permissions
chmod +x "$0"

print_success "Setup completed successfully!"

# Start the application
print_status "Starting File Manager application..."
echo ""
echo "🌐 File Manager will be available at:"
echo "   http://localhost:8082"
echo "   Or click the web preview in Replit"
echo ""
echo "📝 Features available:"
echo "   - File/folder management"
echo "   - Built-in code editor"
echo "   - Web terminal"
echo "   - File upload/download"
echo ""
echo "Press Ctrl+C to stop the server"
echo "----------------------------------------"

# Run the Flask application
nohup python3 /workspace/code/web/app.py > logs 2>&1 
