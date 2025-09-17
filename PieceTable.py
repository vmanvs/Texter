class _Piece:
    def __init__(self, in_added, offset, length):
        """Here the basic unit is piece which will contain characters or bytes.
        is_original(bool): checks whether the added sequence is part of original file or added file
        offset (int): determines the offset from where the element should start
        length (int): is the length of the piece"""
        self.in_added = in_added
        self.offset = offset
        self.length = length

class PieceTable:
    def __init__(self, document):
        self._text_len = len(document)
        self.original = document
        self._added = ""
        self.pieces = [_Piece(False, 0, len(document))]

