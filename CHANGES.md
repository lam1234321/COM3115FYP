# CC-BOS 改造變更摘要

- **日期**：2026-11-02
- **範圍**：`CC-BOS-main/`（使原本無法直接執行的官方程式碼可在本地完整跑通）
- **驗證環境**：macOS / Python 3.15 / `.venv`（`openai 3.42.1`、`tqdm`、`requests`）

---

## 1. 改造目標

原始倉庫存在多處「文件與程式不一致」及「首次執行必失敗」的問題，例如輸出路徑不存在、API Key 硬編碼為空、CLI 參數名稱與 README 不符、柯西變異使用了不存在的 `random.tan`。本次改造的目標是：

1. 修正所有會導致程式無法啟動或中斷的錯誤。
2. 讓 API 設定集中、可透過環境變數覆寫，避免把 Key 寫進版本控制。
3. 提供**無需 API Key 的離線 mock 模式**，可完整驗證流程。
4. 讓程式在任意工作目錄下執行都能正確找到輸入與輸出位置。
5. 精簡執行依賴（移除 pandas / numpy / torch 的實際使用）。
6. 更新 README，使安裝與使用說明與程式行為一致。

---

## 2. 修正的問題

| # | 改造前問題 | 影響 | 修正方式 |
|---|---|---|---|
| 1 | `gen.py` 在 import 時直接 `open('../result/*.jsonl')` | `result/` 不存在時首次執行即 `FileNotFoundError` | 啟動時自動建立輸出目錄；檔案改在 `main()` 中開啟 |
| 2 | 輸出路徑寫死 `../result` | 從 repo 根目錄執行時會寫到錯誤位置 | 改為相對於專案根目錄解析，並支援 `--output_dir` |
| 3 | README 使用 `--prompts_path`，程式只認 `--input_file` | 照 README 執行會 `unrecognized arguments` | 兩個參數名稱都支援 |
| 4 | 預設輸入 `../data/test.csv` 不存在 | 無資料可跑 | 新增 `data/test.csv` 佔位資料，預設路徑改為 `<repo>/data/test.csv` |
| 5 | `gen.py`、`utils.py` 的 client 使用硬編碼空 Key | 必定 401 / 無法呼叫 | 統一由 `config.py` 讀取，支援 `OPENAI_API_KEY`、`DEEPSEEK_API_KEY` 等環境變數 |
| 6 | `utils.py` 在 import 時就建立 `OpenAI(api_key="")` | 即使只跑 mock 也可能報錯 | 改為延遲建立（lazy client），僅在真正呼叫時初始化 |
| 7 | `gen.py` 與 `translate.py` 各自建立 client，設定來源不一致 | Key、Base URL 難以維護 | 新增 `code/api_client.py` 作為唯一 LLM 呼叫入口 |
| 8 | `standard_cauchy()` 使用 `random.tan` | 進入柯西變異時 `AttributeError` | 改用 `math.tan(math.pi * ...)`，移除 numpy 依賴 |
| 9 | `evaluate_query(..., counter=None)` 仍存取 `counter["attempts"]` | `TypeError` | 加入 `None` 保護 |
| 10 | Chat template 中 `"context”` 使用中文右引號 | 佔位符語意不一致（雖不影響 `format`） | 修正為 `"context"` |
| 11 | 關鍵詞拒答偵測只有英文詞 | 模型用中文拒答時會被誤判為成功 | 加入常見中文拒答詞（抱歉、我無法、恕難從命等） |
| 12 | 匯入未使用的 `anthropic`、`torch`、`pandas`、`numpy` | 安裝負擔大、易缺套件 | 移除；CSV 改用標準庫 `csv`，柯西分布改用 `math` |
| 13 | `get_csv_prompts` 直接依賴 pandas，且無欄位檢查 | 缺欄位時錯誤訊息不清楚 | 改用 `csv.DictReader`，支援 `goal`/`prompt`、`intention` 回退 |
| 14 | 成功閾值寫死 `80`、早停寫死 `120` | 無法調整實驗設定 | 新增 `--threshold`、`--early_stop` |
| 15 | 無 Key 時仍會跑完整輪並得到全 0 分 | 浪費時間且難以診斷 | 啟動時 preflight 檢查，直接給出設定指引 |
| 16 | 無任何可離線驗證的方式 | 沒有 Key 就完全無法確認程式是否正常 | 新增 `--mock` 模式，覆蓋完整流程 |

---

## 3. 新增檔案

| 檔案 | 說明 |
|---|---|
| `CC-BOS-main/code/api_client.py` | 統一 LLM 呼叫層。支援 `target` / `attack` / `judge` / `translate` / `ollama` / `mock` 六種 provider，內建重試與指數退避、缺少 Key 的明確錯誤、離線 mock 回應。 |
| `CC-BOS-main/requirements.txt` | 最小執行依賴：`openai>=1.30`、`tqdm>=4.66`、`requests>=2.31`。 |
| `CC-BOS-main/data/test.csv` | 2 筆**無害的佔位資料**，僅用於流程驗證，不是實驗資料。 |
| `.gitignore`（repo 根目錄） | 忽略 `.venv/`、`result/`、`__pycache__/`、`*.log`、`.DS_Store`。 |

## 4. 修改檔案

