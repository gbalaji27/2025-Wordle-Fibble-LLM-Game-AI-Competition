"""
Benchmark runner for LLM Wordle Competition
Runs multiple games and tracks performance metrics
"""

import time
import json
from pathlib import Path

# Optional: wandb for logging (comment out if not using)
try:
    import wandb
    HAS_WANDB = True
except ImportError:
    HAS_WANDB = False
    print("wandb not installed - running without logging")

from classes.GameState import GameState, Status
from classes.LetterCell import Feedback
from constants import LLM_MODEL, MAX_LLM_CONTINUOUS_CALLS

LOG_DIR = Path("benchmarks/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "llm_wordle_results.json"

NUM_RUNS = 10


def run_game(game: GameState, run_id: int, total_tries: int, total_success: int, 
             total_bad_guesses: int, total_good_guesses: int, total_latency: float, 
             total_guess_latency: float, total_guess_count: int, total_llm_calls: int, 
             results_dict=None):
    """Run a single game and track metrics"""
    
    print(f"\n{'='*40}")
    print(f"Starting run {run_id + 1}")
    print(f"{'='*40}")
    
    game.reset()
    total_completion = 0
    completion = 0
    game_start_time = time.time()

    while game.status != Status.end:
        guess_start_time = time.time()
        tries = game.enter_word_from_ai()
        guess_end_time = time.time()
        guess_latency = guess_end_time - guess_start_time
        total_guess_latency += guess_latency

        # Get feedback from the last word
        if game.words:
            feedback = game.words[-1].get_feedback()
        else:
            feedback = []

        # Calculate completion score
        completion = 0
        for fdb in feedback:
            if fdb == Feedback.incorrect:
                completion += 0
            elif fdb == Feedback.present:
                completion += 0.5
            elif fdb == Feedback.correct:
                completion += 1

        if game.was_valid_guess:
            total_completion += completion
            total_good_guesses += 1
            total_bad_guesses += tries - 1 if tries > 0 else 0
            total_llm_calls += tries
        else:
            total_bad_guesses += 1
            total_llm_calls += 1

        total_guess_count += 1

    game_end_time = time.time()
    game_latency = game_end_time - game_start_time
    total_latency += game_latency

    avg_game_completion = total_completion / game.num_of_tries() if game.num_of_tries() > 0 else 0
    total_success += 1 if game.success else 0
    total_tries += game.num_of_tries()

    # Print results
    print(f"\n--- Run {run_id + 1} Results ---")
    print(f"Success: {'✅ YES' if game.success else '❌ NO'}")
    print(f"Tries: {game.num_of_tries()}")
    print(f"Target was: {game.target_word}")
    print(f"Game latency: {game_latency:.2f}s")
    print(f"\n--- Rolling Averages ---")
    print(f"Avg completion: {avg_game_completion:.2f} / 5")
    print(f"Avg tries: {total_tries / (run_id + 1):.2f}")
    print(f"Win rate: {total_success / (run_id + 1):.1%}")
    print(f"Avg latency: {total_latency / (run_id + 1):.2f}s")
    
    if total_guess_count > 0:
        print(f"Avg guess latency: {total_guess_latency / total_guess_count:.2f}s")
    
    if total_bad_guesses > 0:
        print(f"Good/Bad ratio: {total_good_guesses / total_bad_guesses:.2f}")
    else:
        print(f"Good/Bad ratio: {total_good_guesses} (no bad guesses)")
    
    if total_good_guesses > 0:
        print(f"Avg LLM calls/guess: {total_llm_calls / total_good_guesses:.2f}")

    # Log to wandb if available
    if HAS_WANDB:
        wandb.log({
            "average_game_completion": avg_game_completion,
            "rolling_avg_tries": total_tries / (run_id + 1),
            "rolling_avg_success": total_success / (run_id + 1),
            "rolling_avg_game_latency": total_latency / (run_id + 1),
            "rolling_avg_guess_latency": total_guess_latency / total_guess_count if total_guess_count > 0 else 0,
            "good_guess_bad_guess_ratio": total_good_guesses / total_bad_guesses if total_bad_guesses > 0 else total_good_guesses,
            "avg_llm_calls_per_guess": total_llm_calls / total_good_guesses if total_good_guesses > 0 else 0
        }, step=(run_id + 1))

    # Save to results dict
    if results_dict is not None:
        results_dict["games"].append({
            "run_id": run_id + 1,
            "target_word": game.target_word,
            "success": game.success,
            "tries": game.num_of_tries(),
            "average_game_completion": avg_game_completion,
            "latency": game_latency,
            "llm_calls": total_llm_calls,
        })

    return (total_tries, total_success, total_bad_guesses, total_good_guesses, 
            total_latency, total_guess_latency, total_guess_count, total_llm_calls)


def test_games():
    """Run benchmark tests"""
    
    print(f"\n{'#'*50}")
    print(f"# LLM WORDLE BENCHMARK")
    print(f"# Model: {LLM_MODEL}")
    print(f"# Max retries: {MAX_LLM_CONTINUOUS_CALLS}")
    print(f"# Games: {NUM_RUNS}")
    print(f"{'#'*50}")
    
    game = GameState(show_window=False, logging=True)

    # Uncomment for Fibble mode:
    # game.num_lies = 1
    # game.num_guesses = 9

    total_success = 0
    total_tries = 0
    total_bad_guesses = 0
    total_good_guesses = 0
    total_guess_count = 0
    total_latency = 0.0
    total_guess_latency = 0.0
    total_llm_calls = 0

    results = {
        "num_runs": NUM_RUNS,
        "LLM_MODEL": LLM_MODEL,
        "MAX_LLM_CONTINUOUS_CALLS": MAX_LLM_CONTINUOUS_CALLS,
        "games": []
    }

    for i in range(NUM_RUNS):
        (total_tries, total_success, total_bad_guesses, total_good_guesses, 
         total_latency, total_guess_latency, total_guess_count, total_llm_calls) = run_game(
            game, i, total_tries, total_success, total_bad_guesses, 
            total_good_guesses, total_latency, total_guess_latency, 
            total_guess_count, total_llm_calls, results)
        
        if i < NUM_RUNS - 1:
            time.sleep(2.0)  # 2 second delay to avoid rate limiting

    # Calculate final stats
    win_rate = total_success / NUM_RUNS
    avg_tries = total_tries / NUM_RUNS
    avg_latency = total_latency / NUM_RUNS
    avg_llm_calls = total_llm_calls / total_good_guesses if total_good_guesses > 0 else 0

    # Save results
    results["total_bad_guesses"] = total_bad_guesses
    results["total_good_guesses"] = total_good_guesses
    results["total_guess_latency"] = total_guess_latency
    results["total_guess_count"] = total_guess_count
    results["good_guess_bad_guess_ratio"] = (total_good_guesses / total_bad_guesses 
                                              if total_bad_guesses > 0 else float('inf'))
    results["win_rate"] = win_rate
    results["avg_tries"] = avg_tries
    results["avg_latency"] = avg_latency
    results["total_llm_calls"] = total_llm_calls
    results["avg_llm_calls_per_guess"] = avg_llm_calls

    with open(LOG_FILE, "w") as f:
        json.dump(results, f, indent=2)

    # Print final results
    print(f"\n{'='*50}")
    print(f"{'='*50}")
    print(f"  FINAL RESULTS")
    print(f"{'='*50}")
    print(f"{'='*50}")
    print(f"  Win Rate:        {win_rate:.1%} ({total_success}/{NUM_RUNS})")
    print(f"  Average Tries:   {avg_tries:.2f}")
    print(f"  Average Latency: {avg_latency:.2f}s")
    print(f"  Total LLM Calls: {total_llm_calls}")
    print(f"  Avg LLM/Guess:   {avg_llm_calls:.2f}")
    print(f"  Good Guesses:    {total_good_guesses}")
    print(f"  Bad Guesses:     {total_bad_guesses}")
    if total_bad_guesses > 0:
        print(f"  Good/Bad Ratio:  {total_good_guesses / total_bad_guesses:.2f}")
    else:
        print(f"  Good/Bad Ratio:  ∞ (perfect!)")
    print(f"{'='*50}")
    print(f"\nResults saved to: {LOG_FILE}")


if __name__ == "__main__":
    # Initialize wandb if available
    if HAS_WANDB:
        wandb.init(
            project="llm-wordle-comp",
            name=f"{LLM_MODEL}-{MAX_LLM_CONTINUOUS_CALLS}-retries"
        )
    
    test_games()
    
    if HAS_WANDB:
        wandb.finish()