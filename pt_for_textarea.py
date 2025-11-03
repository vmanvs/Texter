from __future__ import annotations

from typing import overload

from PieceTable import PieceTable

from textual.document._document import (
    DocumentBase,
    EditResult,
    Location,
    Newline,
    _detect_newline_style,
    VALID_NEWLINES,
)
from textual.geometry import Size
from textual._cells import cell_len


class PieceTableDocument(DocumentBase):
    """Adapter that makes PieceTable compatible with DocumentBase interface.

    This adapter allows PieceTable to be used with TextArea widget by implementing
    the DocumentBase abstract methods.
    """

    def __init__(self, text: str) -> None:
        """Initialize the PieceTableDocument.

        Args:
            text: The initial text content.
        """
        self._piece_table = PieceTable(text)
        self._newline: Newline = _detect_newline_style(text)
        self._lines_cache: list[str] | None = None
        self._cache_valid = True

    def _invalidate_cache(self) -> None:
        """Invalidate the lines cache when content changes."""
        self._lines_cache = None
        self._cache_valid = False

    def _build_lines_cache(self) -> list[str]:
        """Build and cache the lines from the piece table."""
        if self._cache_valid and self._lines_cache is not None:
            return self._lines_cache

        text = self._piece_table.get_text()
        lines = text.splitlines(keepends=False)

        # Ensure we have an empty line at the end if text ends with newline
        if text.endswith(tuple(VALID_NEWLINES)) or not text:
            lines.append("")

        self._lines_cache = lines
        self._cache_valid = True
        return lines

    @property
    def text(self) -> str:
        """The text from the document as a string."""
        return self._piece_table.get_text()

    @property
    def newline(self) -> Newline:
        """Return the line separator used in the document."""
        return self._newline

    @property
    def lines(self) -> list[str]:
        """Get the lines of the document as a list of strings.

        The strings do not include newline characters.
        """
        return self._build_lines_cache()

    def get_line(self, index: int) -> str:
        """Returns the line with the given index from the document.

        Args:
            index: The index of the line in the document.

        Returns:
            The str instance representing the line.
        """
        lines = self.lines
        if 0 <= index < len(lines):
            return lines[index]
        return ""

    def get_text_range(self, start: Location, end: Location) -> str:
        """Get the text that falls between the start and end locations.

        Args:
            start: The start location of the selection.
            end: The end location of the selection.

        Returns:
            The text between start (inclusive) and end (exclusive).
        """
        if start == end:
            return ""

        top, bottom = sorted((start, end))
        top_row, top_column = top
        bottom_row, bottom_column = bottom

        lines = self.lines

        if top_row == bottom_row:
            # Selection within a single line
            line = lines[top_row] if top_row < len(lines) else ""
            return line[top_column:bottom_column]
        else:
            # Selection spanning multiple lines
            result_parts = []

            # First line
            if top_row < len(lines):
                start_line = lines[top_row]
                result_parts.append(start_line[top_column:])

            # Middle lines
            for row in range(top_row + 1, bottom_row):
                if row < len(lines):
                    result_parts.append(lines[row])

            # Last line
            if bottom_row < len(lines):
                end_line = lines[bottom_row]
                result_parts.append(end_line[:bottom_column])

            return self._newline.join(result_parts)

    def get_size(self, indent_width: int) -> Size:
        """Get the size of the document.

        Args:
            indent_width: The width to use for tab characters.

        Returns:
            The Size of the document bounding box.
        """
        lines = self.lines
        cell_lengths = [cell_len(line.expandtabs(indent_width)) for line in lines]
        max_cell_length = max(cell_lengths, default=0)
        height = len(lines)
        return Size(max_cell_length, height)

    @property
    def line_count(self) -> int:
        """Returns the number of lines in the document."""
        return len(self.lines)

    @property
    def start(self) -> Location:
        """Returns the location of the start of the document (0, 0)."""
        return 0, 0

    @property
    def end(self) -> Location:
        """Returns the location of the end of the document."""
        lines = self.lines
        if not lines:
            return (0, 0)
        last_line = lines[-1]
        return len(lines) - 1, len(last_line)

    def replace_range(self, start: Location, end: Location, text: str) -> EditResult:
        """Replace the text at the given range.

        Args:
            start: A tuple (row, column) where the edit starts.
            end: A tuple (row, column) where the edit ends.
            text: The text to insert between start and end.

        Returns:
            The EditResult containing information about the edit.
        """
        top, bottom = sorted((start, end))
        top_row, top_column = top
        bottom_row, bottom_column = bottom

        # Get the text being replaced
        replaced_text = self.get_text_range(top, bottom)

        # Convert locations to absolute positions in the piece table
        start_index = self._location_to_index(top)
        end_index = self._location_to_index(bottom)

        # Perform the edit in the piece table
        if start_index < end_index:
            # Delete the range first
            self._piece_table.delete(start_index, end_index - start_index)

        # Insert the new text
        if text:
            self._piece_table.insert(start_index, text)

        # Invalidate cache
        self._invalidate_cache()

        # Calculate the new end location
        insert_lines = text.splitlines(keepends=False)
        if text.endswith(tuple(VALID_NEWLINES)):
            insert_lines.append("")

        if not insert_lines:
            end_location = top
        elif len(insert_lines) == 1:
            # Single line insert
            end_location = (top_row, top_column + len(insert_lines[0]))
        else:
            # Multi-line insert
            destination_row = top_row + len(insert_lines) - 1
            destination_column = len(insert_lines[-1])
            end_location = (destination_row, destination_column)

        return EditResult(end_location, replaced_text)

    def get_index_from_location(self, location: Location) -> int:
        """Given a location, returns the index from the document's text.

                Args:
                    location: The location in the document.

                Returns:
                    The index in the document's text.
                """
        row, column = location
        index = row * len(self.newline) + column
        for line_index in range(row):
            index += len(self.get_line(line_index))
        return index



    def get_location_from_index(self, index: int) -> Location:
        """Given a codepoint index in the document's text, returns the corresponding location.

        Args:
            index: The index in the document's text.

        Returns:
            The corresponding location.

        Raises:
            ValueError: If the index doesn't correspond to a location in the document.
        """
        error_message = (
            f"Index {index!r} does not correspond to a location in the document."
        )
        if index < 0 or index > len(self.text):
            raise ValueError(error_message)

        column_index = 0
        newline_length = len(self.newline)
        for line_index in range(self.line_count):
            next_column_index = (
                column_index + len(self.get_line(line_index)) + newline_length
            )
            if index < next_column_index:
                return line_index, index - column_index
            elif index == next_column_index:
                return line_index + 1, 0
            column_index = next_column_index

        raise ValueError(error_message)

    def _location_to_index(self, location: Location) -> int:
        """Convert a (row, column) location to an absolute index in the text.

        Args:
            location: The (row, column) location.

        Returns:
            The absolute index in the piece table.
        """
        row, column = location
        lines = self.lines

        # Calculate index by summing lengths of all previous lines plus newlines
        index = 0
        newline_length = len(self._newline)

        for line_index in range(min(row, len(lines))):
            index += len(lines[line_index]) + newline_length

        # Add the column offset within the current line
        if row < len(lines):
            index += min(column, len(lines[row]))

        return index

    def _index_to_location(self, index: int) -> Location:
        """Convert an absolute index to a (row, column) location.

        Args:
            index: The absolute index in the piece table.

        Returns:
            The (row, column) location.
        """
        lines = self.lines
        newline_length = len(self._newline)

        current_index = 0
        for row, line in enumerate(lines):
            line_length = len(line)
            line_end_index = current_index + line_length

            if index <= line_end_index:
                column = index - current_index
                return row, column

            # Move past this line and its newline
            current_index = line_end_index + newline_length

        # If we've gone past all lines, return the end location
        return self.end

    @overload
    def __getitem__(self, line_index: int) -> str:
        ...

    @overload
    def __getitem__(self, line_index: slice) -> list[str]:
        ...

    def __getitem__(self, line_index: int | slice) -> str | list[str]:
        """Return the content of a line as a string, excluding newline characters.

        Args:
            line_index: The index or slice of the line(s) to retrieve.

        Returns:
            The line or list of lines requested.
        """
        return self.lines[line_index]



#TODO: remove this
# Example usage demonstrating the adapter
if __name__ == "__main__":
    # Create a document using PieceTable backend
    doc = PieceTableDocument("Hello, World!\nThis is line 2.\nLine 3 here.")

    print("Initial text:")
    print(doc.text)
    print(f"\nLine count: {doc.line_count}")
    print(f"Document size: {doc.get_size(4)}")

    # Replace some text
    result = doc.replace_range((0, 7), (0, 12), "Python")
    print(f"\nAfter replacing 'World' with 'Python':")
    print(doc.text)
    print(f"Replaced text: '{result.replaced_text}'")
    print(f"New end location: {result.end_location}")

    # Get text range
    text_range = doc.get_text_range((0, 0), (1, 10))
    print(f"\nText from (0,0) to (1,10): '{text_range}'")

    # Insert text
    doc.replace_range((1, 0), (1, 0), ">> ")
    print(f"\nAfter inserting '>> ' at start of line 2:")
    print(doc.text)

    # Delete text
    doc.replace_range((2, 0), (2, 5), "")
    print(f"\nAfter deleting first 5 chars of line 3:")
    print(doc.text)