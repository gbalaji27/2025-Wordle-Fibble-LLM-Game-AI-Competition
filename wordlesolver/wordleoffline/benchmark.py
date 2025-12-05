"""
OFFLINE Wordle Benchmark - Ollama (20 games)
"""

import time
import json
from pathlib import Path

try:
    import wandb
    HAS_WANDB = True
except ImportError:
    HAS_WANDB = False
    print("wandb not installed - running without logging")

from classes.GameState import GameState, Status
from constants import LLM_MODEL, MAX_LLM_CONTINUOUS_CALLS

LOG_DIR = Path("benchmarks/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

NUM_RUNS = 20  # 20 games for offline/local models


def run_game(game, run_id):
    print(f"\n{'='*40}")
    print(f"Starting run {run_id + 1}")
    print(f"{'='*40}")
    
    game.reset()
    game_start = time.time()
    llm_calls = 0
    good = 0
    bad = 0
    
    while game.status != Status.end:
        calls = game.enter_word_from_ai()
        llm_calls += calls
        if game.was_valid_guess:
            good += 1
            bad += max(0, calls - 1)
        else:
            bad += 1
    
    game_time = time.time() - game_start
    
    print(f"\n--- Run {run_id + 1} Results ---")
    print(f"Success: {'✅ YES' if game.success else '❌ NO'}")
    print(f"Tries: {game.num_of_tries()}")
    print(f"Target was: {game.target_word}")
    print(f"Game latency: {game_time:.2f}s")
    
    return {
        'success': game.success,
        'tries': game.num_of_tries(),
        'target': game.target_word,
        'latency': game_time,
        'llm_calls': llm_calls,
        'good': good,
        'bad': bad
    }


def main():
    print(f"\n{'#'*50}")
    print(f"# OFFLINE WORDLE BENCHMARK (Ollama)")
    print(f"# Model: {LLM_MODEL}")
    print(f"# Games: {NUM_RUNS}")
    print(f"{'#'*50}")
    
    if HAS_WANDB:
        wandb.init(project="llm-wordle-comp", name=f"offline-{LLM_MODEL}")
    
    game = GameState(show_window=False, logging=True)
    
    results = []
    total_wins = 0
    total_tries = 0
    total_latency = 0
    total_llm = 0
    total_good = 0
    total_bad = 0
    
    for i in range(NUM_RUNS):
        r = run_game(game, i)
        results.append(r)
        
        if r['success']:
            total_wins += 1
        total_tries += r['tries']
        total_latency += r['latency']
        total_llm += r['llm_calls']
        total_good += r['good']
        total_bad += r['bad']
        
        n = i + 1
        print(f"\n--- Rolling Averages ---")
        print(f"Win rate: {total_wins/n:.1%}")
        print(f"Avg tries: {total_tries/n:.2f}")
    
    win_rate = total_wins / NUM_RUNS
    avg_tries = total_tries / NUM_RUNS
    avg_latency = total_latency / NUM_RUNS
    ratio = total_good / total_bad if total_bad > 0 else float('inf')
    
    print(f"\n{'='*50}")
    print(f"  OFFLINE WORDLE - FINAL RESULTS")
    print(f"{'='*50}")
    print(f"  Platform:        Ollama (Offline)")
    print(f"  Model:           {LLM_MODEL}")
    print(f"  Games:           {NUM_RUNS}")
    print(f"  Win Rate:        {win_rate:.1%} ({total_wins}/{NUM_RUNS})")
    print(f"  Average Tries:   {avg_tries:.2f}")
    print(f"  Average Latency: {avg_latency:.2f}s")
    print(f"  Good/Bad Ratio:  {ratio:.2f}" if total_bad > 0 else "  Good/Bad Ratio:  ∞")
    print(f"{'='*50}")
    
    output = {
        'platform': 'ollama (offline)',
        'model': LLM_MODEL,
        'num_games': NUM_RUNS,
        'win_rate': win_rate,
        'avg_tries': avg_tries,
        'avg_latency': avg_latency,
        'games': results
    }
    
    log_file = LOG_DIR / "offline_wordle_results.json"
    with open(log_file, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to: {log_file}")
    
    if HAS_WANDB:
        wandb.log({"win_rate": win_rate, "avg_tries": avg_tries})
        wandb.finish()


if __name__ == "__main__":
    main()
