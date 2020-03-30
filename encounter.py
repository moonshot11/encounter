"""
encounter.py

For solo D&D encounters!
"""

import argparse
import csv
import os
import random
import re
import statistics
import sys

from types import SimpleNamespace

MENU_USAGE = """
Useful commands:

    atk <enemy id> <attack total> - Attack the enemy specified by the ID. Roll
                                    your die, add all modifiers, and provide
                                    the total here.
                                    Ex: "atk 2 17"
                                    Attack enemy #2 for a total of 17

    hp <enemy id> <value>         - Set enemy's HP to <value>.

    dmg <enemy id> <damage total> - Damage the enemy by the amount provided.
                                    YOU ARE RESPONSIBLE FOR ALL MODIFIERS AND
                                    RESISTANCE. This program does not account
                                    for enemy resistances.
                                    Ex: "dmg 3 12"
                                    Damage enemy #3 for 12 HP.

    <enemy id> sav <dc> <mods> - Have an enemy perform a saving throw. The
                                 syntax of a saving throw is as follows:

                                 [+/-]<abilities>

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

                                1 sav 12 str+1/dex+0 - Perform a saving throw
                                                       on STR or DEX, whichever
                                                       has the higher ability
                                                       score.

    how - Toggle whether descriptive statuses are printed.
          On by default.

    speed/spd - Toggle whether each monster's speed is printed.
                Off by default.

    load <filename> - Load a saved game. Current game is saved in _load.sav

    save <filename> - Save the current game to the filename provided.

    newgame - Restart the application to generate a new encounter.
              Autosaves current game to _auto.sav

    restart - Set all enemy HP to full. Autosaves current game to _auto.sav

    last - Re-run the previous command

    quit - Save the current game to _quit.sav, and exit.

    help - You're reading it, silly!


Less useful commands:

    debug - Toggle debug output, including exact enemy HP.
            Off by default.

    dead - Toggle whether to list enemies once they have 0 HP.
           Off by default.

    bail - Exit the program without saving.
"""

VALID_ABILITIES = ["str", "dex", "con", "int", "wis", "cha"]
DIFFICULTIES = ["easy", "med", "hard", "deadly", "hell"]

levels = list()
templates = None
DEBUG = False
SHOW_HOW = True
SHOW_SPEED = False
SHOW_DEAD = False

settings = SimpleNamespace(**{
    "MULT_MIN_FACTOR" : None,
    "INIT_FILTER_FLOOR" : None,
    "NEXT_FILTER_FLOOR" : None
})

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

STATUSES = list()
SAVE_PATH = "saves"

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
    def __init__(self, template, nickname, hp=None, status=None, sex=None):
        self.template = template
        self.nickname = nickname
        self.hp = int(hp or template.hp)
        self.sex = sex or random.choice(('m', 'f'))
        if status:
            self.status = status
        else:
            self.refresh_status()

    @property
    def hpinfo(self):
        return "{}/{} HP".format(self.hp, self.template.hp)

    def refresh_status(self):
        """Refresh this creature's status text"""
        GENDER = [
            ("_hishers", "his", "hers"),
            ("_hisher", "his", "her"),
            ("_heshe", "he", "she"),
            ("_himher", "him", "her")
        ]
        frac = self.hp / self.template.hp
        for thresh, msgs in STATUSES:
            if frac > thresh:
                self.status = random.choice(msgs)
                idx = int(self.sex == "f") + 1
                for group in GENDER:
                    self.status = self.status.replace(group[0], group[idx])
                break

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
    avg_lvl = statistics.mean(levels)
    for mon, amt in monster_table.items():
        for i in range(0, amt):
            monsters.append(mon)
    if not monsters:
        return 0

    xp = sum([m.xp for m in monsters])
    amt = len([m for m in monsters
               if m.rating > avg_lvl * settings.MULT_MIN_FACTOR])

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
    with open("thresholds.csv", "r") as fin:
        lines = [line.strip() for line in fin.readlines()
                 if line.strip() and re.match(r"[0-9,]+$", line.strip())]

    targets = {}
    for line in lines:
        line = line.split(",")
        targets[int(line[0])] = line[1:]

    total = 0
    for lvl in levels:
        total += int(targets[lvl][DIFFICULTIES.index(difficulty)])

    return total

def ability_to_mod(value):
    """Convert ability score to modifier"""
    return (value - 10) // 2

def find_monster(monsters, name, error=False):
    """Return first Monster item with name"""
    for mon in monsters:
        if mon.name == name:
            return mon
    if error:
        print("ERROR: Could not find", name)
        sys.exit(1)
    return None

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

