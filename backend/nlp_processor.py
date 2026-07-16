"""
NLP pipeline loader.

Imports the full pipeline (backend.nlp_processor_full) when the optional ML
dependencies are installed, and otherwise exposes NLP_AVAILABLE = False so
the API can report the feature as unavailable instead of silently returning
placeholder data.

Install the optional dependencies with:  pip install -r requirements-ml.txt
"""
from .logger import logger

NLP_AVAILABLE: bool
NLP_UNAVAILABLE_REASON: str = ""

try:
    from .nlp_processor_full import NLPPipeline  # noqa: F401
    NLP_AVAILABLE = True
    logger.info("Full NLP pipeline available")
except ImportError as e:
    NLP_AVAILABLE = False
    NLP_UNAVAILABLE_REASON = str(e)
    logger.warning(
        f"ML dependencies not installed — NLP features disabled ({e}). "
        "Install them with: pip install -r requirements-ml.txt"
    )

    class NLPPipeline:  # type: ignore[no-redef]
        """Placeholder that refuses to run; the API returns 503 before reaching this."""

        def __init__(self):
            raise RuntimeError(
                f"NLP pipeline unavailable: {NLP_UNAVAILABLE_REASON}. "
                "Install ML dependencies with: pip install -r requirements-ml.txt"
            )
