#!/d/Python37/python

import argparse
import random
import re
import sys

class Monster:
    def __init__(self, name, rating):
        self.name = name
        self.rating = rating

def setup_args():
    """Setup arguments"""
    parser = argparse.ArgumentParser()

    parser.add_argument("difficulty", help="Sum of players' levels", type=int)
    parser.add_argument("--max-per-group", "-m", help="Max amt per group",
        default=8, type=int)
    parser.add_argument("--orcs", help="Require orcs", action="store_true")
    parser.add_argument("--use-zero", action="store_true")
    parser.add_argument("--input-file", default="srd5e_monsters.txt")
    parser.add_argument("--min-factor", default=6, type=float)

    args = parser.parse_args()
    return args

def pick_random(monsters, floor, ceil):
    """Get candidates as tuples"""
    candidates = []
    for mon in monsters:
        if floor <= mon.rating <= ceil:
            candidates.append(mon)
    return random.choice(candidates)

def find_monster(monsters, name):
    """Return first Monster item with name"""
    for mon in monsters:
        if mon.name == name:
            return mon
    print("ERROR: Could not find", name)
    sys.exit(1)

def init_data(filename):
    """Read data"""
    monsters = []
    rating = None

    with open(filename, "r") as fin:
        lines = [ln.strip() for ln in fin.readlines()]

    for line in lines:
        if not line:
            continue
        if re.search(r"^\.?\d+$", line):
            rating = 4.0 * float(line)
            continue
        if rating is None:
            continue
        if rating == 0 and not args.use_zero:
            continue

        monsters.append(Monster(line, rating))

    return monsters

if __name__ == "__main__":
    args = setup_args()
    monsters = init_data(args.input_file)
    orc = find_monster(monsters, "Orc")
    difficulty = args.difficulty
    result = {}

    while difficulty > 0:
        # If (somehow) there are no candidates remaining, bail
        if not monsters:
            break

        # Add Orcs if specifically required
        if not result and args.orcs:
            winner = orc
            amt = random.randint(2, 8)
            if difficulty < winner.rating:
                print("WARNING: Orcs too difficult for this group")
        else:
            winner = pick_random(monsters, difficulty/args.min_factor, difficulty)
            amt = random.randint(1, args.max_per_group)

        # Remove chosen monster from further candidacy
        monsters.remove(winner)

        while amt > 0:
            difficulty -= winner.rating
            result[winner] = result.get(winner, 0) + 1
            amt -= 1
            if difficulty - winner.rating < 0:
                break
 
    print()
    total = 0
    for monster, amt in result.items():
        print("{} x{}".format(monster.name, amt))
        total += monster.rating * amt