def manual_monsters():
    """Manually create a monster list"""
    global levels
    # Item: (monster, count)
    monster_count = dict()

    amt_players = 0
    while amt_players < 1:
        amt_players = input_int("How many players are there? ")
    levels = [None] * amt_players

    while True:
        print()
        mons_by_name = sorted(monster_count.keys(), key=lambda k: k.name)
        for i, mon in enumerate(mons_by_name):
            amt = monster_count[mon]
            print("{}) {} x{}".format(i+1, mon.name, amt))
        print()

        print("Commands:")
        print("  set   (set the amount of a monster; add to list if necessary)")
        print("  del   (delete this entry from list)")
        print("  clear (clears all monsters from list, be careful!)")
        print("  done")
        print()

        cmd = input("What would you like to do? ").strip()
        print()

        if cmd == "set":
            choice = input("Which monster? ").strip()
            mon = find_monster(templates, choice)
            if not mon:
                print("I couldn't find that monster")
                continue
            choice = input_int("How many? ")
            monster_count[mon] = choice
        elif cmd == "del":
            if not monster_count:
                print("No monsters to delete!")
                continue
            choice = input_int("Which monster to delete (use number)? ")
            if choice < 1 or choice > len(monster_count):
                print("That number is out of bounds!")
                continue
            del monster_count[mons_by_name[choice-1]]
        elif cmd == "clear":
            monster_count.clear()
        elif cmd == "done":
            if not monster_count:
                print("No monsters added! Add a monster first.")
                continue
            break

    return monster_count

def random_monsters(args):
    """Generate a monster list"""
    next_floor = settings.INIT_FILTER_FLOOR
    difficulty = setup_players()
    avg_player_lvl = statistics.mean(levels)

    monster_templates = templates.copy()
    orc = find_monster(monster_templates, "Orc", error=True)
    target_xp_flr = calc_target_xp(difficulty)
    target_xp_ceil = target_xp_flr * 1.1

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
                # XP delta with this mon added
                mon_xp = multiply(result, mon) - multiply(result)
                # Minimum XP for this mon to be considered
                # (Remaining XP) * next_floor
                min_mon_xp = (target_xp_ceil - multiply(result)) * next_floor

                # If mon XP is small enough to fit in remaining XP,
                # and large enough to meet minimum requirement,
                # and CR is less than avg player's level,
                # and check if rating == 0
                if multiply(result, mon) <= target_xp_ceil and \
                   mon_xp >= min_mon_xp and \
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

        next_floor = settings.NEXT_FILTER_FLOOR
 
    print()
    total = 0
    count = 0
    for monster, amt in result.items():
        print("{} x{}".format(monster.name, amt))
        total += monster.xp * amt
        count += amt
    print()

    print(multiply(result), "XP")
    if DEBUG:
        print(target_xp_flr, "XP <-- target")
        print(target_xp_ceil, "XP <-- target")

    return result

def load_game(filename):
    """Load game from a save file"""
    filename = save_path(filename)
    result = []
    template = None
    nickname = None
    hp = None
    sex = None

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
        elif line.startswith("Sex: "):
            sex = line[5:]
        elif line.startswith("HP: "):
            hp = line[4:]
        elif line.startswith("Status: "):
            status = line[8:]
            enemy = Enemy(template, nickname, hp=hp, status=status, sex=sex)
            result.append(enemy)

    return result

def save_game(filename, enemies, silent=False):
    """Save game to file"""
    filename = save_path(filename)
    if not silent:
        print("Saving to {}...".format(filename))
    lines = []
    for enemy in enemies:
        if isinstance(enemy, Enemy):
            lines.append("Template: {}\n".format(enemy.template.name))
            lines.append("Nickname: {}\n".format(enemy.nickname))
            lines.append("Sex: {}\n".format(enemy.sex))
            lines.append("HP: {}\n".format(enemy.hp))
            lines.append("Status: {}\n".format(enemy.status))
            lines.append("\n")
        else:
            lines.append("#:{}\n\n".format(enemy))
    with open(filename, "w") as fout:
        fout.writelines(lines)

def save_path(filename):
    """Initialize and return save path"""
    if not os.path.isdir(SAVE_PATH):
        os.mkdir(SAVE_PATH)
    return os.path.join(SAVE_PATH, filename + ".sav")

def input_int(msg, sign=False):
    """Prompt for an int (no sign)"""
    choice = ""
    pattern = "^"
    if sign:
        pattern += r"[+-]?"
    pattern += r"\d+"
    pattern += r"$"
    while not re.search(pattern, choice):
        choice = input(msg)
    return int(choice)

