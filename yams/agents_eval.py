from tqdm import tqdm
from p_tqdm import p_map
import os

from yams import play_game
import numpy as np
from time import time
from agents import (
    YamsRandom, YamsT1, YamsT1E, YamsT1T, YamsT2, YamsT2KE
)
import matplotlib.pyplot as plt
from multiprocessing import Pool
import json

agents = [
    (YamsRandom(), 5000),
    (YamsT1(), 2000),
    (YamsT1E(), 2000),
    (YamsT1T(target_scores_file='target_full_custom.json'), 2000),
    (YamsT1T(target_scores_file='target_median_YamsT1E.json'), 2000),
    (YamsT2KE(topk=3), 500)
]

t0 = time()
for agent, n_samples in agents:
    game_scores = []
    # p_bar = tqdm(range(n_samples))
    print("Agent:", agent)
    p_bar = p_map(
        play_game, 
        [agent]*n_samples,
        [False]*n_samples,
        [True]*n_samples
    )
        
    i_sample = 0
    for final_sheet in p_bar:
        
        score = sum(final_sheet.values())
        game_scores.append(score)
        # p_bar.set_postfix_str(np.median(game_scores))
        os.makedirs(f'data/sheets/{agent}/', exist_ok=True)
        with open(f'data/sheets/{agent}/sheet_{i_sample:05}.json', 'w') as file:
            json.dump(final_sheet, file)
        i_sample += 1
        
    gs_mean = np.median(game_scores)

    fig = plt.figure(figsize=(12, 4))
    val, bins, _ = plt.hist(game_scores, density=True, bins=min(50, len(game_scores)))
    plt.plot([gs_mean]*2, [0, val.max()], c='red')
    plt.annotate(f"Median: {gs_mean:.1f}", (gs_mean, 1e-3), c='red')
    plt.title(f'Agent: {agent}, sample size: {len(game_scores)}')
    plt.savefig(f"data/scores_distribution/{agent}.jpg")
    plt.close()

print("Total execution time:", time()-t0)