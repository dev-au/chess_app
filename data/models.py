from datetime import timedelta

from aioredis import Redis
from tortoise import Model, fields
from tortoise.exceptions import ValidationError


class User(Model):
    username = fields.CharField(unique=True, max_length=15)
    password = fields.TextField()
    fullname = fields.CharField(max_length=25)
    age = fields.IntField()
    country = fields.CharField(max_length=25)
    all_games = fields.IntField(default=0)
    wins = fields.IntField(default=0)
    losses = fields.IntField(default=0)
    is_active = fields.BooleanField(default=False)
    is_admin = fields.BooleanField(default=False)
    is_super_admin = fields.BooleanField(default=False)
    playing_now = fields.BooleanField(default=False)

    async def update_status(self, offline=False, online=False):
        if online:
            self.is_active = True
        elif offline:
            self.is_active = False
            self.playing_now = False
        else:
            raise ValueError('You must to set is_active to True or False')
        await self.save()

    async def get_swiss_system_rating(self):
        return self.wins + (self.all_games - self.losses - self.wins) * 0.5

    async def get_offers(self, redis: Redis):
        offers = await redis.get(f'offer:{self.pk}')
        return list(map(int, offers.decode('utf-8').split(':'))) if offers else []

    async def add_offer(self, inviter_user, redis: Redis):
        offers = await redis.get(f'offer:{self.pk}')
        if offers:
            offers = offers.decode('utf-8')
            offers += ':' + str(inviter_user.pk)
        else:
            offers = str(inviter_user.pk)
        await redis.set(f'offer:{self.pk}', offers, ex=timedelta(minutes=5))

    async def remove_offer(self, inviter_user, redis: Redis):
        await redis.set(
            f'offer:{self.pk}',
            ':'.join(filter(lambda x: x != str(inviter_user.pk),
                            (await redis.get(f'offer:{self.pk}')).decode('utf-8').split(':'))),
            ex=timedelta(minutes=5)
        )


class Tournament(Model):
    name = fields.CharField(max_length=50)
    owner = fields.ForeignKeyField('models.User')
    created_at = fields.DatetimeField(auto_now_add=True)
    finishing_at = fields.DatetimeField()


class TournamentParticipant(Model):
    participant = fields.ForeignKeyField('models.User')
    tournament = fields.ForeignKeyField('models.Tournament')
    all_games = fields.IntField(default=0)
    wins = fields.IntField(default=0)
    losses = fields.IntField(default=0)


