# CC-BOS 可執行化變更摘要

> 日期：2026-11-02
> 範圍：`CC-BOS-main/`（ICLR 2026 論文官方實作）
> 目標：讓專案在「不改動論文方法與輸出格式」的前提下，能夠直接安裝、設定、執行與除錯。

---

## 1. 原始狀態與主要問題

原始 repo 是一份研究程式碼上傳，缺少一般專案的可執行配套。實際檢查到以下阻礙：

| # | 問題 | 影響 |
| --- | --- | --- |
| 1 | `config.py` 與各檔案中的 API key、base URL 全是空字串 | 啟動即失敗 |
| 2 | `gen.py` 在 **import 時**就 `open('../result/...','a')` | 沒有 `result/` 目錄時直接 `FileNotFoundError` |
| 3 | `evaluate_query()` 在 `counter=None` 時仍讀 `counter["attempts"]` | `TypeError` |
| 4 | 模型名稱硬編碼（`deepseek-chat`、`gpt-4o`） | 無法換模型或端點 |
| 5 | README 寫 `--prompts_path`，程式實際是 `--input_file` | 照文件跑會報錯 |
| 6 | 預設輸入 `../data/test.csv` 不存在 | 無法開箱測試 |
| 7 | `Chat_template` 內有 `"context”"`（中文引號） | 格式字串與維度名不一致 |
| 8 | 多數例外被 `except` 吞掉，只印一行訊息 | 難以定位是 key、模型還是網路問題 |
| 9 | `environment.yml` 是 Linux + CUDA 專用 | macOS 無法用同一份環境 |
| 10 | 沒有 `.gitignore`，密鑰與輸出可能被提交 | 洩漏風險 |

---

## 2. 變更總覽

| 檔案 | 類型 | 摘要 |
| --- | --- | --- |
| `code/config.py` | 重寫 | 以環境變數／`.env` 為主的四角色設定，含缺少 key 的明確檢查 |
| `code/gen.py` | 修改 | 移除 import 時開檔、修正 `counter`、模型與閾值可配置、新增 CLI、`--dry_run` |
| `code/utils.py` | 修改 | 移除未使用的 `torch` 依賴、judge client 延遲建立、修正 `None` 回應處理 |
| `code/translate.py` | 修改 | client 延遲建立、模型預設值改讀 config、精簡未使用 import |
| `README.md` | 改寫 | 安裝、設定、參數、輸出、troubleshooting 全部對齊實際程式 |
| `requirements.txt` | 新增 | API 模式的輕量依賴 |
| `.env.example` | 新增 | 四種角色的 key／base URL／model 範本 |
| `.gitignore` | 新增 | 忽略 `.env`、`.venv`、`result/*`、`__pycache__` |
| `data/test.csv` | 新增 | 3 筆無害範例，讓管線可立即跑通 |
| `result/.gitkeep` | 新增 | 保留輸出目錄 |

---

## 3. 逐檔說明

### 3.1 `code/config.py`（重寫）

- 新增四種角色，各自可獨立在**不同端點**上：

  | 角色 | 變數前綴 | 預設模型 |
  | --- | --- | --- |
  | 生成器（改寫文言文） | `GENERATOR_*` | `deepseek-chat` |
  | 目標模型（被測試） | `TARGET_*` | `gpt-4o` |
  | 評審（0–5 評分） | `JUDGE_*` | `gpt-4o` |
  | 翻譯（文言文→英文） | `TRANSLATOR_*` | `deepseek-chat` |

- 解析順序：`GENERATOR_API_KEY` → `OPENAI_API_KEY` → 檔案內預設值。
  因此**只填一個 `OPENAI_API_KEY` 也能跑**，需要分開計費或不同供應商時再覆寫。
- 自動載入 repo 根目錄的 `.env`（`python-dotenv` 為選用依賴）。
- 保留舊名稱 `API_SECRET_KEY`、`BASE_URL`、`LOCAL_MODEL_PATH`、`DEVICE`、`BASE_URL_ollama`、`OLLAMA_MODEL`，避免破壞既有 import。
- 新增 `validate()`：一次列出所有缺少的 key，並提示用 `.env` 或 `OPENAI_API_KEY`。
- 新增 `RESULT_DIR`、`DEFAULT_DATA_PATH`，路徑以 repo 根目錄為基準，不再依賴「從哪裡執行」。

### 3.2 `code/gen.py`（修改）

**啟動與設定**

