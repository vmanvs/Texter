import os
import requests

from pygments.lexer import RegexLexer, bygroups
from pygments.token import Token, Text
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import TextArea, Button
from textual.document._wrapped_document import WrappedDocument
from textual.document._document import DocumentBase
from pt_for_textarea import PieceTableDocument
from typing import Optional


Token.GHOSTTEXT = Token.Token.GHOSTTEXT

class GhostTextLexer(RegexLexer):
    name = "Ghosttext"
    aliases = ["ghosttext"]
    tokens = {
        'root': [
            #Match the content inside <<GHOST:>>
            (r'<<GHOST:(.*?)>>', bygroups(Token.GHOSTTEXT)),
            #Match the content inside <<CONTEXT:>>
            (r'<<CONTEXT:(.*?)', bygroups(Token.GHOSTTEXT)),
            #Match everything else and render normally
            (r'.+?(?=<<)|.$', Text),
            (r'\n', Text)
        ]
    }



class NewTextArea(TextArea):
    BINDINGS = [
        Binding("ctrl+s", "save", "Save File", show=True),
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("ctrl+backspace", "delete_word", "Delete Word"),
    ]

    def __init__(self, **kwargs):

        super().__init__(**kwargs)

    def _set_document(self, text: str, language: str | None) -> None:
        """Initiate the piece table data structure for the document"""

        document: DocumentBase

        try:
            document = PieceTableDocument(text)
        except Exception as e:
            return e

        self.document = document
        self.wrapped_document = WrappedDocument(document, tab_width=self.indent_width)

    def on_mount(self) -> None:
        """Fix for rendering glitch where text is offset by one column
           and the second line is not visible."""
        self.move_cursor_relative(columns=1)
        self.delete((0,1), (0,0))



    def _on_key(self, event: events.Key) -> None:
        """Auto-close brackets and special characters"""
        auto_pairs = {
            '*': '**',
            '(': '()',
            '[': '[]',
            '_': '__',
            '`': '``',
            '{': '{}',
        }

        if event.character in auto_pairs:
            self.insert(auto_pairs[event.character])
            self.move_cursor_relative(columns=-1)
            event.prevent_default()

class OllamaAutocomplete:
    """Handles Ollama autocomplete requests"""

    def __init__(self, model="gemma3:1b", endpoint="http://localhost:11434"):
        self.model = model
        self.endpoint = endpoint
        self.enabled = True

    def get_completion(self, context_before: str, context_after: str = "") -> Optional[str]:
        """Get completion from Ollama (non-streaming)"""
        if not self.enabled:
            return None

        try:
            prompt = context_before

            payload = {
                "model": self.model,
                "system":"Generate a suitable completion for the given text. *Do not repeat paragraphs from the prompt*. *Do not generate markdown*.",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 50,
                    "stop": ["\n\n\n", "```"]
                }
            }

            response = requests.post(
                f"{self.endpoint}/api/generate",
                json=payload,
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                completion = data.get('response', '').strip()
                return completion if completion else None

            return None

        except Exception:
            return None


class Test(App):

    def __init__(self, filename:Optional[str]=None):
        super().__init__()
        self.filename = filename if filename else ""
        self.text = ""

        if filename and os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                self.text = f.read()

    def on_mount(self) -> None:
        """Creates the editor instance once the document is loaded."""
        self.editor = self.query_one(NewTextArea)

    def get_context(self, context_size:int=3000) -> Optional[str]:
        """Get the start and end position of the current context."""
        try:
            # Get current cursor position
            cursor_location = self.editor.selection.end

            # Convert cursor location to index in the document
            cursor_index = self.editor.document.get_index_from_location(cursor_location)

            # Calculate start index (don't go below 0)
            start_index = max(0, cursor_index - context_size)

            # Convert start index back to location
            start_location = self.editor.document.get_location_from_index(start_index)

            # Get the text between start and cursor
            context_text = self.editor.document.get_text_range(start_location, cursor_location)

            return context_text

        except Exception as e:
            self.log(f"Error: {e}")
            return

    def on_button_pressed(self, event:Button.Pressed):
        first_line = self.get_pos_for_context()
        self.log(f"Lines: {first_line}, Cursor Position:{self.cursor_position}")


    def compose(self) -> ComposeResult:
        yield NewTextArea(text=self.text)
        yield Button("Get locations", id="get-location-btn")



def main():
    import sys

    #check for filename argument
    filename = sys.argv[1] if len(sys.argv) > 1 else None
    editor = Test(filename=filename)
    editor.run()

if __name__ == "__main__":
    main()