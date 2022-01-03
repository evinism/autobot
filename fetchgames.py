from client import client
import pickle
import os

games_dir = "./data/games"

def fetch_all_games(player_name):
    print(f"Fetching all games for player {player_name}")
    games = client.games.export_by_player(player_name)

    if not os.path.exists(games_dir):
        os.makedirs(games_dir)
    
    games_list = []
    i = 0
    for game in games:
        id = game["id"]
        print(f"Fetched #{i} ({id}).")
        games_list.append(game)
        i += 1

    with open(f"{games_dir}/{player_name}.pickle", 'wb') as f:
        pickle.dump(games_list, f)

if __name__ == "__main__":
    player_name = input("Enter player name: ")
    fetch_all_games(player_name)