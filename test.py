import curses
from typing import Optional, Tuple
from PieceTable import PieceTable


class Cursor:
    """Cursor abstraction for text editor with PieceTable backend"""

    def __init__(self, piece_table: PieceTable):
        self.piece_table = piece_table
        self.position = 0  # Logical position in the text buffer
        self.row = 0  # Display row (0-based)
        self.col = 0  # Display column (0-based)
        self.preferred_col = 0  # Remembered column for vertical movement

        # Cache for performance optimization
        self._line_cache = {}  # Cache line start/end positions
        self._last_text_len = len(piece_table)  # Track text changes

    def invalidate_cache(self) -> None:
        """Call this whenever the text is modified"""
        self._line_cache.clear()
        self._last_text_len = len(self.piece_table)

    def _check_text_changed(self) -> None:
        """Check if text has changed and invalidate cache if needed"""
        current_len = len(self.piece_table)
        if current_len != self._last_text_len:
            self.invalidate_cache()

    # === Position Management ===

    def get_position(self) -> int:
        """Get current logical position"""
        return self.position

    def get_display_position(self) -> Tuple[int, int]:
        """Get current display position as (row, col)"""
        return (self.row, self.col)

    def set_position(self, position: int, update_display: bool = True) -> None:
        """Set cursor to absolute position"""
        self._check_text_changed()
        text_length = len(self.piece_table)
        self.position = max(0, min(position, text_length))

        if update_display:
            self._update_display_position()

    def clamp_position(self) -> None:
        """Ensure position is within valid bounds"""
        text_length = len(self.piece_table)
        if self.position > text_length:
            self.set_position(text_length)

    # === Character Access (with error handling for your piece table) ===

    def _get_char_at(self, position: int) -> Optional[str]:
        """Safely get character at position, handling your piece table's quirks"""
        try:
            if position < 0 or position >= len(self.piece_table):
                return None
            return self.piece_table[position]
        except (IndexError, TypeError):
            return None

    # === Basic Movement ===

    def move_left(self) -> bool:
        """Move cursor one position left. Returns True if moved."""
        if self.position > 0:
            self.position -= 1

            # Quick update for simple cases
            if self.col > 0:
                self.col -= 1
                self.preferred_col = self.col
            else:
                # Need to recalculate when moving to previous line
                self._update_display_position()
            return True
        return False

    def move_right(self) -> bool:
        """Move cursor one position right. Returns True if moved."""
        if self.position < len(self.piece_table):
            char = self._get_char_at(self.position)
            self.position += 1

            if char == '\n':
                self.row += 1
                self.col = 0
                self.preferred_col = 0
            else:
                self.col += 1
                self.preferred_col = self.col
            return True
        return False

    def move_up(self) -> bool:
        """Move cursor up one line. Returns True if moved."""
        if self.row == 0:
            return False

        # Find current line boundaries
        line_start = self._find_line_start(self.position)

        # Find previous line
        if line_start > 0:
            prev_line_end = line_start - 1  # Position of the \n
            prev_line_start = self._find_line_start(prev_line_end)
            prev_line_length = prev_line_end - prev_line_start

            # Move to preferred column or end of line if shorter
            new_col = min(self.preferred_col, prev_line_length)
            self.position = prev_line_start + new_col
            self.row -= 1
            self.col = new_col
            return True
        return False

    def move_down(self) -> bool:
        """Move cursor down one line. Returns True if moved."""
        # Find current line end
        line_end = self._find_line_end(self.position)

        # Check if there's a next line
        if line_end >= len(self.piece_table):
            return False

        # Move to next line
        next_line_start = line_end + 1
        next_line_end = self._find_line_end(next_line_start)
        next_line_length = next_line_end - next_line_start

        # Move to preferred column or end of line if shorter
        new_col = min(self.preferred_col, next_line_length)
        self.position = next_line_start + new_col
        self.row += 1
        self.col = new_col
        return True

    # === Line Movement ===

    def move_to_line_start(self) -> None:
        """Move cursor to beginning of current line"""
        line_start = self._find_line_start(self.position)
        self.position = line_start
        self.col = 0
        self.preferred_col = 0

    def move_to_line_end(self) -> None:
        """Move cursor to end of current line"""
        line_end = self._find_line_end(self.position)
        line_start = self._find_line_start(self.position)

        self.position = line_end
        self.col = line_end - line_start
        self.preferred_col = self.col

    def move_to_document_start(self) -> None:
        """Move cursor to beginning of document"""
        self.position = 0
        self.row = 0
        self.col = 0
        self.preferred_col = 0

    def move_to_document_end(self) -> None:
        """Move cursor to end of document"""
        self.position = len(self.piece_table)
        self._update_display_position()

    # === Word Movement ===

    def move_word_left(self) -> bool:
        """Move cursor to start of previous word"""
        if self.position == 0:
            return False

        # Skip whitespace
        pos = self.position - 1
        while pos > 0 and self._is_whitespace(self._get_char_at(pos)):
            pos -= 1

        # Skip non-whitespace (the word)
        while pos > 0 and not self._is_whitespace(self._get_char_at(pos - 1)):
            pos -= 1

        self.set_position(pos)
        return True

    def move_word_right(self) -> bool:
        """Move cursor to start of next word"""
        text_length = len(self.piece_table)
        if self.position >= text_length:
            return False

        pos = self.position

        # Skip current word
        while pos < text_length and not self._is_whitespace(self._get_char_at(pos)):
            pos += 1

        # Skip whitespace
        while pos < text_length and self._is_whitespace(self._get_char_at(pos)):
            pos += 1

        self.set_position(pos)
        return True

    # === Line Navigation ===

    def goto_line(self, line_number: int) -> bool:
        """Move cursor to specific line (1-based). Returns True if successful."""
        if line_number < 1:
            return False

        target_line = line_number - 1  # Convert to 0-based
        position = 0
        current_line = 0

        # Find the start of the target line
        while position < len(self.piece_table) and current_line < target_line:
            if self._get_char_at(position) == '\n':
                current_line += 1
            position += 1

        if current_line == target_line:
            self.set_position(position)
            return True
        return False

    def get_current_line_number(self) -> int:
        """Get current line number (1-based)"""
        return self.row + 1

    def get_current_line_text(self) -> str:
        """Get text of current line"""
        line_start = self._find_line_start(self.position)
        line_end = self._find_line_end(self.position)

        try:
            # Use your piece table's slicing capability
            return self.piece_table[line_start:line_end]
        except (IndexError, TypeError):
            # Fallback to character-by-character if slicing fails
            text = []
            for pos in range(line_start, line_end):
                char = self._get_char_at(pos)
                if char is not None:
                    text.append(char)
            return ''.join(text)

    # === Helper Methods ===

    def _find_line_start(self, position: int) -> int:
        """Find start position of line containing given position"""
        # Check cache first
        cache_key = f"line_start_{position}"
        if cache_key in self._line_cache:
            return self._line_cache[cache_key]

        start_pos = position
        while start_pos > 0:
            char = self._get_char_at(start_pos - 1)
            if char == '\n':
                break
            start_pos -= 1

        # Cache the result
        self._line_cache[cache_key] = start_pos
        return start_pos

    def _find_line_end(self, position: int) -> int:
        """Find end position of line containing given position"""
        # Check cache first
        cache_key = f"line_end_{position}"
        if cache_key in self._line_cache:
            return self._line_cache[cache_key]

        end_pos = position
        text_length = len(self.piece_table)

        while end_pos < text_length:
            char = self._get_char_at(end_pos)
            if char == '\n':
                break
            end_pos += 1

        # Cache the result
        self._line_cache[cache_key] = end_pos
        return end_pos

    def _update_display_position(self) -> None:
        """Recalculate row and column from current position"""
        self.row = 0
        self.col = 0

        for i in range(self.position):
            char = self._get_char_at(i)
            if char == '\n':
                self.row += 1
                self.col = 0
            else:
                self.col += 1

        self.preferred_col = self.col

    def _is_whitespace(self, char: Optional[str]) -> bool:
        """Check if character is whitespace"""
        return char is not None and char.isspace()

    # === Debug/Info Methods ===

    def get_cursor_info(self) -> dict:
        """Get cursor state for debugging"""
        return {
            'position': self.position,
            'row': self.row,
            'col': self.col,
            'preferred_col': self.preferred_col,
            'line_number': self.get_current_line_number(),
            'char_at_cursor': self._get_char_at(self.position),
            'text_length': len(self.piece_table),
        }


