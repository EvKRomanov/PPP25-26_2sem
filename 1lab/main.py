# Шахматный симулятор (ООП-версия) для консоли.
# Реализованы:
# - базовые правила шахмат;
# - новые виды фигур;
# - откат ходов;
# - подсказка допустимых ходов;
# - подсказка угрожаемых фигур и шаха;
# - сложные правила пешек (двойной ход, взятие на проходе, превращение).

from __future__ import annotations  # Использовать аннотации типов с классами
from dataclasses import dataclass   # способ описать кл-данные для храненияхода
from typing import List, Optional, Tuple  # Типы для аннотаций.

# Размер стандартной шахматной доски 8x8.
BOARD_SIZE: int = 8

# Псевдоним для координат клетки: (строка, столбец).
Coord = Tuple[int, int]


def in_bounds(row: int, col: int) -> bool:
    """Проверяем, что координаты находятся внутри доски 8x8."""
    return 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE


def algebraic_to_coord(s: str) -> Optional[Coord]:
    """
    Преобразуем текстовую координату вида 'e2'
    в внутреннее представление (row, col).
    row = 0 — верхняя (8-я) горизонталь, row = 7 — нижняя (1-я).
    """
    s = s.strip().lower()          # Удаляем пробелы и приводим к нижнему регис
    if len(s) != 2:                # Координата должна состоять ровно из 2 симв
        return None
    file_char, rank_char = s[0], s[1]  # file — буква столба, rank — цифра стр
    if file_char < "a" or file_char > "h":  # Столбец может быть только от a h
        return None
    if rank_char < "1" or rank_char > "8":  # Строка может быть только от 1'8'.
        return None
    col = ord(file_char) - ord("a")         # буквы в цифры по ascii
    row = BOARD_SIZE - int(rank_char)       # п
    return row, col


def coord_to_algebraic(coord: Coord) -> str:  # принимает кортеж из двух чисел
    """
    Обратное преобразование: из (row, col)
    в координату вида 'e2'.
    """
    row, col = coord                           # Распаковываем кортеж.
    file_char = chr(ord("a") + col)            # обратно в букву
    rank_char = str(BOARD_SIZE - row)          # 0 -> '8', ..., 7 -> '1'.
    return file_char + rank_char               # Склеиваем букву и цифру.


class Piece:
    """Базовый класс для любой шахматной фигуры."""

    def __init__(self, color: str, name: str, symbol: str) -> None:
        self.color: str = color     # Цвет фигуры: "white" или "black".
        self.name: str = name       # Человекочитаемое имя (например, "Pawn").
        self.symbol: str = symbol   # Короткий символ для отображения на доске.

    def get_pseudo_legal_moves(
            self, board: "Board", row: int, col: int
            ) -> List[Coord]:
        """
        Псевдолегальные ходы: фигура двигается по своим правилам,
        но мы пока НЕ проверяем шах своему королю.
        Конкретные фигуры переопределяют этот метод.
        """
        return []

    def enemy_color(self) -> str:
        """Возвращает цвет противника для данной фигуры."""
        return "black" if self.color == "white" else "white"

    def __repr__(self) -> str:
        """Короткое текстовое представление фигуры для отладки."""
        return f"{self.color[0].upper()}{self.symbol}"


class SlidingPiece(Piece):
    """
    Базовый класс для "скользящих" фигур — ладья, слон, ферзь.
    Вспомогательный класс, чтобы не дублировать логику.
    """

    def _collect_sliding_moves(
        self,
        board: "Board",
        row: int,
        col: int,
        directions: List[Tuple[int, int]],
    ) -> List[Coord]:
        """
        Идём по каждому направлению, пока не упрёмся в фигуру или край доски.
        directions — список векторов (delta_row, delta_col).
        """
        moves: List[Coord] = []           # Сюда будем собирать возможные ходы.
        for dr, dc in directions:          # Перебираем все направления.
            r, c = row + dr, col + dc  # Двигаемся на одну клетку в этом направ
            while in_bounds(r, c):         # Пока не вышли за пределы доски.
                target = board.get_piece(r, c)  # Смотрим, что находится на кле
                if target is None:           # Если клетка пуста, можем идти
                    moves.append((r, c))
                else:
                    # Если на клетке фигура противника — можем побить и стоп
                    if target.color != self.color:
                        moves.append((r, c))
                    # В любом случае дальше по этому направлению идти нельзя.
                    break
                r += dr         # Переходим ещё на одну клетку по направлению
                c += dc
        return moves


