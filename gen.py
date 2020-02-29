#!/d/Python37/python

import argparse
import csv
import os
import random
import re
import sys

MENU_USAGE = """
Useful commands:

    atk <enemy id> <attack total> - Attack the enemy specified by the ID. Roll
                                    your die, add all modifiers, and provide
                                    the total here.
                                    Ex: "atk 2 17"
                                    Attack enemy #2 for a total of 17

    dmg <enemy id> <damage total> - Damage the enemy by the amount provided.
                                    YOU ARE RESPONSIBLE FOR ALL MODIFIERS AND
                                    RESISTANCE. This program does not account
                                    for enemy resistances.
                                    Ex: "dmg 3 12"
                                    Damage enemy #3 for 12 HP.

    <enemy id> sav <dc> <mods> - Have an enemy perform a saving throw. The
                                 syntax of a saving throw is as follows:

                                 [+/-]<ability>[bonus]

                                 The simplest saving throw is just an ability,
                                 such as con or dex. Put a plus or minus before
                                 it to specify advantage or disadvantage.
                                 Certain monsters have special bonuses just for
                                 saving throws, which are added at the end.
                                 Negative bonuses are allowed.

                                 Examples:

                                 3 sav 12 con - Enemy #3 performs a Constitution
                                                saving throw of DC 12.

                                 5 sav 9 +dex - Enemy #5 performs a Dexterity
                                                saving throw of DC 9 with
                                                advantage.

                                 4 sav 15 str+4 - Enemy #4 performs a Strength
                                                  saving throw of DC 15, with
                                                  a +4 bonus to his roll.

                                 2 sav 8 -wis+1 - Enemy #2 performs a Wisdom
                                                  saving throw of DC 8, with
                                                  disadvantage on the roll and
                                                  a +1 bonus to the total.

    how - Toggle whether descriptive statuses are printed.

    load <filename> - Load a saved game. Current game will be saved in
                      _load.sav

    save <filename> - Save the current game to the filename provided.

    quit - Save the current game to _quit.sav, and exit.

    help - You're reading it, silly!


Less useful commands:

    debug - Toggle debug output, including exact enemy HP.

    bail - Exit the program without saving.
"""

# avg_player_lvl * MULT_MIN_FACTOR to count in encounter multiplier
MULT_MIN_FACTOR = 0.5
# min percentage for this monster's contribution to remaining XP
NEXT_FLOOR = 0.1

levels = list()
templates = None
DEBUG = False
PRINT_HOW = False

cr_to_xp = {
    0 : 10,
    0.125 : 25,
    0.25 : 50,
    0.5 : 100,
    1 : 200,
    2 : 450,
    3 : 700,
    4 : 1100,
    5 : 1800,
    6 : 2300,
    7 : 2900,
    8 : 3900,
    9 : 5000,
    10 : 5900,
    11 : 7200,
    12 : 8400,
    13 : 10000,
    14 : 11500,
    15 : 13300,
    16 : 15000,
    17 : 18000,
    19 : 22000,
    20 : 25000,
    21 : 33000,
    22 : 41000,
    23 : 50000,
    24 : 62000,
    30 : 155000
}

STATUS_HEALTHY = [
    "is having a wonderful day",
    "beams at the thought of destroying you",
    "is thinking about yesterday's wonderful date",
    "is radiating energy from all that morning's protein bars",
    "is filled with DETERMINATION",
    "looks eager to fight",
    "looks pretty healthy"
]

STATUS_OKAY = [
    "is a bit roughed up",
    "is trying to hide a few bruises",
    "has a few cuts and bruises",
    "is irritated and looking to get this overwith"
]

STATUS_BAD = [
    "is very bloodied",
    "looks very tired",
    "looks worn down",
    "isn't doing so good",
    "is enraged"
]

STATUS_AWFUL = [
    "'s limbs are barely attached",
    "is bleeding profusely",
    "is barely conscious",
    "is staggering around",
    "is near death"
]

class Monster:
    """A generic monster template with all static stat info"""
    def __init__(self, name, rating, ac, hp, speed, stats):
        self.name = name
        self.rating = float(rating)
        self.xp = cr_to_xp[self.rating]
        self.ac = int(ac)
        self.hp = int(hp)
        self.speed = speed

        (self.str, self.dex, self.con, self.int, self.wis, self.cha) = \
        tuple([int(s) for s in stats])

class Enemy:
    """A monster instance with dynamic HP and a nickname"""
    def __init__(self, template, nickname, hp=None):
        self.template = template
        self.nickname = nickname
        self.hp = int(hp or template.hp)
        self.status = random.choice(STATUS_HEALTHY)

    @property
    def hpinfo(self):
        return "{}/{} HP".format(self.hp, self.template.hp)

    def refresh_status(self):
        """Refresh this creature's status text"""
        frac = self.hp / self.template.hp
        if frac > 0.6:
            msgs = STATUS_HEALTHY
        elif frac > 0.2:
            msgs = STATUS_OKAY
        elif frac > 0.05:
            msgs = STATUS_BAD
        else:
            msgs = STATUS_AWFUL
        self.status = random.choice(msgs)

