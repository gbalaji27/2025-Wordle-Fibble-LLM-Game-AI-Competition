# 🎯 LLM Wordle Solver

A high-performance Wordle solver using Large Language Models that achieves **100% win rate** with an average of **3.7-3.8 tries** - significantly outperforming the GPT-5 benchmark (5.9 tries).

## 🏆 Results

| Model | Platform | Games | Win Rate | Avg Tries | Avg Latency |
|-------|----------|-------|----------|-----------|-------------|
| llama-3.1-8b-instant | Groq (Online) | 10 | **100%** | **3.80** | 2.73s |
| llama3.2:3b | Ollama (Offline) | 20 | **100%** | **3.70** | 1.33s |
| GPT-5 (Benchmark) | OpenAI | 10 | 100% | 5.90 | - |

**Our solver is ~35% more efficient than the GPT-5 benchmark!**

## 🚀 Features

- **Constraint-based filtering**: Tracks letter positions, frequencies, and exclusions
- **Optimal starting word**: Uses "SALET" (mathematically proven best opener)
- **Smart LLM usage**: Zero LLM calls when only one candidate remains
- **Self-correction**: Validates and retries invalid LLM guesses
- **Dual platform support**: Works with both online APIs and local models
- **Perfect accuracy**: Achieves ∞ good/bad guess ratio (zero invalid guesses)

## 📁 Project Structure

```
├── wordleonline/          # Online version (Groq API)
│   ├── benchmark.py       # Run 10 games
│   ├── constants.py       # API configuration
│   └── classes/
│       ├── GameState.py   # Game logic + AI solver
│       └── LetterCell.py  # Feedback handling
│
└── wordleoffline/         # Offline version (Ollama)
    ├── benchmark.py       # Run 20 games
    ├── constants.py       # Ollama configuration
    └── classes/
        ├── GameState.py   # Game logic + AI solver
        └── LetterCell.py  # Feedback handling
```

## 🛠️ Setup & Usage

### Online (Groq API)

1. Get free API key from [Groq Console](https://console.groq.com/keys)
2. Update `wordleonline/constants.py` with your key
3. Run:
```bash
cd wordleonline
python3 benchmark.py
```

### Offline (Ollama)

1. Install Ollama:
```bash
brew install ollama  # macOS
```

2. Download model:
```bash
ollama pull llama3.2:3b
```

3. Start Ollama server:
```bash
ollama serve
```

4. Run benchmark (in new terminal):
```bash
cd wordleoffline
python3 benchmark.py
```

## 🧠 How It Works

### Algorithm Overview

1. **First Guess**: Always start with "SALET" (optimal information gain)

2. **Constraint Tracking**: After each guess, update constraints:
   - 🟩 Green: Letter is correct at this position
   - 🟨 Yellow: Letter exists but wrong position
   - ⬛ Gray: Letter not in word (or count exceeded)

3. **Candidate Filtering**: Filter word list by all known constraints

4. **LLM Selection**: 
   - If 1 candidate → return immediately (0 LLM calls)
   - If multiple → ask LLM to pick from top candidates

5. **Self-Correction**: If LLM picks invalid word, explain why and retry

### Prompt Format

```
You are playing Wordle. Guess a 5-letter word.

Previous guesses:
  SALET -> S:GRAY, A:YELLOW, L:GREEN, E:GRAY, T:YELLOW

Valid words: tidal,trail,trial,tolls
Tries left: 5
Reply with ONLY a 5-letter word:
```

## 📊 Performance Metrics

- **Win Rate**: 100% (30/30 total games)
- **Average Tries**: 3.70-3.80
- **LLM Calls per Guess**: 0.50-0.55
- **Invalid Guesses**: 0 (perfect accuracy)

## 🔗 Links

- **WandB Dashboard**: [https://wandb.ai/gbalaji27/llm-wordle-comp](https://wandb.ai/gbalaji27/llm-wordle-comp)
- **Competition Page**: [Wordle/Fibble LLM Competition](https://github.com/drchangliu/game-ai-sidekick/tree/main/wordle-fibble-LLM-competition)

## 🙏 Acknowledgments

- Competition hosted by Dr. Chang Liu
- Inspired by GPT-5 benchmark implementation
- Built with assistance from Claude AI
