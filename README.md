# AI-Powered Text Editor with Piece Table

A terminal-based text editor built with Python's Textual framework, featuring efficient document editing through a piece table data structure and AI-powered text completion.

## Features

- **Efficient Text Editing**: Uses a piece table implementation for O(1) insert/delete operations
- **AI Text Completion**: Real-time text suggestions powered by local LLM (Ollama) or external APIs
- **Ghost Text Preview**: View AI suggestions before accepting them
- **Auto-generation**: Automatic text suggestions after pausing (debounced)
- **Terminal-Based UI**: Clean, responsive interface with keyboard shortcuts
- **File Operations**: Save, load, and manage text files with modification tracking

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Docker Installation (Recommended)](#docker-installation-recommended)
  - [Manual Installation](#manual-installation)
- [Usage](#usage)
- [File Management](#file-management)
- [Configuration](#configuration)
  - [Using External AI APIs](#using-external-ai-apis)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### For Docker Installation
- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Docker Compose

### For Manual Installation
- Python 3.9 or higher
- pip (Python package installer)
- Ollama (for local AI completions) - [Download here](https://ollama.ai)

## Installation

### Docker Installation (Recommended)

Docker installation handles all dependencies automatically and includes Ollama configuration.

#### Windows

1. **Install Docker Desktop**
   - Download from [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
   - Run the installer and follow the prompts
   - Restart your computer if prompted

2. **Clone or Download the Project**
   ```powershell
   git clone https://github.com/vmanvs/Texter.git
   cd Texter
   ```

3. **Build and Start Services**
   ```powershell
   # Using PowerShell script
   .\run.ps1 build
   .\run.ps1 up
   
   # Or using docker compose directly
   docker compose build
   docker compose up -d
   ```

4. **Run the Editor**
   ```powershell
   # Start with new file
   .\run.ps1 edit
   
   # Open existing file
   .\run.ps1 edit myfile.txt
   ```

#### Linux/Mac

1. **Install Docker**
   ```bash
   # Linux (Ubuntu/Debian)
   sudo apt update
   sudo apt install docker.io docker-compose
   
   # Mac - Download Docker Desktop from docker.com
   ```

2. **Clone or Download the Project**
   ```bash
   git clone https://github.com/vmanvs/Texter.git
   cd Texter
   ```

3. **Build and Start Services**
   ```bash
   # Using Makefile
   make build
   make up
   
   # Or using docker compose directly
   docker compose build
   docker compose up -d
   ```

4. **Run the Editor**
   ```bash
   # Start with new file
   make edit
   
   # Open existing file
   make edit myfile.txt
   ```

### Manual Installation

Manual installation gives you more control but requires setting up Ollama separately.

#### Windows

1. **Install Python**
   - Download Python 3.9+ from [python.org](https://www.python.org/downloads/)
   - During installation, check "Add Python to PATH"

2. **Install Ollama**
   - Download from [ollama.ai](https://ollama.ai/download)
   - Install and start Ollama
   - Pull the model:
     ```powershell
     ollama pull gemma3:1b
     ```

3. **Install Project Dependencies**
   ```powershell
   # Using PowerShell script
   .\run.ps1 install-local
   
   # Or using pip directly
   pip install -r requirements.txt
   ```

4. **Configure API Endpoint**
   
   Open `txtarea.py` and change line **110** from:
   ```python
   f"http://ollama:11434/api/generate",
   ```
   to:
   ```python
   f"http://localhost:11434/api/generate",
   ```

5. **Run the Editor**
   ```powershell
   # Using PowerShell script
   .\run.ps1 run-local
   
   # Or directly with Python
   python txtarea.py
   
   # Open specific file
   python txtarea.py myfile.txt
   ```

#### Linux/Mac

1. **Install Python**
   ```bash
   # Linux (Ubuntu/Debian)
   sudo apt update
   sudo apt install python3 python3-pip
   
   # Mac (using Homebrew)
   brew install python3
   ```

2. **Install Ollama**
   ```bash
   # Linux
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Mac
   brew install ollama
   
   # Pull the model
   ollama pull gemma3:1b
   
   # Start Ollama service (if not auto-started)
   ollama serve
   ```

3. **Install Project Dependencies**
   ```bash
   # Using Makefile
   make install-local
   
   # Or using pip directly
   pip install -r requirements.txt
   ```

4. **Configure API Endpoint**
   
   Open `txtarea.py` and change line **110** from:
   ```python
   f"http://ollama:11434/api/generate",
   ```
   to:
   ```python
   f"http://localhost:11434/api/generate",
   ```

5. **Run the Editor**
   ```bash
   # Using Makefile
   make run-local
   
   # Or directly with Python
   python txtarea.py
   
   # Open specific file
   python txtarea.py myfile.txt
   ```

## Usage

### Starting the Editor

**Docker:**
```bash
# Windows
.\run.ps1 edit [filename]

# Linux/Mac
make edit [filename]
```

**Manual:**
```bash
# Windows
.\run.ps1 run-local [filename]

# Linux/Mac
make run-local [filename]
python txtarea.py [filename]
```

### AI Text Generation

1. **Manual Generation**: Press `Ctrl+G` to request AI completion
2. **Auto-Generation**: Stop typing for 2 seconds to trigger automatic suggestions
3. **Accepting Suggestions**: Press `Tab` to accept the grey ghost text
4. **Dismissing Suggestions**: Type any key to clear ghost text
5. **Cancelling Generation**: Press any key during generation to cancel

## File Management

### File Storage Location

**All files are stored in the `my-files/` directory.**

- **Opening Files**: Files should be placed in `my-files/` directory
  ```bash
  # File structure
  project-root/
  ├── my-files/
  │   ├── myfile.txt      # Your files here
  │   └── notes.txt
  └── txtarea.py
  ```

- **Saving Files**: When you save a file using `Ctrl+S`, it will be automatically saved to `my-files/`
  - If the file doesn't exist, you'll be prompted for a filename
  - The `.txt` extension is added automatically
  - Files are saved as: `my-files/yourfilename.txt`

- **Creating the Directory**:
  ```bash
  # Windows
  mkdir my-files
  
  # Linux/Mac
  mkdir -p my-files
  ```

### File Operations

- `Ctrl+S`: Save current file
- `Ctrl+Q`: Quit (prompts if unsaved changes)
- `Ctrl+D`: Force quit without saving (when in quit dialog)

## Configuration

### Basic Settings

Edit these settings in `txtarea.py`:

**AI Model** (Line 96):
```python
"model": "gemma3:1b"  # Change to your preferred Ollama model
```

**Context Size** (Line 653):
```python
context_size = 3000  # Characters before cursor sent as context
```

**Auto-generation Delay** (Line 56):
```python
self._auto_generate_delay = 2.0  # Seconds of inactivity before auto-gen
```

### Using External AI APIs

You can configure the editor to use external AI APIs like Claude, GPT-4, Gemini, etc., instead of local Ollama.

#### Configuration Steps

1. **Locate the API Configuration**
   
   Open `txtarea.py` and find the `get_completion` method (around line 96-110).

2. **Replace the API Endpoint and Payload**

   **Current Ollama Configuration (Lines 96-110):**
   ```python
   payload = {
       "model": "gemma3:1b",
       "prompt": prompt,
       "stream": False,
       "options": {
           "temperature": 0.3,
           "num_predict": 500,
           "stop": ["\n\n\n", "```"]
       }
   }
   
   async with httpx.AsyncClient(timeout=20.0) as client:
       response = await client.post(
           f"http://localhost:11434/api/generate",  # Line 110
           json=payload,
           timeout=20
       )
   ```

#### Example: Using Claude API

```python
async def get_completion(self, context_before: str, context_after: str = "") -> Optional[str]:
    """Get completion from Claude API"""
    try:
        prompt = context_before
        
        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 500,
            "temperature": 0.3,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                json=payload,
                headers={
                    "x-api-key": "YOUR_ANTHROPIC_API_KEY",
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                timeout=20
            )
        
        if response.status_code == 200:
            data = response.json()
            completion = data['content'][0]['text'].strip()
            return completion
        
        return None
        
    except (httpx.RequestError, Exception):
        return None
```

#### Example: Using OpenAI GPT-4

```python
async def get_completion(self, context_before: str, context_after: str = "") -> Optional[str]:
    """Get completion from OpenAI API"""
    try:
        prompt = context_before
        
        payload = {
            "model": "gpt-4",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful text completion assistant."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 500
        }
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers={
                    "Authorization": "Bearer YOUR_OPENAI_API_KEY",
                    "Content-Type": "application/json"
                },
                timeout=20
            )
        
        if response.status_code == 200:
            data = response.json()
            completion = data['choices'][0]['message']['content'].strip()
            return completion
        
        return None
        
    except (httpx.RequestError, Exception):
        return None
```

#### Example: Using Google Gemini

```python
async def get_completion(self, context_before: str, context_after: str = "") -> Optional[str]:
    """Get completion from Google Gemini API"""
    try:
        prompt = context_before
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 500,
            }
        }
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=YOUR_GEMINI_API_KEY",
                json=payload,
                timeout=20
            )
        
        if response.status_code == 200:
            data = response.json()
            completion = data['candidates'][0]['content']['parts'][0]['text'].strip()
            return completion
        
        return None
        
    except (httpx.RequestError, Exception):
        return None
```

#### Important Notes for External APIs

1. **API Keys**: Replace placeholder API keys with your actual keys
2. **Cost**: External APIs typically charge per request - monitor your usage
3. **Rate Limits**: Be aware of API rate limits to avoid service interruptions
4. **Timeouts**: Adjust the `timeout` parameter if you experience frequent timeouts
5. **Error Handling**: The current implementation has basic error handling; consider adding more robust logging
6. **Security**: Never commit API keys to version control - use environment variables:

```python
import os

api_key = os.getenv("ANTHROPIC_API_KEY")  # Set via environment variable
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | Save file |
| `Ctrl+Q` | Quit (prompts if unsaved) |
| `Ctrl+G` | Manually trigger AI completion |
| `Tab` | Accept ghost text suggestion |
| `Ctrl+D` | Force quit without saving (in quit dialog) |
| `Esc` | Cancel dialog/dismiss ghost text |

## Troubleshooting

### Docker Issues

**Container won't start:**
```bash
# Check container logs
docker compose logs

# Rebuild containers
docker compose down
docker compose build --no-cache
docker compose up -d
```

**Ollama model not loading:**
```bash
# Enter container and pull model manually
docker compose exec ollama ollama pull gemma3:1b
```

### Manual Installation Issues

**"Module not found" errors:**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

**Ollama connection refused:**
```bash
# Check if Ollama is running
ollama list

# Start Ollama service
ollama serve

# Verify endpoint in txtarea.py is set to localhost:11434
```

**Permission errors on Linux:**
```bash
# Add execute permissions to scripts
chmod +x *.sh

# Run Python with correct permissions
python3 txtarea.py
```

### AI Generation Issues

**No AI suggestions appearing:**
1. Verify Ollama/API is running and accessible
2. Check the endpoint URL in `txtarea.py` (line 110)
3. Ensure the model is downloaded: `ollama list`
4. Check for errors in the application logs

**Slow AI responses:**
1. Try a smaller model (e.g., `gemma3:1b` instead of larger models)
2. Reduce context size in configuration
3. Check your system resources (CPU/RAM usage)

### File Issues

**Files not saving:**
1. Ensure `my-files/` directory exists
2. Check write permissions on the directory
3. Verify disk space availability

**Can't open files:**
1. Ensure files are in `my-files/` directory
2. Use correct filename: `python txtarea.py myfile.txt` (not `my-files/myfile.txt`)

## Project Structure

```
project-root/
├── my-files/              # Your text files (create this directory)
│   └── *.txt
├── PieceTable.py          # Core piece table implementation
├── pt_for_textarea.py     # Textual DocumentBase adapter
├── txtarea.py             # Main editor application
├── sysprompt.txt          # AI system prompt
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Docker Compose setup
├── run.ps1                # Windows convenience script
├── Makefile.txt           # Linux/Mac convenience commands
└── README.md              # This file
```

## Performance Characteristics

- **Insert/Delete**: O(1) - only modifies piece array
- **Get Text**: O(n) where n = number of pieces
- **Memory**: O(m) where m = total edited characters

## License

MIT License - Feel free to use and modify for your projects.

## Acknowledgments

- Built with [Textual](https://github.com/Textualize/textual)
- AI powered by [Ollama](https://ollama.ai)
- Piece table concept from [Charles Crowley's research](https://www.cs.unm.edu/~crowley/papers/sds.pdf)