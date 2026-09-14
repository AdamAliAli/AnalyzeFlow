"""Provider selection. The AI teammate registers their class here."""

from __future__ import annotations

from app.core.config import settings
from app.core.logging import get_logger
from app.services.ai.contract import AnalyzerProvider
from app.services.ai.mock_provider import MockAnalyzerProvider

logger = get_logger(__name__)

_REGISTRY: dict[str, type] = {
    "mock": MockAnalyzerProvider,
}


def register(name: str, provider_cls: type) -> None:
    """Call this from a provider module to make it selectable via AI_PROVIDER."""
    _REGISTRY[name] = provider_cls


def _load_optional_providers() -> None:
    """Import provider modules that may not exist yet.

    These files are the AI teammate's deliverable. Until they land, the import
    fails silently and the backend runs on the mock provider.
    """
    for module_name in (
        "app.services.ai.openai_provider",
        "app.services.ai.anthropic_provider",
        "app.services.ai.openrouter_provider",
    ):
        try:
            __import__(module_name)
        except ImportError:
            continue
        except Exception:
            logger.exception("Provider module %s failed to import", module_name)


def get_provider(name: str | None = None) -> AnalyzerProvider:
    _load_optional_providers()
    key = (name or settings.ai_provider or "mock").lower()

    provider_cls = _REGISTRY.get(key)
    if provider_cls is None:
        logger.warning(
            "AI_PROVIDER=%r is not registered (available: %s). Falling back to mock.",
            key,
            ", ".join(sorted(_REGISTRY)),
        )
        provider_cls = MockAnalyzerProvider

    return provider_cls()


def available_providers() -> list[str]:
    _load_optional_providers()
    return sorted(_REGISTRY)
