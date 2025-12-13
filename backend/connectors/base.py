"""
Base Connector Interface

Defines the abstract interface that all data source connectors must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, AsyncIterator, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class NormalizedSignal:
    """
    Normalized signal format that all connectors must produce.
    
    This is the common data structure used across the system,
    regardless of the original data source.
    """
    source_url: str
    source_domain: str
    title: str
    snippet: str
    published_at: datetime
    country_codes: List[str] = field(default_factory=list)
    themes: List[str] = field(default_factory=list)
    persons: List[str] = field(default_factory=list)
    sentiment: float = 0.0
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            'source_url': self.source_url,
            'source_name': self.source_domain,
            'title': self.title,
            'snippet': self.snippet,
            'timestamp': self.published_at,
            'country_code': self.country_codes[0] if self.country_codes else None,
            'themes': self.themes,
            'persons': self.persons,
            'sentiment': self.sentiment
        }


class BaseConnector(ABC):
    """
    Base interface for all data source connectors.
    
    Each connector is responsible for:
    1. Fetching raw data from its source
    2. Normalizing data to the NormalizedSignal format
    3. Handling its own errors and rate limiting
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this connector."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of the data source."""
        pass
    
    @abstractmethod
    async def fetch(self, since: datetime) -> AsyncIterator[Dict[str, Any]]:
        """
        Fetch raw data from the source.
        
        Args:
            since: Only fetch items published after this time
        
        Yields:
            Raw data dictionaries from the source
        """
        pass
    
    @abstractmethod
    def normalize(self, raw: Dict[str, Any]) -> NormalizedSignal:
        """
        Convert raw data to normalized signal format.
        
        Args:
            raw: Raw data dictionary from fetch()
        
        Returns:
            NormalizedSignal instance
        
        Raises:
            ValueError: If the raw data cannot be normalized
        """
        pass
    
    async def ingest(self, since: datetime) -> List[NormalizedSignal]:
        """
        Fetch and normalize all signals since the given time.
        
        This is the main entry point for using a connector.
        Handles errors gracefully - logs but doesn't fail on individual items.
        
        Args:
            since: Only fetch items published after this time
        
        Returns:
            List of normalized signals
        """
        signals = []
        errors = 0
        
        async for raw in self.fetch(since):
            try:
                signal = self.normalize(raw)
                signals.append(signal)
            except ValueError as e:
                errors += 1
                # Log but don't fail the entire batch
                pass
            except Exception as e:
                errors += 1
                pass
        
        return signals
    
    def is_configured(self) -> bool:
        """
        Check if the connector is properly configured.
        
        Override this to check for required API keys, URLs, etc.
        """
        return True
    
    def get_config(self) -> Dict[str, str]:
        """
        Return the connector's configuration for debugging.
        
        Should NOT include sensitive values like API keys.
        """
        return {
            "name": self.name,
            "description": self.description,
            "configured": self.is_configured()
        }
