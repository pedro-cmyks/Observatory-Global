# ADR-0002: Information Flow Heat Formula

**Status**: Accepted
**Date**: 2025-01-12
**Decision Makers**: Pedro Villegas, Development Team
**Tags**: algorithm, nlp, visualization

## Context

Observatory Global needs to detect and visualize "information flow" between countries - when similar topics trend in multiple locations over time. This is the core "Waze-like" feature that shows how narratives propagate globally.

We need to define:
1. How to measure topic similarity between countries
2. How to weight temporal proximity (recent flows are "hotter")
3. What threshold to use for filtering noise
4. How to visualize flow intensity

## Decision

### Heat Formula

```python
heat = similarity_score × time_decay_factor
```

Where:
- **similarity_score**: TF-IDF cosine similarity ∈ [0, 1]
- **time_decay_factor**: `exp(-Δt / HALFLIFE)` where Δt = hours between topic appearances

### Components

#### 1. Similarity Score (Spatial Dimension)

**Method**: TF-IDF + Cosine Similarity

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def calculate_similarity(topics_country_A, topics_country_B):
    """
    topics_country_A: ["election results", "climate summit", ...]
    topics_country_B: ["election outcomes", "UN climate talks", ...]
    """
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(topics_country_A + topics_country_B)

    similarity_matrix = cosine_similarity(
        tfidf_matrix[:len(topics_country_A)],
        tfidf_matrix[len(topics_country_A):]
    )

    # Maximum similarity between any pair of topics
    return float(similarity_matrix.max())
```

**Why TF-IDF over simple keyword matching**:
- Captures semantic similarity ("election results" ≈ "election outcomes")
- Handles multi-word phrases (bigrams)
- Reduces weight of common words ("the", "of", etc.)
- Industry standard, well-tested

#### 2. Time Decay (Temporal Dimension)

**Half-Life**: 6 hours

```python
import math

HEAT_HALFLIFE_HOURS = 6  # Configurable via env var

def time_decay_factor(delta_hours):
    """
    Exponential decay: heat drops to 50% after HALFLIFE hours
    """
    return math.exp(-delta_hours / HEAT_HALFLIFE_HOURS)
```

**Examples**:
| Δt | Decay Factor | Heat (if similarity = 0.8) |
|----|--------------|----------------------------|
| 0h | 1.00 | 0.80 (very hot) |
| 3h | 0.61 | 0.49 (warm) |
| 6h | 0.37 | 0.30 (cooling) |
| 12h | 0.14 | 0.11 (cold) |
| 24h | 0.02 | 0.01 (nearly extinct) |

**Why 6-hour half-life**:
- Balances recency vs. historical context
- Most news cycles operate on 6-12 hour windows
- Flows older than 24h are effectively invisible (< 2% heat)
- Too short (1h): only captures simultaneous events, misses propagation
- Too long (24h): everything looks connected, no actionable insight

#### 3. Flow Threshold

**Minimum Heat**: 0.5 (configurable)

```python
FLOW_THRESHOLD = 0.5  # Only show flows with heat >= 0.5
```

**Interpretation**:
- `heat >= 0.8`: 🔥 **Very hot** - likely direct propagation or shared event
- `heat >= 0.6`: 🟠 **Hot** - strong similarity, recent timing
- `heat >= 0.5`: 🟡 **Warm** - moderate similarity, still relevant
- `heat < 0.5`: ❄️ **Cold** - filtered out as noise

**Why 0.5 threshold**:
- Filters random coincidences (low similarity OR old timing)
- Keeps ~20-30% of potential flows in typical testing
- User can adjust via API: `GET /v1/flows?threshold=0.7`

### Complete Example

**Scenario**: US trends "election fraud claims" at 10:00 AM. Colombia trends "election fraud allegations" at 1:00 PM (3 hours later).

```python
# Step 1: Calculate similarity
topics_US = ["election fraud claims", "voting irregularities", ...]
topics_CO = ["election fraud allegations", "vote counting issues", ...]

similarity = calculate_similarity(topics_US, topics_CO)
# Result: 0.87 (very high - same semantic meaning)

# Step 2: Calculate time decay
delta_hours = 3
decay = exp(-3 / 6) = 0.61

# Step 3: Final heat
heat = 0.87 × 0.61 = 0.53