class Rook(SlidingPiece):
    """Ладья — ходит по вертикалям и горизонталям."""

    def __init__(self, color: str) -> None:
        super().__init__(color, "Rook", "R")

    def get_pseudo_legal_moves(
            self, board: "Board", row: int, col: int
            ) -> List[Coord]:
        # Ладья ходит по четырём направлениям: вверх, вниз, влево, вправо.
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        return self._collect_sliding_moves(board, row, col, directions)


class Bishop(SlidingPiece):
    """Слон — ходит по диагоналям."""

    def __init__(self, color: str) -> None:
        super().__init__(color, "Bishop", "B")

    def get_pseudo_legal_moves(
            self, board: "Board", row: int, col: int
            ) -> List[Coord]:
        # Слон ходит по четырём диагоналям.
        directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        return self._collect_sliding_moves(board, row, col, directions)


class Queen(SlidingPiece):
    """Ферзь — комбинация ладьи и слона."""

    def __init__(self, color: str) -> None:
        super().__init__(color, "Queen", "Q")

    def get_pseudo_legal_moves(
            self, board: "Board", row: int, col: int
            ) -> List[Coord]:
        # Ферзь сочетает все направления ладьи и слона.
        directions = [
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1),
            (-1, -1),
            (-1, 1),
            (1, -1),
            (1, 1),
        ]
        return self._collect_sliding_moves(board, row, col, directions)


class Knight(Piece):
    """Конь — ходит буквой Г, 'перепрыгивая' через фигуры."""

    def __init__(self, color: str) -> None:
        super().__init__(color, "Knight", "N")

    def get_pseudo_legal_moves(
            self, board: "Board", row: int, col: int
            ) -> List[Coord]:
        # Возможные смещения для коня.
        deltas = [
            (-2, -1),
            (-2, 1),
            (-1, -2),
            (-1, 2),
            (1, -2),
            (1, 2),
            (2, -1),
            (2, 1),
        ]
        moves: List[Coord] = []
        for dr, dc in deltas:
            r, c = row + dr, col + dc
            if not in_bounds(r, c):   # Пропускаем клетки за пределами доски.
                continue
            target = board.get_piece(r, c)  # Проверяем, есть ли фигура на клет
            if target is None or target.color != self.color:
                # Можно или просто пойти на пустую клетку, или побить чужую фиг
                moves.append((r, c))
        return moves


class King(Piece):
    """Король — ходит на одну клетку в любом направлении."""

    def __init__(self, color: str) -> None:
        super().__init__(color, "King", "K")

    def get_pseudo_legal_moves(
            self, board: "Board", row: int, col: int
            ) -> List[Coord]:
        # Все 8 соседних направлений.
        deltas = [
            (-1, -1),
            (-1, 0),
            (-1, 1),
            (0, -1),
            (0, 1),
            (1, -1),
            (1, 0),
            (1, 1),
        ]
        moves: List[Coord] = []
        for dr, dc in deltas:
            r, c = row + dr, col + dc
            if not in_bounds(r, c):
                continue
            target = board.get_piece(r, c)
            if target is None or target.color != self.color:
                moves.append((r, c))
        # Рокировку в этой версии для простоты не реализуем.
        return moves


