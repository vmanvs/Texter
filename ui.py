import curses
import os.path
from _ast import arg
from fileinput import filename
from typing import Tuple, Optional
from PieceTable import PieceTable

class Cursor:
    """Cursor abstraction for the text editor"""

    def __init__(self, piece_table:PieceTable ):
        self.piece_table = piece_table
        self.position = 0  #logical position in the text buffer
        self.row = 0       #display row
        self.column = 0    #display column
        self.preferred_column = 0  #remembered column for vertical movements

        self._line_cache = {} #cache line start and end positions
        self._cache_version = 0 #invalidate cache when text changes

    def invalidate_cache(self) -> None:
        """Clears cache when the text is modified"""
        self._line_cache.clear()
        self._last_text_change = len(self.piece_table) #>>review whether this should be in init

    def _check_text_change(self):
        """Check if the text has changed and invalidate cache if needed"""
        current_len = len(self.piece_table) # len calls the __len__ implementation in the PieceTable

        if current_len != self._last_text_change:
            self.invalidate_cache()

    #position management for the cursor

    def get_position(self) -> int:
        """Returns the logical position of the cursor in the text"""
        return self.position

    def get_display_position(self) -> Tuple[int,int]:
        """Returns the position(row, col) of the cursor"""
        return self.row, self.column

    def set_position(self, position:int, update_display:bool = True) -> None:
        """Changes the position of the cursor"""
        self._check_text_change()
        text_length = len(self.piece_table)
        self.position = max(0, min(text_length, position)) #return the lowest of either position or the end of the buffer

        if update_display:
            self._update_display_position()

    def clamp_position(self) -> None:
        """Ensures that the position is in the range of the text"""
        text_length = len(self.piece_table)
        if self.position > text_length:
            self.set_position(text_length)

    #accessor methods

    #>> add a method for getting a slice of string

    def _get_char_at(self, position:int) -> Optional[str]:
        """Returns the character at position on the text"""
        try:
            if position < 0 or position >= len(self.piece_table):
                return None
            return self.piece_table[position]  #this calls the __getitem__ from the piece table
        except (IndexError, TypeError):
            return None

    #basic movements

    def move_down(self) -> bool:
        """Moves the cursor down one line, returns true if successful"""
        line_end = self._find_line_end(self.position)

        if line_end > len(self.piece_table):
            return False

        new_line_start = line_end + 1
        new_line_end = self._find_line_end(new_line_start)
        new_line_length = new_line_end - new_line_start

        #Move to the preferred column or the end of new line if shorter
        new_col = min(self.preferred_column, new_line_length)
        self.position = new_line_start + new_col
        self.row += 1
        self.column = new_col
        return True

    def move_up(self) -> bool:
        """Move the cursor up one line, returns true if successful"""
        if self.row == 0 :
            return False

        line_start = self._find_line_start(self.position)

        if line_start > 0:
            new_line_end = line_start - 1
            new_line_start = self._find_line_start(new_line_end)
            new_line_length = new_line_end - new_line_start

            new_col = min(self.preferred_column, new_line_length)
            self.position = new_line_start + new_col
            self.row -= 1
            self.column = new_col
            return True
        return False

    def move_right(self) -> bool:
        """Moves the cursor left one position, returns true if successful"""
        if self.position < len(self.piece_table):
            char = self._get_char_at(self.position)
            self.position += 1

            if char is '\n':
                self.row += 1
                self.column = 0
                self.preferred_column = 0
            else:
                self.column += 1
                self.preferred_column = self.column

            return True
        return False

    def move_left(self) -> bool:
        """Moves the cursor left one position, returns true if successful"""

        if self.position > 0:
            self.position -= 1

            if self.column > 0:
                self.column -= 1
                self.preferred_column = self.column
            else:
                self._update_display_position() #need to recalculate position when moving to previous line
            return True
        return False


    #line movements

    def move_to_line_start(self) -> None:
        """Move to the start of the current line"""
        line_start = self._find_line_start(self.position)
        self.position = line_start
        self.column = 0
        self.preferred_column = 0

    def move_to_line_end(self) -> None:
        """Move to the end of the current line"""
        line_end = self._find_line_end(self.position)
        line_start = self._find_line_start(self.position)

        self.position = line_end
        self.column = line_end-line_start
        self.preferred_column = self.column

        # h e l l o _ w o r l d \n t e s t ( '_' represents space, A = 10, B = 11 and so on)
        # 0 1 2 3 4 5 6 7 8 9 A  B C D E F    #in the piece table format, the strings will be in a single line and won't be abstracted line-wise
        # line1 start = 0
        # line1 end = 11
        # line2 start = 12
        # line3 end = 15
        # column should be in 14-12 = 3 (0 indexed) is correct

    def move_to_document_start(self) -> None:
        """Move to start of the current document"""
        self.position = 0
        self.column = 0
        self.row = 0
        self.preferred_column = 0

    def move_to_document_end(self) -> None:
        """Move the cursor to the end of current document"""
        self.position = len(self.piece_table)
        self._update_display_position()

    #word movement

    def move_word_left(self) -> bool:
        """Move cursor to the start of the current word or end of previous word (if cursor at whitespace)"""
        if self.position == 0:
            return False

        pos = self.position - 1
        while pos > 0 and self._is_whitespace(self._get_char_at(pos)): #skip the whitespace, for situations where cursor is at whitespace
            pos -= 1

        while pos > 0 and not self._is_whitespace(self._get_char_at(pos-1)): #skip the word, note: checks pos-1, until whitespace is returned
            pos -= 1

        self.set_position(pos)
        return True

    def move_word_right(self) -> bool:
        """Move the cursor to the end of current word or the beginning of next word (if cursor at whitespace)"""
        if self.position >= len(self.piece_table):
            return False

        pos = self.position

        while pos < len(self.piece_table) and not self._is_whitespace(self._get_char_at(pos)): #skip the current word
            pos += 1
        while pos < len(self.piece_table) and self._is_whitespace(self._get_char_at(pos)): #skip the white_space
            pos += 1
        self.set_position(pos)

        return True

    #in the move_word_left and move_word_right, it is important to decide whether to check for the word first or the
    #whitespace, while moving to start of current word or the beginning of previous word, we check for the whitespace first, that
    #ensures that `not self._is_whitespace(self._get_char_at(pos-1)` functions correctly, if we reverse the order it would skip 2 words


    def goto_line(self, line_number: int) -> bool:
        """Jump to a given line (1-based) in the text editor, returns true if successful"""

        if line_number < 1:
            return False

        target_line = line_number - 1 #convert to 0-based
        position = 0
        current_line = 0

        while position < len(self.piece_table) and current_line < target_line:
            if self._get_char_at(position) == '\n':
                current_line += 1
            position += 1

        if current_line == target_line:
            self.set_position(position)
            return True
        return False

    def get_current_line_number(self) -> int:
        """Returns the current line number 1-based"""
        return  self.row+1

    def get_current_line_text(self) -> str:
        """Returns the content of current line"""
        line_start = self._find_line_start(self.position)
        line_end = self._find_line_end(self.position)

        text = []
        for i in range(line_start, line_end):
            char = self._get_char_at(i)
            if char is not None:
             text.append(char)

        return "".join(text)

    #helper methods

    def _update_display_position(self) -> None:
        """Recalculate row and column from current position"""
        self.row = 0
        self.column = 0

        for i in range(self.position):
            char = self._get_char_at(i)
            if char is '\n':
                self.row += 1
                self.column = 0
            else:
                self.column += 1

        self.preferred_column = self.column

    def _is_whitespace(self, char:str) -> bool:  #>> review the warning
        """Checks if the character is whitespace or not"""
        return char is not None and char.isspace()

    def _find_line_start(self, position:int) -> int:
        """Fine the start of the line containing the given position"""
        #check cache
        cache_key = f"line_start:{position}"
        if cache_key in self._line_cache:
            return self._line_cache[cache_key] #looking up a key in dictionary is O(1)

        start_pos = position
        while start_pos > 0:
            char = self._get_char_at(start_pos - 1) #check the char at position before current position
            if char is '\n':
                break
            start_pos -= 1

            # Hello \n World
            # 01234 5  6789A

            #say start_pos = 8
            #'o' != '\n' start_pos -= 1 i.e. 7
            #'W' != '\n' start_pos -= 1 i.e. 6
            #'\n' is present: break look and return start_pos i.e. 6

        self._line_cache[cache_key] = start_pos #add to cache
        return start_pos

    def _find_line_end(self, position:int) -> int:
        """Fine the end of the line containing the given position"""
        cache_key = f"line_end:{position}"
        if cache_key in self._line_cache:
            return self._line_cache[cache_key]
        end_pos = position
        text_length = len(self.piece_table)

        while end_pos < text_length:
            char = self._get_char_at(end_pos)
            if char is '\n': #returns upto \n
                break
            end_pos += 1

        self._line_cache[cache_key] = end_pos
        return end_pos


