import os
import httpx
import asyncio

from textual import events

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.document._document import EditResult
from textual.document._document_navigator import DocumentNavigator
from textual.document._edit import Edit
from textual.widget import Widget
from textual.widgets import TextArea, Button, Header, Footer, Label, Input, LoadingIndicator, Static
from textual.screen import Screen
from textual.document._wrapped_document import WrappedDocument
from textual.containers import Container
from textual.strip import Strip
from textual.timer import Timer

from rich.style import Style
from rich.segment import Segment

from pt_for_textarea import PieceTableDocument

from typing import Optional


class NewTextArea(TextArea):
    BINDINGS = [
        Binding("ctrl+s", "save", "Save File", show=True),
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("ctrl+backspace", "delete_word", "Delete Word", show=False),
        Binding("tab", "accept_ghost", "Accept AI", show=True),
        Binding("ctrl+g", "generate_text", "Generate Text", show=True),
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

        self.filename = ""
        self.modified = False
        self._quit_after_save = False

        self._ghost_active = False
        self.ghost_text = ""
        self._ghost_start = (0, 0)
        self._ghost_end = (0, 0)
        # Ghost style: grey at 60% opacity
        self._ghost_style = Style(color="rgb(128,128,128)", dim=True, italic=True)

        self.auto_generate_enabled: bool = True
        self._auto_generate_delay: float = 2.0
        self._auto_generate_timer: Timer | None = None

    """
    def _on_key(self, event: events.Key) -> None:
        #Auto-close brackets and special characters
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
    """

    async def get_completion(self, context_before: str, context_after: str = "") -> Optional[str]:
        """Get completion from Ollama (non-streaming)"""
        try:
            prompt = context_before

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
                    f"http://ollama:11434/api/generate",
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

    def edit(self, edit: Edit) -> EditResult:
        """Override edit to track modifications."""
        if not self.modified:
            self.modified = True
        return super().edit(edit)

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

        # Log for debugging
        #self.app.log(f"Ghost text starting at position: {cursor_pos}")

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
        #self.app.log(f"Ghost text ending at position: {self._ghost_end}")
        #self.app.log(f"Ghost text range: rows {self._ghost_start[0]} to {self._ghost_end[0]}")

        # Move cursor back to start of ghost text
        self.move_cursor(cursor_pos)
        self._ghost_active = True

        # CRITICAL, clear line cache so that styling is actually applied
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

    def on_key(self, event: events.Key) -> None:
        """
        Handle key presses to:
        1. Cancel in-progress AI generation.
        2. Clear active ghost text on any key press (except Tab).
        3. Implements Debounce Logic for text generation if no input for a spicified period of time.
        """

        # 1. Check if AI is running and cancel it
        if self.app.ai_task and not self.app.ai_task.done():
            # Any key press (even modifiers) will cancel the request.
            self.app.log("Key press detected during AI generation, cancelling...")
            self.app.cancel_ai_generation()
            return  # Stop all further processing

        # 2. Check if ghost text is active and clear it
        if self._ghost_active:
            key = event.key

            # The 'tab' key is handled by 'action_accept_ghost', so we ignore it.
            if key == "tab":
                pass
            # Ignore pure modifier keys (Shift, Ctrl, etc.)
            elif key in ("shift", "ctrl", "alt", "meta"):
                pass
            # Any other key (e.g., 'a', 'backspace', 'enter', 'arrow_up')
            # will clear the ghost text.
            else:
                self.clear_ghost_text()
                # We DON'T prevent_default() here. We want the key press
                # (e.g., typing 'a' or pressing 'backspace')
                # to be processed normally *after* the ghost is cleared.

        #---Debounce Logic---
        if self.auto_generate_enabled:
            key = event.key
            if key not in ("shift", "ctrl", "alt", "meta"):
                #If timer is already running stop it
                if self._auto_generate_timer:
                    self._auto_generate_timer.stop()
                    self.app.log(f"Debounce timer reset.")

            self._auto_generate_timer = self.set_timer(
                self._auto_generate_delay,
                self._trigger_auto_generation,
                name="AutogenDebounce"
            )



        # 3. Call the parent implementation
        # This allows all default behavior (typing, bindings, actions)
        # to run *after* our logic.
        super()._on_key(event)

    def _trigger_auto_generation(self) -> None:
        """Called by debounce timer to trigger auto-generation."""
        if self.auto_generate_enabled:
            self.app.log(f"Debounce Generation fired.")
            #Clear Timer Reference
            self._auto_generate_timer = None

            #Do not generate if feature disabled
            if not self.auto_generate_enabled:
                return

            if self.app.ai_task and not self.app.ai_task.done():
                self.app.log(f"Debounce-Gen skipped: AI-Gen already in progress.")
                return

            if self._ghost_active:
                self.app.log(f"Debounce-Gen skipped: Ghost text already active.")
                return

            if not self.text.strip():
                self.app.log(f"Debounce-Gen skipped: No text.")
                return

            #---Checks passed, trigger autogen---
            self.app.log("Debounce-Gen started.")

            asyncio.create_task(self.action_generate_text())


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



    def action_accept_ghost(self) -> None:
        """Action to accept ghost text with Tab key."""
        if self._ghost_active:
            self.accept_ghost_text()

            return
        # If no ghost text, let default Tab behavior happen
        position = self.selection.end
        self.insert(" " * 4, position)

    def _write_file_sync(self, filename: str, text: str):
        """Synchronous file writing function to be run in a thread."""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(text)
        self.modified = False

    async  def action_generate_text(self) -> None:
        """Action to toggle ghost text (for testing)."""

        if self.app.ai_task:
            self.app.log(f"AI generator is running")
            return
        self.app.ai_task = asyncio.create_task(self.app.handle_ghost_wrapper())


    async def handle_save_dialog_result(self, filename: Optional[str]):
        """
        Callback for when the SaveScreen is dismissed.
        This method is run *after* the user interacts with the save dialog.
        """
        if filename:  # User provided a filename
            text = self.text
            cwd = os.getcwd()
            self.filename = f"{filename}.txt"
            self.app.title = filename  # Update app title

            try:
                # Run the blocking I/O in a separate thread
                await asyncio.to_thread(self._write_file_sync, self.filename, text)
                self.app.notify(f"{filename} saved to {cwd}")
                if self._quit_after_save:
                    self._quit_after_save = False
                    self.app.exit()
            except Exception as e:
                self.app.notify(f"Failed to save file: {e}", severity="error")

        else:  # User cancelled
            self.app.notify("Save cancelled")


    async def handle_quit_dialog_result(self, save: Optional[bool]):
        """
        Callback for when the QuitScreen is dismissed.
        """
        if save is True:
            result = await self.action_save()
            if result and result[0]:
                #Save successful, quit
                self.app.exit()
            elif result is None:
                #Save screen was pushed, set quit after save to true
                self._quit_after_save = True
            else:
                self.app.notify(f"Failed to quit file", severity="error")
        if save is False:
            self.app.exit()
        if save is None:
            self.app.notify("Quit cancelled")


    def action_quit(self) -> None:
        if self.modified:
            self.app.push_screen(QuitScreen(), self.handle_quit_dialog_result)
        else:
            self.app.exit()


    async def action_save(self, **kwargs) -> Optional[tuple[bool, str]]:
        """Action to save the file"""
        text = self.text
        cwd = os.getcwd()

        try:
            # Case 1 & 2: We have a valid filename (new or existing)
            if self.filename and self.filename != "untitled":
                # Run the blocking I/O in a separate thread
                await asyncio.to_thread(self._write_file_sync, self.filename, text)


                self.app.notify(f"{self.filename} saved to {cwd}")
                return True, f"{self.filename} saved"

            # Case 3: Filename is "untitled" or empty.
            else:
                # Push the SaveScreen and set our new callback to handle the result.
                # This is NON-BLOCKING. The action_save method finishes here.
                self.app.push_screen(SaveScreen(), self.handle_save_dialog_result)

                # We can't return a status because the operation is
                # now asynchronous. The callback will handle notifications.
                return

        except Exception as e:
            self.app.notify(f"Failed to save file: {e}", severity="error")
            # Check if we were in the 'if' block
            if self.filename and self.filename != "untitled":
                return False, f"Failed to save file: {e}"


# TODO: add these to a separate file

class Left(Widget):
    DEFAULT_CSS = """
    Left {
        align-horizontal: left;
        width: 1fr;
        height: auto;
        margin-top: 2;
    }
    """


class Right(Widget):
    """A container which aligns children on the X axis."""

    DEFAULT_CSS = """
    Right {
        align-horizontal: right;
        width: 1fr;
        height: auto;
        margin-top: 2;
    }
    """

class Center(Widget):
    """A container which aligns children on the X axis."""

    DEFAULT_CSS = """
    Center {
        align-horizontal: center;
        width: 1fr;
        height: auto;
        margin-top: 2;
    }
    """



class AbsCenter(Widget):
    """A container which aligns children on the both axes."""

    DEFAULT_CSS = """
        AbsCenter {
            align-horizontal: center;
            align-vertical: middle;
            width: 1fr;
            height: 1fr;
        }
        """


class SaveScreen(Screen[str]):
    """Screen for saving a file with user input."""
    CSS = """
    #label1 {
        margin-top: 1;
        margin-bottom: 2;
    }

    #label2 {
        margin-bottom: 1;
    }
    """

    BINDINGS = [("escape", "dismiss(None)", "Cancel")]

    def compose(self) -> ComposeResult:
        from textual.containers import Horizontal, VerticalGroup

        yield Header()

        with AbsCenter():
            dialog = VerticalGroup(id="dialog")
            dialog.styles.width = 60
            dialog.styles.height = 24
            dialog.styles.border = ("thick", "grey")
            dialog.styles.background = "black"
            dialog.styles.padding = (1, 2)
            dialog.border_title = "Save File"

            with dialog:
                yield Label("Enter filename to save:", id="label1")
                yield Input(placeholder="filename", id="filename_input")
                with Horizontal(classes="button-group"):
                    with Right():
                        yield Button("Save", variant="primary", id="save_btn")
                    with Left():
                        yield Button("Cancel", variant="default", id="cancel_btn")
                yield Label("You cannot name a file 'untitled', with lowercase 'u'.", id='label2')
                yield Label("'.txt' to the filename is auto added.")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_btn":
            input_widget = self.query_one("#filename_input", Input)
            if input_widget.value != "":
                filename = input_widget.value
                if filename.strip():
                    self.dismiss(filename)
            else:
                self.notify("Please enter a filename")
        elif event.button.id == "cancel_btn":
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle when user presses Enter in the input."""
        filename = event.value
        if filename.strip():
            self.dismiss(filename)
        else:
            self.notify("Please enter a filename")

class QuitScreen(Screen[bool]):

    BINDINGS = [
        Binding("ctrl+d", "dismiss(False)", "Force Quit", show=True),
        Binding("escape", "dismiss(None)", "Cancel", show=True),
        Binding("ctrl+s", "dismiss(True)", "Save", show=True),
    ]

    CSS = """
        #label1 {
            margin-top: 1;
            margin-bottom: 2;
        }
    """


    def compose(self) -> ComposeResult:
        from textual.containers import Horizontal, VerticalGroup

        yield Header()

        with AbsCenter():
            dialog = VerticalGroup(id="dialog")
            dialog.styles.width = 60
            dialog.styles.height = 24
            dialog.styles.border = ("thick", "grey")
            dialog.styles.background = "black"
            dialog.styles.padding = (1, 2)
            dialog.border_title = "Quit"

            with dialog:
                yield Label(f"The file '{self.app.filename}' was modified, save changes?", id="label1")
                with Horizontal(classes="button-group"):
                    with Right():
                        yield Button(label="Save", variant="primary", id="save_btn")
                    with Center():
                        yield Button(label="Force Quit", variant="warning", id='force_quit')
                    with Left():
                        yield Button(label="Cancel", variant="default", id="cancel_btn")
                yield Label("Use 'TAB' or bindings on footer to navigate.")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:

        if event.button.id == "save_btn":
            self.dismiss(True)
        if event.button.id == "force_quit" :
            self.dismiss(False)
        if event.button.id == "cancel_btn":
            self.dismiss(None)


class Test(App):

    CSS = """
    NewTextArea {
        width: 100%;
        height: 1fr;
        border: solid $primary;
    }

    #button-container {
        height: 1;
        background: $boost;
        dock: bottom;
        layout: horizontal;
        align: left middle;
    }

    Button {
        margin: 0 1;
    }
    
    #status-bar {
        dock: bottom;
        height: 1;
        width: 100%;
        layout: horizontal;
        background: $boost;
        display: none; /* Start hidden */
        padding: 0 1;
        align: left middle;
    }
    
    #ai-loader {
        margin-right: 1;
        width: 60%;
        display: none; /* Hide loader initially */
    }

    #ai-status {
        width: 1fr;
        color: $text-muted;
    }
    """

    def __init__(self, filename: Optional[str] = None):
        super().__init__()
        self.filename = filename if filename else ""
        self.text = ""

        self.ai_task: asyncio.Task | None = None

        if filename and os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                self.text = f.read()


    def on_mount(self) -> None:
        """Sets required attributes, once the app runs."""
        # Creates the editor instance once the document is loaded.
        self.editor = self.query_one(NewTextArea)


        # Set Title
        self.title = self.filename
        self.editor.filename = self.filename

    def get_context_before_cursor(self, sysprompt="", context_size: int = 3000) -> str:
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
            self.log(context_text)
            return f'{sysprompt} {context_text}'

        except Exception as e:
            self.log(f"Error getting context: {e}")
            return ""

    # Redundant, might be useful later
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

    def clear_status(self) -> None:
        """Clears the contents of the status bar and hides it"""
        try:
            status_bar = self.query_one("#status-bar")
            loader = self.query_one("#ai-loader", LoadingIndicator)
            status_text = self.query_one("#ai-status", Static)

            status_bar.styles.display = "none"
            loader.styles.display = "none"
            status_text.update("")
        except Exception as e:
            pass #in case widgets not mounted

    async def handle_ghost(self) -> None:
        """Calls the required methods to render ghost text."""

        status_bar = self.query_one("#status-bar")
        loader = self.query_one("#ai-loader", LoadingIndicator)
        status_text = self.query_one("#ai-status", Static)

        try:
            # --- SHOW "LOADING" STATE ---
            status_bar.styles.display = "block"
            loader.styles.display = "block"
            status_text.update("Generating AI text...")

            context = self.get_context_before_cursor()
            # self.notify() # No longer needed, we have a status bar

            # Get the completion
            completion = await (self.editor.get_completion(context_before=context))

            if completion:
                self.log(f"Got completion: %r " % completion)
                self.editor.show_ghost_text(completion)
                # --- HIDE ON SUCCESS ---
                self.clear_status()

            else:
                text = "Error showing the text please try again."
                self.editor.show_ghost_text(text)
                # --- SHOW ERROR STATE ---
                loader.styles.display = "none"
                status_text.update("[Error] AI generation failed.")
                # Hide error after 3 seconds
                self.set_timer(3.0, self.clear_status)

        except Exception as e:
            self.log(f"Error in handle_ghost: {e}")
            # --- SHOW EXCEPTION STATE ---
            loader.styles.display = "none"
            status_text.update(f"[Error] {e}")
            self.set_timer(3.0, self.clear_status)

    async def handle_ghost_wrapper(self) -> None:
        """Wraps handle_ghost to provide cleanup."""
        try:
            # Run the actual generation logic
            await self.handle_ghost()

        except asyncio.CancelledError:
            self.log(f"AI generator task was cancelled.")
            # Ensure status is cleared if cancelled
            self.clear_status()

        except Exception as e:
            self.log(f"AI generator task error: {e}")
            # Show a fallback error
            loader = self.query_one("#ai-loader", LoadingIndicator)
            status_text = self.query_one("#ai-status", Static)
            loader.styles.display = "none"
            status_text.update(f"[Critical Error] {e}")
            self.set_timer(3.0, self.clear_status)

        finally:
            # This 'finally' block now runs when the *task* finishes,
            # not when the *action* finishes.
            self.log(f"AI task finished, clearing task reference.")
            self.ai_task = None  # This is the cleanup


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

    def cancel_ai_generation(self) -> None:
        if self.ai_task:
            self.ai_task.cancel()
            self.log(self.ai_task.done())
            self.log(f"AI generation cancelled.")


    def action_quit(self) -> None:
        self.editor.action_quit()

    def compose(self) -> ComposeResult:
        yield NewTextArea(text=self.text)
        yield Header()

        yield Footer()

        with Container(id="status-bar"):
            yield Static(id="ai-status")

            yield LoadingIndicator(id="ai-loader")

        #with Container(id="button-container"):
        #    yield Button("Show Ghost Text (Ctrl+G)", id="show-ghost", variant="primary")
        #    yield Button("Cancel Ghost", id="cancel-ghost", variant="primary")
        #    yield Button("Accept Ghost", id="accept-ghost", variant="primary")

def main():
    import sys

    # check for filename argument
    filename = sys.argv[1] if len(sys.argv) > 1 else ("untitled")
    editor = Test(filename=filename)
    editor.run()


if __name__ == "__main__":
    main()