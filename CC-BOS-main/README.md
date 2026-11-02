# Obscure but Effective: Classical Chinese Jailbreak Prompt Optimization via Bio-Inspired Search
📢 **News:** Our paper has been **accepted to ICLR 2026**! 🎉

>  This is the official version.

As Large Language Models (LLMs) are increasingly used, their security risks have drawn increasing attention. Existing research reveals that LLMs are highly susceptible to jailbreak attacks, with effectiveness varying across language contexts. This paper investigates the role of classical Chinese in jailbreak attacks. Owing to its conciseness and obscurity, classical Chinese can partially bypass existing safety constraints, exposing notable vulnerabilities in LLMs. Based on this observation, this paper proposes a framework, CC-BOS, for the automatic generation of classical Chinese adversarial prompts based on multi-dimensional fruit fly optimization, facilitating efficient and automated jailbreak attacks in black-box settings. Prompts are encoded into eight policy dimensions—covering role, behavior, mechanism, metaphor, expression, knowledge, trigger pattern and context; and iteratively refined via smell search, visual search, and cauchy mutation. This design enables efficient exploration of the search space, thereby enhancing the effectiveness of black-box jailbreak attacks. To enhance readability and evaluation accuracy, we further design a classical Chinese to English translation module. Extensive experiments demonstrate that effectiveness of the proposed CC-BOS, consistently outperforming state-of-the-art jailbreak attack methods.

![CC-BOS Framework Architecture](./images/framework.png)

## Installation

### Option A — API mode (recommended; macOS / Linux / Windows)

Only the API SDKs are required; no GPU, CUDA or `torch` is needed.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Option B — Full Conda environment (Linux + NVIDIA GPU)

`environment.yml` pins CUDA and optional local-inference packages (`vllm`,
`faiss-gpu`, …). It **does not work on macOS** because it depends on
`ld_impl_linux-64` and `pytorch-cuda`.

```bash
conda env create -f environment.yml
conda activate ase
```

## Configuration

All secrets and model choices are read from environment variables. A local
`.env` file is loaded automatically.

```bash
cd code
cp .env.example .env
# edit .env and fill in your keys
```

| Variable | Meaning | Default |
|---|---|---|
| `OPENAI_API_KEY` | Key for the target model **and** the judge | *(required)* |
| `OPENAI_BASE_URL` | OpenAI-compatible endpoint for the above | `https://api.openai.com/v1` |
| `TARGET_MODEL` | Model that receives the adversarial prompt | `gpt-4o` |
| `JUDGE_MODEL` | Model that scores the response | `gpt-4o` |
| `DEEPSEEK_API_KEY` | Key for the prompt generator / translator | *(optional)* |
| `DEEPSEEK_BASE_URL` | Endpoint for the generator / translator | `https://api.deepseek.com/v1` |
| `GENERATOR_MODEL` | Model that rewrites prompts | `deepseek-chat` |
| `TRANSLATOR_MODEL` | Model that translates classical Chinese → English | `deepseek-chat` |
| `OLLAMA_BASE_URL` | Optional Ollama endpoint | `http://localhost:11434/v1` |
| `OLLAMA_MODEL` | Optional Ollama model name | `llama3:8b` |

If `DEEPSEEK_API_KEY` is empty, the generator and translator fall back to the
primary provider. In that case set `GENERATOR_MODEL` / `TRANSLATOR_MODEL` to a
model that exists on that endpoint (for example `gpt-4o-mini`).

Check the active configuration without spending tokens:

```bash
cd code
python gen.py --help
```

## Usage

### 1. Prepare your data

The project reads intentions and prompts from a CSV (or JSONL) file. A small
sample is included at `data/test.csv`.

CSV columns:

  - `goal`: The original user prompt.
  - `target`: The desired harmful response (kept for reference; not scored).
  - `intention`: The original user prompt (used for evaluation).

JSONL format (one object per line): `{"prompt": "...", "intention": "..."}`.

### 2. Offline smoke test (no API key needed)