class ScreenCursor:
    """Manage the screen cursor"""

    def __init__(self, logical_cursor: Cursor):
        self.logical_cursor = logical_cursor
        self.scroll_x = 0
        self.scroll_y = 0


    def get_screen_position(self) -> Tuple[int, int]:
        """Returns the screen cursor position (maybe -ve if scrolled off)"""
        logical_row, logical_column = self.logical_cursor.get_display_position()

        return logical_row-self.scroll_x, logical_column-self.scroll_y

    def is_cursor_visible(self, screen_height: int, screen_width: int) -> bool:
        """Returns True if the screen cursor is on the screen"""
        screen_row, screen_column = self.get_screen_position()

        return 0 <= screen_row < screen_height and 0 <= screen_column < screen_width

    def ensure_cursor_visible(self, screen_height: int, screen_width: int,
                              margin: int = 0) -> Tuple[bool, bool]: #understand this better
        """Adjusts the view so that the cursor is visible on the screen: returns (scrolled_v, scrolled_h)"""

        logical_row, logical_column = self.logical_cursor.get_display_position()
        scrolled_v = False
        scrolled_h = False

        if logical_row < screen_height + margin:
            self.scroll_y = max(0, logical_row - margin)
            scrolled_v = True

        elif logical_row >=  self.scroll_y + screen_height - margin:
            self.scroll_y = logical_row - screen_height + margin + 1
            scrolled_v = True

        if logical_column > screen_width + margin:
            self.scroll_x = max(0, logical_column - margin)
            scrolled_h = True
        elif logical_column >= self.scroll_x + screen_width - margin:
            self.scroll_x = logical_column - screen_width + margin + 1
            scrolled_h = True

        return scrolled_v, scrolled_h

    def scroll_down(self, lines: int = 1) -> None:
        """Scrolls the cursor down one line"""
        self.scroll_y += lines

    def scroll_up(self, lines: int = 1) -> None:
        """Scrolls the cursor up one line"""
        self.scroll_y = max(0, self.scroll_y - lines) #we shouldn't go less than 0 in the viewport

    def scroll_left(self, columns: int = 1) -> None:
        """Scrolls the cursor left one column"""
        self.scroll_x = max(0, self.scroll_x - columns) #we shouldn't go more right than 0th column in the viewport

    def scroll_right(self, columns: int = 1) -> None:
        """Scrolls the cursor right one column"""
        self.scroll_x += columns