class Pawn(Piece):
    """Пешка — самая сложная по правилам фигура."""

    def __init__(self, color: str) -> None:
        super().__init__(color, "Pawn", "P")

    def get_pseudo_legal_moves(
            self, board: "Board", row: int, col: int
            ) -> List[Coord]:
        """
        Реализуем:
        - обычный ход на одну клетку вперёд;
        - двойной ход с начальной позиции;
        - обычные взятия по диагонали;
        - взятие на проходе (использует board.en_passant_target).
        """
        moves: List[Coord] = []

        # Направление движения пешки:
        # белые идут "вверх" (к нулевой строке), чёрные — "вниз".
        direction = -1 if self.color == "white" else 1

        # Одна клетка вперёд.
        one_ahead_row = row + direction
        if in_bounds(one_ahead_row, col) and \
           board.get_piece(one_ahead_row, col) is None:
            moves.append((one_ahead_row, col))

            # Две клетки вперёд — только если пешка ещё не ходила.
            start_row = 6 if self.color == "white" else 1
            two_ahead_row = row + 2 * direction
            if row == start_row and \
               board.get_piece(two_ahead_row, col) is None:
                moves.append((two_ahead_row, col))

        # Диагональные взятия (обычные и на проходе).
        for dc in (-1, 1):
            r = row + direction
            c = col + dc
            if not in_bounds(r, c):
                continue
            target = board.get_piece(r, c)
            # Обычное взятие фигуры противника.
            if target is not None and target.color != self.color:
                moves.append((r, c))
            # Взятие на проходе: целевая клетка совпадает с en_passant_target.
            if board.en_passant_target is not None and \
               (r, c) == board.en_passant_target:
                moves.append((r, c))

        return moves


# --- Дополнительные (новые) типы фигур ---

class Chancellor(Piece):
    """
    Первая оригинальная фигура.
    Ходит как ладья И как конь (часто называется 'Чанселор').
    """

    def __init__(self, color: str) -> None:
        super().__init__(color, "Chancellor", "C")

    def get_pseudo_legal_moves(
            self, board: "Board", row: int, col: int
            ) -> List[Coord]:
        # Используем логику ладьи и коня.
        rook_part = Rook(self.color).get_pseudo_legal_moves(board, row, col)
        knight_part = Knight(self.color) \
            .get_pseudo_legal_moves(board, row, col)
        return rook_part + knight_part


class Archbishop(Piece):
    """
    Вторая оригинальная фигура.
    Ходит как слон И как конь.
    """

    def __init__(self, color: str) -> None:
        super().__init__(color, "Archbishop", "A")

    def get_pseudo_legal_moves(
            self, board: "Board", row: int, col: int
            ) -> List[Coord]:
        bishop_part = Bishop(self.color) \
            .get_pseudo_legal_moves(board, row, col)
        knight_part = Knight(self.color) \
            .get_pseudo_legal_moves(board, row, col)
        return bishop_part + knight_part


class Amazon(Piece):
    """
    Третья оригинальная фигура.
    Ходит как ферзь И как конь (иногда называется 'Амазонка').
    """

    def __init__(self, color: str) -> None:
        super().__init__(color, "Amazon", "Z")  # Используем букву Z

    def get_pseudo_legal_moves(
            self, board: "Board", row: int, col: int
            ) -> List[Coord]:
        queen_part = Queen(self.color).get_pseudo_legal_moves(board, row, col)
        knight_part = Knight(self.color) \
            .get_pseudo_legal_moves(board, row, col)
        return queen_part + knight_part


@dataclass
class Move:
    """
    Класс для хранения информации об одном ходе.
    Нужен для реализации отката ходов.
    """
    start: Coord                    # Откуда ходили.
    end: Coord                      # Куда ходили.
    piece: Piece                    # Кем ходили (фигура после хода).
    captured: Optional[Piece]       # Съеденная фигура, если была.
    was_en_passant: bool = False    # Было ли взятие на проходе.
    captured_coord: Optional[Coord] = None  # Место сьеденной пешки на проходе
    en_passant_before: Optional[Coord] = None  # Значение en_pas... до хода.
    promotion: bool = False         # Было ли превращение пешки.
    original_pawn: Optional[Piece] = None     # Пешка до превращения.


