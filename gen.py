#!/d/Python37/python

import argparse
import random
import re
import sys

# avg_player_lvl * MULT_MIN_FACTOR to count in encounter multiplier
MULT_MIN_FACTOR = 0.5
# min percentage for this monster's contribution to remaining XP
NEXT_FLOOR = 0.1

levels = None
avg_player_lvl = None

class Monster:
    def __init__(self, name, rating, xp):
        self.name = name
        self.rating = rating
        self.xp = xp

def setup_args():
    """Setup arguments"""
    parser = argparse.ArgumentParser()

    parser.add_argument("difficulty", choices=["easy", "med", "hard", "deadly"],
            help="Difficulty")
    parser.add_argument("levels", nargs="*", type=int,
            help="Space-separated string of player levels")
    parser.add_argument("--max-per-group", "-m", default=4, type=int,
            help="Max amt per group")
    parser.add_argument("--orcs", help="Require orcs", action="store_true")
    parser.add_argument("--use-zero", action="store_true",
            help="Use 0 CR monsters")
    parser.add_argument("--input-file", default="srd.txt",
            help="The data file with monster information")

    args = parser.parse_args()
    return args

def multiply(monster_table, *args):
    """Apply multiplier to xp based on number of enemies"""
    monsters = list(args)
    for mon, amt in monster_table.items():
        for i in range(0, amt):
            monsters.append(mon)
    if not monsters:
        return 0

    xp = sum([m.xp for m in monsters])
    avg_cr = sum([m.rating for m in monsters]) / len(monsters)
    amt = len([m for m in monsters if m.rating > avg_player_lvl * MULT_MIN_FACTOR])

    if amt <= 1: index = 0
    elif amt == 2: index = 1
    elif amt in range(3, 7): index = 2
    elif amt in range(7, 11): index = 3
    elif amt in range(11, 15): index = 4
    else: index = 5
    
    if len(levels) <= 2:
        index = min(index + 1, 5)
    elif len(levels) >= 6:
        index = max(index - 1, 0)

    multipliers = [1, 1.5, 2, 2.5, 3, 4]
    return multipliers[index] * xp

def calc_target_xp(difficulty):
    """Get target XP from table"""
    diffs = ["easy", "med", "hard", "deadly"]

    with open("thresholds.csv", "r") as fin:
        lines = [line.strip() for line in fin.readlines()
                 if line.strip() and re.match(r"[0-9,]+$", line.strip())]

    targets = {}
    for line in lines:
        line = line.split(",")
        targets[int(line[0])] = line[1:]

    total = 0
    for lvl in levels:
        total += int(targets[lvl][diffs.index(difficulty)])

    return total

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
    xp = None

    with open(filename, "r") as fin:
        lines = [ln.strip() for ln in fin.readlines()]

    for line in lines:
        if not line:
            continue
        # Search for "CR (N XP)" lines
        match_obj = re.search(r"^((?:0\.)?\d+)\s+\((\d+)\s*XP\s*\)$",
                line.replace(",", ""))
        if match_obj:
            rating = float(match_obj.group(1))
            xp = int(match_obj.group(2))
            continue
        if rating is None or xp is None:
            continue

        monsters.append(Monster(line, rating, xp))

    return monsters

if __name__ == "__main__":
    args = setup_args()
    levels = args.levels
    avg_player_lvl = sum([int(x) for x in levels]) / len(levels)

    monsters = init_data(args.input_file)
    orc = find_monster(monsters, "Orc")
    target_xp_ceil = calc_target_xp(args.difficulty)
    target_xp_flr = target_xp_ceil * 0.9

    result = {}
    xp_total = 0
    monster_count = 0

    while not (target_xp_flr < multiply(result) and
               multiply(result) <= target_xp_ceil):
        # Add Orcs if specifically required
        if not result and args.orcs:
            winner = orc
            amt = random.randint(2, 8)
            if target_xp_ceil < winner.xp:
                print("WARNING: Orcs too difficult for this group")
        else:
            # Populate candidates and choose who's next
            candidates = []
            for mon in monsters:
                if multiply(result, mon) <= target_xp_ceil and \
                   multiply(result, mon) - multiply(result) >= (target_xp_ceil - multiply(result)) * NEXT_FLOOR and \
                   mon.rating <= avg_player_lvl:
                    candidates.append(mon)
            # If no available creatures, bail
            if not candidates:
                break
            winner = random.choice(candidates)
            amt = random.randint(1, args.max_per_group)

        # Remove chosen monster from further candidacy
        monsters.remove(winner)

        while amt > 0:
            xp_total += winner.xp
            result[winner] = result.get(winner, 0) + 1
            amt -= 1
            monster_count += 1
            if multiply(result, winner) > target_xp_ceil:
                break
 
    print()
    total = 0
    count = 0
    for monster, amt in result.items():
        print("{} x{}".format(monster.name, amt))
        total += monster.xp * amt
        count += amt
    print()

    print(multiply(result), "XP")
    print(target_xp_flr, "XP <-- target")
    print(target_xp_ceil, "XP <-- target")