class Match(Model):
    white_player = fields.ForeignKeyField('models.User', related_name='white_player')
    black_player = fields.ForeignKeyField('models.User', related_name='black_player')
    tournament = fields.ForeignKeyField('models.Tournament', null=True)
    # 1-King 2-Queen 3-Rook 4-Bishop 5-Knight 6-Pawn
    board = fields.TextField(
        default="1113121513141412151116141715181321162216231624162516261627162816"
                "-8123822583248422852186248725882371267226732674267526762677267826")
    # Example:
    # 1413 -> 14 means: Coordinates: 1D, 13 means: 1 is white piece 3 is Rook
    # 2526 -> 25 is Coordinates 2E, next 2 mean is black piece 6 is Pawn

    started_at = fields.DatetimeField(auto_now_add=True)
    finished_at = fields.DatetimeField(null=True)
    now_turn = fields.IntField(default=1)
    during_1 = fields.TimeDeltaField()
    during_2 = fields.TimeDeltaField()
    winner = fields.IntField(default=-1)  # -1 means is during, 0-draw, 1-white_player was won 2-black_player was won

    async def move(self, from_at: str, to_at: str):
        from_idx = self.chess_notation_to_index(from_at)
        to_idx = self.chess_notation_to_index(to_at)

        piece = self.board[from_idx:from_idx + 2]
        if piece[1] == '0':
            raise ValidationError("No piece at the source location.")

        if self.now_turn == 1 and piece[0] != '1':
            raise ValidationError("It's white's turn.")
        elif self.now_turn == 2 and piece[0] != '2':
            raise ValidationError("It's black's turn.")

        # Validate the move
        if not self._validate_move(piece, from_idx, to_idx):
            raise ValidationError("Invalid move.")

        # Update the board
        new_board = list(self.board)
        new_board[from_idx:from_idx + 2] = '00'  # Empty the source cell
        new_board[to_idx:to_idx + 2] = piece  # Move the piece to the destination cell
        self.board = "".join(new_board)

        # Update the turn
        self.now_turn = 2 if self.now_turn == 1 else 1

        # Check for checkmate or stalemate
        if self._is_checkmate(self.now_turn):
            return "Checkmate!"
        elif self._is_stalemate(self.now_turn):
            return "Stalemate!"

        await self.save()

    def _is_check(self, color: str) -> bool:
        king_position = self._find_king(color)
        return self._is_position_under_threat(king_position, '1' if color == '2' else '2')

    def _is_checkmate(self, color: str) -> bool:
        if not self._is_check(color):
            return False
        return not self._has_legal_moves(color)

    def _is_stalemate(self, color: str) -> bool:
        if self._is_check(color):
            return False
        return not self._has_legal_moves(color)

    def _has_legal_moves(self, color: str) -> bool:
        for from_idx in range(0, len(self.board), 2):
            piece = self.board[from_idx:from_idx + 2]
            if piece[0] == color:
                for to_idx in range(0, len(self.board), 2):
                    if self._validate_move(piece, from_idx, to_idx):
                        # Perform the move and check if it resolves the check
                        temp_board = list(self.board)
                        temp_board[to_idx:to_idx + 2] = piece
                        temp_board[from_idx:from_idx + 2] = '00'
                        temp_board = "".join(temp_board)
                        if not self._is_check(color):
                            return True
        return False

    def _find_king(self, color: str) -> int:
        for idx in range(0, len(self.board), 2):
            piece = self.board[idx:idx + 2]
            if piece[0] == color and piece[1] == '1':  # '1' represents the King
                return idx
        return -1

    def _is_position_under_threat(self, position: int, opponent_color: str) -> bool:
        for idx in range(0, len(self.board), 2):
            piece = self.board[idx:idx + 2]
            if piece[0] == opponent_color:
                if self._validate_move(piece, idx, position):
                    return True
        return False

    @staticmethod
    def chess_notation_to_index(notation: str) -> int:
        file = notation[0].upper()
        rank = notation[1]

        files = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8}
        return (int(rank) - 1) * 8 * 2 + (files[file] - 1) * 2

    def _validate_move(self, piece: str, from_idx: int, to_idx: int) -> bool:
        piece_type = int(piece[1])

        if piece_type == 1:  # King
            return self._validate_king_move(from_idx, to_idx)
        elif piece_type == 2:  # Queen
            return self._validate_queen_move(from_idx, to_idx)
        elif piece_type == 3:  # Rook
            return self._validate_rook_move(from_idx, to_idx)
        elif piece_type == 4:  # Bishop
            return self._validate_bishop_move(from_idx, to_idx)
        elif piece_type == 5:  # Knight
            return self._validate_knight_move(from_idx, to_idx)
        elif piece_type == 6:  # Pawn
            return self._validate_pawn_move(piece[0], from_idx, to_idx)

        return False

    def _validate_king_move(self, from_idx: int, to_idx: int) -> bool:
        row_diff = abs((from_idx // 2) // 8 - (to_idx // 2) // 8)
        col_diff = abs((from_idx // 2) % 8 - (to_idx // 2) % 8)
        return row_diff <= 1 and col_diff <= 1 and not self._is_same_color(from_idx, to_idx)

    def _validate_queen_move(self, from_idx: int, to_idx: int) -> bool:
        return (self._validate_rook_move(from_idx, to_idx) or
                self._validate_bishop_move(from_idx, to_idx))

    def _validate_rook_move(self, from_idx: int, to_idx: int) -> bool:
        if self._is_same_color(from_idx, to_idx):
            return False
        from_row, from_col = (from_idx // 2) // 8, (from_idx // 2) % 8
        to_row, to_col = (to_idx // 2) // 8, (to_idx // 2) % 8
        if from_row == to_row:
            step = 2 if from_col < to_col else -2
            for col in range(from_col + step, to_col, step):
                if self.board[from_row * 16 + col * 2: from_row * 16 + col * 2 + 2] != '00':
                    return False
        elif from_col == to_col:
            step = 16 if from_row < to_row else -16
            for row in range(from_row * 16 + step, to_row * 16, step):
                if self.board[row + from_col * 2: row + from_col * 2 + 2] != '00':
                    return False
        else:
            return False
        return True

    def _validate_bishop_move(self, from_idx: int, to_idx: int) -> bool:
        if self._is_same_color(from_idx, to_idx):
            return False
        from_row, from_col = (from_idx // 2) // 8, (from_idx // 2) % 8
        to_row, to_col = (to_idx // 2) // 8, (to_idx // 2) % 8
        if abs(from_row - to_row) == abs(from_col - to_col):
            row_step = 16 if from_row < to_row else -16
            col_step = 2 if from_col < to_col else -2
            for step in range(1, abs(from_row - to_row)):
                if self.board[
                   from_idx + step * (row_step + col_step): from_idx + step * (row_step + col_step) + 2] != '00':
                    return False
            return True
        return False

    def _validate_knight_move(self, from_idx: int, to_idx: int) -> bool:
        from_row, from_col = (from_idx // 2) // 8, (from_idx // 2) % 8
        to_row, to_col = (to_idx // 2) // 8, (to_idx // 2) % 8
        if (abs(from_row - to_row), abs(from_col - to_col)) in [(2, 1), (1, 2)]:
            return not self._is_same_color(from_idx, to_idx)
        return False

    def _validate_pawn_move(self, color: str, from_idx: int, to_idx: int) -> bool:
        from_row, from_col = (from_idx // 2) // 8, (from_idx // 2) % 8
        to_row, to_col = (to_idx // 2) // 8, (to_idx // 2) % 8
        if color == '1':
            if from_row == 1 and to_row == from_row + 2 and from_col == to_col and self._is_empty(to_row - 1,
                                                                                                  to_col):
                return self._is_empty(to_row, to_col)
            if to_row == from_row + 1 and from_col == to_col:
                return self._is_empty(to_row, to_col)
            if to_row == from_row + 1 and abs(to_col - from_col) == 1:
                return not self._is_empty(to_row, to_col) and self._is_opponent(color, to_idx)
        else:
            if from_row == 6 and to_row == from_row - 2 and from_col == to_col and self._is_empty(to_row + 1,
                                                                                                  to_col):
                return self._is_empty(to_row, to_col)
            if to_row == from_row - 1 and from_col == to_col:
                return self._is_empty(to_row, to_col)
            if to_row == from_row - 1 and abs(to_col - from_col) == 1:
                return not self._is_empty(to_row, to_col) and self._is_opponent(color, to_idx)
        return False

    def _is_empty(self, row: int, col: int) -> bool:
        return self.board[row * 16 + col * 2: row * 16 + col * 2 + 2] == '00'

    def _is_opponent(self, color: str, idx: int) -> bool:
        return (color == '1' and self.board[idx] == '2') or (color == '2' and self.board[idx] == '1')

    def _is_same_color(self, from_idx: int, to_idx: int) -> bool:
        return self.board[from_idx] == self.board[to_idx]