class Board:
    """Класс доски: хранит фигуры, очередь хода и историю ходов."""

    def __init__(self) -> None:
        # Создаём пустую сетку 8x8, заполненную None.
        self.grid: List[List[Optional[Piece]]] = [
            [None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)
        ]
        self.current_color: str = "white"      # Начинают белые.
        self.en_passant_target: Optional[Coord] = None  # Клетка для взятия
        self.history: List[Move] = []          # Список сделанных ходов.
        self.setup_initial_position()          # Сразу расставляем фигуры.

    # --- Методы работы с клетками ---

    def get_piece(self, row: int, col: int) -> Optional[Piece]:
        """Возвращает фигуру на указанной клетке или None."""
        return self.grid[row][col]

    def set_piece(self, row: int, col: int, piece: Optional[Piece]) -> None:
        """Ставит фигуру на клетку (или None, чтобы очистить клетку)."""
        self.grid[row][col] = piece

    # --- Инициализация начальной позиции ---

    def setup_initial_position(self) -> None:
        """Расставляем стандартные шахматные фигуры на стартовые позиции."""
        # Расставляем ладьи.
        self.set_piece(7, 0, Rook("white"))
        self.set_piece(7, 7, Rook("white"))
        self.set_piece(0, 0, Rook("black"))
        self.set_piece(0, 7, Rook("black"))

        # Расставляем коней.
        self.set_piece(7, 1, Knight("white"))
        self.set_piece(7, 6, Knight("white"))
        self.set_piece(0, 1, Knight("black"))
        self.set_piece(0, 6, Knight("black"))

        # Расставляем слонов.
        self.set_piece(7, 2, Bishop("white"))
        self.set_piece(7, 5, Bishop("white"))
        self.set_piece(0, 2, Bishop("black"))
        self.set_piece(0, 5, Bishop("black"))

        # Ферзи.
        self.set_piece(7, 3, Queen("white"))
        self.set_piece(0, 3, Queen("black"))

        # Короли.
        self.set_piece(7, 4, King("white"))
        self.set_piece(0, 4, King("black"))

        # Пешки.
        for col in range(BOARD_SIZE):
            self.set_piece(6, col, Pawn("white"))
            self.set_piece(1, col, Pawn("black"))

        # Дополнительно: можно для примера поставить по одной новой фигуре.
        # Здесь мы не ставим их изначально,но они доступны как варианты смены П

    # --- Печать доски ---

    def print_board(self) -> None:
        """Выводит доску в текстовом виде в консоль."""
        print("  +------------------------+")  # Верхняя рамка.
        for row in range(BOARD_SIZE):
            rank = BOARD_SIZE - row          # Номер горизонтали (8..1).
            print(rank, "|", end=" ")        # Печатаем номер строки слева.
            for col in range(BOARD_SIZE):
                piece = self.get_piece(row, col)
                if piece is None:
                    symbol = "."             # Пустую клетку обозначаем точкой.
                else:
                    # Белые фигуры делаем заглавными, чёрные — строчными.
                    symbol = piece.symbol.upper() if piece.color == "white" \
                        else piece.symbol.lower()
                print(symbol, end=" ")
            print("|")                       # Правая рамка строки.
        print("  +------------------------+")  # Нижняя рамка.
        print("    a b c d e f g h")          # Подпись столбцов.

    # --- Поиск короля и проверка шаха ---

    def find_king(self, color: str) -> Optional[Coord]:
        """Находит координаты короля указанного цвета."""
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                piece = self.get_piece(row, col)
                if isinstance(piece, King) and piece.color == color:
                    return row, col
        return None

    def is_square_attacked(self, row: int, col: int, by_color: str) -> bool:
        """
        Проверяем, бьёт ли клетку (row, col) хоть одна фигура цвета by_color.
        Используем псевдолегальные ходы фигур противника.
        """
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                piece = self.get_piece(r, c)
                if piece is None or piece.color != by_color:
                    continue
                for move_row, move_col in piece.get_pseudo_legal_moves(
                    self, r, c
                ):
                    if move_row == row and move_col == col:
                        return True
        return False

    def is_in_check(self, color: str) -> bool:
        """Находится ли король указанного цвета под боем."""
        king_pos = self.find_king(color)
        if king_pos is None:
            return False
        kr, kc = king_pos
        return self.is_square_attacked(
            kr, kc, by_color="black" if color == "white" else "white"
        )

    # --- Генерация ЛЕГАЛЬНЫХ ходов (учитываем шах своему королю) ---

    def generate_legal_moves_from(self, row: int, col: int) -> List[Coord]:
        """
        Возвращает список координат, куда фигура с клетки (row, col)
        может сделать легальный ход (без оставления своего короля под шахом).
        """
        piece = self.get_piece(row, col)
        if piece is None or piece.color != self.current_color:
            return []
        legal_moves: List[Coord] = []
        for r, c in piece.get_pseudo_legal_moves(self, row, col):
            # Сохраняем текущее состояние, чтобы откатить пробный ход.
            saved_en_passant = self.en_passant_target
            captured = self.get_piece(r, c)
            # Дополнительные данные для взятия на проходе.
            was_en_passant = False
            captured_coord = None

            # Обрабатываем особый случай взятия на проходе.
            if isinstance(piece, Pawn) and captured is None and \
               self.en_passant_target == (r, c):
                was_en_passant = True
                direction = -1 if piece.color == "white" else 1
                pawn_row = r + direction  # Реальная позиция съедаемой пешки.
                pawn_col = c
                captured = self.get_piece(pawn_row, pawn_col)
                captured_coord = (pawn_row, pawn_col)
                self.set_piece(pawn_row, pawn_col, None)

            # Делаем пробный ход.
            self.set_piece(row, col, None)
            self.set_piece(r, c, piece)
            self.en_passant_target = None  # При проверке считаем будто сброшен

            # Если после хода король не под шахом — ход легален.
            if not self.is_in_check(piece.color):
                legal_moves.append((r, c))

            # Откатываем пробный ход.
            self.set_piece(row, col, piece)
            self.set_piece(r, c, captured)
            self.en_passant_target = saved_en_passant
            if was_en_passant and captured_coord is not None and \
               captured is not None:
                cr, cc = captured_coord
                self.set_piece(cr, cc, captured)

        return legal_moves

    # --- Совершение реального хода и откат ---

    def make_move(self, start: Coord, end: Coord, promotion_choice: Optional[str] = None) -> bool:
        """
        Пытается сделать ход из start в end.
        Возвращает True, если ход был выполнен, иначе False.
        """
        sr, sc = start
        er, ec = end
        if not in_bounds(sr, sc) or not in_bounds(er, ec):
            print("Координаты вне доски.")
            return False

        piece = self.get_piece(sr, sc)
        if piece is None:
            print("На начальной клетке нет фигуры.")
            return False
        if piece.color != self.current_color:
            print("Сейчас ход другого цвета.")
            return False

        legal_moves = self.generate_legal_moves_from(sr, sc)
        if (er, ec) not in legal_moves:
            print("Ход недопустим.")
            return False

        # Сохраняем информацию для отката.
        captured = self.get_piece(er, ec)
        was_en_passant = False
        captured_coord = None
        en_passant_before = self.en_passant_target

        # Сбрасываем en_passant_target перед вычислением нового.
        self.en_passant_target = None

        # Обработка взятия на проходе.
        if isinstance(piece, Pawn) and captured is None and \
           en_passant_before == (er, ec):
            was_en_passant = True
            direction = -1 if piece.color == "white" else 1
            pawn_row = er + direction       # Реальная координата съедаемой пеш
            pawn_col = ec
            captured = self.get_piece(pawn_row, pawn_col)
            captured_coord = (pawn_row, pawn_col)
            self.set_piece(pawn_row, pawn_col, None)

        # Перемещаем фигуру.
        self.set_piece(sr, sc, None)
        self.set_piece(er, ec, piece)

        # Устанавливаем новую возможность взятия на проходе
        # если пешка только что сделала двойной ход.
        if isinstance(piece, Pawn):
            if abs(er - sr) == 2:
                middle_row = (er + sr) // 2
                self.en_passant_target = (middle_row, ec)

        # Обработка превращения пешки.
        promotion = False
        original_pawn = None
        if isinstance(piece, Pawn):
            last_rank = 0 if piece.color == "white" else 7
            if er == last_rank:
                promotion = True
                original_pawn = piece
                # Создаём новую фигуру согласно выбору пользователя.
                new_piece = self.create_promotion_piece(piece.color, promotion_choice)
                self.set_piece(er, ec, new_piece)
                piece = new_piece

        # Сохраняем ход в историю.
        move = Move(
            start=start,
            end=end,
            piece=piece,
            captured=captured,
            was_en_passant=was_en_passant,
            captured_coord=captured_coord,
            en_passant_before=en_passant_before,
            promotion=promotion,
            original_pawn=original_pawn,
        )
        self.history.append(move)

        # Меняем очередь хода.
        self.current_color = "black" if self.current_color == "white" else "white"

        # Сообщаем, если после хода получился шах противнику.
        if self.is_in_check(self.current_color):
            print("Шах!")

        return True

    def undo_last_move(self) -> None:
        """Откатывает последний ход, если он есть."""
        if not self.history:
            print("Нет ходов для отката.")
            return

        move = self.history.pop()      # Забираем последний ход из истории.
        sr, sc = move.start
        er, ec = move.end
        piece = move.piece

        # Восстанавливаем en_passant_target.
        self.en_passant_target = move.en_passant_before

        # Обрабатываем превращение пешки: возвращаем исходную пешку.
        if move.promotion and move.original_pawn is not None:
            self.set_piece(er, ec, move.original_pawn)
            piece = move.original_pawn

        # Ставим фигуру обратно на стартовую клетку.
        self.set_piece(sr, sc, piece)

        # Восстанавливаем съеденную фигуру, если была.
        if move.was_en_passant and move.captured is not None and move.captured_coord is not None:
            # Для взятия на проходе фигура возвращается на отдельную клетку.
            cr, cc = move.captured_coord
            self.set_piece(cr, cc, move.captured)
            self.set_piece(er, ec, None)
        else:
            # Обычное взятие: возвращаем фигуру на конечную клетку.
            self.set_piece(er, ec, move.captured)

        # Меняем очередь хода обратно.
        self.current_color = "black" if self.current_color == "white" else "white"

    # --- Вспомогательные методы ---

    def create_promotion_piece(
            self, color: str, choice: Optional[str]
            ) -> Piece:
        """
        Создаёт фигуру для превращения пешки.
        choice может быть 'Q', 'R', 'B', 'N', 'C', 'A', 'Z'.
        По умолчанию — ферзь.
        """
        if not choice:
            choice = "Q"
        ch = choice.upper()

        if ch == "Q":
            return Queen(color)
        if ch == "R":
            return Rook(color)
        if ch == "B":
            return Bishop(color)
        if ch == "N":
            return Knight(color)
        if ch == "C":
            return Chancellor(color)
        if ch == "A":
            return Archbishop(color)
        if ch == "Z":
            return Amazon(color)

        # Если пользователь ввёл что-то непонятное — всё равно даём ферзя.
        return Queen(color)

    def threatened_pieces(self, color: str) -> List[Coord]:
        """
        Возвращает список координат фигур указанного цвета,
        которые находятся под боем фигур противника.
        """
        threatened: List[Coord] = []
        enemy = "black" if color == "white" else "white"
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                piece = self.get_piece(row, col)
                if piece is None or piece.color != color:
                    continue
                if self.is_square_attacked(row, col, enemy):
                    threatened.append((row, col))
        return threatened


