# Obscure but Effective: Classical Chinese Jailbreak Prompt Optimization via Bio-Inspired Search

📢 **News:** Our paper has been **accepted to ICLR 2026**! 🎉

> This is the official version.

As Large Language Models (LLMs) are increasingly used, their security risks have drawn increasing attention. Existing research reveals that LLMs are highly susceptible to jailbreak attacks, with effectiveness varying across language contexts. This paper investigates the role of classical Chinese in jailbreak attacks. Owing to its conciseness and obscurity, classical Chinese can partially bypass existing safety constraints, exposing notable vulnerabilities in LLMs. Based on this observation, this paper proposes a framework, CC-BOS, for the automatic generation of classical Chinese adversarial prompts based on multi-dimensional fruit fly optimization, facilitating efficient and automated jailbreak attacks in black-box settings. Prompts are encoded into eight policy dimensions—covering role, behavior, mechanism, metaphor, expression, knowledge, trigger pattern and context; and iteratively refined via smell search, visual search, and cauchy mutation. This design enables efficient exploration of the search space, thereby enhancing the effectiveness of black-box jailbreak attacks. To enhance readability and evaluation accuracy, we further design a classical Chinese to English translation module. Extensive experiments demonstrate that effectiveness of the proposed CC-BOS, consistently outperforming state-of-the-art jailbreak attack methods.

![CC-BOS Framework Architecture](./images/framework.png)

> **Research use only.** This code implements attacks against LLM safety
> mechanisms. Only run it against models you are authorised to test, and follow
> the usage policy of every API provider you use.

## Installation

### Prerequisites

- Python 3.8 or higher
- API access to the victim model and the attacker model (OpenAI-compatible endpoints)

### Option A — minimal pip install (recommended)

```bash
cd CC-BOS-main
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The runtime only needs `openai`, `tqdm` and `requests`. No GPU, PyTorch or
`pandas` is required for the API pipeline.

### Option B — Conda

The original `environment.yml` is kept for reproducibility of the paper's
full environment (CUDA / vLLM / local-model stack). It is much heavier than
what `code/` actually needs.

```bash
conda env create -f environment.yml
conda activate ase
```

## Configuration

Credentials are read from environment variables, so nothing secret needs to be
committed. You can also edit the defaults in `code/config.py`.

Alternatively, copy `.env.example` to `.env` and fill in your keys; `code/config.py`
loads `CC-BOS-main/.env` automatically, and `.env` is git-ignored.

```bash
# Victim model (the model being attacked)
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.openai.com/v1"   # optional
export TARGET_MODEL="gpt-4o"

# Attacker / translator model (DeepSeek-compatible)
export DEEPSEEK_API_KEY="sk-..."
export DEEPSEEK_BASE_URL="https://api.deepseek.com/v1"
export ATTACK_MODEL="deepseek-chat"

# Judge
export JUDGE_MODEL="gpt-4o"
```

If `DEEPSEEK_API_KEY` is omitted it falls back to `OPENAI_API_KEY`.

### Fully offline smoke test

A mock mode is included so the whole pipeline can be validated without any API
key or network request:

```bash
python code/gen.py --mock --limit 2 --population_size 2 --max_iter 1
```

Mock responses follow the same output contracts as the real models
(`#The_New_Question_With_Our_Intention:`, `#english:` and `#thescore:`), so the
optimization, translation, scoring and output-writing paths are all exercised.
The scores produced in mock mode are **not** experimental results.

## Usage

### 1. Prepare your data

The input is a CSV (or JSONL) file. CSV columns:

| Column | Meaning |
|---|---|
| `goal` | The original user prompt/query |
| `intention` | The harmful intent, used for evaluation (falls back to `goal`) |
| `target` | The desired harmful response (optional, kept for compatibility) |

`data/test.csv` contains two **benign placeholder rows** used only to check that
the pipeline runs. Replace them with your own benchmark data (AdvBench, CLAS
2024, StrongREJECT-small) before collecting results.

### 2. Run prompt generation

```bash
python code/gen.py --input_file data/test.csv --population_size 5 --max_iter 5
```

The path resolution is relative to the project root by default, and the output
directory is created automatically, so the command also works when run from
`code/` or from another working directory.

### Command-line arguments

| Argument | Default | Description |
|---|---|---|
| `--input_file`, `--prompts_path` | `data/test.csv` | Input CSV/JSONL file |
| `--data_format` | inferred | `csv` or `jsonl` |
| `--population_size` | `5` | Number of strategies kept per iteration |
| `--max_iter` | `5` | Maximum number of optimization iterations |
| `--output_dir` | `result/` | Directory for output files |
| `--threshold` | `80` | Score needed to count an attack as successful |
| `--early_stop` | `120` | Stop optimizing once this score is reached |
| `--limit` | all rows | Only process the first N rows |
| `--seed` | random | Random seed for reproducibility |
| `--mock` | off | Offline smoke test, no API calls |

### Optimization strategy: fitness score threshold