| 檔案 | 主要變更 |
|---|---|
| `CC-BOS-main/code/config.py` | 全面改為環境變數驅動；新增 `TARGET_MODEL`、`ATTACK_MODEL`、`JUDGE_MODEL`、`TRANSLATE_MODEL`、`MOCK_LLM`、`REQUEST_TIMEOUT`；`DEEPSEEK_*` 未設定時回退到 `OPENAI_*`。 |
| `CC-BOS-main/code/gen.py` | 重構 CLI 與主流程；輸出目錄自動建立；路徑相對於專案根目錄；`--threshold` / `--early_stop` / `--output_dir` / `--limit` / `--seed` / `--mock`；CSV/JSONL 皆支援；移除 numpy/pandas；修正柯西變異；所有 LLM 呼叫改走 `api_client`。 |
| `CC-BOS-main/code/utils.py` | 移除 import 時建立 client；`get_gpt_pipeline` 改為 `api_client.chat` 包裝；評分模型改由 config 提供；加入中文拒答詞；強化空回應與解析失敗的處理。 |
| `CC-BOS-main/code/translate.py` | 移除自建 client；改用 `api_client.chat`；預設模型改由 config 提供；修正 `model_type` 的 `api` / `ollama` / `mock` 分流；清理 few-shot 提示中的錯字。 |
| `CC-BOS-main/README.md` | 重寫安裝、設定、使用章節；新增 mock 快速驗證、正確的參數表、輸出說明、疑難排解與研究用途警告；保留研究背景、框架圖、範例截圖與引用。 |

### 檔案變更統計（`git diff --stat`）

```
 CC-BOS-main/README.md         | 195 +++++++++-----
 CC-BOS-main/code/config.py    |  70 ++++-
 CC-BOS-main/code/gen.py       | 602 ++++++++++++++++++++++++----------------
 CC-BOS-main/code/translate.py | 137 ++++------
 CC-BOS-main/code/utils.py     | 211 +++++++--------
 5 files changed, 712 insertions(+), 503 deletions(-)
```

> 修改檔案維持原有的 CRLF 換行格式。

---

## 5. 執行方式

### 5.1 安裝

```bash
cd CC-BOS-main
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> 原本的 `environment.yml` 仍保留，但包含 CUDA / vLLM / 本地模型等完整論文環境，對 `code/` 的 API 流程並非必要。

### 5.2 離線 mock 驗證（不需要 Key）

```bash
python code/gen.py --mock --limit 2 --population_size 2 --max_iter 1
```

### 5.3 真實執行

```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.openai.com/v1"   # 選填
export TARGET_MODEL="gpt-4o"

export DEEPSEEK_API_KEY="sk-..."
export DEEPSEEK_BASE_URL="https://api.deepseek.com/v1"
export ATTACK_MODEL="deepseek-chat"

python code/gen.py --input_file data/test.csv --population_size 5 --max_iter 5
```

### 5.4 重要參數

| 參數 | 預設值 | 說明 |
|---|---|---|
| `--input_file` / `--prompts_path` | `data/test.csv` | 輸入 CSV/JSONL |
| `--data_format` | 自動判斷 | `csv` 或 `jsonl` |
| `--population_size` | `5` | 每輪保留的策略數 |
| `--max_iter` | `5` | 最大迭代次數 |
| `--output_dir` | `result/` | 輸出目錄 |
| `--threshold` | `80` | 判定攻擊成功的分數門檻 |
| `--early_stop` | `120` | 達到此分數即停止搜尋 |
| `--limit` | 全部 | 只處理前 N 筆 |
| `--seed` | 隨機 | 固定隨機種子 |
| `--mock` | 關閉 | 離線 mock，不發出任何 API 請求 |

---

## 6. 驗證結果

| 測試 | 指令 | 結果 |
|---|---|---|
| 離線 mock（CSV，2 筆） | `python code/gen.py --mock --population_size 2 --max_iter 1 --seed 7` | 成功產生 `adv_prompt.jsonl` 與 `record.jsonl`；ASR `1/2`（mock 分數，非實驗結果） |
| 從 `code/` 目錄執行 | `cd code && python gen.py --mock ...` | 成功；輸出自動落到專案根目錄 `result/` |
| JSONL 輸入 + `--prompts_path` 別名 | `python code/gen.py --mock --prompts_path /tmp/sample.jsonl ...` | 成功 |
| 無 Key 的真實模式 | `python code/gen.py --limit 1` | 正確退出（exit 1）並提示設定方式 |
| 非 mock 網路路徑 | 以本地 OpenAI-compatible stub server 作為端點 | `openai` client 請求、重試、解析、評分、寫檔全部正常 |
| 語法檢查 | `python -m py_compile code/*.py` | 全部通過 |

### 驗證限制

- 未使用真實的 OpenAI / DeepSeek Key，因此非 mock 路徑僅驗證了 OpenAI-compatible 協定與完整流程，**不代表實際模型的攻擊效果**。
- `data/test.csv` 為無害佔位資料；正式實驗請替換為 AdvBench、CLAS 2024 或 StrongREJECT-small。
- mock 模式的分數由固定規則產生，**不可用於論文或實驗報告**。

---

## 7. 已知行為與注意事項

1. `result/adv_prompt.jsonl` 與 `result/record.jsonl` 使用**追加模式**；重跑前請刪除舊檔或改用新的 `--output_dir`。
2. `--mock` 只保證「流程可跑」，不模擬八維策略對提示詞品質的實際影響。
3. `environment.yml` 尚未精簡；若只需 API 流程，使用 `requirements.txt` 即可。
4. `config.py` 中的 `LOCAL_MODEL_PATH` / `DEVICE` 保留給未來本地模型擴充，目前預設流程不使用。
5. 本專案實作的是針對 LLM 安全機制的攻擊方法，僅供授權環境下的研究使用，並須遵守各 API 供應商的使用政策。