class ScreenCursor:
    """Manages cursor display on screen with scrolling support"""

    def __init__(self, logical_cursor: Cursor):
        self.logical_cursor = logical_cursor
        self.scroll_y = 0  # Vertical scroll offset
        self.scroll_x = 0  # Horizontal scroll offset

    def get_screen_position(self) -> Tuple[int, int]:
        """Get cursor position on screen (may be negative if scrolled off)"""
        logical_row, logical_col = self.logical_cursor.get_display_position()
        return (logical_row - self.scroll_y, logical_col - self.scroll_x)

    def is_cursor_visible(self, screen_height: int, screen_width: int) -> bool:
        """Check if cursor is visible on screen"""
        screen_row, screen_col = self.get_screen_position()
        return (0 <= screen_row < screen_height and
                0 <= screen_col < screen_width)

    def ensure_cursor_visible(self, screen_height: int, screen_width: int,
                              margin: int = 0) -> Tuple[bool, bool]:
        """Adjust scroll to ensure cursor is visible. Returns (scrolled_v, scrolled_h)"""
        logical_row, logical_col = self.logical_cursor.get_display_position()
        scrolled_v = False
        scrolled_h = False

        # Vertical scrolling
        if logical_row < self.scroll_y + margin:
            self.scroll_y = max(0, logical_row - margin)
            scrolled_v = True
        elif logical_row >= self.scroll_y + screen_height - margin:
            self.scroll_y = logical_row - screen_height + margin + 1
            scrolled_v = True

        # Horizontal scrolling
        if logical_col < self.scroll_x + margin:
            self.scroll_x = max(0, logical_col - margin)
            scrolled_h = True
        elif logical_col >= self.scroll_x + screen_width - margin:
            self.scroll_x = logical_col - screen_width + margin + 1
            scrolled_h = True

        return (scrolled_v, scrolled_h)

    def scroll_up(self, lines: int = 1) -> None:
        """Scroll screen up"""
        self.scroll_y = max(0, self.scroll_y - lines)

    def scroll_down(self, lines: int = 1) -> None:
        """Scroll screen down"""
        self.scroll_y += lines

    def scroll_left(self, cols: int = 1) -> None:
        """Scroll screen left"""
        self.scroll_x = max(0, self.scroll_x - cols)

    def scroll_right(self, cols: int = 1) -> None:
        """Scroll screen right"""
        self.scroll_x += cols


