import curses
from curses.textpad import Textbox
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

