from functools import partial
from typing import List
from stockfish import Stockfish
import click
import chess.pgn
from chess import Move
from pathlib import Path
from pprint import pprint
from .q_test import dixon_test
from cachetools import LRUCache
from multiprocessing import Pool, Lock
from os import cpu_count
from uuid import uuid1
from itertools import chain, islice


STARTING_POSITION = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
POSITION_CACHE = LRUCache(maxsize=4096)
CACHE_LOCK = Lock()


def chunks(iterable, size=10):
    iterator = iter(iterable)
    for first in iterator:
        yield chain([first], islice(iterator, size - 1))


def iterate_pgns(pgn_fd) -> chess.pgn.Game:
    while game := chess.pgn.read_game(pgn_fd):
        yield game


def get_new_game(game: chess.pgn.Game) -> chess.pgn.Game:
    annotated_game = chess.pgn.Game()
    annotated_game.headers = game.headers
    return annotated_game


def walk(pgn_path, game: chess.pgn.Game):
    fish = get_fish("/usr/local/bin/stockfish")
    annotated_game = get_new_game(game)
    fish.set_fen_position(STARTING_POSITION)
    annotated_game = get_best_moves_for_game(fish, game, annotated_game)
    with Path(f"./annotated-pgns/{pgn_path.name}_{uuid1()}.pgn").open("a") as new_fd:
        print(annotated_game, file=new_fd, end="\n\n")


def multiproc_analyze(pgn: str):
    mp = Pool()
    chunksize = cpu_count()
    pgn_path = Path(pgn)
    with pgn_path.open("r") as fd:
        walk_with_path = partial(walk, pgn_path)
        list(mp.imap(walk_with_path, chunks(iterate_pgns(fd)), chunksize=chunksize))


def analyze(fish: Stockfish, pgn: str):
    pgn_path = Path(pgn)
    n = 1
    with pgn_path.open("r") as fd:
        while game := chess.pgn.read_game(fd):
            annotated_game = get_new_game(game)
            fish.set_fen_position(STARTING_POSITION)
            annotated_game = get_best_moves_for_game(fish, game, annotated_game)
            with Path(f"./annotated-pgns/{pgn_path.name}_{n}.pgn").open("a") as new_fd:
                print(annotated_game, file=new_fd, end="\n\n")
            n += 1


def evaluate_position(
    fish: Stockfish, node: chess.pgn.GameNode, moves: List[str]
) -> List[dict]:
    fen = node.board().fen()
    with CACHE_LOCK:
        cached = POSITION_CACHE.get(fen)
        if cached:
            return cached
        else:
            fish.set_position(moves)
            evaluation = fish.get_top_moves(5)
            POSITION_CACHE[fen] = evaluation
            return evaluation


def copy_move(
    node: chess.pgn.GameNode, annotated_node: chess.pgn.GameNode
) -> chess.pgn.GameNode:
    annotated_node = annotated_node.add_variation(Move.from_uci(str(node.move)))
    annotated_node.comment = node.comment
    return annotated_node


def get_best_moves_for_game(
    fish: Stockfish, game: chess.pgn.Game, annotated_game=chess.pgn.Game
):
    evaluations = {}
    moves = []
    is_white = True
    annotated_node = annotated_game
    for node in game.mainline():
        annotated_node = copy_move(node, annotated_node)
        moves.append(str(node.move))
        best_moves = evaluate_position(fish, node, moves)
        centipawns = [
            evals["Centipawn"] for evals in best_moves if evals["Centipawn"] is not None
        ]
        move_mapping = {
            evals["Centipawn"]: evals["Move"]
            for evals in best_moves
            if evals["Centipawn"] is not None
        }
        outlier_black, outlier_white = dixon_test(centipawns)
        if is_white and outlier_white:
            annotated_node.comment = f"ONLY MOVE: {outlier_white}cn {node.comment}"
        elif not is_white and outlier_black:
            annotated_node.comment = f"ONLY MOVE: {outlier_black}cn {node.comment}"
        is_white = not is_white
    return annotated_game


def get_fish(fish_path: str) -> Stockfish:
    parameters = {"Threads": 6, "Hash": 4096}
    fish = Stockfish(fish_path, parameters=parameters)
    fish.set_depth(20)
    fish.set_elo_rating(2400)
    return fish


@click.command()
@click.option("--pgn", "-p", "pgns", multiple=True)
@click.option("--stockfish", "-s", "fish_path", default="/usr/local/bin/stockfish")
def main(pgns: List[str], fish_path: str):
    # fish = get_fish(fish_path)
    # for pgn in pgns:
    #     analyze(fish, pgn)
    for pgn in pgns:
        multiproc_analyze(pgn)


main()
