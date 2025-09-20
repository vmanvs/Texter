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
        """
        Get the length of the text sequence
        :return: length (int)
        """
        return self._text_len

    def __getitem__(self, key):
        """
        Abstraction to the piece table data retrieval, uses python slices for such operations
        :int/slice key: the index of the item, or a slice containing start/stop/step values
        :return: text sequence
        """
        if isinstance(key, int):
            return self.string_at(key, 1) #return 1 character from the given index
        elif isinstance(key, slice):
            start, stop, step = key.indices(len(self))
            return self.string_at(start, stop-start)[::step]
        else:
            raise TypeError("Piece table can only handle int or slice, it can't be {}".format(type(key).__name__))

    def insert(self, index, text): #need to use recursion for this method
        element = _Piece(True, index, len(text))


    def delete(self, index, length):
        """
        Delete the text sequence from the table
        :int index: the index of the piece to be deleted
        :int length: the length of the piece to be deleted
        :return:
        """
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


    def replace(self, index, replace_count, items):
        """
        :int index: starting index of the piece to be replaced
        :int replace_count: number of pieces to be replaced
        :list[_Pieces] items: Piece of items to take place
        :returns list[_Pieces]
        """
        #includes whole starting piece---the items---includes the piece after the replacement count effectively removing the pointers to replaced items
        return self.pieces[index:] + items + self.pieces[index+replace_count:]



    def get_text(self):
        """Gets the text sequence of the piece
        :return: text sequence: string
        """
        document = ""
        for piece in self.pieces:
            if piece.in_added:
                document += self._added[piece.offset:piece.offset + piece.length]
            else:
                document += self.original[piece.offset:piece.offset + piece.length]

        return document

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

        #if single piece return text from the piece
        if start_piece_index == stop_piece_index:
            # start from the given index instead of the buffer if 1 buffer
            document = buffer[start_piece_offset:start_piece_offset+length]
        else:
            #start_piece.offset is the starting index of the buffer
            #start_piece_offset is the specific position within that buffer from where to search from :see get_text_and_offset

            document = buffer[start_piece_offset:start_piece.offset + length] #include the first buffer completely
            for i in range(start_piece_index + 1, stop_piece_index + 1): #from the second index to the stop index
                cur_piece = self.pieces[i]
                buffer = self._added if cur_piece.in_added else self.original

                if i==stop_piece_index:
                    document += buffer[cur_piece.offset:stop_piece_offset] #if last index, add upto the specified length
                else:
                    document += buffer[cur_piece.offset:cur_piece.offset + cur_piece.length] #else include the piece completely

        return document




