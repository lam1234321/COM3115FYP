"""Central configuration for CC-BOS.

Every value can be overridden with an environment variable, which is convenient
for CI or for keeping secrets out of the repository. Edit the defaults below if
you prefer to keep the settings in this file.

Environment variables
---------------------
OPENAI_API_KEY / OPENAI_BASE_URL       victim (target) model credentials
DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL   attacker model credentials
TARGET_MODEL                           victim model name           (default gpt-4o)
ATTACK_MODEL                           prompt mutation model       (default deepseek-chat)
JUDGE_MODEL                            judge model name            (default gpt-4o)
TRANSLATE_MODEL                        translator model name       (default deepseek-chat)
CCBOS_MOCK=1                           run the whole pipeline without any API calls
CCBOS_TIMEOUT                          per-request timeout seconds (default 120)
"""

import os


def _env(name: str, default: str = "") -> str:
    """Environment variable first, then the default written in this file."""
    return os.environ.get(name, default)


# ---------------------------------------------------------------------------
# Victim / target model (the model being attacked), OpenAI-compatible API
# ---------------------------------------------------------------------------
API_SECRET_KEY = _env("OPENAI_API_KEY", "")   # e.g. "sk-..."
BASE_URL = _env("OPENAI_BASE_URL", "")        # e.g. "https://api.openai.com/v1"
TARGET_MODEL = _env("TARGET_MODEL", "gpt-4o")

# ---------------------------------------------------------------------------
# Attacker model used to rewrite prompts (DeepSeek-compatible API).
# Falls back to the target credentials when no separate key is provided.
# ---------------------------------------------------------------------------
DEEPSEEK_API_KEY = _env("DEEPSEEK_API_KEY", "") or API_SECRET_KEY
DEEPSEEK_BASE_URL = _env("DEEPSEEK_BASE_URL", "") or BASE_URL
ATTACK_MODEL = _env("ATTACK_MODEL", "deepseek-chat")

# ---------------------------------------------------------------------------
# Judge and translator
# ---------------------------------------------------------------------------
JUDGE_MODEL = _env("JUDGE_MODEL", "gpt-4o")
TRANSLATE_MODEL = _env("TRANSLATE_MODEL", "deepseek-chat")

# ---------------------------------------------------------------------------
# Local model configuration (optional, not used by the default API pipeline)
# ---------------------------------------------------------------------------
LOCAL_MODEL_PATH = _env("LOCAL_MODEL_PATH", "")
DEVICE = _env("DEVICE", "cuda")

# ---------------------------------------------------------------------------
# Ollama configuration
# ---------------------------------------------------------------------------
BASE_URL_ollama = _env("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = _env("OLLAMA_MODEL", "llama3:8b")

# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------
# When true, no network request is made; deterministic mock responses are used.
MOCK_LLM = _env("CCBOS_MOCK", "0").strip().lower() in {"1", "true", "yes", "on"}
REQUEST_TIMEOUT = float(_env("CCBOS_TIMEOUT", "120"))
