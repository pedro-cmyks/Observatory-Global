"""
Story Summarization with Citations

Optional LLM-based summarization that is:
- Disabled by default
- Always grounded in source content
- Returns citations to source URLs
"""

import os
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Feature flag - only enable if explicitly set
LLM_ENABLED = os.getenv("ENABLE_LLM_SUMMARY", "false").lower() == "true"
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
LLM_API_KEY = os.getenv("OPENAI_API_KEY", "")


def is_summarization_enabled() -> bool:
    """Check if LLM summarization is enabled."""
    return LLM_ENABLED and bool(LLM_API_KEY)


async def summarize_story_cluster(
    signals: List[Dict],
    max_signals: int = 5
) -> Dict:
    """
    Generate a summary of related signals using LLM.
    
    The LLM is ONLY a summarizer - it does not determine truth or importance.
    All output includes citations to source URLs.
    
    Args:
        signals: List of signal dicts with 'source_url', 'title', 'snippet' keys
        max_signals: Maximum signals to include in context
    
    Returns:
        Dict with:
        - summary: Generated summary text (or None if disabled)
        - citations: List of source URLs used
        - method: 'llm_grounded', 'disabled', or 'error'
    """
    # Get source URLs for citations
    context_signals = signals[:max_signals]
    citations = [s.get("source_url") for s in context_signals if s.get("source_url")]
    
    # Check if LLM is enabled
    if not is_summarization_enabled():
        return {
            "summary": None,
            "citations": citations,
            "method": "disabled",
            "message": "LLM summarization is disabled. Set ENABLE_LLM_SUMMARY=true to enable."
        }
    
    # Build context from signals
    context_parts = []
    for i, s in enumerate(context_signals):
        title = s.get('title', 'Untitled')
        snippet = s.get('snippet', s.get('source_url', 'No content'))
        source = s.get('source_url', 'Unknown source')
        context_parts.append(f"[{i+1}] {title}\nSource: {source}\n{snippet[:300]}")
    
    context_text = "\n\n".join(context_parts)
    
    prompt = f"""Summarize the following news coverage in 2-3 sentences.
You MUST cite sources using [1], [2], etc. notation corresponding to the source numbers below.
Do NOT add information not present in the sources.
Do NOT make judgments about truth, accuracy, or importance.
Only describe what the sources report.

Sources:
{context_text}

Summary with citations:"""

    try:
        # Only import if needed
        import openai
        
        client = openai.AsyncOpenAI(api_key=LLM_API_KEY)
        
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a neutral news summarizer. Always cite sources with [N] notation. Never add information beyond what sources provide."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.3
        )
        
        summary = response.choices[0].message.content.strip()
        
        return {
            "summary": summary,
            "citations": citations,
            "method": "llm_grounded",
            "model": LLM_MODEL
        }
        
    except ImportError:
        logger.warning("OpenAI package not installed")
        return {
            "summary": None,
            "citations": citations,
            "method": "error",
            "message": "OpenAI package not installed"
        }
    except Exception as e:
        logger.error(f"LLM summarization error: {e}")
        return {
            "summary": None,
            "citations": citations,
            "method": "error",
            "message": str(e)
        }


def create_simple_summary(signals: List[Dict]) -> str:
    """
    Create a simple non-LLM summary from signal titles.
    
    Fallback for when LLM is disabled.
    """
    if not signals:
        return "No signals available."
    
    titles = [s.get('title') for s in signals[:3] if s.get('title')]
    
    if not titles:
        themes = []
        for s in signals[:3]:
            if s.get('themes'):
                themes.extend(s['themes'][:2])
        if themes:
            return f"Coverage includes: {', '.join(set(themes[:5]))}"
        return f"Coverage from {len(signals)} sources."
    
    return " | ".join(titles)


# Tooltip for UI
SUMMARIZATION_TOOLTIP = """
Story Summarization

When enabled, uses AI to create brief summaries of related news coverage.

Important notes:
• Summarization is DISABLED by default
• Summaries always include source citations [1], [2], etc.
• The AI only describes what sources report - it does not verify truth
• Click citations to view original sources

To enable: Set ENABLE_LLM_SUMMARY=true in environment
""".strip()
