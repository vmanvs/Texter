import os
import requests
import asyncio

import httpx

from textual import events

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.document._document_navigator import DocumentNavigator
from textual.widgets import TextArea, Button
from textual.document._wrapped_document import WrappedDocument

from textual.document._document import DocumentBase
from textual.containers import Container
from textual.strip import Strip
from rich.style import Style
from rich.segment import Segment
from pt_for_textarea2 import PieceTableDocument
from typing import Optional


class NewTextArea(TextArea):
    BINDINGS = [
        Binding("ctrl+s", "save", "Save File", show=True),
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("ctrl+backspace", "delete_word", "Delete Word"),
        Binding("ctrl+g", "toggle_ghost", "Toggle Ghost Text", show=True),
        Binding("tab", "accept_ghost", "Accept Ghost", show=False),
    ]

    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        text = kwargs.get("text", "")

        try:
            document = PieceTableDocument(text)
            self.document = document
        except Exception as e:
            document = PieceTableDocument("")

        self.wrapped_document = WrappedDocument(
            document,
            tab_width=self.indent_width
        )

        self.navigator = DocumentNavigator(self.wrapped_document)

        self._rewrap_and_refresh_virtual_size()

        self._ghost_active = False
        self.ghost_text = ""
        self._ghost_start = (0, 0)
        self._ghost_end = (0, 0)
        # Ghost style: grey at 60% opacity
        self._ghost_style = Style(color="rgb(128,128,128)", dim=True, italic=True)

    """def _set_document(self, text: str, language: str | None) -> None:
        #Initiate the piece table data structure for the document

        document: DocumentBase

        try:
            document = PieceTableDocument(text)
        except Exception as e:
            return

        self.document = document
        width = self.size.width
        self.wrapped_document = WrappedDocument(document, tab_width=self.indent_width, width=width)
    """

    """def on_mount(self) -> None:
        Fix for rendering glitch where text is offset by one column
           and the second line is not visible.
        self.move_cursor_relative(columns=1)
        self.delete((0,1), (0,0))

    """

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

    def render_line(self, y: int) -> Strip:
        # Override render_line to apply custom styling to ghost text.
        # Get the default rendered line
        strip = super().render_line(y)

        # If no ghost text is active, return the default
        if not self._ghost_active:
            return strip

        # Extract the text content from this strip
        strip_text = ''.join(seg.text for seg in strip._segments)

        # Check if this strip contains any part of our ghost text
        ghost_lines = self.ghost_text.split('\n')

        # Find which ghost line (if any) appears in this strip
        # We need exact matching to avoid styling old ghost text locations
        matching_ghost_line_idx = None
        for idx, ghost_line in enumerate(ghost_lines):
            # Must match the exact ghost line content (not just a substring)
            if ghost_line and ghost_line in strip_text:
                # Additional check: make sure this is actually our current ghost text
                # by verifying the line content matches what should be there
                matching_ghost_line_idx = idx
                break

        if matching_ghost_line_idx is None:
            return strip

        # Get the actual ghost line we're styling
        ghost_line = ghost_lines[matching_ghost_line_idx]

        # Find where in the strip the ghost text actually starts
        # This handles the issue where ghost text might not start at column 0
        ghost_text_position_in_strip = strip_text.find(ghost_line)
        if ghost_text_position_in_strip == -1:
            return strip  # Ghost line not found in this strip

        # Determine which columns should be styled as ghost
        if matching_ghost_line_idx == 0:
            # First line of ghost text
            # The ghost starts at ghost_start_col in the document
            # But in the rendered strip, it appears at ghost_text_position_in_strip
            ghost_col_start = ghost_text_position_in_strip
            if len(ghost_lines) == 1:
                # Single line ghost text
                ghost_col_end = ghost_col_start + len(ghost_line)
            else:
                # Multi-line, first line goes to end
                ghost_col_end = ghost_col_start + len(ghost_line)
        elif matching_ghost_line_idx == len(ghost_lines) - 1:
            # Last line of ghost text
            ghost_col_start = ghost_text_position_in_strip
            ghost_col_end = ghost_col_start + len(ghost_line)
        else:
            # Middle line - entire ghost line is styled
            ghost_col_start = ghost_text_position_in_strip
            ghost_col_end = ghost_col_start + len(ghost_line)

        # Apply ghost styling only to the segments within the column range
        new_segments = []
        current_col = 0

        for segment in strip._segments:
            seg_text = segment.text
            seg_len = len(seg_text)
            seg_end_col = current_col + seg_len

            # Check if this segment overlaps with ghost column range
            if seg_end_col <= ghost_col_start or current_col >= ghost_col_end:
                # No overlap - keep original
                new_segments.append(segment)
            elif current_col >= ghost_col_start and seg_end_col <= ghost_col_end:
                # Fully within ghost range
                new_segments.append(Segment(seg_text, self._ghost_style))
            else:
                # Partial overlap - split the segment
                if current_col < ghost_col_start < seg_end_col:
                    # Split at start of ghost
                    before_len = ghost_col_start - current_col
                    new_segments.append(Segment(seg_text[:before_len], segment.style))

                    if seg_end_col <= ghost_col_end:
                        # Rest is ghost
                        new_segments.append(Segment(seg_text[before_len:], self._ghost_style))
                    else:
                        # Also split at end of ghost
                        ghost_len = ghost_col_end - ghost_col_start
                        new_segments.append(Segment(seg_text[before_len:before_len + ghost_len], self._ghost_style))
                        new_segments.append(Segment(seg_text[before_len + ghost_len:], segment.style))
                elif current_col < ghost_col_end < seg_end_col:
                    # Split at end of ghost
                    ghost_len = ghost_col_end - current_col
                    new_segments.append(Segment(seg_text[:ghost_len], self._ghost_style))
                    new_segments.append(Segment(seg_text[ghost_len:], segment.style))

            current_col = seg_end_col

        return Strip(new_segments, strip.cell_length)

    """
        def normalize_quotes(self, text: str) -> str:
            #Convert Unicode quotes to ASCII quotes for matching.
            # Replace various Unicode quotes with ASCII equivalents
            replacements = {
                '\u201c': '"',  # LEFT DOUBLE QUOTATION MARK
                '\u201d': '"',  # RIGHT DOUBLE QUOTATION MARK
                '\u2018': "'",  # LEFT SINGLE QUOTATION MARK
                '\u2019': "'",  # RIGHT SINGLE QUOTATION MARK
                '\u2013': '-',  # EN DASH
                '\u2014': '-',  # EM DASH
                '\u2026': '...',  # HORIZONTAL ELLIPSIS
            }
            for unicode_char, ascii_char in replacements.items():
                text = text.replace(unicode_char, ascii_char)
            return text
    """

    def show_ghost_text(self, text: str) -> None:
        """Display ghost text at the current cursor position in grey.

        The text will appear in grey at 60% opacity.
        Press Tab to accept the ghost text, or any other key to dismiss it.

        Args:
            text: The ghost text to display
        """
        if self._ghost_active:
            self.clear_ghost_text()

        cursor_pos = self.selection.end
        self._ghost_start = cursor_pos
        self.ghost_text = text

        # Log for debugging
        self.app.log(f"Ghost text starting at position: {cursor_pos}")

        # Insert the text normally
        self.insert(text, cursor_pos)

        # Calculate end position
        end_row, end_col = cursor_pos
        lines_in_ghost = text.count('\n')
        if lines_in_ghost > 0:
            last_line = text.split('\n')[-1]
            self._ghost_end = (end_row + lines_in_ghost, len(last_line))
        else:
            self._ghost_end = (end_row, end_col + len(text))

        # Log for debugging
        self.app.log(f"Ghost text ending at position: {self._ghost_end}")
        self.app.log(f"Ghost text range: rows {self._ghost_start[0]} to {self._ghost_end[0]}")

        # Move cursor back to start of ghost text
        self.move_cursor(cursor_pos)
        self._ghost_active = True

        # Force refresh to apply styling
        self.refresh()

    def clear_ghost_text(self) -> None:
        """Remove the ghost text from the document."""
        if not self._ghost_active:
            return

        try:
            # Delete the range
            self.delete(self._ghost_start, self._ghost_end)

            self._ghost_active = False
            self.ghost_text = ""
            self._ghost_start = (0, 0)
            self._ghost_end = (0, 0)

            # Force refresh
            self.refresh()
        except Exception as e:
            # Reset flags on error
            self._ghost_active = False
            self.ghost_text = ""

    def accept_ghost_text(self) -> None:
        """Accept the ghost text and keep it as real text."""
        if not self._ghost_active:
            return

        # Move cursor to end of accepted text
        self.move_cursor(self._ghost_end)

        # Just reset flags - the text is already in the document
        self._ghost_active = False
        self.ghost_text = ""
        self._ghost_start = (0, 0)
        self._ghost_end = (0, 0)

        # Force refresh to remove styling
        self.refresh()

    def action_toggle_ghost(self) -> None:
        """Action to toggle ghost text (for testing)."""
        if self._ghost_active:
            self.clear_ghost_text()
        else:
            self.show_ghost_text("    # This is grey ghost text\n    return result")

    def action_accept_ghost(self) -> None:
        """Action to accept ghost text with Tab key."""
        if self._ghost_active:
            self.accept_ghost_text()

            return
        # If no ghost text, let default Tab behavior happen
        position = self.selection.end
        self.insert(" " * 4, position)

    async def get_completion(self, context_before: str, context_after: str = "") -> Optional[str]:
        """Get completion from Ollama (non-streaming)"""
        try:
            prompt = context_before

            payload = {
                "model": "gemma3:1b",
                "system": "Generate a suitable completion for the given text. *Do not repeat paragraphs from the prompt*. *Do not generate markdown*.",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 50,
                    "stop": ["\n\n\n", "```"]
                }
            }

            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"http://localhost:11434/api/generate",
                    json=payload,
                    timeout=20
                )

            if response.status_code == 200:
                data = response.json()
                completion = data.get('response', '').strip()
                return completion

            return None

        except (httpx.RequestError, Exception):
            return None


