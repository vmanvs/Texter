import os

from textual.app import App, ComposeResult
from textual.widgets import TextArea
from textual.document._document import Document, DocumentBase
from pt_for_textarea import PieceTableDocument
from typing import Optional

class NewTextArea(TextArea):
    def __init__(self, **kwargs):

        super().__init__(**kwargs)

    def _set_document(self, text: str, language: str | None) -> None:
        document: DocumentBase

        try:
            document = PieceTableDocument(text)
        except Exception as e:
            return e



class Test(App):

    def __init__(self, filename:Optional[str]=None):
        super().__init__()
        self.filename = filename if filename else "Untitled"
        self.text = ""

        if filename and os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                self.text = f.read()


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