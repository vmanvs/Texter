import curses
from curses.textpad import Textbox
from typing import Tuple

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
        self._cache_version += 1

    def get_position(self) -> int:
        return self.position

    def get_display_position(self) -> Tuple[int,int]:
        """Returns the position(row, col) of the cursor"""
        return self.row, self.column

    def set_position(self, row: int, col: int) -> None:
        """Changes the position of the cursor"""
