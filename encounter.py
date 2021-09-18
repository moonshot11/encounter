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

if hasattr(re, "acc"):
    raise Exception("re module already has matchobj attribute!")
re.matchobj = None

def re_search(*args, **kwargs):
    """Wrapper for re.search()"""
    re.matchobj = re.search(*args, **kwargs)
    return re.matchobj

MENU_USAGE = """
Useful commands:

    atk <enemy id> <attack total> - Attack the enemy specified by the ID. Roll
                                    your die, add all modifiers, and provide
                                    the total here.
                                    Ex: "atk 2 17"
                                    Attack enemy #2 for a total of 17

    hp <enemy id> <value>         - Set enemy's HP to <value>.

    dmg <enemy id> <damage total> - Damage the enemy by the amount provided.
        [[$@+-]<damage type>]       Optionally, provide the damage type. This
                                    might mean splitting a single attack into
                                    multiple "dmg" commands, to account for
                                    different damage types. Prepend the type with
                                    a "+" for magical attacks, "-" for nonmagical
                                    attacks, "$" for silvered attacks, and "@" for
                                    adamantine attacks.
                                    Ex: "dmg 3 12"
                                    Damage enemy #3 for 12 HP.
                                    Ex: "dmg 4 10 +fire"
                                    Damage enemy #4 with adjusted magical fire damage.

    check <enemy id> <dmg/cond>   - Check whether this enemy has a weakness,
                                    resistance, or immunity to a given
                                    damage type or condition.

    <enemy id> sav <mods> <dc> - Have an enemy perform a saving throw. The
                                 syntax of a saving throw is as follows:

                                 [+/-]<abilities>

                                 The simplest saving throw is just an ability,
                                 such as con or dex. Put a plus or minus before
                                 it to specify advantage or disadvantage.
                                 Certain monsters have special bonuses just for
                                 saving throws, which are added at the end.
                                 Negative bonuses are allowed.

                                 Examples:

                                 3 sav con 12 - Enemy #3 performs a Constitution
                                                saving throw of DC 12.

                                 5 sav +dex 9 - Enemy #5 performs a Dexterity
                                                saving throw of DC 9 with
                                                advantage.

                                 4 sav str+4 15 - Enemy #4 performs a Strength
                                                  saving throw of DC 15, with
                                                  a +4 bonus to his roll.

                                 2 sav -wis+1 8 - Enemy #2 performs a Wisdom
                                                  saving throw of DC 8, with
                                                  disadvantage on the roll and
                                                  a +1 bonus to the total.

                                1 sav str+1/dex+0 12 - Perform a saving throw
                                                       on STR or DEX, whichever
                                                       has the higher ability
                                                       score.

    mf <enemy id> [m|f] - Refresh the status of an enemy,
                          and optionally change its gender.

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

    xp   - Print the total XP for this encounter

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
names = list()
templates = None
DEBUG = False
SHOW_HOW = True
SHOW_SPEED = False
SHOW_DEAD = False

PHYS_DMG = [
    "bludgeoning",
    "piercing",
    "slashing"
]

DMG_TYPES = PHYS_DMG + [
    "acid",
    "cold",
    "fire",
    "force",
    "lightning",
    "necrotic",
    "poison",
    "psychic",
    "radiant",
    "thunder",

    "nonmagicalnonadamantine",
    "nonmagicalnonsilvered",

    "magical",
    "nonmagical",
    "spell", # Just the archmage
    "magicalpiercing" # Just the rakshasa
]
COND_TYPES = [
    "blinded",
    "charmed",
    "deafened",
    "exhaustion",
    "frightened",
    "grappled",
    "incapacitated",
    "invisible",
    "paralyzed",
    "petrified",
    "poisoned",
    "prone",
    "restrained",
    "stunned",
    "unconscious"
]
MOD_IMMUNE = "immu"
MOD_RESIST = "res"
MOD_VUL = "weak"
MOD_VALUES = {
    MOD_IMMUNE : 0,
    MOD_RESIST : 0.5,
    MOD_VUL : 2
}

# Encounter XP (NOT difficulty XP)
exp = 0

settings = SimpleNamespace(**{
    "INIT_FILTER_FLOOR" : None,
    "NEXT_FILTER_FLOOR" : None
})

# Environments to pull from
valid_envs = set()
envs = set()
# Base monster to require (often orcs)
base_monster = None

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
    18 : 20000,
    19 : 22000,
    20 : 25000,
    21 : 33000,
    22 : 41000,
    23 : 50000,
    24 : 62000,
    30 : 155000
}

cr_threshold = [
    # Dummy value to offset list
    # so item at [1] corresponds
    # to level 1.
    None,
    # levels 1-4
    0, 0, 0, 0,
    # levels 5-10
    1, 1, 2, 3, 4, 4,
    # levels 11-16
    5, 6, 7, 8, 9, 9,
    # levels 17-20
    10, 11, 12, 13
]

STATUSES = list()
SAVE_PATH = "saves"

class Monster:
    """A generic monster template with all static stat info"""
    def __init__(self, name, rating, ac, hp, speed, stats, modline):
        self.name = name.strip()
        self.rating = float(rating)
        self.xp = cr_to_xp[self.rating]
        self.ac = int(ac)
        self.hp = int(hp)
        self.speed = speed
        self.envs = set()
        self.dmg_mods = dict()
        self.cond_mods = dict()

        (self.str, self.dex, self.con, self.int, self.wis, self.cha) = \
        tuple([int(s) for s in stats])

        # Set damage type modifiers
        line = modline.lower().replace(" ", "")
        mods = line.split(",")
        for moditem in mods:
            MODS_OR = f"{MOD_VUL}|{MOD_IMMUNE}|{MOD_RESIST}"
            if re_search(r"^(.+)(" + MODS_OR + r")$", moditem):
                name, mod = re.matchobj.groups()
                if name in DMG_TYPES:
                    self.dmg_mods[name] = mod
                elif name in COND_TYPES:
                    self.cond_mods[name] = mod
                else:
                    print(f"Did not recognized {name} in {self.name}")

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
    parser.add_argument("--use-zero", action="store_true",
            help="Use 0 CR monsters")
    parser.add_argument("--monster-data", default="mm",
            help="The data file with monster information")

    args = parser.parse_args()
    return args

def daily_xp_quota():
    """Calculate daily xp quota for party"""
    # Adventuring Day XP
    # Adjusted XP per character per day
    xp_per_day = [
        None,
          300,   600,  1200,  1700,  3500,
         4000,  5000,  6000,  7500,  9000,
        10500, 11500, 13500, 15000, 18000,
        20000, 25000, 27000, 30000, 40000
    ]

    total = sum([xp_per_day[lvl] for lvl in levels])
    return total

def multiply(monster_table, *args):
    """Apply multiplier to xp based on number of enemies"""
    monsters = list(args)
    avg_lvl = int(statistics.mean(levels))
    for mon, amt in monster_table.items():
        for i in range(0, amt):
            monsters.append(mon)
    if not monsters:
        return SimpleNamespace(xp=0, adj=0)

    xp = sum([m.xp for m in monsters])
    amt = len([ m for m in monsters
                if m.rating >= cr_threshold[avg_lvl] ])

    if amt <= 1: index = 1
    elif amt == 2: index = 2
    elif amt in range(3, 7): index = 3
    elif amt in range(7, 11): index = 4
    elif amt in range(11, 15): index = 5
    else: index = 6
    
    if len(levels) <= 2:
        index = min(index + 1, 5)
    elif len(levels) >= 6:
        index = max(index - 1, 0)

    multipliers = [0.5, 1, 1.5, 2, 2.5, 3, 4, 5]
    return SimpleNamespace(xp=xp, adj=multipliers[index] * xp)

def calc_target_xp(difficulty, print_all=False):
    """Get target XP from table"""
    with open("thresholds.csv", "r") as fin:
        lines = [line.strip() for line in fin.readlines()
                 if line.strip() and re.match(r"[0-9,]+$", line.strip())]

    targets = {}
    for line in lines:
        line = line.split(",")
        targets[int(line[0])] = line[1:]

    if print_all:
        for difficulty in DIFFICULTIES:
            total = 0
            for lvl in levels:
                total += int(targets[lvl][DIFFICULTIES.index(difficulty)])
            print(f"{difficulty}: {total}")
    else:
        total = 0
        for lvl in levels:
            total += int(targets[lvl][DIFFICULTIES.index(difficulty)])

    return total

def ability_to_mod(value):
    """Convert ability score to modifier"""
    return (value - 10) // 2

def find_monster(monsters, name, error=False):
    """Return first Monster item with name"""
    all_results = list()
    for mon in monsters:
        # Immediately return an exact match
        if mon.name.lower() == name.lower():
            return mon
        if mon.name.lower().startswith(name.lower()):
            all_results.append(mon)
    if len(all_results) == 1:
        return all_results[0]
    if len(all_results) > 1:
        print("Found multiple matching monsters:")
        for mon in sorted(all_results, key=lambda x: x.name.lower()):
            print(f"    {mon.name}")
    if error and len(all_results) != 1:
        print("ERROR: Could not find", name)
        sys.exit(1)
    return None

def init_data(filename):
    """Read data"""
    monsters = []

    with open(filename, "r") as fin:
        reader = csv.DictReader(fin)
        for line in reader:
            monster = Monster(
                 line['Name'], line['CR'],
                 line['AC'], line['HP'], line['Speeds'],
                [line['STR'], line['DEX'], line['CON'],
                 line['INT'], line['WIS'], line['CHA']],
                 line['WRI'])
            envs = set()
            for k,v in line.items():
                if k.startswith("Env ") and v == "x":
                    env = k[4:].lower()
                    valid_envs.add(env)
                    monster.envs.add(env)
            monsters.append(monster)

    return monsters

def manual_monsters():
    """Manually create a monster list"""
    global levels
    # Item: (monster, count)
    monster_count = dict()

    setup_players(difficulty=False)

    while True:
        print()
        if monster_count:
            mons_by_name = sorted(monster_count.keys(), key=lambda k: k.name)
            for i, mon in enumerate(mons_by_name):
                amt = monster_count[mon]
                print("{}) {} x{}".format(i+1, mon.name, amt))
            print()
        global exp
        exp = multiply(monster_count).adj
        print(exp, "adjusted XP")
        print()

        print("Commands:")
        print("  set   (set the amount of a monster; add to list if necessary)")
        print("  del   (delete this entry from list)")
        print("  clear (clear all monsters from list - be careful!)")
        print("  xp    (print party's xp info)")
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
            choice = input_int(f"How many {mon.name}? ")
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
        elif cmd == "xp":
            calc_target_xp(None, print_all=True)
            quota = daily_xp_quota()
            print()
            print("Encounter quota (daily/3):", quota // 3, "XP")
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
    target_xp_flr = calc_target_xp(difficulty)
    target_xp_ceil = target_xp_flr * 1.1

    result = {}
    xp_total = 0
    monster_count = 0
    # Adjust minimum xp if no elegible monsters
    min_adj = 0

    while not (target_xp_flr < multiply(result).adj and
               multiply(result).adj <= target_xp_ceil):
        # Minimum XP for this mon to be considered
        # (Remaining XP) * next_floor
        min_mon_xp = (target_xp_ceil - multiply(result).adj) * next_floor - min_adj
        # Add base_monster if provided
        if not result and base_monster:
            winner = base_monster
            amt = random.randint(2, 8)
            if target_xp_ceil < winner.xp:
                print(f"WARNING: {base_monster.name}s too difficult for this group")
        else:
            # Populate candidates and choose who's next
            candidates = []
            for mon in monster_templates:
                # XP delta with this mon added
                mon_xp = multiply(result, mon).adj - multiply(result).adj

                # If mon XP is small enough to fit in remaining XP,
                # and large enough to meet minimum requirement,
                # and CR is less than avg player's level,
                # and check if 0 CR is allowed
                # and check if envs are restricted
                if multiply(result, mon).adj <= target_xp_ceil and \
                   mon_xp >= min_mon_xp and \
                   mon.rating <= avg_player_lvl and \
                   (mon.rating > 0 or args.use_zero) and \
                   bool(not envs or envs.intersection(mon.envs)):
                    candidates.append(mon)
            # If no available creatures, bail
            if not candidates:
                if min_mon_xp > 0:
                    min_adj += 100
                    continue
                elif not args.use_zero:
                    print("Adding 0 CR monsters to pool")
                    args.use_zero = True
                    min_adj = 0
                    continue
                else:
                    print("No more candidates - exiting")
                    break
            min_adj = 0
            winner = random.choice(candidates)
            amt = random.randint(1, args.max_per_group)

        # Remove chosen monster from further candidacy
        monster_templates.remove(winner)

        while amt > 0:
            xp_total += winner.xp
            result[winner] = result.get(winner, 0) + 1
            amt -= 1
            monster_count += 1
            if multiply(result, winner).adj > target_xp_ceil:
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

    global exp
    exp = multiply(result).xp
    print(exp, "XP")
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

        # Set XP
        elif line.startswith("XP: "):
            global exp
            exp = int(line[4:])

    return result

def save_game(filename, enemies, silent=False):
    """Save game to file"""
    filename = save_path(filename)
    if not silent:
        print("Saving to {}...".format(filename))
    lines = []
    lines.append(f"XP: {exp}\n")
    lines.append("\n")
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
        if i < len(names):
            name = names[i]
        else:
            name = f"Player {i+1}"
        roll = input_int(f"What is {name}'s initiative? ", sign=True)
        inits.append( (name, roll) )
    for mon in monsters_count:
        inits.append( (mon, random.randint(1, 20) + ability_to_mod(mon.dex)) )
    inits.sort(key=lambda x: x[1], reverse=True)
    colors_raw = ["red", "blue", "green", "orange", "purple", "pink", "yellow"]
    colors = colors_raw.copy()
    for x, c1 in enumerate(colors_raw):
        for y, c2 in enumerate(colors_raw):
            if y > x:
                colors.append(f"{colors[x]}-{colors[y]}")

    for mon, init in inits:
        if mon in monsters_count:
            count = 0
            amt = monsters_count[mon]
            for i in range(amt):
                nickname = mon.name
                if amt > 1:
                    nickname += f" [{colors[i]}]"
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
        while not enemies:
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

        match = re.search(basic_pattern.format("dmg") + "\s*([@$+-]*)(\w*)\s*$", choice)

        if match:
            uid = int(match.group(1))
            delta = int(match.group(2))
            properties = match.group(3)
            token = match.group(4).lower()

            if uid not in select:
                print("Enemy #{} does not exist!".format(uid))
                continue

            enemy = select[uid]
            dmg_mods = set()

            if token:
                types_found = [v for v in DMG_TYPES if v.startswith(token)]

                # If user provides "poison", it should match "poison",
                # not create unavoidable ambiguity with "poisoned"
                if token in types_found:
                    types_found = [token]
                if len(types_found) > 1:
                    print(f"Token '{token}' ambiguous: {types_found}")
                    continue
                elif not types_found:
                    print(f"Could not resolve token: {token}")
                    continue

                dmg_type = types_found[0]
                if "+" in properties:
                    magical = "magical"
                elif "-" in properties:
                    magical = "nonmagical"
                else:
                    magical = "nonmagical" if dmg_type in PHYS_DMG else "magical"

                if dmg_type in enemy.template.dmg_mods:
                    dmg_mods.add(enemy.template.dmg_mods[dmg_type])
                elif dmg_type in PHYS_DMG:
                    if magical and magical in enemy.template.dmg_mods:
                        dmg_mods.add(enemy.template.dmg_mods[magical])
                    elif "nonmagicalnonadamantine" in enemy.template.dmg_mods and \
                            "+" not in properties and "@" not in properties:
                        dmg_mods.add(enemy.template.dmg_mods["nonmagicalnonadamantine"])
                    elif "nonmagicalnonsilvered" in enemy.template.dmg_mods and \
                            "+" not in properties and "$" not in properties:
                        dmg_mods.add(enemy.template.dmg_mods["nonmagicalnonsilvered"])

            factor = 1
            for dmg_mod in dmg_mods:
                factor *= MOD_VALUES[dmg_mod]
            if factor == 0:
                print("It didn't seem to have any effect")
                continue
            elif 0 < factor < 1:
                print("It didn't seem very effective")
            elif factor > 1:
                print("It seemed particularly effective")
            delta = int(delta * factor)

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

        match = re.search(r"^\s*check\s+(\d+)\s+(\w+)\s*$", choice)
        if match:
            uid = int(match.group(1))
            if uid not in select:
                print("Enemy #{} does not exist!".format(uid))
                continue
            token = match.group(2)
            enemy = select[uid]
            ALL_TYPES = DMG_TYPES + COND_TYPES
            types_found = [v for v in ALL_TYPES if v.startswith(token)]
            if token in types_found:
                types_found = [token]
            if len(types_found) > 1:
                print(f"Token '{token}' ambiguous: {types_found}")
                continue
            elif not types_found:
                print(f"Could not resolve token: {token}")
                continue
            else:
                if token in enemy.template.dmg_mods:
                    res_class = enemy.template.dmg_mods[token]
                    if res_class == MOD_IMMUNE:
                        res_class = "is immune to"
                    elif res_class == MOD_RESIST:
                        res_class = "resists"
                    elif res_class == MOD_VUL:
                        res_class = "is weak to"
                    print(enemy.template.name, res_class, token)
                elif token in enemy.template.cond_mods:
                    print(f"{enemy.template.name} cannot be {token}")
                else:
                    print(f"{enemy.template.name} + {token}: No info")
            continue

        match = re.search(r"(\d+)\s+sav\s+([\w+-/]+)\s+(-?\d+)$", choice)
        if match:
            uid = int(match.group(1))
            if uid not in select:
                print("Enemy #{} does not exist!".format(uid))
                continue
            enemy = select[uid]
            check_str = match.group(2)
            dc = int(match.group(3))

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

        if re_search(r"^\s*mf\s+(\d+)\s*([mf]?)\s*$", choice):
            uid = int(re.matchobj.group(1))
            if uid not in select:
                print("Enemy #{} does not exist!".format(uid))
                continue
            enemy = select[uid]
            new_gender = re.matchobj.group(2)

            if new_gender:
                enemy.sex = new_gender
            enemy.refresh_status()
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
        elif choice == "xp":
            print(exp, "XP")
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


def settings_loop():
    """Display and print settings"""
    global envs
    global base_monster

    while True:
        print()
        print("Envs:", envs or "")
        print("Base monster:", getattr(base_monster, "name", ""))
        print()
        choice = input("Modify (e)nvironment, (L)ist environments, (B)ase monster, or (R)eturn? ")
        choice = choice.lower().strip()

        if choice in ("e", "environment"):
            print("Enter environment name (-env clears one, -- clears all)")
            choice = input("? ").lower().strip()
            if choice in valid_envs:
                envs.add(choice)
            elif choice.startswith("-") and choice[1:] in envs:
                envs.remove(choice[1:])
            elif choice == "--":
                envs.clear()
            else:
                print("Env not valid!")
        elif choice in ("l", "list"):
            print()
            for env in sorted(valid_envs):
                print(env)
        elif choice in ("b", "base"):
            choice == "b"
            choice = input("Enter monster (-- to clear): ").lower().strip()
            if find_monster(templates, choice):
                base_monster = find_monster(templates, choice)
            elif choice.startswith("--"):
                base_monster = None

        elif choice in ("r", "return"):
            return
        else:
            print("I didn't understand that")
            continue


def startup_prompt():
    """Prompt user for initial info"""
    print()
    print("~~~ Welcome to Encounter! ~~~")
    print()
    choice = None
    enemies = None
    while True:
        choice = input("(R)andomize monsters, (C)hoose your own, (S)ettings, (L)oad a save? ")
        choice = choice.strip().lower()
        if not choice:
            continue
        if choice in ("l", "load"):
            while True:
                loadfile = input("Enter file to load: ").strip()
                if not os.path.isfile(save_path(loadfile)):
                    print("Cannot open file")
                    continue
                enemies = load_game(loadfile)
                break
        elif choice in ("c", "choose"):
            monster_count = manual_monsters()
            global exp
            exp = multiply(monster_count).xp
            print(exp, "XP")
            enemies = init_enemies(monster_count)
        elif choice in ("r", "random", "randomize"):
            monster_count = random_monsters(args)
            enemies = init_enemies(monster_count)
        elif choice in ("s", "settings"):
            settings_loop()
        elif choice in ("q", "quit", "exit"):
            sys.exit(0)
        else:
            print("I did not recognize that.")
            choice = None

        if enemies:
            return enemies

def setup_players(difficulty=True):
    """Setup players and return difficulty"""
    global levels
    levels.clear()
    choice = ""

    amt = 0
    while amt < 1:
        amt = input_int("How many players are there? ")
    for i in range(amt):
        choice = ""
        lvl = 0
        name = names[i] if i < len(names) else f"Player {i+1}"
        while lvl < 1 or lvl > 20:
            lvl = input_int(f"What is {name}'s level (1-20)? ".format(i+1))
        levels.append(lvl)


    if not difficulty:
        return None

    diff_str = ", ".join(DIFFICULTIES)
    while choice not in DIFFICULTIES and choice != "rand":
        choice = input("Choose a difficulty ({}): ".format(diff_str))
        choice = choice.lower()

    if choice == "rand":
        droll = random.randint(1, 20)
        if droll <= 4:
            choice = "easy"
        elif droll >= 19:
            choice = "hard"
        else:
            choice = "med"

    return choice

def init_names(filename):
    """Initialize player aliases"""
    if not os.path.isfile(filename):
        return
    with open(filename, "r") as fin:
        lines = fin.readlines()
    for line in lines:
        line = line.strip()
        if line:
            names.append(line)

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
    templates = init_data(os.path.join("mdata", args.monster_data + ".csv"))
    init_status("status.txt")
    init_names("names.txt")
    loop_game()