# Result: 🟡 Warm flow (heat = 0.53 > threshold 0.5)
# Visualization: Medium-thick orange arc from US → CO
```

## Consequences

### Positive
- ✅ **Interpretable**: Heat score [0,1] maps naturally to colors/thickness
- ✅ **Tunable**: Three parameters (similarity method, half-life, threshold) for fine-tuning
- ✅ **Mathematically sound**: Exponential decay is standard in physics, epidemiology
- ✅ **Efficient**: Cosine similarity is O(n) with sparse matrices
- ✅ **Testable**: Clear formula, reproducible results

### Negative
- ⚠️ **Directionality ambiguous**: High heat doesn't prove A→B causality, only correlation
- ⚠️ **Language barriers**: TF-IDF works poorly across different languages (e.g., US English → Brazil Portuguese)
- ⚠️ **False positives**: Coincidental events look like flows (e.g., natural disasters)
- ⚠️ **Computational cost**: Comparing all country pairs = O(n²) operations

### Mitigations
1. **Directionality**: Assign flow direction as earlier_country → later_country (heuristic)
2. **Language**: Use Google Translate API for cross-language similarity (post-MVP)
3. **False positives**: Add metadata filter (e.g., exclude disaster/weather keywords)
4. **Performance**: Cache similarity matrix for 15min, only recalculate on new data

## Alternatives Considered

### 1. Simple Keyword Overlap
```python
heat = len(set(topics_A) & set(topics_B)) / len(set(topics_A) | set(topics_B))
```
**Rejected**: Misses semantic similarity. "election" vs. "vote" = 0 similarity.

### 2. Linear Time Decay
```python
decay = max(0, 1 - delta_hours / 24)
```
**Rejected**: Unrealistic - real-world propagation follows exponential curves.

### 3. Fixed Time Window (No Decay)
```python
heat = similarity if delta_hours < 6 else 0
```
**Rejected**: Too binary. Loses nuance (3h flow vs. 5h flow treated differently).

### 4. Levenshtein Distance
**Rejected**: Character-level distance irrelevant for semantic meaning.

### 5. BERT Embeddings + Cosine Similarity
**Accepted for future**: Better semantic understanding, but requires GPU and increases latency. Revisit in Iteration 2.

## Implementation Notes

### Environment Variables
```bash
HEAT_HALFLIFE_HOURS=6
FLOW_THRESHOLD=0.5
USE_BERT_EMBEDDINGS=false  # Future enhancement
SIMILARITY_CACHE_TTL_SECONDS=900  # 15 minutes
```

### Database Schema
```sql
CREATE TABLE flows (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    from_country VARCHAR(2) NOT NULL,
    to_country VARCHAR(2) NOT NULL,
    heat FLOAT NOT NULL CHECK (heat >= 0 AND heat <= 1),
    similarity_score FLOAT NOT NULL,
    time_delta_hours FLOAT NOT NULL,
    shared_topics JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_flows_heat ON flows(heat DESC);
CREATE INDEX idx_flows_countries ON flows(from_country, to_country);
CREATE INDEX idx_flows_timestamp ON flows(timestamp DESC);
```

### API Response Format
```json
{
  "flows": [
    {
      "from_country": "US",
      "to_country": "CO",
      "heat": 0.53,
      "similarity_score": 0.87,
      "time_delta_hours": 3,
      "shared_topics": [
        {"label": "election fraud claims", "from_count": 45, "to_count": 23}
      ],
      "direction_confidence": "medium"
    }
  ],
  "metadata": {
    "formula": "heat = similarity × exp(-Δt / 6h)",
    "threshold": 0.5,
    "total_flows": 47,
    "filtered_flows": 22
  }
}
```

## Validation Plan

### Metrics to Track
1. **Distribution of heat scores**: Histogram to verify threshold is reasonable
2. **Flow count per time window**: Ensure not too sparse (<5) or dense (>100)
3. **User feedback**: Do visualized flows match intuition of real-world events?

### A/B Testing (Post-MVP)
- Test half-life: 3h vs. 6h vs. 12h
- Test threshold: 0.4 vs. 0.5 vs. 0.6
- Measure: User engagement (clicks, time on map, filter usage)

## References
- [TF-IDF Explained](https://en.wikipedia.org/wiki/Tf%E2%80%93idf)
- [Cosine Similarity for Text](https://scikit-learn.org/stable/modules/metrics.html#cosine-similarity)
- [Exponential Decay in Information Diffusion](https://arxiv.org/abs/1906.01293)
- [Half-Life of News on Social Media](https://www.journalism.org/2016/05/26/news-use-across-social-media-platforms-2016/)

## Review Date
**2025-02-12** (30 days) - Reassess after:
- Collecting heat score distributions from production data
- User feedback on flow visualization
- Performance profiling of similarity calculations
- Experimenting with BERT embeddings on subset of data
