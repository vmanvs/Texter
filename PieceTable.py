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
    #expects a string (document)
    def __init__(self, document):
        self._text_len = len(document)
        self.original = document
        self._added = ""
        self.pieces = [_Piece(False, 0, len(document))] #store the info about pieces in an array

    def __len__(self):
        return self._text_len

    def __getitem__(self, index):


    def insert(self, index, text): #need to use recursion for this method
        element = _Piece(True, index, len(text))


    def delete(self, index, length):
        element = _Piece(True, index, length)


    def get_piece_and_offset(self, index):

        if index < 0:
            raise IndexError("Index can't be negative.")

        #start from the given index
        remaining_offset = index
        #compare the index to piece length
        for i in range(len(self.pieces)):
            piece = self.pieces[i]

            if remaining_offset <= piece.length: #if the remaining_offset is within piece, return the piece index and offset to piece
                return i, piece.offset+remaining_offset
            remaining_offset -= piece.length

            return IndexError("Text index can't be greater than length of text.")


    def replace(self, index, length, text):

    def get_text(self):

    def string_at(self, index, length):
        """
        Get string of particular length from index
        :int index: the index from where to begin
        :int length: the length of the string to find
        :return: string
        """

        start_piece_index, start_piece_offset = self.get_piece_and_offset(index)
        stop_piece_index, stop_piece_offset = self.get_piece_and_offset(index+length)

        start_piece = self.pieces[start_piece_index]
        buffer = self._added if start_piece.in_added else self.original #choose the add buffer if the piece exists in it, else choose the original buffer