class Test(App):
    CSS = """
    Screen {
        background: $surface;
    }

    NewTextArea {
        width: 100%;
        height: 1fr;
        border: solid $primary;
    }

    #button-container {
        height: auto;
        padding: 1;
        background: $boost;
        dock: bottom;
    }

    Button {
        margin: 0 1;
    }
    """

    def __init__(self, filename: Optional[str] = None):
        super().__init__()
        self.filename = filename if filename else ""
        self.text = ""

        if filename and os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                self.text = f.read()

    def on_mount(self) -> None:
        """Creates the editor instance once the document is loaded."""
        self.editor = self.query_one(NewTextArea)

    def get_context_before_cursor(self, context_size: int = 3000) -> str:
        """Get text from a variable number of characters before the cursor to the cursor position."""
        try:
            cursor_location = self.editor.selection.end
            cursor_index = self.editor.document.get_index_from_location(cursor_location)
            start_index = max(0, cursor_index - context_size)
            start_location = self.editor.document.get_location_from_index(start_index)
            context_text = self.editor.document.get_text_range(start_location, cursor_location)
            sysprompt = "Generate a suitable completion of at least 100 words with meaningful sentences that do not end abruptly for the given text. *Do not repeat paragraphs from the prompt*. *Do not generate markdown*.\n"
            return f'{sysprompt} {context_text}'
        except Exception as e:
            self.log(f"Error getting context: {e}")
            return ""

    def get_pos_for_context(self, context_size: int = 3000) -> tuple[tuple[int, int], tuple[int, int]]:
        """Get the start and end position of the current context."""
        try:
            end_location = self.editor.selection.end
            end_index = self.editor.document.get_index_from_location(end_location)
            start_index = max(0, end_index - context_size)
            start_location = self.editor.document.get_location_from_index(start_index)
            return start_location, end_location
        except Exception as e:
            self.notify(f"Error getting positions: {e}")
            return (0, 0), (0, 0)

    async def handle_ghost(self):
        context = self.get_context_before_cursor()
        # Get the completion
        completion = await self.editor.get_completion(context_before=context)

        if completion:
            self.log(f"Got completion: %r " % completion)
            text = "“The data streams here aren’t just repeating; they’re fracturing, like a shattered mirror,” Elara stated, herscanner focusing on a particularly chaotic cluster of holographic projections—a chaotic collage of Cygnus Prime’s past,"
            self.editor.show_ghost_text(
                "This is a ghost text. And this, this my friend is an awfully long ghost text, I dont know why it exists, but the very fact ")
        else:
            text = "“The data streams here aren’t just repeating; they’re fracturing, like a shattered mirror,” Elara stated, herscanner focusing "
            self.editor.show_ghost_text(text)

    async def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses for different ghost text operations."""
        button_id = event.button.id

        if button_id == "show-ghost":
            await self.handle_ghost()
            self.log(self.editor.ghost_text)

        if button_id == "accept-ghost":
            self.editor.accept_ghost_text()

        if button_id == "cancel-ghost":
            self.editor.clear_ghost_text()

    def compose(self) -> ComposeResult:
        yield NewTextArea(text=self.text)
        with Container(id="button-container"):
            yield Button("Show Ghost Text (Ctrl+G)", id="show-ghost", variant="primary")
            yield Button("Cancel Ghost", id="cancel-ghost", variant="primary")
            yield Button("Accept Ghost", id="accept-ghost", variant="primary")


def main():
    import sys

    # check for filename argument
    filename = sys.argv[1] if len(sys.argv) > 1 else None
    editor = Test(filename=filename)
    editor.run()


if __name__ == "__main__":
    main()