class EditorCursorIntegration:
    """Integration layer for cursor with your PieceTable and curses"""

    def __init__(self, piece_table: PieceTable):
        self.piece_table = piece_table
        self.cursor = Cursor(piece_table)
        self.screen_cursor = ScreenCursor(self.cursor)

    def handle_text_change(self):
        """Call this after any text modification"""
        self.cursor.invalidate_cache()
        self.cursor.clamp_position()

    def insert_text_at_cursor(self, text: str):
        """Insert text at cursor position and update cursor"""
        self.piece_table.insert(self.cursor.position, text)
        self.cursor.set_position(self.cursor.position + len(text))
        self.handle_text_change()

    def delete_at_cursor(self, length: int = 1, backward: bool = True):
        """Delete text at cursor position"""
        if backward:
            if self.cursor.position >= length:
                self.piece_table.delete(self.cursor.position - length, length)
                self.cursor.set_position(self.cursor.position - length)
        else:
            if self.cursor.position + length <= len(self.piece_table):
                self.piece_table.delete(self.cursor.position, length)

        self.handle_text_change()

    def handle_keypress(self, key: int) -> bool:
        """Handle cursor movement keys. Returns True if key was handled."""
        if key == curses.KEY_LEFT:
            return self.cursor.move_left()
        elif key == curses.KEY_RIGHT:
            return self.cursor.move_right()
        elif key == curses.KEY_UP:
            return self.cursor.move_up()
        elif key == curses.KEY_DOWN:
            return self.cursor.move_down()
        elif key == curses.KEY_HOME:
            self.cursor.move_to_line_start()
            return True
        elif key == curses.KEY_END:
            self.cursor.move_to_line_end()
            return True
        elif key == curses.KEY_PPAGE:  # Page Up
            height, _ = curses.LINES - 1, curses.COLS
            for _ in range(height):
                if not self.cursor.move_up():
                    break
            return True
        elif key == curses.KEY_NPAGE:  # Page Down
            height, _ = curses.LINES - 1, curses.COLS
            for _ in range(height):
                if not self.cursor.move_down():
                    break
            return True
        # Word movement (Ctrl+Left, Ctrl+Right)
        elif key == 545:  # Ctrl+Right (may vary by terminal)
            return self.cursor.move_word_right()
        elif key == 560:  # Ctrl+Left (may vary by terminal)
            return self.cursor.move_word_left()
        return False

    def render_text(self, stdscr, screen_height: int, screen_width: int):
        """Render text to screen with scrolling"""
        try:
            text = self.piece_table.get_text()
            lines = text.split('\n')

            # Render visible lines
            for i, line in enumerate(lines[self.screen_cursor.scroll_y:
            self.screen_cursor.scroll_y + screen_height]):
                if i >= screen_height:
                    break

                # Handle horizontal scrolling
                display_line = line[self.screen_cursor.scroll_x:
                                    self.screen_cursor.scroll_x + screen_width]

                try:
                    stdscr.addstr(i, 0, display_line)
                except curses.error:
                    pass  # Ignore errors from writing to screen edges
        except Exception:
            # Fallback if get_text() fails
            stdscr.addstr(0, 0, "Error reading text")

    def render_cursor(self, stdscr, screen_height: int, screen_width: int):
        """Position the terminal cursor on screen"""
        self.screen_cursor.ensure_cursor_visible(screen_height, screen_width)
        screen_row, screen_col = self.screen_cursor.get_screen_position()

        if (0 <= screen_row < screen_height and
                0 <= screen_col < screen_width):
            try:
                stdscr.move(screen_row, screen_col)
            except curses.error:
                pass  # Ignore cursor positioning errors

    def get_status_line(self) -> str:
        """Get status line text for display"""
        info = self.cursor.get_cursor_info()
        return (f"Pos:{info['position']} "
                f"Line:{info['line_number']} "
                f"Col:{info['col'] + 1} "
                f"Len:{info['text_length']}")


