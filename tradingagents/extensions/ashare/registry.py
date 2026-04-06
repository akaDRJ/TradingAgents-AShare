"""Provider registry for A-share extension.

Allows registration and lookup of data provider implementations.
Providers are organized by name and capability.
"""

from typing import Any, Callable, Dict, Optional, Set


class ProviderRegistry:
    """Registry of data provider implementations keyed by provider name."""

    def __init__(self) -> None:
        # provider_name -> method_name -> callable
        self._providers: Dict[str, Dict[str, Callable]] = {}
        # provider_name -> set of method names it provides
        self._provider_methods: Dict[str, Set[str]] = {}

    def register(self, provider: str, method: str, func: Callable) -> None:
        """Register a provider's method implementation.

        Args:
            provider: Provider name (e.g. "tushare", "akshare")
            method: Method name (e.g. "get_stock_data")
            func: Callable implementation
        """
        if provider not in self._providers:
            self._providers[provider] = {}
            self._provider_methods[provider] = set()
        self._providers[provider][method] = func
        self._provider_methods[provider].add(method)

    def get(self, provider: str, method: str) -> Optional[Callable]:
        """Get a provider's implementation for a method.

        Returns:
            Callable or None if not registered
        """
        return self._providers.get(provider, {}).get(method)

    def list_providers(self) -> list[str]:
        """List all registered provider names."""
        return list(self._providers.keys())

    def list_methods(self, provider: str) -> list[str]:
        """List all methods registered for a provider."""
        return list(self._provider_methods.get(provider, set()))

    def has_provider(self, provider: str) -> bool:
        """Check if a provider is registered."""
        return provider in self._providers


# Global registry instance
_global_registry = ProviderRegistry()


def get_registry() -> ProviderRegistry:
    """Return the global provider registry."""
    return _global_registry


def register_provider(provider: str, method: str, func: Callable) -> None:
    """Register a provider method in the global registry."""
    _global_registry.register(provider, method, func)