def setup_args():
    """Setup arguments"""
    parser = argparse.ArgumentParser()

    parser.add_argument("--max-per-group", "-m", default=4, type=int,
            help="Max amt per group")
    parser.add_argument("--orcs", help="Require orcs", action="store_true")
    parser.add_argument("--use-zero", action="store_true",
            help="Use 0 CR monsters")
    parser.add_argument("--monster-data", default="srd.csv",
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
    max_cr = max([m.rating for m in monsters])
    amt = len([m for m in monsters if m.rating > max_cr * MULT_MIN_FACTOR])

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

def ability_to_mod(value):
    """Convert ability score to modifier"""
    return (value - 10) // 2

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

    with open(filename, "r") as fin:
        reader = csv.DictReader(fin)
        for line in reader:
            monsters.append(Monster(
                 line['Name'], line['CR'],
                 line['AC'], line['HP'], line['Speeds'],
                [line['STR'], line['DEX'], line['CON'],
                 line['INT'], line['WIS'], line['CHA']]))

    return monsters

def generate_monsters(args):
    """Generate a monster list"""
    difficulty = setup_players()
    if difficulty not in ("easy", "med", "hard", "deadly"):
        print("Requires {easy, med, hard, deadly}")
        sys.exit(1)
    avg_player_lvl = sum([int(x) for x in levels]) / len(levels)

    monster_templates = templates.copy()
    orc = find_monster(monster_templates, "Orc")
    target_xp_ceil = calc_target_xp(difficulty)
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
            for mon in monster_templates:
                if multiply(result, mon) <= target_xp_ceil and \
                   multiply(result, mon) - multiply(result) >= (target_xp_ceil - multiply(result)) * NEXT_FLOOR and \
                   mon.rating <= avg_player_lvl and \
                  (mon.rating > 0 or args.use_zero):
                    candidates.append(mon)
            # If no available creatures, bail
            if not candidates:
                if args.use_zero:
                    print("No more candidates - exiting")
                    break
                else:
                    print("Adding 0 CR monsters to pool")
                    args.use_zero = True
                    continue
            winner = random.choice(candidates)
            amt = random.randint(1, args.max_per_group)

        # Remove chosen monster from further candidacy
        monster_templates.remove(winner)

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

    return result

def load_game(filename):
    """Load game from a save file"""
    result = []
    template = None
    nickname = None
    hp = None

    with open(filename, "r") as fin:
        lines = [ln.strip() for ln in fin.readlines() if ln.strip()]
    for line in lines:
        # Add "Player 1" to list
        if line.startswith("#:"):
            result.append(line[2:])
        # Add enemies
        elif line.startswith("Template: "):
            criteria = line[10:]
            template = [x for x in templates if x.name == criteria][0]
        elif line.startswith("Nickname: "):
            nickname = line[10:]
        elif line.startswith("HP: "):
            hp = line[4:]
        elif line.startswith("Status: "):
            status = line[8:]
            enemy = Enemy(template, nickname, hp=hp)
            enemy.status = status
            result.append(enemy)

    return result

def save_game(filename, enemies):
    """Save game to file"""
    print("Saving to {}...".format(filename))
    lines = []
    for enemy in enemies:
        if isinstance(enemy, Enemy):
            lines.append("Template: {}\n".format(enemy.template.name))
            lines.append("Nickname: {}\n".format(enemy.nickname))
            lines.append("HP: {}\n".format(enemy.hp))
            lines.append("Status: {}\n".format(enemy.status))
            lines.append("\n")
        else:
            lines.append("#:{}\n\n".format(enemy))
    with open(filename, "w") as fout:
        fout.writelines(lines)

def init_enemies(monsters_count):
    """Create list of enemies"""
    enemies = list()
    inits = list()
    print("\n\nRoll for initiative!")
    for i in range(len(levels)):
        msg = "What is Player {}'s initiative? ".format(i+1)
        roll = int(input(msg))
        inits.append( ("Player {}".format(i+1), roll) )
    for mon in monsters_count:
        inits.append( (mon, random.randint(1, 20)) )
    inits.sort(key=lambda x: x[1], reverse=True)
    colors = ["red", "blue", "green", "orange", "purple", "pink", "yellow"]
    for mon, init in inits:
        if mon in monsters_count:
            count = 0
            amt = monsters_count[mon]
            for i in range(amt):
                enemies.append(
                    Enemy(mon, "{} [{}] ({})".format(
                        mon.name, colors[count], mon.speed)))
                count += 1
        else:
            enemies.append(mon)

    return enemies

def loop_game(enemies):
    """Play the game!"""
    global DEBUG
    global PRINT_HOW
    select = dict()
    while True:
        print("\n")
        choice = ""
        idx = 1
        for mon in enemies:
            if isinstance(mon, Enemy) and mon.hp > 0:
                how = " ... {}".format(mon.status) if PRINT_HOW else ""
                print("{}) {}{}".format(str(idx).rjust(2), mon.nickname, how))
                if DEBUG:
                    print("    " + mon.hpinfo)
                select[idx] = mon
            elif not isinstance(mon, Enemy):
                print("    " + mon)
            if isinstance(mon, Enemy):
                idx += 1
        choice = input("> ").strip()
        if not choice:
            continue
        print("\n")

        basic_pattern = r"^{}\s+(\d+)\s+(-?\d+)"
        match = re.search(basic_pattern.format("atk") + "$", choice)
        if match:
            enemy = select[int(match.group(1))]
            atk = int(match.group(2))
            if atk >= enemy.template.ac:
                print(" == Hit! ==")
            else:
                print(" == Miss! ==")
            continue

        match = re.search(basic_pattern.format("dmg") + "$", choice)

        if match:
            enemy = select[int(match.group(1))]
            delta = int(match.group(2))
            enemy.hp -= delta
            enemy.hp = max(0, min(enemy.hp, enemy.template.hp))
            enemy.refresh_status()
            if enemy.hp == 0:
                print(enemy.nickname, "is dead!")
            else:
                print("{} took {} damage!".format(enemy.nickname, delta))
            continue

        match = re.search(r"(\d+)\s+sav\s+(-?\d+)\s+([\w+-]+)$", choice)
        if match:
            enemy = select[int(match.group(1))]
            dc = int(match.group(2))
            check_str = match.group(3)

            # Pull out details of saving throw
            match = re.match(r"([-+])?(\w\w\w)([-+]\d+)?", check_str)
            if not match:
                continue
            adv = match.group(1)
            attr = match.group(2)
            bonus = match.group(3) or 0

            if hasattr(enemy.template, attr):
                ability = getattr(enemy.template, attr)
                mod = ability_to_mod(ability)
                if DEBUG:
                    print("{} {} -> {}".format(attr, ability, mod))
            else:
                print("Enemy doesn't have attr:", attr)
                continue

            # Process saving throw
            roll = random.randint(1, 20)
            reroll = random.randint(1, 20)
            if DEBUG: print("Rolls: {}, {}".format(roll, reroll))

            if adv == "+":
                roll = max(roll, reroll)
            elif adv == "-":
                roll = min(roll, reroll)

            total = roll + mod + int(bonus)
            if DEBUG:
                print("{} = {} + {} + {}".format(total, roll, mod, bonus))

            if total >= dc:
                print("=== Saved! ===")
            else:
                print("=== Failed! ===")
            continue

        # -- Misc commands --
        if choice.startswith("save"):
            if choice[4:].strip():
                filename = choice[4:].strip()
            else:
                filename = "_save.sav"
            save_game(filename, enemies)
        elif choice == "quit":
            save_game("_quit.sav", enemies)
            print("Quitting...")
            return
        elif choice == "bail":
            print("Quitting without saving...")
            return
        elif choice.startswith("load "):
            filename = choice[5:].strip()
            if not os.path.isfile(filename):
                print("Cannot load file:", filename)
                continue
            temp_enemies = load_game(filename)
            save_game("_load.sav", enemies)
            enemies = temp_enemies
        elif choice == "debug":
            DEBUG = not DEBUG
        elif choice == "how":
            PRINT_HOW = not PRINT_HOW
        elif choice == "help":
            print(MENU_USAGE)
        else:
            print("Command not recognized. Type 'help' for info.")


def run_game(args, loadfile=None, monsters_count=None):
    """Run a game as DM!"""
    enemies = list()

    if loadfile:
        enemies = load_game(loadfile)
    elif monsters:
        enemies = init_enemies(monsters_count)

    loop_game(enemies)

def startup_prompt():
    """Prompt user for initial info"""
    print()
    print("~~~ Welcome to Encounter! ~~~")
    print()
    choice = None
    while True:
        choice = input("(G)enerate new monsters, or (L)oad an existing game? ")
        choice = choice.strip().lower()
        if not choice:
            continue
        if choice in ("l", "load"):
            choice = "l"
        elif choice in ("g", "gen", "generate"):
            choice = "g"
        elif choice in ("q", "quit", "exit"):
            sys.exit(0)
        else:
            print("I did not recognize that.")
            continue
        return choice

def setup_players():
    """Setup players and return difficulty"""
    global levels
    choice = ""

    while not re.search(r"^\d+$", choice):
        choice = input("How many players are there? ")

    amt = int(choice)
    for i in range(amt):
        choice = ""
        while True:
            choice = input("What is Player {}'s level? ".format(i+1))
            if not re.search(r"^\d+$", choice):
                choice = ""
                continue
            if int(choice) < 1 or int(choice) > 20:
                print("Must be between 1 and 20")
                choice = ""
                continue
            levels.append(int(choice))
            break

    while choice not in ("easy", "med", "hard", "deadly"):
        choice = input("Choose a difficulty (easy, med, hard, deadly): ")
        choice = choice.lower()

    return choice

if __name__ == "__main__":
    args = setup_args()
    templates = init_data(args.monster_data)
    monsters = None
    choice = startup_prompt()
    if choice == "g":
        monsters = generate_monsters(args)
        run_game(args, monsters_count=monsters)
    else:
        while True:
            choice = input("Enter file to load: ").strip()
            if not os.path.isfile(choice):
                print("Cannot open file")
                continue
            break
        run_game(args, loadfile=choice)