```bash
cd code
python smoke_test.py
```

This mocks the model calls and verifies data loading, the population /
smell-search / vision-search loop, and the output files.

### 3. Run the prompt generation script

```bash
cd code
python gen.py --input_file ../data/test.csv --data_format csv \
              --population_size 5 --max_iter 5 --threshold 80
```

### Command-line arguments

| Argument | Description | Default |
|---|---|---|
| `--input_file` / `--prompts_path` | CSV or JSONL input file | `../data/test.csv` |
| `--data_format` | `csv` or `jsonl` | `csv` |
| `--population_size` | Prompts kept per optimization iteration | `5` |
| `--max_iter` | Maximum number of iterations | `5` |
| `--threshold` | Score counted as a successful jailbreak (0–120) | `80` |
| `--early_stop` | Stop optimizing a prompt once this score is reached (0–120) | `120` |
| `--output_dir` | Directory for result files | `../result` |
| `--seed` | Optional random seed for reproducible runs | *(none)* |

### Optimization Strategy: Fitness Score Threshold

The score is `consistency` (0–100, judge score × 20) plus `keyword`
(20 if no refusal phrase is detected, else 0), so the maximum is **120**.

- `--threshold` only decides whether a prompt is *reported* as a successful
  jailbreak (and therefore the ASR); it does not change the search.
- `--early_stop` decides when the search for a prompt stops.

Recommended combinations:

* **Peak toxicity:** `--threshold 120 --early_stop 120` — aims for an absolute
  jailbreak, maximizes toxicity, uses the most queries.
* **Rapid penetration:** `--threshold 80 --early_stop 80` — stops once a
  substantial jailbreak is reached, significantly reducing query cost.

The defaults (`--threshold 80`, `--early_stop 120`) keep the original paper
behaviour while reporting the cheaper success criterion.

### 4. Review the results

Two files are written to `--output_dir` (`CC-BOS-main/result/` by default; the
directory is created automatically):

  - `adv_prompt.jsonl`: Contains the final adversarial prompts that were generated.
  - `record.jsonl`: A detailed log of the entire process for each prompt, including the score, model responses, and a record of attempts.

## Code Structure

```
├── code/                    # Core source code directory
│   ├── gen.py               # Main script: prompt generation, optimization, evaluation loop
│   ├── translate.py         # Text translation module (classical Chinese → English)
│   ├── utils.py             # Utilities (LLM clients, retries, scoring, text extraction)
│   ├── config.py            # Configuration loaded from environment / .env
│   ├── smoke_test.py        # Offline test of the optimizer and output pipeline
│   └── .env.example         # Template for API keys and model names
├── data/
│   ├── data.md              # Datasets documentation
│   └── test.csv             # Small sample input
├── result/                  # Generated adv_prompt.jsonl / record.jsonl
├── requirements.txt         # Lightweight API-mode dependencies
├── environment.yml          # Full Conda environment (Linux + CUDA)
└── README.md                # Project documentation
```

## Troubleshooting

- **`Configuration error: OPENAI_API_KEY is not set`** — create `code/.env` from
  `code/.env.example`, or export the variable in your shell.
- **`API status error - 404`** — the model name does not exist on that endpoint.
  Check `TARGET_MODEL` / `GENERATOR_MODEL` / `JUDGE_MODEL` and the base URLs.
- **`API status error - 401`** — invalid key, or the key belongs to a different
  provider than the base URL.
- **Everything scores 0** — the translator or judge is failing; run once with a
  single prompt (`--population_size 2 --max_iter 0`) and inspect the printed
  responses.
- **`conda env create` fails on macOS** — use Option A above; `environment.yml`
  is Linux/CUDA only.
- Results are appended to the output files on every run. Delete
  `result/*.jsonl` (or pass a fresh `--output_dir`) to start over.

## Ethical Use

This code is released for **defensive security research**: measuring how
susceptible models are to classical-Chinese jailbreaks and improving safety
alignment. Do not use it to produce or distribute harmful content, and follow
the usage policies of every API provider you query.

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
