#!/d/Python37/python

import argparse
import re

def setup_args():
    """Setup arguments"""
    parser = argparse.ArgumentParser()

    parser.add_argument("difficulty", help="Sum of players' levels", type=int)
    parser.add_argument("-n", help="Number of classes", type=int, dest="amt")
    parser.add_argument("--use-zero", action="store_true")

    args = parser.parse_args()
    return args

def init_data():
    """Read data"""
    filename = "srd_monsters.txt"
    data = {}
    rating = None

    with open(filename, "r") as fin:
        lines = [ln.strip() for ln in fin.readlines()]

    for line in lines:
        if not line:
            continue
        if re.search(r"^\.?\d+$", line):
            rating = int(8 * float(line))
            data.setdefault(rating, list())
            continue
        if rating is None:
            continue
        data[rating].append(line)

    if not args.use_zero:
        del data[0]

    return data

if __name__ == "__main__":
    args = setup_args()
    monsters = init_data()
    # Multiple monster CR by 8 and player by 2
    difficulty = args.difficulty * 2

    result = []

    while difficulty < 0
        f
        for rating in set(monsters.keys()):
            if rating > difficulty:
                del monsters[rating]
        f
