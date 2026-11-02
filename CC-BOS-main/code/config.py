"""Central configuration for CC-BOS.

Every setting can be supplied through environment variables (a ``.env`` file in
the repository root is loaded automatically when ``python-dotenv`` is
installed).  Resolution order is:

    1. provider-specific variable, e.g. ``GENERATOR_API_KEY``
    2. shared fallback, ``OPENAI_API_KEY`` / ``OPENAI_BASE_URL``
    3. default value in this file

Copy ``.env.example`` to ``.env`` and fill in the keys you actually use.
"""

from __future__ import annotations

import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

try:  # optional dependency
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env")
except ImportError:  # pragma: no cover - dotenv is optional
    pass


def _env(name: str, default: str = "") -> str:
    """Read an environment variable, treating blank strings as unset."""
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip()


DEFAULT_API_KEY = _env("OPENAI_API_KEY")
DEFAULT_BASE_URL = _env("OPENAI_BASE_URL")


def _service(prefix: str, default_model: str) -> dict:
    return {
        "api_key": _env(f"{prefix}_API_KEY", DEFAULT_API_KEY),
        "base_url": _env(f"{prefix}_BASE_URL", DEFAULT_BASE_URL),
        "model": _env(f"{prefix}_MODEL", default_model),
    }


# ---------------------------------------------------------------------------
# The four roles played by LLMs in the pipeline
# ---------------------------------------------------------------------------
# Generator : rewrites the query into Classical Chinese using the 8 dimensions
# Target    : the model under test (receives the adversarial prompt)
# Judge     : scores the target response (0-5 rubric)
# Translator: translates Classical Chinese back to English for the judge
GENERATOR = _service("GENERATOR", "deepseek-chat")
TARGET = _service("TARGET", "gpt-4o")
JUDGE = _service("JUDGE", "gpt-4o")
TRANSLATOR = _service("TRANSLATOR", "deepseek-chat")

# Flat aliases (handy for scripts and for backwards compatibility)
GENERATOR_API_KEY = GENERATOR["api_key"]
GENERATOR_BASE_URL = GENERATOR["base_url"]
GENERATOR_MODEL = GENERATOR["model"]

TARGET_API_KEY = TARGET["api_key"]
TARGET_BASE_URL = TARGET["base_url"]
TARGET_MODEL = TARGET["model"]

JUDGE_API_KEY = JUDGE["api_key"]
JUDGE_BASE_URL = JUDGE["base_url"]
JUDGE_MODEL = JUDGE["model"]

TRANSLATOR_API_KEY = TRANSLATOR["api_key"]
TRANSLATOR_BASE_URL = TRANSLATOR["base_url"]
TRANSLATOR_MODEL = TRANSLATOR["model"]

# Names used by the original release; kept so existing imports keep working.
API_SECRET_KEY = TRANSLATOR_API_KEY or DEFAULT_API_KEY
BASE_URL = TRANSLATOR_BASE_URL or DEFAULT_BASE_URL

# ---------------------------------------------------------------------------
# Local / Ollama backends (only needed for the "ollama" / local code paths)
# ---------------------------------------------------------------------------
LOCAL_MODEL_PATH = _env("LOCAL_MODEL_PATH")
DEVICE = _env("DEVICE", "cuda")
BASE_URL_ollama = _env("OLLAMA_BASE_URL")
OLLAMA_MODEL = _env("OLLAMA_MODEL", "llama3:8b")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
RESULT_DIR = _env("RESULT_DIR", str(_ROOT / "result"))
DEFAULT_DATA_PATH = str(_ROOT / "data" / "test.csv")


def validate(required=("generator", "target", "judge", "translator")) -> None:
    """Raise a readable error when a required API key is missing."""
    services = {
        "generator": (GENERATOR, "GENERATOR_API_KEY"),
        "target": (TARGET, "TARGET_API_KEY"),
        "judge": (JUDGE, "JUDGE_API_KEY"),
        "translator": (TRANSLATOR, "TRANSLATOR_API_KEY"),
    }

    missing = [
        env_name
        for name in required
        for service, env_name in [services[name]]
        if not service["api_key"]
    ]

    if not missing:
        return

    raise RuntimeError(
        "Missing API key(s): "
        + ", ".join(missing)
        + "\n\nSet them in a .env file at the repository root (see .env.example), "
        "or export them in your shell. A single OPENAI_API_KEY can be used for "
        "every role, in which case the per-role variables can be left empty."
    )
