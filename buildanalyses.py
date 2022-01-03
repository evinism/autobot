import pickle
import os
from fetchgames import fetch_all_games
import subprocess
import chess
import time
import re


games_dir = "./data/games"


info_regex =  re.compile(r"^info depth ([0-9]+) seldepth [0-9]+ multipv [0-9]+ score (cp|mate) (-?[0-9]+) nodes [0-9]+ nps [0-9]+ tbhits [0-9]+ time [0-9]+ pv(( \w+)+)$")


def parse_and_coalesce_uci_output(uci_output, max_depth):
    potential_moves = {
    }
    for log_line in uci_output:
        match = info_regex.match(log_line.strip())
        if not match:
            continue
        depth = int(match.group(1))
        score_type = match.group(2)
        score = int(match.group(3))
        pv = match.group(4).strip().split(' ')
        move = pv[0]

        if move not in potential_moves:
            score_at_depth = [None] * (max_depth)
        else:
            score_at_depth = potential_moves[move]["score_at_depth"]
        score_at_depth[depth - 1] = (score_type, score)

        potential_moves[move] = {
            "depth": depth,
            "score_at_depth": score_at_depth,
            "pv": pv,
        }
    return potential_moves


def get_stockfish_analysis(game, depth=10):
    id = game['id']
    line = ""
    moves = game["moves"].split(' ')
    board = chess.Board()

    proc = subprocess.Popen(['stockfish'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    # Set up the game!!
    proc.stdin.write('position startpos\n'.encode())
    proc.stdin.write("setoption name MultiPV value 100\n".encode())
    proc.stdin.write("setoption name UCI_AnalyseMode value true\n".encode())
    proc.stdin.flush()

    game_analysis = {
        "depth": depth,
        "move_analyses": []
    }

    for move in moves:
        move_analysis = {
            'move': move,
            'bestmove': None,
            'uci_output': [],
            'potential_moves': None
        }
        board.push_san(move)

        fen = board.fen()
        proc.stdin.write(f"position fen {fen}\n".encode())
        proc.stdin.write(f"go depth {depth}\n".encode())
        proc.stdin.flush()

        lines = []
        line = proc.stdout.readline().decode()
        lines.append(line)

        while not line.startswith("bestmove"):
            line = proc.stdout.readline().decode()
            lines.append(line)

        print(f"{move} ", end=" ", flush=True)
        #print(lines)
        move_analysis['bestmove'] = line
        move_analysis['potential_moves'] = parse_and_coalesce_uci_output(lines, depth)
        game_analysis['move_analyses'].append(move_analysis)

    return (game, game_analysis)

def build_analyses(player_name):
    if not os.path.exists(f"./data/games/{player_name}.pickle"):
        fetch_all_games(player_name)
    else:
        print("Already fetched all games for {}".format(player_name))
    games = pickle.load(open(f"./data/games/{player_name}.pickle", 'rb'))

    if not os.path.exists(f"./data/analyses/{player_name}"):
        os.makedirs(f"./data/analyses/{player_name}")

    i = 0
    for game in games:
        id = game["id"]
        if game['variant'] != "standard" or game['speed'] not in {'blitz', 'rapid'}:
            continue

        # Analysis
        print("=====")
        print(f"Analyzing game {id} ({i + 1} of {len(games)})\n")

        then = time.time()
        analysis = get_stockfish_analysis(game)
        now = time.time()
  
        print(f"\nAnalyzed game {id}. Took {now - then} seconds.")

        with open(f"./data/analyses/{player_name}/{id}.pickle", 'wb') as f:
            pickle.dump(analysis, f)
        i += 1

if __name__ == "__main__":
    player_name = input("Enter player name: ")
    build_analyses(player_name)