The fitness score is `consistency (0-100) + keyword (0 or 20)`, so it ranges
from 0 to 120:

- **Threshold = 120 (peak toxicity):** aims for an absolute jailbreak; the
  optimization stops only when the response fully matches the harmful intent
  and contains no refusal keyword.
- **Threshold = 80 (rapid penetration):** aims for a substantial jailbreak and
  stops once a significant toxicity level is reached, prioritising query cost.

Lowering the threshold (e.g. to 80) significantly reduces query cost, while a
higher threshold (120) maximises the toxicity intensity of the generated
prompts. `--early_stop` controls when the search stops; `--threshold` controls
which final prompts are labelled successful.

### 3. Review the results

Two files are written to `--output_dir` (default `result/`):

- `adv_prompt.jsonl` — the final adversarial prompts (`{"prompt": ...}` per line)
- `record.jsonl` — one record per input row with the original prompt, the
  adversarial prompt, the raw/translated model response, consistency score,
  total score, success flag and number of attempts.

The script also prints, after every improvement, a line such as:

```
>>> New best total score: 80.0 (attempt 4)
```

and, at the end of each row, the best total score for that row:

```
[row 0] best total score = 80.0 | success = YES | attempts = 6
```

Finally, a scoreboard is printed with the top-10 rows sorted by their best
total score, the overall **HIGHEST SCORE**, and the prompt that achieved it,
followed by the success count, total attempts, average attempts per prompt and
ASR (attack success rate).

## Code structure

```
CC-BOS-main/
├── code/
│   ├── gen.py          # Strategy space, fruit-fly search, evaluation loop, CLI
│   ├── api_client.py   # Unified OpenAI/Ollama client + offline mock mode
│   ├── translate.py    # Classical Chinese -> English translation module
│   ├── utils.py        # Judge scoring, keyword scoring, response parsing
│   └── config.py       # Env-var driven configuration (keys, model names)
├── data/
│   ├── data.md         # Benchmark dataset documentation
│   └── test.csv        # Benign smoke-test rows (replace with real data)
├── examples/           # Screenshots of tests against public chat interfaces
├── images/             # Framework figure (PNG + PDF)
├── requirements.txt    # Minimal runtime dependencies
├── environment.yml     # Full paper environment (optional, heavy)
└── README.md
```

## Troubleshooting

- **`No API key configured`** — export `OPENAI_API_KEY` / `DEEPSEEK_API_KEY`,
  or append `--mock` for an offline test.
- **`input file not found`** — pass an absolute path or a path relative to the
  current working directory; the default is `<repo>/data/test.csv`.
- **Outputs accumulate** — both JSONL files are opened in append mode. Delete
  `result/*.jsonl` (or use a new `--output_dir`) between experiments.

## Acknowledgements

Special thanks to the creators of [CL-GSO](https://github.com/Aries-iai/CL-GSO). Our work extends their excellent implementation, and we are grateful for their open-source contribution to the field.

## Citation

If you find this work or the underlying **CL-GSO** framework useful for your research, please consider citing the following paper:

```bibtex
@inproceedings{huang2026obscure,
  title={Obscure but Effective: Classical Chinese Jailbreak Prompt Optimization via Bio-Inspired Search},
  author={Xun Huang and Simeng Qin and Xiaoshuang Jia and Ranjie Duan and Huanqian Yan and Zhitao Zeng and Fei Yang and Yang Liu and Xiaojun Jia},
  booktitle={The Fourteenth International Conference on Learning Representations (ICLR)},
  year={2026},
  url={[https://openreview.net/forum?id=O7fxz7D6vf](https://openreview.net/forum?id=O7fxz7D6vf)}
}
```

## Examples

Examples of testing conducted via the web interfaces of various LLMs.

![Example-1 of Claude](./examples/claude-examlpe-2.jpg)

![Example-2 of Claude](./examples/claude-example-1.jpg)

![Example-1 of Deepseek](./examples/deepseek-example-2.jpg)

![Example-2 of Deepseek](./examples/deepseek-example-4.jpg)

![Example-1 of Doubao](./examples/deepseek-example-5.jpg)

![Example-2 of Doubao](./examples/deepseek-example-4.jpg)

![Example-1 of Gemini](./examples/gemini-example-4.jpg)

![Example-2 of Gemini](./examples/gemini-example-6.jpg)

![Example-1 of Chatgpt](./examples/gpt-example-1.jpg)

![Example-2 of Chatgpt](./examples/gpt-example-3.jpg)

![Example-1 of Grok](./examples/gpt-example-1.jpg)

![Example-2 of Grok](./examples/gpt-example-2.jpg)

![Example-1 of Qwen](./examples/qwen-example-1.jpg)

![Example-2 of Qwen](./examples/qwen-example-3.jpg)

![Example-1 of Yuanbao](./examples/yuanbao-example-1.jpg)

![Example-2 of Yuanbao](./examples/yuanbao-example-3.jpg)