- 移除 import 時就開啟 `../result/adv_prompt.jsonl`、`record.jsonl` 的全域檔案控制代碼；改在 `main()` 內建立目錄後開檔。
- 移除未使用的 `math`、`SequenceMatcher`、`defaultdict`、`Anthropic`、`time`。
- Client 改由 `config` 建立；沒有 key 時為 `None`，只有真正呼叫時才報錯，讓 `--dry_run` 與 `--help` 在無 key 環境也能用。
- 新增 `RUNTIME`，集中管理生成／目標／評審／翻譯模型、成功閾值與提前停止分數。

**錯誤修正**

- `evaluate_query()`：只有 `counter is not None` 時才讀取 `counter["attempts"]`，修掉 `TypeError`。
- `Chat_template`：`"context”"` → `"context"`。
- 硬編碼的 `120` 提前停止分數改讀 `RUNTIME["early_stop_score"]`。
- CSV 載入時檢查 `goal`、`intention` 欄位；JSONL 檢查 `prompt`、`intention` 鍵，錯誤訊息帶檔名與行號。
- 空資料集、找不到輸入檔、缺少 key 都改成可讀的 `SystemExit`，不再噴完整 traceback。

**新增命令列功能**

| 參數 | 說明 |
| --- | --- |
| `--input_file` / `--prompts_path` | 輸入檔；後者是向後相容別名 |
| `--data_format {csv,jsonl}` | 輸入格式 |
| `--population_size`、`--max_iter` | 搜尋規模 |
| `--threshold` | 判定成功的分數（預設 80） |
| `--early_stop_score` | 提前停止分數（預設 120） |
| `--result_dir` | 輸出目錄，自動建立 |
| `--overwrite` | 覆寫而非附加輸出 |
| `--limit` | 只跑前 N 筆，便於煙霧測試 |
| `--seed` | 固定 `random` / `numpy`，可重現 |
| `--dry_run` | 完全不呼叫 LLM，驗證整條管線 |
| `--generator_model` 等四個 | 覆寫 `.env` 中的模型名稱 |

**輸出**

- 檔案格式與欄位**完全未變**：`adv_prompt.jsonl` 仍是 `{"prompt": ...}`；`record.jsonl` 仍含 `id/intention/original_prompt/adversarial_prompt/raw_response/model_response/consistency/score/success/jailbreak_attempts`。
- 預設輸出位置改為 `<repo>/result/`，不再依賴相對路徑 `../result/`。

### 3.3 `code/utils.py`（修改）

- 移除未使用的 `torch` import，API 模式不必安裝 PyTorch。
- Judge client 改由 `JUDGE_*`（或 `OPENAI_API_KEY`）建立；未設定時給出明確錯誤。
- `get_consistency_score()` 的預設 judge 模型改讀 `JUDGE_MODEL`。
- `extract_content()` 對 `None`／空字串直接回傳 `None`。
- `get_consistency_score()` 在 judge 回傳空值時回傳 `0.0`，不再落入 `AttributeError`。
- 原本的 0–5 評分 rubric 與拒絕詞表**未改動**。

### 3.4 `code/translate.py`（修改）

- Client 改為延遲建立；無 key 時 `openai_client = None`。
- 翻譯模型預設值改讀 `TRANSLATOR_MODEL`，仍可用參數覆寫。
- 無 key 時給出明確錯誤，避免 `None.chat` 的 `AttributeError`。
- 移除未使用的 `os`、`sys`、`time`、`concurrent.futures`、`partial`、`extract_content` import。
- 翻譯 prompt、few-shot 範例、分段邏輯**未改動**。

### 3.5 `README.md`（改寫）

- 安裝改為兩條路徑：`requirements.txt`（推薦）與原本的 Conda/CUDA（選用）。
- 設定改為 `.env` 流程，補上四種角色的表格與 fallback 規則。
- 修正 `--prompts_path` → `--input_file`，並保留別名說明。
- 補上完整參數表、`--dry_run` 煙霧測試、輸出位置、troubleshooting。
- 更新 code structure，納入 `requirements.txt`、`.env.example`、`data/test.csv`、`result/`。
- 修正範例圖片錯置：Doubao 誤用 DeepSeek 圖、Grok 誤用 GPT 圖。

### 3.6 新增檔案

