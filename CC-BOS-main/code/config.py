# Configuration
#
# All values are read from environment variables. If a `.env` file exists in
# this directory (or any parent directory), it is loaded automatically.
# Copy `.env.example` to `.env` and fill in your credentials.
#
# The defaults below make the project work with a single OpenAI-compatible
# provider: every role (generator / translator / target / judge) falls back to
# OPENAI_API_KEY unless a dedicated key is provided.

import os

try:  # python-dotenv is optional; a missing dependency must not break setup
    from dotenv import load_dotenv

    _here = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(_here, ".env"))
    load_dotenv(os.path.join(_here, "..", ".env"))
except ImportError:  # pragma: no cover - exercised only without dotenv
    pass


def _env(*names, default=""):
    """Return the first non-empty environment variable among *names*."""
    for name in names:
        value = os.getenv(name)
        if value:
            return value.strip()
    return default


# ---------------------------------------------------------------------------
# Primary provider (target model + judge). Any OpenAI-compatible endpoint.
# ---------------------------------------------------------------------------
API_SECRET_KEY = _env("OPENAI_API_KEY", "API_SECRET_KEY")
BASE_URL = _env("OPENAI_BASE_URL", "BASE_URL", default="https://api.openai.com/v1")

# ---------------------------------------------------------------------------
# Generator / translator provider. Defaults to DeepSeek but may be any
# OpenAI-compatible endpoint. If the key is empty, the primary provider is
# used with GENERATOR_MODEL / TRANSLATOR_MODEL instead.
# ---------------------------------------------------------------------------
DEEPSEEK_API_KEY = _env("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = _env(
    "DEEPSEEK_BASE_URL", default="https://api.deepseek.com/v1"
)

# ---------------------------------------------------------------------------
# Model names
# ---------------------------------------------------------------------------
TARGET_MODEL = _env("TARGET_MODEL", default="gpt-4o")
JUDGE_MODEL = _env("JUDGE_MODEL", default=TARGET_MODEL)
GENERATOR_MODEL = _env("GENERATOR_MODEL", default="deepseek-chat")
TRANSLATOR_MODEL = _env("TRANSLATOR_MODEL", default="deepseek-chat")

# ---------------------------------------------------------------------------
# Optional local / Ollama inference
# ---------------------------------------------------------------------------
LOCAL_MODEL_PATH = _env("LOCAL_MODEL_PATH")
DEVICE = _env("DEVICE", default="cuda")
BASE_URL_ollama = _env("OLLAMA_BASE_URL", default="http://localhost:11434/v1")
OLLAMA_MODEL = _env("OLLAMA_MODEL", default="llama3:8b")


def validate():
    """Return a list of human readable configuration problems.

    An empty list means the project is ready to run.
    """
    problems = []
    if not API_SECRET_KEY:
        problems.append(
            "OPENAI_API_KEY is not set (needed for the target model and the judge)."
        )
    if not TARGET_MODEL:
        problems.append("TARGET_MODEL is empty.")
    if not JUDGE_MODEL:
        problems.append("JUDGE_MODEL is empty.")
    if not GENERATOR_MODEL:
        problems.append("GENERATOR_MODEL is empty.")
    if not TRANSLATOR_MODEL:
        problems.append("TRANSLATOR_MODEL is empty.")
    return problems


def describe():
    """Return a short, secret-free summary of the active configuration."""
    generator = (
        f"{GENERATOR_MODEL} @ {DEEPSEEK_BASE_URL}"
        if DEEPSEEK_API_KEY
        else f"{GENERATOR_MODEL} @ {BASE_URL} (fallback to OPENAI_API_KEY)"
    )
    return "\n".join(
        [
            f"  target model : {TARGET_MODEL} @ {BASE_URL}",
            f"  judge model  : {JUDGE_MODEL} @ {BASE_URL}",
            f"  generator    : {generator}",
            f"  translator   : {TRANSLATOR_MODEL}",
        ]
    )
