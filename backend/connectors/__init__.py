"""
Pluggable Connector Interface for Observatory Global

This module provides a base interface for data source connectors
and a registry for managing available connectors.
"""

from .base import BaseConnector, NormalizedSignal
from typing import Dict, Type, List

# Registry of available connectors
_CONNECTORS: Dict[str, Type[BaseConnector]] = {}


def register_connector(name: str, connector_class: Type[BaseConnector]):
    """
    Register a connector class with a name.
    
    Args:
        name: Unique identifier for the connector (e.g., 'newsapi', 'rss')
        connector_class: The connector class to register
    """
    _CONNECTORS[name] = connector_class


def get_connector(name: str) -> BaseConnector:
    """
    Get an instance of a registered connector.
    
    Args:
        name: The connector name
    
    Returns:
        Instantiated connector
    
    Raises:
        ValueError: If connector name is not registered
    """
    if name not in _CONNECTORS:
        available = list(_CONNECTORS.keys())
        raise ValueError(
            f"Unknown connector: {name}. Available connectors: {available}"
        )
    return _CONNECTORS[name]()


def list_connectors() -> List[str]:
    """Return list of registered connector names."""
    return list(_CONNECTORS.keys())


def is_connector_available(name: str) -> bool:
    """Check if a connector is registered."""
    return name in _CONNECTORS


# Auto-register available connectors on import
# Each connector checks for required config and only registers if available

try:
    from .newsapi import NewsAPIConnector, NEWSAPI_ENABLED
    if NEWSAPI_ENABLED:
        register_connector("newsapi", NewsAPIConnector)
except ImportError:
    pass

try:
    from .rss import RSSConnector, RSS_FEEDS
    if RSS_FEEDS:
        register_connector("rss", RSSConnector)
except ImportError:
    pass

# Export public interface
__all__ = [
    'BaseConnector',
    'NormalizedSignal',
    'register_connector',
    'get_connector',
    'list_connectors',
    'is_connector_available'
]