class TextEditor:
    def __init__(self, filename:Optional[str] = None):
        self.filename = filename
        self.modified = False

        if filename and os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            self.piece_table = PieceTable(content)
        else:
            self.piece_table = PieceTable("")

        self.cursor = Cursor(self.piece_table)
        self.screen_cursor = ScreenCursor(self.cursor)
        self.mode = "NORMAL" #supported: NORMAL, INSERT, COMMAND
        self.message = ""
        self.command_buffer = "" #input for the command buffer

    def handle_text_change(self):
        """To be called after every text change"""
        self.cursor.invalidate_cache()
        self.cursor.clamp_position()

    def inset_at_cursor(self, text: str) -> None:
        """Insert text at the given position"""
        self.piece_table.insert(self.cursor.position, text)
        self.cursor.set_position(self.cursor.position + len(text))
        self.handle_text_change()


    def delete_at_cursor(self, length: int = 1, backward: bool = True) -> None:
        """Delete text at the given position"""
        if backward: #i.e. from a higher index to a lower index, which will dominate most cases
            if self.cursor.position >= length:
                self.piece_table.delete(self.cursor.position - length, length)
                self.cursor.set_position(self.cursor.position - length)
                self.handle_text_change()

        else:
            if self.cursor.position + length <= len(self.piece_table):
                self.piece_table.delete(self.cursor.position, length)

        self.handle_text_change()


    def save_file(self, filename: Optional[str] = None):
        """Save the current buffer to a file"""
        if filename:
            self.filename = filename

        if not self.filename:
            return "No file name specified"

        try:
            content = self.piece_table.get_text()
            with open(self.filename, 'w', encoding='utf-8') as f:
                f.write(content)
            self.modified = False
            return True, f"Saved the file  to {self.filename}"
        except Exception as e:
            return False, f"Error saving the file: {str(e)}"

    def open_file(self,  filename: Optional[str] = None):
        """Open a file"""

        if not os.path.exists(filename):
            return f"{filename} does not exist at the given path"

        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            self.piece_table = PieceTable(content)
            self.cursor = Cursor(self.piece_table)
            self.screen_cursor = ScreenCursor(self.cursor)
            self.filename = filename
            self.modified = False
            return True, f"Opened {filename}"
        except Exception as e:
            return False, f"Error opening the file: {str(e)}"

    def handle_keypress(self, key: int) -> bool:
        if key == curses.KEY_LEFT:
            return self.cursor.move_left()
        elif key == curses.KEY_RIGHT:
            return self.cursor.move_right()
        elif key == curses.KEY_UP:
            return self.cursor.move_up()
        elif key == curses.KEY_DOWN:
            return self.cursor.move_down()
        elif key == curses.KEY_F2:
            self.cursor.move_to_line_start()
            return True
        elif key == curses.KEY_F3:
            self.cursor.move_to_line_end()
            return True
        elif key == curses.KEY_PPAGE:
            for _ in range(20):
                if not self.cursor.move_up(): #call self.cursor.move_up() 20 times or until it returns false
                     break
            return True
        elif key == curses.KEY_NPAGE:       #same explanation as above
            for _ in range(20):
                if not self.cursor.move_down():
                    break
            return True
        return False

    def render_text(self, stdscr, screen_height: int, screen_width: int):
        """Render the text from the piece table onto the screen"""

        try:
            text = self.piece_table.get_text()
            lines = text.split('\n') # foo.split() returns a list of substrings

            for i, line in enumerate(lines[self.screen_cursor.scroll_y:
                                     self.screen_cursor.scroll_y + screen_height]): #slice the list from the current_row
                                                                                    # to the current_row + screen height
                if i >= screen_height:
                    break

                display_line = line[self.screen_cursor.scroll_x: self.screen_cursor.scroll_x + screen_width] #slice the characters in a row
                                                                                                    #from current_column to current_column+screen_width
                try:
                    stdscr.addstr(i, 0, display_line)
                except curses.error:
                    pass

        except Exception:
            stdscr.addstr(0, 0, "Error reading text")

    def render_status_bar(self, stdscr, screen_height: int, screen_width: int):
        """Render the status bar on the bottom displaying current mode, filename, if buffer has been modified,
         to input text in command mode and current logical position"""
        try:
            #Mode indicator
            mode_str = f" {self.mode}"
            if mode_str == "INSERT":
                attr = curses.A_REVERSE | curses.A_BOLD #A_REVERSE -> reverses foreground and background colors, A_BOLD is bold mode
            elif mode_str == "COMMAND":
                attr = curses.A_REVERSE
            else:
                attr = curses.A_REVERSE | curses.A_DIM #A_DIM is dim mode

            #left side: mode and insert indicator

            left_side = mode_str
            if self.filename:
                left_side += f" {os.path.basename(self.filename)}"
            if self.modified:
                left_side += " [+]"

            right_side = f" Ln {self.cursor.row + 1}, Col {self.cursor.column + 1}, Position {self.cursor.position}"

            spacing = screen_width - len(left_side) - len(right_side)

            status_line = left_side + " "*max(0, spacing) + right_side
            status_line = status_line[:screen_width-1]

            stdscr.addstr(screen_height-2, 0, status_line, attr)

            if self.mode == "COMMAND":
                cmd_line = ":" + self.command_buffer
                stdscr.addstr(screen_height-1, 0, cmd_line[:screen_width - 1])
            elif self.message:
                stdscr.addstr(screen_height-1, 0, self.message[:screen_width-1])
            else:
                stdscr.addstr(screen_height-1, 0, ""*(screen_width-1)) #empty line

        except curses.error:
            pass

    def render_cursor(self, stdscr, screen_height: int, screen_width: int):
        """Render the cursor on the screen, at the given logical position"""
        self.screen_cursor.ensure_cursor_visible(screen_height, screen_width)
        screen_row, screen_column = self.screen_cursor.get_screen_position()

        if 0 <= screen_row < screen_height and 0 <= screen_column < screen_width:
            try:
                stdscr.move(screen_row, screen_column)
            except curses.error:
                pass

    def execute_command(self, command: str):
        """Execute the given command in command mode"""
        parts = command.strip().split(maxsplit=1) #strip remove the leading and trailing whitespace,
                                                  #split(maxsplit=1) breaks the string into to 2 parts, if no delimiter is specified
                                                  #split is done by whitespaces
        if not parts:
            return

        cmd = parts[0]
        args = parts[1] if len(parts) > 1 else None

        if cmd in ('q', 'quit'):
            if self.modified:
                self.message = "Unsaved changes! Use :q! to force quit or :wq to save and quit"
            else:
                return 'quit'
        elif cmd == 'q!':
            return 'quit'
        elif cmd in ('w', 'write'): #takes the filename as the args
            success, msg = self.save_file(args)
            self.message = msg
        elif cmd == 'wq':
            success, msg = self.save_file(args)
            if success:
                return 'quit'
        elif cmd in ('e', 'edit'):
            if args:
                success, msg = self.open_file(args)
                self.message = msg
            else:
                self.message = "Usage: :e <filename>"
        elif cmd in ('o', 'open'):
            if args:
                success, msg = self.open_file(args)
                self.message = msg
            else:
                self.message = "Usage: :o <filename>"
        else:
            self.message = f"Unknown command: {cmd}"

        return None

