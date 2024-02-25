import json
from collections import Counter
from itertools import product
from typing import List, Tuple, Union

import numpy as np
from yams import (
    SHEET_KEYS,
    SHEET_POSSIBLE_VALUES,
    get_sheet_points,
    print_pretty_sheet
)

def best_evaluation(throw_evaluation):
    max_score = max(throw_evaluation.values())
    best_options = [
        (k, throw_evaluation[k])
        for k in reversed(SHEET_KEYS)
        if throw_evaluation[k] == max_score
    ]

    return best_options[0]


def generate_all_throws(dice_kept, max_dice=5):
    """Generate all throws that can be derived from an original set of dice"""
    n_dice = len(dice_kept)
    n_next_dice = max_dice - n_dice
    next_possibilities = product(*[range(1, 7) for _ in range(n_next_dice)])
    all_possibilities = {
        tuple(sorted((*dice_kept, *poss))) for poss in next_possibilities
    }
    return list(all_possibilities)


def powerset(s):
    res = []
    x = len(s)
    for i in range(1 << x):
        res.append([s[j] for j in range(x) if (i & (1 << j))])

    ddupl_res = list(set(tuple(sorted(x)) for x in res))
    return ddupl_res


class YamsAgent:
    """Agents to play Yams.
    Agents should never modify game's state, in particular player sheets.
    """

    def __init__(self):
        pass

    def lock_dice(self, sheet, throw) -> Tuple[int]:
        raise NotImplementedError

    def choose_row(self, sheet, throw):
        raise NotImplementedError

    def __str__(self):
        return self.__class__.__name__


class YamsT1(YamsAgent):
    """Agent looking at throws at "depth 1" (thus T1).
    To lock dice, we look at
    1. All possible lock choices
    2. All possible random throws (each one is equipossible)
    3. Scoring each random throw post-lock
    4. Aggregating for each lock choice the scores with median
    5. Choosing the lock choice with best median score
    """

    def score_throw(self, sheet, throw):
        return best_evaluation(get_sheet_points(sheet, throw))

    def get_lock_score(self, sheet, throw):
        lock_choices = powerset(throw)
        lock_scores = dict()

        for lock_choice in lock_choices:
            all_random_throws = generate_all_throws(lock_choice)
            random_throws_eval = [
                self.score_throw(sheet, possible_throw)
                for possible_throw in all_random_throws
            ]
            # Any aggregate function valid here
            agg_score = np.mean([score[1] for score in random_throws_eval])
            lock_scores[lock_choice] = agg_score
        return lock_scores

    def lock_dice(self, sheet, throw, is_first_lock=True):
        lock_scores = self.get_lock_score(sheet, throw)
        # print(retain_scores)
        max_agg_score = max(lock_scores.values())
        best_recommendations = [
            lock_choice
            for (lock_choice, score) in lock_scores.items()
            if score == max_agg_score
        ]
        return best_recommendations[0]

    def choose_row(self, sheet, throw) -> List[Union[str, int]]:
        # sheet_points = get_sheet_points(sheet, throw)
        row, points = self.score_throw(sheet, throw)
        if sheet[row] is not None:
            row = self.eliminate_row(sheet)
            points = 0

        return row

    def eliminate_row(self, sheet):
        for k in [
            "Yams",
            1,
            "Grande Suite",
            "Petite Suite",
            "Full",
            2,
            "Carré",
            "Brelan",
            3,
            4,
            5,
            6,
        ]:
            if sheet[k] is None:
                return k
        print_pretty_sheet(sheet)
        raise ValueError("The sheet seems full. Can't eliminate any row")


class YamsRandom(YamsT1):

    def lock_dice(self, sheet, throw, is_first_lock=True):
        retain_choices = powerset(throw)
        return np.random.choice(retain_choices)


class YamsT1E(YamsT1):

    def __init__(self, points_power=1.5):

        self.expected_scores = {k: np.max(SHEET_POSSIBLE_VALUES[k]) for k in SHEET_KEYS}
        # To speed things up
        self.points_power = points_power
        self.custom_power = {x: x**points_power for x in range(100)}
        self.score_cache = {}

    def score_throw(self, sheet, throw, is_first_lock=True):
        sheet_hash = hash(json.dumps(sheet))
        throw_hash = hash(throw)
        sheet_points = get_sheet_points(sheet, throw)
        if (sheet_hash, throw_hash) in self.score_cache:
            return self.score_cache[(sheet_hash, throw_hash)]

        row_scores = {
            k: self.custom_power[sheet_points[k]] / self.expected_scores[k]
            for k in sheet_points.keys()
        }
        max_score = max(row_scores.values())
        best_options = [(k, v) for (k, v) in row_scores.items() if v == max_score]
        if len(best_options) > 1:
            best_options_by_points = list(
                sorted(best_options, key=lambda x: -sheet_points[x[0]])
            )
            # print(throw, best_options, best_options_by_points)
            final_score = best_options_by_points[0]
        else:
            # print(throw, best_options)
            final_score = best_options[0]

        self.score_cache[(sheet_hash, throw_hash)] = final_score
        return final_score
    
