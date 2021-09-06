# encounter

## Introduction

Maybe you don't have any friends. Maybe you have lots of friends and they suck. Maybe you do have friends and they're cool, but I doubt that, because then I'd be your friend.

Whatever the reason you want to D&D alone, Encounter is here to help. This program facilitates solo battles, although you will still need game pieces, character sheets, and monster info. **Resources are included at the bottom of this document.**

What this program does:
- Randomly generates monster lists according to the number and level of playable characters.
- Manages HP and AC, so you won't be tempted to metagame.
- Rolls ONLY initiative and saving throws for monsters.
- Provides an interface to save/load battles.
- Preserves turn order.

What this program *doesn't* do:
- Control monster movement.
- Understand monster attacks/spells. You'll manage that yourself.
- Perform monster attack/damage rolls, or any player die rolls.
- Track who's turn it currently is.

Have fun, and kick the snot out of a Violet Fungus!

## Installation

1. Go to https://www.python.org/ and install the latest Python 3 to your machine. This is an interpreter which runs Python programs.

2. On this page (https://github.com/moonshot11/encounter/), click the bright green button that says "Clone or download", and then "Download ZIP".

3. On your computer, extract the ZIP file.

4. In the newly-created folder, double-click "encounter.py" to start the program. You can create a shortcut to this file, but **do not move encounter.py without the other files.** It relies on the data in that folder to run!

## Getting Started

If this is your first time running Encounter, you won't have any saved files, so at the prompt, type "r" and hit Enter to randomize an encounter.

```
~~~ Welcome to Encounter! ~~~

(R)andomize monsters, (C)hoose your own, or (L)oad a save file? r
```

Next, it will prompt you to set up the players. Note that as of now, players are not named, so you will need to keep track of who is Player 1, Player 2, etc.

Let's set up a game with Level 4 and Level 3 players, and create a medium-difficulty encounter. Difficulties are calculated based on the math in DMG 5e pg. 82.

```
How many players are there? 2
What is Player 1's level (1-20)? 4
What is Player 2's level (1-20)? 3
Choose a difficulty (easy, med, hard, deadly, hell): med
```

The game will print the list of monsters. If you are doing everything else by hand, you can stop here. Otherwise, let's keep going!

Note: "hell" is a made-up difficulty not in the DMG. Its XP thresholds are 40% greater than the deadly difficulty.

```
Lion x1
Merfolk x2

375.0 XP
```

Now, you have to roll your own die to figure out the players' initiatives. **Encounter knows nothing about your character sheets**, so remember to add your initiative modifier yourself when you enter the total.

```
Roll for initiative!
What is Player 1's initiative? 16
What is Player 2's initiative? 11
```

That's it!  You're ready to begin your battle!

## Battle

When a battle has started, you will see a prompt with monster information and turn order:

```
 1) Lion ... has strong political opinions
 -) Player 1
 2) Merfolk [red] ... is radiating energy after eating 20 protein bars!
 3) Merfolk [blue] ... is having a wonderful day
 -) Player 2
> _
```

The creature at the top of the list has the highest initiative. Start there and work your way down.

You must now enter commands. Only a single command actually changes the "state" of the game: doing damage. Every other command will at most tell you the result (whether an attack hits, or whether a saving throw succeeds).

Each time you do damage, an autosave file will be overwritten, called `_auto.sav`. If this program crashes, you can always load that file to resume where you left off.

### Battle commands:

- **Attack**: `atk <enemy id> <attack total>`  
*Example: Attack enemy #2 for a total of 17:* `atk 2 17`    
Attack the enemy specified by the ID. Roll your die, add all modifiers, and provide the total here.  Output will appear telling you whether your attack was successful.  

- **Damage**: `dmg <enemy id> <damage total>`  
*Example: Damage enemy 3 for 5 hp:* `dmg 3 5`  
Damage the enemy. If the enemy dies, you will be told, and the enemy will no longer be displayed. If you accidentally enter too much damage, you can reverse it by dealing "negative" damage. This will revive a dead enemy. For example, `dmg 3 -999` will restore any SRD creature to max health. Enemy health *can* drop below 0 HP, so you should only use extreme `dmg` values when fully healing a creature.  
**You are responsible for all modifiers, resistances, and immunities.** This program does not account for attack type.

- **Set health**: `hp <enemy id> <amount>`  
Example: Set enemy #2's health to 1 HP: `hp 2 1`  
Set the enemy's health to <value>. Rarely, this is necessary when an enemy must have a specific amount of health (such as a Zombie), and enemy health can go negative in this program.  (Enemy health cannot exceed its maximum, so use `dmg` to restore a monster to full health.)

- **Saving throws**: `<enemy id> sav <modifiers> <dc>`  
Have an enemy perform a saving throw. The syntax for the modifiers is as follows:  
`[+/-]<ability>[bonus]`  
For example:   `3 sav +con+5 12` - Enemy #3 performs a Constitution saving throw with advantage, and adds +5 to the result.  It checks against a DC 12.
See the section below on saving throws for more detail on this command.

### Display commands

- **Toggle status flavor text**: `how`  
*Default: on.*  
You may have noticed that the lion above has strong political opinions. This flavor text changes as each enemy's health grows more dire. It can optionally be toggle on/off by entering `how` (short for "how are they looking?").

- **Toggle enemy speed**: `speed` or `spd`  
*Default: off.*  
You can toggle displaying all enemies' speeds, to aid in moving pieces around without consulting the monster info. The speed info will appear in parentheses:  
```
 1) Lion (50) ... has strong political opinions
 -) Player 1
 2) Merfolk [red] (10, swim 40) ... is radiating energy after eating 20 protein bars!
 3) Merfolk [blue] (10, swim 40) ... is having a wonderful day
 -) Player 2
>
```

- **Toggle showing dead enemies** `dead`  
*Default: off.*  
Toggles whether to show dead enemies. By default, they are not displayed in the list of monsters once their health drops below 1 HP.

### Misc

- **Load/save**  
`load <filename>`  
`save <filename>`  
Load or save to a file, e.g. `save game1`. You can call the files whatever you like, but they are stored as text files and can be open in Notepad. If you don't want to see each enemy's HP, don't open this file!  
Games are loaded and saved by providing **only** the filename (`load game1`), and the program fills in the rest ("saves/game1.sav").  
When you load a game, the previous game is saved in `saves/_load.sav`.

- **Start a new game** `newgame`  
Set up a new encounter. An autosave is created in `saves/_auto.sav` of your current game in before starting a new one.

- **Restart current battle** `restart`  
Sets all health of every enemy (even if dead) back to full health. Autosaves to `saves/_auto.sav` before resetting.

- **Re-run last command** `last`
Runs the last command. Useful if you need to do the same saving throw multiple times.

- **Quit** `quit`  
Save the current game to `saves/_quit.sav` and exit.

- **XP** `xp`  
Print the total XP of the current encounter.

- **Help** `help`  
Display this information in-game.

## Saving Throws Modifiers

Saving throw commands work as follows:

`<enemy id> sav <modifiers> <dc>`

Example modifiers:

`con` - Perform a Constitution saving throw.

`-dex` - Perform a Dexterity saving throw, with disadvantage.

`wis+3` - Perform a Wisdom saving throw, with a +3 bonus.

`+str-2` - Perform a Strength saving throw, with advantage and a -2 bonus.

The `+` and `-` at the start represent advantage and disadvantage, with the number after the ability optionally adding to the roll. The roll is performed automatically, and you will be told whether the saving throw succeeded:

```
 1) Lion ... has strong political opinions
 -) Player 1
 2) Merfolk [red] ... is radiating energy after eating 20 protein bars!
 3) Merfolk [blue] ... is having a wonderful day
 -) Player 2
> 2 sav wis+3 12


=== Saved! ===
```

Since Encounter doesn't know what is being saved, it is up to you to apply all effects and damage.

## Resources

**Character sheets, maps, monster icons\*, and more:**  
https://app.roll20.net/editor/

**Monster information (SRD 5e):**  
https://5thsrd.org/gamemaster_rules/monster_indexes/monsters_by_name

\*If there are multiple of the same enemy in battle, a color label (`red`, `blue`, etc.) will be displayed by the name. This can be useful on sites such as Roll20, where you can add color designators to the map.

Have fun!