# Example usage:
def example_editor_loop():
    """Example of how to use the cursor with your piece table in a curses editor"""

    def main(stdscr):
        # Initialize
        piece_table = PieceTable("Hello, World!\nThis is a test.\nAnother line.")
        editor = EditorCursorIntegration(piece_table)

        curses.curs_set(1)  # Show cursor
        stdscr.keypad(True)  # Enable special keys

        while True:
            height, width = stdscr.getmaxyx()
            stdscr.clear()

            # Render text
            editor.render_text(stdscr, height - 1, width)

            # Show status
            status = editor.get_status_line()
            stdscr.addstr(height - 1, 0, status[:width - 1])

            # Position cursor
            editor.render_cursor(stdscr, height - 1, width)

            stdscr.refresh()

            # Handle input
            key = stdscr.getch()

            if key == ord('q'):
                break
            elif key == ord('i'):  # Insert mode
                status_msg = "INSERT MODE - ESC to exit"
                stdscr.addstr(height - 1, 0, status_msg[:width - 1])
                stdscr.refresh()

                while True:
                    key = stdscr.getch()
                    if key == 27:  # ESC
                        break
                    elif key in (curses.KEY_BACKSPACE, 127, 8):
                        editor.delete_at_cursor(1, backward=True)
                    elif key in (curses.KEY_ENTER, 10, 13):
                        editor.insert_text_at_cursor('\n')
                    elif 32 <= key <= 126:  # Printable characters
                        editor.insert_text_at_cursor(chr(key))

                    # Redraw
                    stdscr.clear()
                    editor.render_text(stdscr, height - 1, width)
                    status_msg = "INSERT MODE - ESC to exit"
                    stdscr.addstr(height - 1, 0, status_msg[:width - 1])
                    editor.render_cursor(stdscr, height - 1, width)
                    stdscr.refresh()

            elif not editor.handle_keypress(key):
                # Key not handled
                pass

    curses.wrapper(main)


if __name__ == "__main__":
    example_editor_loop()