class YamsT1T(YamsT1E):

    def __init__(self, 
                 target_scores_file='target_median_YamsT1E.json',
                 points_power=1.5):
        super().__init__(points_power=points_power)

        with open(target_scores_file, encoding='utf-8') as target_file:
            target_scores = json.load(target_file)
        self.target_name = "_".join(
            target_scores_file.split('.')[0].split('_')[1:]
        )
        for i in range(1, 7):
            target_scores[i] = target_scores[str(i)]
            del target_scores[str(i)]
        self.expected_scores = target_scores

    def score_throw(self, sheet, throw, is_first_lock=True):
        sheet_hash = hash(json.dumps(sheet))
        throw_hash = hash(throw)
        sheet_points = get_sheet_points(sheet, throw)
        if (sheet_hash, throw_hash) in self.score_cache:
            return self.score_cache[(sheet_hash, throw_hash)]

        row_scores = {
            k: 2*sheet_points[k] - self.expected_scores[k]
            for k in SHEET_KEYS
        }

        max_score = max(row_scores.values())
        best_options = [(k, v) for (k, v) in row_scores.items() if v == max_score]
        if len(best_options) > 1:
            best_options_by_points = list(
                sorted(best_options, key=lambda x: -sheet_points[x[0]])
            )
            final_score = best_options_by_points[0]
        else:
            final_score = best_options[0]

        self.score_cache[(sheet_hash, throw_hash)] = final_score
        return final_score
    
    def __str__(self):
        return f'{self.__class__.__name__}_{self.target_name}'


class YamsT2(YamsT1):
    """Agent looking at throws at maximum "depth 2" (thus T2).
    To lock dice, we look at
    1. All possible lock choices
    2. All possible random throws (each one is equipossible)
        a. All possible lock choices for each random throw
        b. All possible random throws for each secondary lock choice
        c. Score each random throw of each secondary lock choice
    3. Scoring each primary lock choice with mean of each random throw post second. lock
    4. Aggregating for each retain choice the scores with mean
    5. Choosing the retain choice with best mean score
    """

    def __init__(
        self,
    ):

        self.lock_cache = {}
        self.lock_cache_hit = 0
        self.lock_cache_missed = 0

        self.score_cache = {}
        self.score_cache_hit = 0
        self.score_cache_missed = 0

    def score_throw(self, sheet, throw):
        sheet_hash = hash(json.dumps(sheet))
        throw_hash = hash(throw)
        if (sheet_hash, throw_hash) in self.score_cache:
            self.score_cache_hit += 1
            return self.score_cache[(sheet_hash, throw_hash)]

        score = super().score_throw(sheet, throw)
        self.score_cache_missed += 1
        self.score_cache[(sheet_hash, throw_hash)] = score
        return score

    def get_lock_score(self, sheet, throw, recursive=False):
        sheet_hash = hash(json.dumps(sheet))
        throw_hash = hash(throw)
        if (sheet_hash, throw_hash, recursive) in self.lock_cache:
            self.lock_cache_hit += 1
            return self.lock_cache[(sheet_hash, throw_hash, recursive)]

        self.lock_cache_missed += 1

        lock_choices = powerset(throw)
        lock_scores = dict()

        for lock_choice in lock_choices:
            all_random_throws = generate_all_throws(lock_choice)
            if recursive:
                random_throws_lock_scores = [
                    self.get_lock_score(sheet, random_throw, recursive=False)
                    for random_throw in all_random_throws
                ]
                random_throws_scores = []
                for random_throw_lock_score in random_throws_lock_scores:
                    random_throws_scores.extend(random_throw_lock_score.values())
                agg_score = np.mean(random_throws_scores)
                # print(f"Got lock score for {lock_choice}: ({agg_score:.2f} {recursive})")

            else:
                # Normal
                random_throws_eval = [
                    self.score_throw(sheet, possible_throw)
                    for possible_throw in all_random_throws
                ]
                # Any aggregate function valid here
                agg_score = np.mean([score[1] for score in random_throws_eval])
            lock_scores[lock_choice] = agg_score

        self.lock_cache[(sheet_hash, throw_hash, recursive)] = lock_scores
        return lock_scores

    def lock_dice(self, sheet, throw, is_first_lock=False):
        if not is_first_lock:
            return super().lock_dice(sheet, throw)

        lock_scores = self.get_lock_score(sheet, throw, recursive=is_first_lock)
        # print(retain_scores)
        max_agg_score = max(lock_scores.values())
        best_recommendations = [
            lock_choice
            for (lock_choice, score) in lock_scores.items()
            if score == max_agg_score
        ]
        return best_recommendations[0]

    def choose_row(self, sheet, throw) -> List[Union[str, int]]:
        # sheet_points = get_sheet_points(sheet, throw)
        row, points = self.score_throw(sheet, throw)
        if sheet[row] is not None:
            row = self.eliminate_row(sheet)
            points = 0

        return row

