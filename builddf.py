import pandas as pd
import numpy as np
import os
import pickle
import chess

# If you have a mate in 10, how many points is that in comparison?
MATE_OFFSET = 2000 # centipawns
MATE_RATIO = 1000 # centipawns

def collapse_score(type, score):
    if type == "cp":
        return score
    elif type == "mate":
        return (MATE_RATIO / score) + MATE_OFFSET

NEAR_FUTURE = 4 # how many moves in the future to generate columns for

def project_move_to_row(position, move, next_board_fen):
    move_analysis = position["potential_moves"][move]

    data = {}

    board = chess.Board(position["fen"])
    allied_color = board.turn

    if allied_color == chess.WHITE:
        enemy_color = chess.BLACK
    else:
        enemy_color = chess.WHITE
    
    cp_multiplier = 1 if allied_color == chess.WHITE else -1

    pieces = {
        chess.PAWN,
        chess.KNIGHT,
        chess.BISHOP,
        chess.ROOK,
        chess.QUEEN,
    }

    depths = []
    for score_tup in move_analysis["score_at_depth"]:
        if score_tup is None:
            depths.append(None)
        else:
            score_type, score = score_tup
            depths.append(collapse_score(score_type, score) * cp_multiplier)

    for i, score in enumerate(depths):
        data[f"depth_{i}"] = score
    data["overall_score"] = list(filter(lambda x: x is not None, depths))[-1]
    data['san'] = board.san(board.parse_uci(move))

    for i, move in enumerate(move_analysis["pv"][0:NEAR_FUTURE]):
        if i == 0:
            data["label"] = int(board.fen() == next_board_fen)

        for piece in pieces:
            data[f"allied_pieces_{piece}_{i}"] = len(board.pieces(piece, allied_color))
        for piece in pieces:
            data[f"enemy_pieces_{piece}_{i}"] = len(board.pieces(piece, enemy_color))
        data[f"num_pseudo_legal_moves_{i}"] = len(list(board.pseudo_legal_moves))
        data[f"num_legal_moves_{i}"] = len(list(board.legal_moves))
        data[f"has_en_passant_{i}"] = int(board.has_legal_en_passant())
        data[f"num_of_checkers_{i}"] = len(list(board.checkers()))
        data[f"is_2f_repetition_{i}"] = int(board.is_repetition(count = 2))
    return data


def project_position_to_partial_df(position, next_board_fen):
    rows = []
    for move in position["potential_moves"]:
        row = project_move_to_row(position, move, next_board_fen)
        rows.append(row)
    df = pd.DataFrame(rows)
    return df


def project_analysis_to_partial_df(analysis, player_name):
    if analysis['game']['players']['white']['user']['name'] == player_name:
        target_player_color = chess.WHITE
    else:
        target_player_color = chess.BLACK
    df = None
    for i, position in enumerate(analysis["position_analyses"][:-1]):
        fen = position["fen"]
        board = chess.Board(fen)
        next_board_fen = analysis["position_analyses"][i+1]["fen"]
        if board.turn == target_player_color:
            partial = project_position_to_partial_df(position, next_board_fen)
            if df is None:
                df = partial
            else:
                df = df.append(partial)
    return df


def project_path_to_partial_df(path, player_name):
    print(f"Starting {path}")
    with open(path, 'rb') as f:
        game_analysis = pickle.load(f)
        return project_analysis_to_partial_df(game_analysis, player_name)

def load_analyses(player_name, depth):
    items = [f"./data/analyses/{player_name}/depth-{depth}/{path}" for path in os.listdir(f'./data/analyses/{player_name}/depth-{depth}')]
    print(f"Loading {len(items)} analyses...")
    print(f"Sample path: {items[0]}")
    df = None
    for path in items:
        partial_df = project_path_to_partial_df(path, player_name)
        if df is None:
            df = partial_df
        else:
            df = df.append(partial_df)
    return df

def build_df(player_name, depth):
    analyses = load_analyses(player_name, depth)
    if not os.path.exists(f"./data/dfs/{player_name}"):
        os.makedirs(f"./data/dfs/{player_name}")
    with open(f"./data/dfs/{player_name}/depth-{depth}.pickle", 'wb') as f:
        pickle.dump(analyses, f)
    print(f"Saved {len(analyses)} potential moves to {player_name}/depth-{depth}.pickle")


if __name__ == "__main__":
    player_name = input("Enter player name: ")
    depth = int(input("Enter depth: "))
    build_df(player_name, depth)