def print_help() -> None:
    """Печатает подсказку по командам интерфейса."""
    print("Команды:")
    print("  move e2 e4    - сделать ход с e2 на e4")
    print("  e2e4          - короткая форма хода")
    print("  moves e2      - показать все допустимые ходы фигуры с клетки e2")
    print("  threats       - показать свои фигуры под боем и отметить шах")
    print("  undo          - откатить последний ход")
    print("  help          - напечатать эту справку")
    print("  exit          - выйти из программы")


def main() -> None:
    """Точка входа в программу."""
    board = Board()              # Создаём и инициализируем доску.
    print("Шахматный симулятор (ООП-версия).")
    print("Белые ходят первыми.")
    print_help()                    # Печатаем доступные команды.

    # Главный цикл игры.
    while True:
        print()
        board.print_board()         # Показываем текущую доску
        print(f"Ходят {board.current_color}.")  # чей ход

        command = input("Введите команду: ").strip()  # ввод пользова
        if not command:             # Пустую строку просто игнорируем
            continue

        lower = command.lower()  # Для анализа команд исп ниж регистр

        if lower in ("exit", "quit", "q"):
            print("Выход из программы.")
            break

        if lower in ("help", "h", "?"):
            print_help()
            continue

        if lower == "undo":
            board.undo_last_move()
            continue

        if lower == "threats":
            # Выводим все фигуры текущего игрока, которые находятся под боем.
            threatened = board.threatened_pieces(board.current_color)
            if not threatened:
                print("Угрожаемых фигур нет.")
            else:
                algebraic_list = [coord_to_algebraic(c) for c in threatened]
                print("Угрожаемые фигуры на клетках:", ", ".join(algebraic_list))
            if board.is_in_check(board.current_color):
                print("Ваш король под шахом!")
            continue

        # Команда вида "moves e2".
        if lower.startswith("moves"):
            parts = lower.split()
            if len(parts) != 2:
                print("Формат: moves e2")
                continue
            coord = algebraic_to_coord(parts[1])
            if coord is None:
                print("Неверная координата.")
                continue
            row, col = coord
            moves = board.generate_legal_moves_from(row, col)
            if not moves:
                print("Допустимых ходов нет.")
            else:
                algebraic_moves = [coord_to_algebraic(m) for m in moves]
                print("Допустимые ходы:", ", ".join(algebraic_moves))
            continue

        # Попробуем распознать обычный ход.
        parts = lower.split()
        start_coord: Optional[Coord] = None
        end_coord: Optional[Coord] = None

        # Вариант "e2e4".
        if len(parts) == 1 and len(parts[0]) == 4:
            start_coord = algebraic_to_coord(parts[0][:2])
            end_coord = algebraic_to_coord(parts[0][2:])
        # Вариант "move e2 e4".
        elif len(parts) == 3 and parts[0] == "move":
            start_coord = algebraic_to_coord(parts[1])
            end_coord = algebraic_to_coord(parts[2])

        if start_coord is None or end_coord is None:
            print("Не удалось разобрать команду. Введите 'help' для справки.")
            continue

        # Для превращения пешки попросим выбор фигуры, если нужно.
        promotion_choice: Optional[str] = None
        sr, sc = start_coord
        er, ec = end_coord
        piece = board.get_piece(sr, sc)
        if isinstance(piece, Pawn):
            last_rank = 0 if piece.color == "white" else 7
            if er == last_rank:
                print("Превращение пешки! Выберите фигуру:")
                print("Q - ферзь, R - ладья, B - слон, N - конь,")
                print("C - Chancellor, A - Archbishop, Z - Amazon.")
                promotion_choice = input("Фигура (по умолчанию Q): ").strip()

        # Пытаемся сделать ход.
        board.make_move(start_coord, end_coord, promotion_choice=promotion_choice)


if __name__ == "__main__":
    main()