class EditorCursorIntegration:
    """Integration layer for PieceTable and curses"""

    def __init__(self, piece_table: PieceTable):
        self.piece_table = piece_table
        self.cursor = Cursor(piece_table)
        self.screen_cursor = ScreenCursor(self.cursor)

    def handle_text_change(self):
        """To be called after every text change"""
        self.cursor.invalidate_cache()
        self.cursor.clamp_position()

    def inset_at_cursor(self, text: str) -> None:
        """Insert text at the given position"""
        self.piece_table.insert(self.cursor.position, text)
        self.cursor.set_position(self.cursor.position + len(text))
        self.handle_text_change()

    def delete_at_cursor(self, length: int = 1, backward: bool = True) -> None:
        """Delete text at the given position"""
        if backward: #i.e. from a higher index to a lower index, which will dominate most cases
            if self.cursor.position >= length:
                self.piece_table.delete(self.cursor.position - length, length)
                self.cursor.set_position(self.cursor.position - length)
                self.handle_text_change()

        else:
            if self.cursor.position + length <= len(self.piece_table):
                self.piece_table.delete(self.cursor.position, length)

        self.handle_text_change()

    def handle_keypress(self, key: int) -> bool:
        """Handle key presses, returns true is successful"""
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
        elif key == curses.KEY_PPAGE:
        elif key == curses.KEY_NPAGE:


        #manage word movements (CTRL + Left, CTRL + Right)

        elif key == 545:
            self.cursor.move_word_right()
        elif key == 546:
            self.cursor.move_word_left()

        return False

    def render_text(self, stdscr, screen_height: int, screen_width: int):
        """Render text to screen"""
        