"""NLP processing for topic extraction and analysis."""

import logging
import hashlib
from typing import List, Dict, Any
from collections import Counter
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import numpy as np

try:
    from langdetect import detect, LangDetectException
except ImportError:
    detect = None
    LangDetectException = Exception

from app.models.schemas import Topic

logger = logging.getLogger(__name__)


class NLPProcessor:
    """NLP processor for analyzing and extracting topics from text data."""

    def __init__(self):
        self.min_topic_length = 3
        self.max_topic_length = 100

    def process_and_extract_topics(
        self,
        items: List[Dict[str, Any]],
        limit: int = 10
    ) -> List[Topic]:
        """
        Process items and extract topics using NLP techniques.

        Args:
            items: List of items with 'title', 'source', and 'count' fields
            limit: Maximum number of topics to return

        Returns:
            List of Topic objects
        """
        if not items:
            return []

        try:
            # Step 1: Clean and deduplicate titles
            processed_items = self._clean_and_deduplicate(items)

            # Step 2: Detect language for each item
            for item in processed_items:
                item['language'] = self._detect_language(item['title'])

            # Step 3: Extract keywords and cluster similar topics
            topics = self._extract_topics_with_clustering(processed_items, limit)

            return topics

        except Exception as e:
            logger.error(f"Error processing topics: {e}", exc_info=True)
            # Return simple fallback
            return self._simple_topic_extraction(items, limit)

    def _clean_and_deduplicate(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Clean titles and remove duplicates."""
        seen_titles = set()
        cleaned = []

        for item in items:
            title = item.get('title', '').strip()

            # Basic cleaning
            title = re.sub(r'\s+', ' ', title)
            title = title[:self.max_topic_length]

            if len(title) < self.min_topic_length:
                continue

            # Normalize for deduplication
            normalized = title.lower()

            if normalized not in seen_titles:
                seen_titles.add(normalized)
                item['title'] = title
                cleaned.append(item)

        return cleaned

    def _detect_language(self, text: str) -> str:
        """Detect language of text."""
        if detect is None:
            return "unknown"

        try:
            return detect(text)
        except (LangDetectException, Exception):
            return "unknown"

    def _extract_topics_with_clustering(
        self,
        items: List[Dict[str, Any]],
        limit: int
    ) -> List[Topic]:
        """Extract topics using TF-IDF and clustering."""
        if len(items) < 3:
            return self._simple_topic_extraction(items, limit)

        try:
            # Extract titles
            titles = [item['title'] for item in items]

            # TF-IDF vectorization
            vectorizer = TfidfVectorizer(
                max_features=100,
                ngram_range=(1, 3),
                stop_words='english',
                min_df=1,
            )

            tfidf_matrix = vectorizer.fit_transform(titles)

            # Determine optimal number of clusters
            n_clusters = min(limit, len(items) // 2, 10)
            n_clusters = max(n_clusters, 1)

            # K-means clustering
            if n_clusters > 1:
                kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                cluster_labels = kmeans.fit_predict(tfidf_matrix)
            else:
                cluster_labels = np.zeros(len(items))

            # Group items by cluster
            clusters = {}
            for idx, label in enumerate(cluster_labels):
                if label not in clusters:
                    clusters[label] = []
                clusters[label].append(items[idx])

            # Create topics from clusters
            topics = []
            for cluster_id, cluster_items in clusters.items():
                # Get most representative title (highest count)
                cluster_items.sort(key=lambda x: x.get('count', 0), reverse=True)
                main_item = cluster_items[0]

                # Extract label (use most common keywords)
                label = self._extract_cluster_label(cluster_items)

                # Aggregate counts
                total_count = sum(item.get('count', 0) for item in cluster_items)

                # Get sample titles
                sample_titles = [item['title'] for item in cluster_items[:3]]

                # Get sources
                sources = list(set(item['source'] for item in cluster_items))

                # Calculate confidence (based on cluster size and coherence)
                confidence = min(0.95, 0.5 + (len(cluster_items) / len(items)) * 0.5)

                topic = Topic(
                    id=f"topic-{hashlib.md5(label.encode()).hexdigest()[:8]}",
                    label=label,
                    count=total_count,
                    sample_titles=sample_titles,
                    sources=sources,
                    confidence=round(confidence, 2),
                )

                topics.append(topic)

            # Sort by count and limit
            topics.sort(key=lambda x: x.count, reverse=True)
            return topics[:limit]

        except Exception as e:
            logger.error(f"Error in clustering: {e}")
            return self._simple_topic_extraction(items, limit)

    def _extract_cluster_label(self, cluster_items: List[Dict[str, Any]]) -> str:
        """Extract a representative label for a cluster."""
        # Use the title of the item with highest count
        if cluster_items:
            return cluster_items[0]['title']
        return "Unknown Topic"

    def _simple_topic_extraction(
        self,
        items: List[Dict[str, Any]],
        limit: int
    ) -> List[Topic]:
        """Simple topic extraction fallback without clustering."""
        topics = []

        # Group by title and aggregate
        title_groups = {}
        for item in items:
            title = item.get('title', '').strip()
            if title not in title_groups:
                title_groups[title] = {
                    'count': 0,
                    'sources': set(),
                    'titles': []
                }
            title_groups[title]['count'] += item.get('count', 1)
            title_groups[title]['sources'].add(item.get('source', 'unknown'))
            title_groups[title]['titles'].append(title)

        # Convert to topics
        for title, data in sorted(
            title_groups.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )[:limit]:
            topic = Topic(
                id=f"topic-{hashlib.md5(title.encode()).hexdigest()[:8]}",
                label=title,
                count=data['count'],
                sample_titles=data['titles'][:3],
                sources=list(data['sources']),
                confidence=0.75,
            )
            topics.append(topic)

        return topics