def init_enemies(monsters_count):
    """Create list of enemies"""
    enemies = list()
    inits = list()
    print("\n\nRoll for initiative!")
    for i in range(len(levels)):
        roll = input_int("What is Player {}'s initiative? ".format(i+1),
                         sign=True)
        inits.append( ("Player {}".format(i+1), roll) )
    for mon in monsters_count:
        inits.append( (mon, random.randint(1, 20) + ability_to_mod(mon.dex)) )
    inits.sort(key=lambda x: x[1], reverse=True)
    colors = ["red", "blue", "green", "orange", "purple", "pink", "yellow"]
    for mon, init in inits:
        if mon in monsters_count:
            count = 0
            amt = monsters_count[mon]
            for i in range(amt):
                nickname = mon.name
                if amt > 1 and count < len(colors):
                    nickname += " [{}]".format(colors[count])
                enemies.append(Enemy(mon, nickname))
                count += 1
        else:
            enemies.append(mon)

    return enemies

def loop_game():
    """Play the game!"""
    def autosave(enemies):
        save_game("_auto", enemies, silent=True)
    global DEBUG
    global SHOW_HOW
    global SHOW_SPEED
    global SHOW_DEAD

    enemies = dict()
    select = dict()
    prev_cmd = None

    while True:
        # -- Game startup --
        if not enemies:
            enemies = startup_prompt()
            select.clear()
            idx = 1

        if not select:
            for mon in enemies:
                if not isinstance(mon, Enemy):
                    continue
                select[idx] = mon
                idx += 1

        # -- Main loop --
        print("\n")
        choice = ""
        for mon in enemies:
            if isinstance(mon, Enemy) and (mon.hp > 0 or SHOW_DEAD):
                how = " ... {}".format(mon.status) if SHOW_HOW else ""
                speed = " ({})".format(mon.template.speed) if SHOW_SPEED else ""
                idx = next(k for k,v in select.items() if v == mon)
                print("{}) {}{}{}".format(
                    str(idx).rjust(2), mon.nickname, speed, how))
                if DEBUG:
                    print("    " + mon.hpinfo)
            elif not isinstance(mon, Enemy):
                print(" -) " + mon)
        choice = input("> ").strip().lower()
        if not choice:
            continue

        if choice == "last" or choice == ".":
            choice = prev_cmd
            print("Re-running:", choice)
        prev_cmd = choice

        print("\n")

        basic_pattern = r"^{}\s+(\d+)\s+(-?\d+)"
        match = re.search(basic_pattern.format("atk") + "$", choice)
        if match:
            uid = int(match.group(1))
            if uid not in select:
                print("Enemy #{} does not exist!".format(uid))
                continue
            enemy = select[uid]
            atk = int(match.group(2))
            if atk >= enemy.template.ac:
                print("=== Hit! ===")
            else:
                print("=== Miss! ===")
            continue

        match = re.search(basic_pattern.format("dmg") + "$", choice)

        if match:
            uid = int(match.group(1))
            if uid not in select:
                print("Enemy #{} does not exist!".format(uid))
                continue
            enemy = select[uid]
            delta = int(match.group(2))
            enemy.hp -= delta
            enemy.hp = min(enemy.hp, enemy.template.hp)
            enemy.refresh_status()
            if enemy.hp <= 0:
                print("  {} is dead!".format(enemy.nickname))
                enemy.status = "is dead!"
            elif delta > 0:
                print("  {} took {} damage!".format(enemy.nickname, delta))
            elif delta < 0:
                print("  {} recovered {} HP!".format(enemy.nickname, -delta))
            else:
                print("  {} took...no damage?".format(enemy.nickname))
            autosave(enemies)
            continue

        match = re.search(basic_pattern.format("hp") + "$", choice)
        if match:
            uid = int(match.group(1))
            if uid not in select:
                print("Enemy #{} does not exist!".format(uid))
                continue
            enemy = select[uid]
            hp = int(match.group(2))
            enemy.hp = hp
            enemy.refresh_status()
            print("  {} HP set!".format(hp))
            autosave(enemies)
            continue

        match = re.search(r"(\d+)\s+sav\s+(-?\d+)\s+([\w+-/]+)$", choice)
        if match:
            uid = int(match.group(1))
            if uid not in select:
                print("Enemy #{} does not exist!".format(uid))
                continue
            enemy = select[uid]
            dc = int(match.group(2))
            check_str = match.group(3)

            # Pull out details of saving throw
            match = re.match(r"([-+])?([-+a-zA-Z/\d]+)?", check_str)
            if not match:
                continue
            adv = match.group(1)
            attr = match.group(2)

            abilities = attr.split("/")
            scores = list()
            reloop = True
            # Check if any abilities aren't valid
            for ability in abilities:
                match = re.search("^(\w+)([+-]\d+)?", ability)
                if not match:
                    print("Ability {} not formatted correctly!".format(ability))
                    continue
                trait = match.group(1)
                override = match.group(2)
                if trait not in VALID_ABILITIES:
                    print("Ability {} not recognizd!".format(trait))
                    break
                if override:
                    scores.append(int(override))
                else:
                    score = int(getattr(enemy.template, trait))
                    score = ability_to_mod(score)
                    scores.append(score)
            else:
                reloop = False
            if reloop:
                continue

            # Process saving throw
            bonus = max(scores)
            roll = random.randint(1, 20)
            reroll = random.randint(1, 20)
            if DEBUG: print("Rolls: {}, {}".format(roll, reroll))

            if adv == "+":
                roll = max(roll, reroll)
            elif adv == "-":
                roll = min(roll, reroll)

            total = roll + bonus
            if DEBUG:
                print("{} = {} + {}".format(total, roll, bonus))

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
                filename = "_save"
            save_game(filename, enemies)
        elif choice == "quit":
            save_game("_quit", enemies)
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
            save_game("_load", enemies)
            enemies = temp_enemies
            select.clear()
        elif choice == "debug":
            DEBUG = not DEBUG
        elif choice == "how":
            SHOW_HOW = not SHOW_HOW
        elif choice in ("speed", "spd"):
            SHOW_SPEED = not SHOW_SPEED
        elif choice == "dead":
            SHOW_DEAD = not SHOW_DEAD
        elif choice == "newgame":
            autosave(enemies)
            enemies.clear()
            select.clear()
        elif choice == "restart":
            autosave(enemies)
            for enemy in select.values():
                enemy.hp = enemy.template.hp
                enemy.refresh_status()
        elif choice == "help":
            print(MENU_USAGE)
        else:
            print("Command not recognized. Type 'help' for info.")


