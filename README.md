# AI-Powered Text Editor with Piece Table

A terminal-based text editor built with Python's Textual framework, featuring efficient document editing through a piece table data structure and AI-powered text completion.

## Features

- **Efficient Text Editing**: Uses a piece table implementation for O(1) insert/delete operations
- **AI Text Completion**: Real-time text suggestions powered by local LLM (Ollama)
- **Ghost Text Preview**: View AI suggestions before accepting them
- **Auto-generation**: Automatic text suggestions after pausing (debounced)
- **Terminal-Based UI**: Clean, responsive interface with keyboard shortcuts
- **File Operations**: Save, load, and manage text files with modification tracking

## Architecture

### Piece Table Implementation

The editor uses a **piece table** data structure for efficient text manipulation:

- **Two Buffers**: Maintains an immutable `original` buffer and an append-only `added` buffer
- **Piece Array**: Tracks text segments as pieces containing references to buffer positions
- **Efficient Operations**: Insert and delete operations only modify the piece array, not the actual text buffers
- **Benefits**: Constant-time edits, easy undo/redo support, and memory efficiency for large documents

The piece table avoids costly string concatenations and copies, making it ideal for text editors handling large files or frequent edits.

### Text Editor Integration

The editor bridges the piece table with Textual's `TextArea` widget through an adapter pattern:

- **PieceTableDocument**: Implements Textual's `DocumentBase` interface
- **Line Caching**: Maintains a cache of document lines for efficient rendering
- **Location Translation**: Converts between (row, column) coordinates and absolute text indices
- **Wrapped Document**: Integrates with Textual's text wrapping and navigation systems

This adapter allows the piece table to work seamlessly with Textual's rich text editing features while maintaining performance benefits.

### LLM Integration

The editor provides AI-powered text completion using a local Ollama instance:

- **Context-Aware**: Sends up to 3000 characters before the cursor as context
- **Ghost Text Rendering**: Displays AI suggestions in grey, italic text
- **Non-Blocking**: Uses async/await for smooth UI responsiveness
- **Cancellable**: User can interrupt generation with any keypress
- **Auto-Generation**: Triggers suggestions automatically after 2 seconds of inactivity (debounced)

The ghost text appears inline at the cursor position and can be accepted with `Tab` or dismissed by typing.

## Installation

### Prerequisites

- Python 3.9+
- Ollama running locally with a model installed

### Setup

1. Install dependencies:
```bash
pip install textual httpx
```

2. Install and start Ollama:
```bash
# Install Ollama from https://ollama.ai
ollama pull gemma3:1b  # or your preferred model
ollama serve
```

3. Clone this repository and navigate to the directory

## Usage

### Starting the Editor

```bash
# Create new file
python txtarea.py

# Open existing file
python txtarea.py myfile.txt
```

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | Save file |
| `Ctrl+Q` | Quit (prompts if unsaved) |
| `Ctrl+G` | Manually trigger AI completion |
| `Tab` | Accept ghost text suggestion |
| `Ctrl+D` | Force quit without saving |
| `Esc` | Cancel dialog/dismiss ghost text |

### AI Text Generation

1. **Manual Generation**: Press `Ctrl+G` to request AI completion
2. **Auto-Generation**: Stop typing for 2 seconds to trigger automatic suggestions
3. **Accepting Suggestions**: Press `Tab` to accept the grey ghost text
4. **Dismissing Suggestions**: Type any key to clear ghost text
5. **Cancelling Generation**: Press any key during generation to cancel

## Configuration

Edit these settings in `txtarea.py`:

```python
# AI model (in NewTextArea.get_completion)
"model": "gemma3:1b"

# Context size (characters before cursor)
context_size = 3000

# Auto-generation delay (seconds)
self._auto_generate_delay = 2.0
```

## Project Structure

```
├── PieceTable.py           # Core piece table implementation
├── pt_for_textarea.py      # Textual DocumentBase adapter
├── txtarea.py              # Main editor application
└── README.md               # This file
```

## How It Works

### Text Editing Flow

1. User types → `NewTextArea` receives keystroke
2. Edit operation → `PieceTableDocument.replace_range()` called
3. Piece table updated → Only piece array modified, buffers unchanged
4. Cache invalidated → Lines cache cleared for re-rendering
5. UI refreshed → Textual renders updated document

### AI Completion Flow

1. User pauses typing → Debounce timer starts (2 seconds)
2. Timer fires → Context extracted (3000 chars before cursor)
3. API request → Sent to local Ollama instance
4. Response received → Text inserted as "ghost" at cursor
5. User accepts/dismisses → Ghost text accepted or removed

### Ghost Text Rendering

The editor overrides `render_line()` to apply custom styling:

- Calculates which display lines contain ghost text
- Splits line segments at ghost text boundaries
- Applies grey, italic styling to ghost segments
- Preserves other text styling unchanged

## Performance Characteristics

- **Insert/Delete**: O(1) - only modifies piece array
- **Get Text**: O(n) where n = number of pieces
- **Find Position**: O(p) where p = number of pieces (can be optimized with binary search)
- **Memory**: O(m) where m = total edited characters (original + additions)

## Limitations

- Requires local Ollama instance
- No syntax highlighting (can be added)
- Limited to single-file editing
- Auto-generation may feel intrusive for some workflows

## Future Improvements

- [ ] Binary search optimization for `get_piece_and_offset()`
- [ ] Undo/redo stack using piece table checkpoints
- [ ] Syntax highlighting support
- [ ] Multi-file tabs
- [ ] Configurable AI model parameters
- [ ] Streaming AI responses for longer completions
- [ ] Custom keybindings configuration

## License

MIT License - Feel free to use and modify for your projects.

## Contributing

Contributions welcome! Please ensure:
- Code follows existing style conventions
- Add tests for new features
- Update documentation for API changes

## Acknowledgments

- Built with [Textual](https://github.com/Textualize/textual)
- AI powered by [Ollama](https://ollama.ai)
- Piece table concept from classic text editor research - [Charles Crowley](https://www.cs.unm.edu/~crowley/papers/sds.pdf)
