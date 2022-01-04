from dotenv import load_dotenv
load_dotenv()

import pickle
import os
from fetchgames import fetch_all_games
import subprocess
import chess
import time
import re
import random

from multiprocessing import Pool

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
            "score_at_depth": score_at_depth,
            "pv": pv,
            "depth": depth,
            "overall_score": score_at_depth[-1]
        }
    return potential_moves


def analyze_position(fen, proc, depth):
    position_analysis = {
        'fen': fen,
        'potential_moves': None
    }

    proc.stdin.write(f"position fen {fen}\n".encode())
    proc.stdin.write(f"go depth {depth}\n".encode())
    proc.stdin.flush()

    lines = []
    line = proc.stdout.readline().decode()
    lines.append(line)

    while not line.startswith("bestmove"):
        line = proc.stdout.readline().decode()
        lines.append(line)

    #print(f"{move} ", end=" ", flush=True)
    position_analysis['potential_moves'] = parse_and_coalesce_uci_output(lines, depth)
    return position_analysis

def get_stockfish_analysis(game, depth):
    moves = game["moves"].split(' ')
    board = chess.Board()

    proc = subprocess.Popen(['stockfish'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    proc.stdin.write('position startpos\n'.encode())
    proc.stdin.write("setoption name MultiPV value 100\n".encode())
    proc.stdin.write("setoption name UCI_AnalyseMode value true\n".encode())
    proc.stdin.flush()

    game_analysis = {
        "game": game,
        "depth": depth,
        "position_analyses": []
    }

    def analyze():
        game_analysis['position_analyses'].append(analyze_position(board.fen(), proc, depth))

    analyze()
    for move in moves:
        board.push_san(move)
        analyze()

    proc.terminate()
    return game_analysis


def analyze_game(game, depth, player_name, index: int, total: int):
    if game['variant'] != "standard" or game['speed'] not in {'blitz', 'rapid'}:
        return
    id = game['id']
    print(f"Analyzing game {id} ({index} of {total})\n")
    if os.path.exists(f"./data/analyses/{player_name}/depth-{depth}/{id}.pickle"):
        print(f"Already analyzed game {id}")
        return
    analysis = None
    try:
        then = time.time()
        analysis = get_stockfish_analysis(game, depth)
        now = time.time()

        print(f"\nAnalyzed game {id}. Took {now - then} seconds at depth {depth}.")
    except Exception as e:
        print(f"\nFailed to analyze game {id}.")
        print(e)
    if analysis:
        with open(f"./data/analyses/{player_name}/depth-{depth}/{id}.pickle", 'wb') as f:
            pickle.dump(analysis, f)


def build_analyses(player_name: str, depth: int = 12, num_games: int = None):
    if not os.path.exists(f"./data/games/{player_name}.pickle"):
        fetch_all_games(player_name)
    else:
        print("Already fetched all games for {}".format(player_name))

    with open(f"./data/games/{player_name}.pickle", 'rb') as games_file:
        games = pickle.load(games_file)

    if not os.path.exists(f"./data/analyses/{player_name}/depth-{depth}"):
        os.makedirs(f"./data/analyses/{player_name}/depth-{depth}")

    arglist = [(game, depth, player_name, i, len(games)) for i, game in enumerate(games)]
    if num_games is not None and num_games > 0:
        arglist = random.sample(arglist, num_games)

    with Pool(processes=int(os.environ.get('PARALLELIZATION', '12'))) as pool:
        pool.starmap(analyze_game, arglist)
    print("Done building analyses!")

if __name__ == "__main__":
    player_name = input("Enter player name: ")
    depth = int(input("Enter depth: "))
    number_of_games = int(input("Enter number of games to analyze, 0 for all: "))
    build_analyses(player_name, depth, number_of_games)