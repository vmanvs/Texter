import os
import httpx

from textual import events

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.document._document_navigator import DocumentNavigator
from textual.widgets import TextArea, Button
from textual.document._wrapped_document import WrappedDocument
from textual.containers import Container
from textual.strip import Strip

from rich.style import Style
from rich.segment import Segment

from pt_for_textarea import PieceTableDocument

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

        # If no ghost text is active, or document isn't set, return the default
        if not self._ghost_active or not self.document:
            return strip

        # Get the absolute vertical offset (display line index)
        scroll_x, scroll_y = self.scroll_offset
        absolute_y = scroll_y + y

        # Get the (row, col) document location for the start of this virtual line `y`.
        try:
            # _offset_to_line_info maps absolute_y to (document_line_index, section_index)
            line_info = self.wrapped_document._offset_to_line_info[absolute_y]
            doc_row, section_index = line_info
        except IndexError:
            # We're rendering a line beyond the document (e.g., empty space)
            return strip

        # This is the (row, col) start and end of the ghost text in the document
        ghost_start_loc = self._ghost_start
        ghost_end_loc = self._ghost_end

        # If this document row is not part of the ghost text, exit early.
        if (
                doc_row < ghost_start_loc[0]
                or doc_row > ghost_end_loc[0]
        ):
            return strip

        # This display line IS on a document row that contains ghost text.
        # We need to find the starting *document column* for this section.
        try:
            # get_sections returns the list of wrapped parts for a document line
            all_sections = self.wrapped_document.get_sections(doc_row)
            # The starting column is the sum of the lengths of all preceding sections
            current_doc_col = sum(len(section) for section in all_sections[:section_index])
        except IndexError:
            # This should not happen if _offset_to_line_info is correct, but be safe.
            return strip

        # Now we iterate through the segments of the strip, tracking the *document column*
        new_segments = []

        for segment in strip._segments:
            seg_text = segment.text
            seg_len = len(seg_text)  # Length in characters (codepoints)

            # The document (row, col) range for *this specific segment*
            seg_start_loc = (doc_row, current_doc_col)
            seg_end_loc = (doc_row, current_doc_col + seg_len)

            # Compare the segment's document location with the ghost's location
            # (row, col) tuples can be compared directly.

            # 1. Segment is entirely BEFORE ghost text
            if seg_end_loc <= ghost_start_loc:
                new_segments.append(segment)

            # 2. Segment is entirely AFTER ghost text
            elif seg_start_loc >= ghost_end_loc:
                new_segments.append(segment)

            # 3. Segment is entirely WITHIN ghost text
            elif seg_start_loc >= ghost_start_loc and seg_end_loc <= ghost_end_loc:
                new_segments.append(Segment(seg_text, self._ghost_style))

            # 4. Segment overlaps: starts BEFORE, ends WITHIN ghost
            elif seg_start_loc < ghost_start_loc < seg_end_loc <= ghost_end_loc:
                # ghost_start_loc[1] is the ghost's starting column
                # current_doc_col is the segment's starting column
                split_index = ghost_start_loc[1] - current_doc_col
                new_segments.append(Segment(seg_text[:split_index], segment.style))
                new_segments.append(Segment(seg_text[split_index:], self._ghost_style))

            # 5. Segment overlaps: starts WITHIN, ends AFTER ghost
            elif ghost_start_loc <= seg_start_loc < ghost_end_loc < seg_end_loc:
                split_index = ghost_end_loc[1] - current_doc_col
                new_segments.append(Segment(seg_text[:split_index], self._ghost_style))
                new_segments.append(Segment(seg_text[split_index:], segment.style))

            # 6. Segment overlaps: ghost is contained entirely WITHIN segment
            elif seg_start_loc < ghost_start_loc < ghost_end_loc < seg_end_loc:
                split1_index = ghost_start_loc[1] - current_doc_col
                split2_index = ghost_end_loc[1] - current_doc_col
                new_segments.append(Segment(seg_text[:split1_index], segment.style))
                new_segments.append(Segment(seg_text[split1_index:split2_index], self._ghost_style))
                new_segments.append(Segment(seg_text[split2_index:], segment.style))

            # 7. Default (should be covered by 1 & 2): segment style is unchanged
            else:
                new_segments.append(segment)

            # Advance the document column for the next segment
            current_doc_col += seg_len

        return Strip(new_segments, strip.cell_length)

    """
        def normalize_quotes(self, text: str) -> str: #unoptimized O(n)
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

        #TODO: Remove this
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

        #TODO: remove this
        # Log for debugging
        self.app.log(f"Ghost text ending at position: {self._ghost_end}")
        self.app.log(f"Ghost text range: rows {self._ghost_start[0]} to {self._ghost_end[0]}")

        # Move cursor back to start of ghost text
        self.move_cursor(cursor_pos)
        self._ghost_active = True

        #CRITICAL, clear line cache so that styling is actually applied
        self._line_cache.clear()

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

            self._line_cache.clear()

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

        self._line_cache.clear()

        # Force refresh to remove styling
        self.refresh()

    #TODO: remove this
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

    def get_context_before_cursor(self, sysprompt="", context_size: int = 3000 ) -> str:
        """Get text from a variable number of characters before the cursor to the cursor position."""

        try:
            if sysprompt and os.path.exists(sysprompt):
                with open(sysprompt, 'r', encoding='utf-8') as f:
                    sysprompt = f.read()
            sysprompt = sysprompt

            cursor_location = self.editor.selection.end
            cursor_index = self.editor.document.get_index_from_location(cursor_location)
            start_index = max(0, cursor_index - context_size)
            start_location = self.editor.document.get_location_from_index(start_index)
            context_text = self.editor.document.get_text_range(start_location, cursor_location)

            return f'{sysprompt} {context_text}'

        except Exception as e:
            self.log(f"Error getting context: {e}")
            return ""


    #Redundant, might be useful later
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

    async def handle_ghost(self) -> None:
        """Calls the required methods to render ghost text."""

        context = self.get_context_before_cursor()
        # Get the completion
        completion = await self.editor.get_completion(context_before=context)

        if completion:
            self.log(f"Got completion: %r " % completion)

            self.editor.show_ghost_text(completion)

        else:
            text = "Error showing the text please try again."
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