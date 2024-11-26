# https://www.kaggle.com/code/callummaystone/silly-goose-chess-bot-agn-cube4d-dre
from Chessnut import Game
import random
import logging

# Configure Debugging and Logging
DEBUG = True
logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def debug(message):
    """Utility function for debugging."""
    if DEBUG:
        logging.debug(message)

# Constants
PIECE_VALUES = {
    "p": 1, "n": 3, "b": 3, "r": 5, "q": 9, "k": 0,
    "P": -1, "N": -3, "B": -3, "R": -5, "Q": -9, "K": 0
}
CENTER_SQUARES = {"d4", "d5", "e4", "e5"}
CORNER_SQUARES = {"a1", "h1", "a8", "h8"}
KING_ACTIVITY_SQUARES = {"c4", "c5", "d3", "d6", "e3", "e6", "f4", "f5"}

# Global decay tracking
MOVE_HISTORY = {}

# Define weights for move prioritization
WEIGHTS = {
    "central_control": 3,
    "captures": 5,
    "check": 10,
    "promotion": 15,
    "cornering": 10
}

def apply_decay(move):
    """Apply a decay factor to repetitive moves."""
    if move in MOVE_HISTORY:
        MOVE_HISTORY[move] += 1
    else:
        MOVE_HISTORY[move] = 1
    return max(0, 10 - MOVE_HISTORY[move])  # Reduce score for repetitive moves

def fen_to_board(fen):
    """Convert FEN string to a board representation."""
    rows = fen.split()[0].split("/")
    board = {}
    for rank_idx, row in enumerate(rows):
        file_idx = 0
        for char in row:
            if char.isdigit():
                file_idx += int(char)  # Empty squares
            else:
                square = f"{chr(file_idx + ord('a'))}{8 - rank_idx}"
                board[square] = char
                file_idx += 1
    return board

def get_opponent_king_position(board, player):
    """Find the opponent king's position."""
    king = "k" if player == "w" else "K"
    for square, piece in board.items():
        if piece == king:
            return square
    return None

def is_adjacent(square1, square2):
    """Check if two squares are adjacent."""
    file_diff = abs(ord(square1[0]) - ord(square2[0]))
    rank_diff = abs(int(square1[1]) - int(square2[1]))
    return max(file_diff, rank_diff) == 1

def king_seeks_cover(board, king_square, enemy_attacks, friendly_pieces):
    """Direct the king to safer squares."""
    possible_moves = []
    file, rank = king_square[0], int(king_square[1])
    for file_offset in [-1, 0, 1]:
        for rank_offset in [-1, 0, 1]:
            if file_offset == 0 and rank_offset == 0:
                continue
            target_file = chr(ord(file) + file_offset)
            target_rank = str(rank + rank_offset)
            target_square = f"{target_file}{target_rank}"
            if target_square in board:
                possible_moves.append(target_square)
    safe_moves = [
        move for move in possible_moves
        if move not in enemy_attacks and move not in friendly_pieces
    ]
    prioritized_moves = sorted(
        safe_moves,
        key=lambda sq: (
            sq in CORNER_SQUARES,
            sq[0] in "ah" or sq[1] in "18"
        ),
        reverse=True,
    )
    return prioritized_moves

def determine_game_phase(board):
    """Determine game phase based on material count."""
    material_count = sum(abs(PIECE_VALUES[piece.lower()]) for piece in board.values() if piece != " ")
    if material_count > 20:
        return "opening"
    elif 10 < material_count <= 20:
        return "midgame"
    else:
        return "endgame"

def prioritize_moves(game, moves, phase, board):
    """Prioritize moves dynamically based on game phase."""
    prioritized_moves = []
    player = "w" if game.get_fen().split()[1] == "w" else "b"
    opponent_king = get_opponent_king_position(board, player)
    
    for move in moves:
        start_square = move[:2]
        end_square = move[2:4]
        piece = board.get(start_square, " ")
        target_piece = board.get(end_square, " ")

        # Checkmate moves
        g = Game(game.get_fen())
        g.apply_move(move)
        if g.status == Game.CHECKMATE:
            debug(f"Checkmate move: {move}")
            return [move]

        # Endgame: Restrict opponent king or defend friendly king
        if phase == "endgame" and opponent_king:
            if is_adjacent(end_square, opponent_king):
                debug(f"Restricting opponent king: {move}")
                score = 5 + apply_decay(move)
                prioritized_moves.append((move, score))
            elif end_square in KING_ACTIVITY_SQUARES:
                debug(f"Targeting key square: {move}")
                score = 3 + apply_decay(move)
                prioritized_moves.append((move, score))
            continue

        # Captures
        if target_piece != " ":
            debug(f"Capture: {move}, capturing {target_piece}")
            score = WEIGHTS["captures"] + PIECE_VALUES.get(target_piece.lower(), 0)
            prioritized_moves.append((move, score))
            continue

        # Central control
        if end_square in CENTER_SQUARES:
            debug(f"Central control: {move}")
            score = WEIGHTS["central_control"]
            prioritized_moves.append((move, score))
            continue

        # Default moves
        score = apply_decay(move)
        prioritized_moves.append((move, score))

    prioritized_moves.sort(key=lambda x: x[1], reverse=True)
    return [move for move, _ in prioritized_moves]

def chess_bot(obs):
    """Dynamic chess bot with prioritization."""
    fen = obs['board']
    game = Game(fen)
    moves = list(game.get_moves())

    if not moves:
        return None

    board = fen_to_board(fen)
    phase = determine_game_phase(board)
    debug(f"Game phase: {phase}")

    prioritized_moves = prioritize_moves(game, moves, phase, board)
    best_move = prioritized_moves[0] if prioritized_moves else random.choice(moves)
    debug(f"Best move: {best_move}")
    return best_move