def init_status(filename):
    """Initialize statuses"""
    global STATUSES
    STATUSES.clear()
    curr = list()

    with open(filename, "r") as fin:
        lines = [ln.strip() for ln in fin.readlines()]

    for line in lines:
        if not line:
            continue
        if re.search(r"^[0-9.]+$", line):
            STATUSES.append( (float(line), curr) )
            curr = list()
        else:
            curr.append(line)
    # The file set is for > 0 HP
    if curr:
        STATUSES.append( (0, curr) )


def startup_prompt():
    """Prompt user for initial info"""
    print()
    print("~~~ Welcome to Encounter! ~~~")
    print()
    choice = None
    while not choice:
        choice = input("(R)andomize monsters, (C)hoose your own, or (L)oad a save file? ")
        choice = choice.strip().lower()
        if not choice:
            continue
        if choice in ("l", "load"):
            choice = "l"
        elif choice in ("c", "choose"):
            choice = "c"
        elif choice in ("r", "random", "randomize"):
            choice = "r"
        elif choice in ("q", "quit", "exit"):
            sys.exit(0)
        else:
            print("I did not recognize that.")
            choice = None

    if choice == "c":
        monster_count = manual_monsters()
        enemies = init_enemies(monster_count)
    elif choice == "r":
        monster_count = random_monsters(args)
        enemies = init_enemies(monster_count)
    elif choice == "l":
        while True:
            loadfile = input("Enter file to load: ").strip()
            if not os.path.isfile(save_path(loadfile)):
                print("Cannot open file")
                continue
            enemies = load_game(loadfile)
            break

    return enemies

def setup_players():
    """Setup players and return difficulty"""
    global levels
    levels.clear()
    choice = ""

    amt = 0
    while amt < 1:
        amt = input_int("How many players are there? ")
    for i in range(amt):
        choice = ""
        while True:
            lvl = 0
            while lvl < 1 or lvl > 20:
                lvl = input_int("What is Player {}'s level (1-20)? ".format(i+1))
            levels.append(lvl)
            break

    while choice not in DIFFICULTIES:
        diff_str = ", ".join(DIFFICULTIES)
        choice = input("Choose a difficulty ({}): ".format(diff_str))
        choice = choice.lower()

    return choice

def init_config(filename):
    """Initialize settings"""
    # Read file
    with open(filename, "r") as fin:
        lines = [ln.strip() for ln in fin.readlines()]

    # Scan lines
    for line in lines:
        match = re.search(r"^\s*(\w+)\s+([\d.]+)\s*$", line)
        if not match or not hasattr(settings, match.group(1)):
            continue
        setattr(settings, match.group(1), float(match.group(2)))

    # Verify that everything was initialized
    for k, v in vars(settings).items():
        if v is None:
            print("ERROR: setting {} not initialized!".format(k))
            sys.exit(1)

if __name__ == "__main__":
    args = setup_args()
    init_config("settings.txt")
    templates = init_data(args.monster_data)
    init_status("status.txt")
    loop_game()
