import os

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import TextArea
from textual.document._document import DocumentBase
from pt_for_textarea import PieceTableDocument
from typing import Optional

class NewTextArea(TextArea):
    BINDINGS = [
        Binding("ctrl+s", "save", "Save File", show=True),
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("ctrl+backspace", "delete_word", "Delete Word"),
    ]

    def __init__(self, **kwargs):

        super().__init__(**kwargs)

    def _set_document(self, text: str, language: str | None) -> None:
        document: DocumentBase

        try:
            document = PieceTableDocument(text)
        except Exception as e:
            return e

    def on_mount(self) -> None:
        """Fix for rendering glitch where text is offset by one column
           and the second line is not visible."""
        self.move_cursor_relative(columns=1)
        self.delete((0,1), (0,0))


    def _on_key(self, event: events.Key) -> None:
        if event.character == '*':
            self.insert('**')
            self.move_cursor_relative(columns=-1)
            event.prevent_default()
        if event.character == '(':
            self.insert('()')
            self.move_cursor_relative(columns=-1)
            event.prevent_default()
        if event.character == '[':
            self.insert('[]')
            self.move_cursor_relative(columns=-1)
            event.prevent_default()
        if event.character == '_':
            self.insert('__')
            self.move_cursor_relative(columns=-1)
            event.prevent_default()
        if event.character == '`':
            self.insert('``')
            self.move_cursor_relative(columns=-1)
            event.prevent_default()
        if event.character == '{':
            self.insert('{}')
            self.move_cursor_relative(columns=-1)
            event.prevent_default()



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


    def compose(self) -> ComposeResult:
        yield NewTextArea(text=self.text)



def main():
    import sys

    #check for filename argument
    filename = sys.argv[1] if len(sys.argv) > 1 else None
    editor = Test(filename=filename)
    editor.run()

if __name__ == "__main__":
    main()