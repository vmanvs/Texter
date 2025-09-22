class _Piece:
    def __init__(self, in_added, offset, length):
        """
        Here the basic unit is piece which will contain characters or bytes.
        in_added(bool): checks whether the added sequence is part of original file or added file
        offset (int): determines the offset from where the element should start
        length (int): is the length of the piece
        """
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
        """
        Takes the index of the text-sequence after which the text needs to be inserted
        :int index:
        :str text:
        """
        if len(text) == 0:
            return

        piece_index, piece_offset = self.get_piece_and_offset(index)
        cur_piece = self.pieces[piece_index]

        added_offset = len(self._added)
        self._added += text
        self._text_len += len(text)

        #piece_offset is the exact position for insertion of text in the buffer
        #while, cur_piece.offset is the starting position of the buffer

        if (
            cur_piece.in_added and
            piece_offset == cur_piece.offset + cur_piece.length == added_offset
        #exact insertion point == end of current piece == end of the add buffer
        ):
            cur_piece.length += len(text)
            return

        insert_pieces = [
            _Piece(cur_piece.in_added, cur_piece.offset, piece_offset-cur_piece.offset),
            _Piece(True, added_offset, len(text)),
            _Piece(cur_piece.in_added, piece_offset, cur_piece.length-(piece_offset-cur_piece.offset)),
        ]

        #    ========== initially
        #    ========== ====  (space represents a different buffer)
        #    ^   ^      ^
        #    A   B      C
        # remember the original buffer is read only, changes can only be made in the add buffer
        # A=cur_piece.offset, B=piece_offset, C=added_offset

        insert = list(filter(lambda piece: piece.length > 0, insert_pieces))

        self.pieces = self.replace(piece_index, 1, insert)

    def delete(self, index, length):
        """
        Delete the text sequence from the table
        :int index: the index of the piece to be deleted
        :int length: the length of the piece to be deleted
        :return:
        """

        start_piece_index, start_piece_offset = self.get_piece_and_offset(index)
        stop_piece_index, stop_piece_offset = self.get_piece_and_offset(index+length)
        self._text_len -= length

        #Single Piece Logic
        #if single piece check if delete is at the beginning or end of the piece
        if start_piece_index == stop_piece_index: #same piece
            piece = self.pieces[start_piece_index]

            if piece.offset == start_piece_offset: #delete at the beginning
                piece.offset += length
                piece.length -= length
                return

            # ============= (single piece)
            # ^     ^
            # A     B
            # A=piece.offset, B=length, after deletion =>
            # ******=======
            #       ^
            #       C = new offset: piece.offset+length


            if (piece.offset + piece.length) == stop_piece_offset: #delete at the end
                piece.length -= length
                return

            # ========== (single piece)
            # ^    ^   ^
            # A    B   C
            # A: piece.offset, C: piece.offset+piece.length,  C-B: delete length
            # After deletion:;
            # ======**** p.s. The objects are not actually removed just the pointers to them are removed making them inaccessible

        #Multi-Piece Logic
        start_piece = self.pieces[start_piece_index]
        end_piece = self.pieces[stop_piece_index]

        delete_pieces = [

            _Piece(start_piece.in_added, start_piece.offset, start_piece_offset-start_piece.offset ),
            # About piece length :Since we are deleting the entire sequence after start_piece_offset: e.g.
            # Hello
            # 01234
            # lets say we want to delete 'lo'
            # in this case start_piece_offset = 3 and start_piece.offset = 0
            # Hel
            # new_length = 3-0 = 3 which is correct.

            _Piece(end_piece.in_added, stop_piece_offset, end_piece.length + (stop_piece_offset-end_piece.offset)),
            # About piece offset: since we are deleting everything before the stop_piece_offset we will push the pointer back to that position
            # Beautiful_World ('_' defines a space character)
            # 0123456789ABCDE (A=10, B=11, C=12,.....)
            # lets say we want to delete everything upto World
            # stop_piece_index = A
            # end_piece.offset = 0
            # new offset should be the offset of 'W' i.e. 10
            # About length: end_piece.length = 15, stop_piece_offset = 10, end_piece.offset = 0
            # 15 - (10-0) = 5 which is correct

        ]

        delete = list(filter(lambda piece: piece.length > 0, delete_pieces))

        delete_count = stop_piece_index - start_piece_index + 1 #this is for multi piece delete only

        self.pieces = self.replace(start_piece_index, delete_count, delete)


    def get_piece_and_offset(self, index):
        """
        Essentially translates: logical position x in the combined text to; piece:y, position_in_buffer(piece):z
        :param index:
        :return:
        """

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