class YamsT2KE(YamsT1E):
    """Agent looking at throws at maximum "depth 2" (thus T2).
    To lock dice, we look at
    1. All possible lock choices
    2. All possible random throws (each one is equipossible)
        a. All possible lock choices for each random throw
        b. All possible random throws for each secondary lock choice
        c. Score each random throw of each secondary lock choice
    3. Scoring each primary lock choice with mean of each random throw post second. lock
    4. Aggregating for each retain choice the scores with mean
    5. Choosing the retain choice with best mean score
    """

    def __init__(
        self, topk=5, points_power=1.5
    ):
        super().__init__(points_power)
        self.topk = topk

        self.lock_cache = {}
        self.lock_cache_hit = 0
        self.lock_cache_missed = 0

        self.score_cache = {}
        self.score_cache_hit = 0
        self.score_cache_missed = 0

    def score_throw(self, sheet, throw):
        sheet_hash = hash(json.dumps(sheet))
        throw_hash = hash(throw)
        if (sheet_hash, throw_hash) in self.score_cache:
            self.score_cache_hit += 1
            return self.score_cache[(sheet_hash, throw_hash)]

        score = super().score_throw(sheet, throw)
        self.score_cache_missed += 1
        self.score_cache[(sheet_hash, throw_hash)] = score
        return score

    def get_lock_score(self, sheet, throw, recursive=False):
        sheet_hash = hash(json.dumps(sheet))
        throw_hash = hash(throw)
        if (sheet_hash, throw_hash, recursive) in self.lock_cache:
            self.lock_cache_hit += 1
            return self.lock_cache[(sheet_hash, throw_hash, recursive)]

        self.lock_cache_missed += 1

        # Normal T1 lock scores
        lock_scores = super().get_lock_score(sheet, throw)
        if not recursive:
            return lock_scores
        
        # Reducing lock choices to maximum topk choices
        topk_score = sorted(lock_scores.values(), reverse=True)[self.topk]
        lock_choices = [
            lock_choice 
            for (lock_choice, lock_score) in lock_scores.items()
            if lock_score >= topk_score
        ] if len(lock_scores) > self.topk else lock_scores.keys()

        
        for lock_choice in lock_choices:
            all_random_throws = generate_all_throws(lock_choice)
            random_throws_lock_scores = [
                self.get_lock_score(sheet, random_throw, recursive=False)
                for random_throw in all_random_throws
            ]
            random_throws_scores = []
            for random_throw_lock_score in random_throws_lock_scores:
                random_throws_scores.extend(random_throw_lock_score.values())
            agg_score = np.median(random_throws_scores)
            # print(f"Got lock score for {lock_choice}: ({agg_score:.2f} {recursive})")

            lock_scores[lock_choice] = agg_score

        self.lock_cache[(sheet_hash, throw_hash, recursive)] = lock_scores
        return lock_scores

    def lock_dice(self, sheet, throw, is_first_lock=False):
        if not is_first_lock:
            return super().lock_dice(sheet, throw)

        lock_scores = self.get_lock_score(sheet, throw, recursive=is_first_lock)
        # print(retain_scores)
        max_agg_score = max(lock_scores.values())
        best_recommendations = [
            lock_choice
            for (lock_choice, score) in lock_scores.items()
            if score == max_agg_score
        ]
        return best_recommendations[0]

    def choose_row(self, sheet, throw) -> List[Union[str, int]]:
        # sheet_points = get_sheet_points(sheet, throw)
        row, points = self.score_throw(sheet, throw)
        if sheet[row] is not None:
            row = self.eliminate_row(sheet)
            points = 0

        return row


class YamsHuman(YamsAgent):

    def lock_dice(self, sheet, throw):
        retain_choices = powerset(throw)
        user_lock = input(f"Which dice from {throw} do you want to lock?\n")
        try:
            user_choice = tuple(int(elem) for elem in user_lock)
        except ValueError:
            print("Please type only integers from 1 to 6.")
            self.lock_dice(sheet, throw)

        while not tuple(sorted(user_choice)) in retain_choices:
            print(f"{user_choice} is not a valid lock choice.")
            user_lock = input(f"Which dice from {throw} do you want to lock?\n")
            try:
                user_choice = tuple(int(elem) for elem in user_lock)
            except ValueError:
                print("Please type only integers from 1 to 6.")

        return user_choice