- **`requirements.txt`**：`openai`、`pandas`、`numpy`、`tqdm`、`python-dotenv`、`requests`。
- **`.env.example`**：四角色 key／base URL／model 的完整範本。
- **`.gitignore`**：`.env`、`.venv/`、`__pycache__/`、`result/*`（保留 `.gitkeep`）。
- **`data/test.csv`**：3 筆**無害**範例（光合作用、絲路、TCP 壅塞控制），僅用於確認管線可跑；正式實驗請換成 `data/data.md` 列的 AdvBench／CLAS 2024／StrongREJECT-small。
- **`result/.gitkeep`**：確保輸出目錄存在。

---

## 4. 驗證結果

在 macOS + Python 3.15.2 下建立 `.venv` 並安裝 `requirements.txt` 後執行：

```bash
# 1) 語法檢查
python3 -m py_compile code/gen.py code/utils.py code/translate.py code/config.py
# -> OK

# 2) 無 key 的完整管線煙霧測試
cd code
python gen.py --dry_run --limit 1 --population_size 2 --max_iter 1 --overwrite --seed 0
# -> 完成 6 次嘗試，寫出 result/adv_prompt.jsonl 與 result/record.jsonl
# -> ASR: 0/1 (0.0%)（dry-run 固定 0 分，屬預期）

# 3) 缺少 key 的錯誤訊息
python gen.py --limit 1 --overwrite
# -> Configuration error:
#    Missing API key(s): GENERATOR_API_KEY, TARGET_API_KEY, JUDGE_API_KEY, TRANSLATOR_API_KEY
#    ...（清楚提示 .env / OPENAI_API_KEY）

# 4) JSONL 輸入 + 舊參數別名
python gen.py --data_format jsonl --prompts_path /tmp/sample.jsonl \
  --dry_run --limit 1 --population_size 1 --max_iter 1 --overwrite
# -> OK

# 5) 無 key 時 import 不應失敗
python -c "import config, utils, translate; print('ok')"
# -> ok（client 皆為 None）
```

**尚未驗證**：真實 LLM 端到端呼叫（需要有效 key 與網路），因此生成品質、翻譯品質與實際 ASR 數字仍以論文／原始環境為準。

---

## 5. 使用方式（最短路徑）

```bash
cd CC-BOS-main

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# 編輯 .env：至少填 OPENAI_API_KEY + OPENAI_BASE_URL，
# 或分別填 GENERATOR_/TARGET_/JUDGE_/TRANSLATOR_ 四組

cd code
python gen.py --input_file ../data/test.csv --population_size 5 --max_iter 5
```

先確認環境：

```bash
python gen.py --dry_run --limit 1 --population_size 2 --max_iter 1 --overwrite
```

---

## 6. 相容性與行為變更

- **輸出 schema 不變**，既有分析腳本可續用。
- **預設輸出目錄**由 `../result/` 改為 `<repo>/result/`；可用 `--result_dir` 指定回舊位置。
- **附加模式仍為預設**（與原版一致）；重跑前想清空請加 `--overwrite`。
- **模型預設值不變**（`deepseek-chat` / `gpt-4o`），只是改為可覆寫。
- **分數語義不變**：`score = consistency (0–100) + keyword (0 或 20)`，滿分 120；`--threshold` 預設 80。
- `API_SECRET_KEY`、`BASE_URL` 等舊變數仍存在，但新程式碼請優先用 `config` 中的四角色設定。

---

## 7. 已知限制與建議下一步

1. **`target` 欄位目前程式未使用**：README 已標註為 optional；若要做 target-guided 生成，需另外接進 prompt。
2. **翻譯與評分都是額外 LLM 呼叫**：成本約為 `population × (1 + 2 × max_iter)` 次以上；建議先用 `--limit 1` 與小 `population_size` 估成本。
3. **`environment.yml` 未改動**：它仍是 Linux/CUDA 的完整環境；macOS 請用 `requirements.txt`。若需本地模型，建議另建 `environment-local.yml`。
4. **沒有單元測試**：本次只做語法與煙霧測試；若要長期維護，建議補 `pytest` 測 `extract_content`、`get_keyword_score`、CSV 驗證與 CLI 參數。
5. **沒有重試/斷點續跑**：長時間實驗若中斷，需自行依 `record.jsonl` 的 `id` 過濾重跑。

---

## 8. 安全性聲明

此專案會自動生成對抗性提示並測試模型的越獄行為，屬**雙用途（dual-use）安全研究**。請僅在受控的學術評測、已授權的模型或本地環境中使用；不要對未授權的線上服務發動攻擊。`data/test.csv` 特意使用無害題目，避免在倉庫中散布有害內容。
