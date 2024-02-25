from collections import Counter
from typing import List
import numpy as np

def roll_dice(n=5, real_dice=False):
    if real_dice:
        try:
            table_dice = input("Thrown dices:")
            dices = tuple(sorted(int(dice) for dice in table_dice))
            assert len(dices) == n
            for d in dices:
                assert 1 <= d <= 6
        except Exception as exception:
            print("!!!")
            print(exception)
            table_dice = input("Thrown dices:")
            dices = tuple(sorted(int(dice) for dice in table_dice))
            assert len(dices) == n
            for d in dices:
                assert 1 <= d <= 6
        finally:
            return dices
    else:
        return tuple(sorted(np.random.randint(1, 7, n)))


PETITE_SUITES: List[set] = [{1, 2, 3, 4}, {2, 3, 4, 5}, {3, 4, 5, 6}]
GRANDE_SUITES: List[set] = [{1, 2, 3, 4, 5}, {2, 3, 4, 5, 6}]
SHEET_KEYS = [
    1,
    2,
    3,
    4,
    5,
    6,
    "Bonus",
    "Chance",
    "Brelan",
    "Carré",
    "Full",
    "Petite Suite",
    "Grande Suite",
    "Yams",
]

SHEET_POSSIBLE_VALUES = {
    1: list(range(6)),  # column 1
    2: list(e * 2 for e in range(6)),  # column 2
    3: list(e * 3 for e in range(6)),  # column 3
    4: list(e * 4 for e in range(6)),  # column 4
    5: list(e * 5 for e in range(6)),  # column 5
    6: list(e * 6 for e in range(6)),  # column 6
    "Bonus": [0, 35],  # bonus
    "Chance": list(range(0, 31)),  # chance
    "Brelan": list(e * 3 for e in range(7)),  # brelan
    "Carré": list(e * 4 for e in range(7)),  # carré
    "Full": [0, 25],  # full
    "Petite Suite": [0, 30],  # petite suite
    "Grande Suite": [0, 40],  # grande suite
    "Yams": [0, 50],  # yams
}


def print_pretty_sheet(sheet):
    for k, v in sheet.items():
        print(f"{str(k):12s} -> {str(v) if v is not None else '':2s}")
        if k == "Bonus":
            print("=" * 18)


def check_petite_suite(throw):
    for p_suite in PETITE_SUITES:
        if p_suite.issubset(set(throw)):
            return True
    return False


def check_grande_suite(throw):
    for g_suite in GRANDE_SUITES:
        if g_suite.issubset(set(throw)):
            return True
    return False


def get_sheet_points(sheet: dict, throw: tuple, real=False):
    sheet_row_used = {k: 0 for k in SHEET_KEYS}
    # [1::6] columns
    for i in range(1, 7):
        if sheet[i] is None:
            eval = i * throw.count(i)
            sheet_row_used[i] = int(eval)
            # Bonus
            if real or sheet['Bonus']:
                continue
            curr_balance = (
                sum(map(lambda x: x if x else 0, [sheet[i] for i in range(1, 7)]))
                + eval
            )
            if curr_balance >= 63:
                sheet_row_used[i] += 35

    # Chance
    if not sheet["Chance"]:
        eval = sum(throw)
        sheet_row_used["Chance"] = int(eval)

    # Full
    occ_counter = Counter(throw)
    i_max, i_occ = occ_counter.most_common(1)[0]
    if not sheet["Full"] and len(occ_counter) == 2 and i_occ == 3:
        sheet_row_used["Full"] = 25

    # Brelan
    if not sheet["Brelan"] and i_occ >= 3:
        eval = 3 * i_max
        sheet_row_used["Brelan"] = int(eval)

    # Carré
    if not sheet["Carré"] and i_occ >= 4:
        eval = 4 * i_max
        sheet_row_used["Carré"] = int(eval)

    # P. Suite
    if not sheet["Petite Suite"] and check_petite_suite(throw):
        sheet_row_used["Petite Suite"] = 30
    # G. Suite
    if not sheet["Grande Suite"] and check_grande_suite(throw):
        sheet_row_used["Grande Suite"] = 40
    # Yams
    if not sheet["Yams"] and i_occ == 5:
        sheet_row_used["Yams"] = 50

    return sheet_row_used

def play_round(sheet, agent, verbose=True, real_dice=False):
    # First throw, full random
    first_throw = roll_dice(real_dice=real_dice)
    if verbose: print("First throw:", first_throw)

    # Locking some dice a first time
    locked_dice = agent.lock_dice(sheet, first_throw, is_first_lock=True)
    if verbose: print("Locked dice:", locked_dice)

    # Throwing some dice a second time
    second_throw = roll_dice(5 - len(locked_dice), real_dice=real_dice)
    if verbose: print("Second throw:", second_throw)
    second_throw = tuple(sorted((*locked_dice, *second_throw)))

    # Locking some dice a second time
    locked_dice = agent.lock_dice(sheet, second_throw, is_first_lock=False)
    if verbose: print("Keeping dice:", locked_dice)

    # Throwing some more dice a third and final time
    final_throw = roll_dice(5 - len(locked_dice), real_dice=real_dice)
    if verbose: print("Third throw:", final_throw)
    final_throw = tuple(sorted((*locked_dice, *final_throw)))

    row = agent.choose_row(sheet, final_throw)
    points = get_sheet_points(sheet, final_throw, real=True)
    sheet[row] = points[row]
    
    # bonus
    bonus_balance = 0
    is_bonus_finished = True
    for i in range(1, 7):
        if sheet[i] is None:
            is_bonus_finished = False
        else:
            bonus_balance += sheet[i]

    if bonus_balance >= 63:
        if verbose: print("Bonus reached!")
        sheet["Bonus"] = 35
    elif is_bonus_finished:
        sheet["Bonus"] = 0
        
    if verbose: print_pretty_sheet(sheet)

def play_game(agent, verbose=False, return_sheet=False, real_dice=False):
    my_sheet = {k: None for k in SHEET_KEYS}
    while None in my_sheet.values():
        play_round(my_sheet, agent, verbose=verbose, real_dice=real_dice)
    if return_sheet:
        return my_sheet
    else:
        return sum(my_sheet.values())