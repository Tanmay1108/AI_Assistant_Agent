from typing import Any, Dict, Optional

from core.config import settings

# from .claude_provider import ClaudeProvider
from .base import BaseAIProvider
from .openai_provider import OpenAIProvider


class AIProviderRouter:
    def __init__(self):
        self.providers: Dict[str, BaseAIProvider] = {}

        if settings.OPENAI_API_KEY:
            self.providers["openai"] = OpenAIProvider()
        # if settings.ANTHROPIC_API_KEY:
        #     self.providers["claude"] = ClaudeProvider()

        self.default_provider = settings.DEFAULT_AI_PROVIDER

    def get_provider(self, provider_name: Optional[str] = None) -> BaseAIProvider:
        provider_name = provider_name or self.default_provider

        if provider_name not in self.providers:
            raise ValueError(f"AI provider '{provider_name}' is not configured")

        return self.providers[provider_name]

    async def process_with_fallback(self, method_name: str, *args, **kwargs):
        """Try primary provider, fallback to secondary if available"""
        primary_provider = self.get_provider()

        try:
            method = getattr(primary_provider, method_name)
            return await method(*args, **kwargs)
        except Exception as e:
            # Try fallback provider if available
            fallback_providers = [
                name for name in self.providers.keys() if name != self.default_provider
            ]

            for fallback_name in fallback_providers:
                try:
                    fallback_provider = self.get_provider(fallback_name)
                    method = getattr(fallback_provider, method_name)
                    return await method(*args, **kwargs)
                except Exception:
                    continue

            # If all providers fail, raise original exception
            raise e
