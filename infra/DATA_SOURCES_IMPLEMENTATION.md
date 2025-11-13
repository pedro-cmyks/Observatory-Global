# Quick Start: Data Collection Implementation for Top 3 Sources

## 1. Hacker News Firebase API

### Endpoint
```
Base URL: https://hacker-news.firebaseio.com/v0
```

### Key Endpoints
- `/topstories.json` - Top 500 story IDs
- `/newstories.json` - New 500 story IDs
- `/item/{id}.json` - Individual story/comment
- `/updates.json` - Changed items
- `/user/{username}.json` - User profile

### Quick Python Implementation
```python
import requests
import time
from datetime import datetime

class HNCollector:
    BASE_URL = "https://hacker-news.firebaseio.com/v0"
    
    def fetch_top_stories(self, limit=30):
        """Get top stories metadata"""
        stories_resp = requests.get(f"{self.BASE_URL}/topstories.json")
        story_ids = stories_resp.json()[:limit]
        
        stories = []
        for sid in story_ids:
            item = requests.get(f"{self.BASE_URL}/item/{sid}.json").json()
            if item:
                stories.append({
                    'id': item.get('id'),
                    'title': item.get('title'),
                    'score': item.get('score'),
                    'time': datetime.fromtimestamp(item.get('time', 0)),
                    'url': item.get('url'),
                    'comments': item.get('descendants', 0),
                    'type': item.get('type')
                })
        return stories
    
    def fetch_story_comments(self, story_id, max_depth=2):
        """Fetch comment thread for story"""
        item = requests.get(f"{self.BASE_URL}/item/{story_id}.json").json()
        comments = []
        
        def recurse_comments(kid_ids, depth=0):
            if depth > max_depth or not kid_ids:
                return
            for kid_id in kid_ids[:5]:  # Limit for demo
                kid = requests.get(f"{self.BASE_URL}/item/{kid_id}.json").json()
                if kid:
                    comments.append({
                        'id': kid.get('id'),
                        'text': kid.get('text'),
                        'score': kid.get('score'),
                        'author': kid.get('by'),
                        'time': datetime.fromtimestamp(kid.get('time', 0))
                    })
                    if kid.get('kids'):
                        recurse_comments(kid.get('kids'), depth+1)
        
        if item.get('kids'):
            recurse_comments(item.get('kids'))
        
        return comments

# Usage
collector = HNCollector()
stories = collector.fetch_top_stories(10)
for story in stories:
    print(f"{story['title']} ({story['score']} points, {story['comments']} comments)")
```

### Rate Limiting Strategy
- Poll topstories every 15-30 seconds
- Batch API calls where possible
- Use exponential backoff for 429/500 errors
- No authentication required

### Data Storage Schema
```sql
CREATE TABLE hn_stories (
    id INTEGER PRIMARY KEY,
    title TEXT,
    url TEXT,
    score INTEGER,
    author TEXT,
    time TIMESTAMP,
    descendants INTEGER,
    collected_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE hn_comments (
    id INTEGER PRIMARY KEY,
    story_id INTEGER,
    text TEXT,
    author TEXT,
    score INTEGER,
    time TIMESTAMP,
    parent_id INTEGER,
    FOREIGN KEY (story_id) REFERENCES hn_stories(id)
);
```

---

## 2. Mastodon/Fediverse Public API

### Endpoints (per instance)
```
Base URL: https://{instance}/api/v1
Examples: mastodon.social, techhub.social, pixelfed.social
```

### Key Endpoints
- `/timelines/public` - Public timeline (paginated)
- `/timelines/public?local=true` - Local instance timeline
- `/trends/statuses` - Trending statuses
- `/trends/tags` - Trending hashtags
- `/streaming/public` - WebSocket streaming (real-time)
- `/streaming/public/local` - Local streaming

### Quick Python Implementation
```python
import requests
import json
from datetime import datetime
import websocket

class MastodonCollector:
    def __init__(self, instances=None):
        self.instances = instances or [
            'mastodon.social',
            'techhub.social',
            'pixelfed.social'
        ]
        self.base_url_template = "https://{}/api/v1"
    
    def fetch_public_timeline(self, instance, limit=40):
        """Fetch public timeline from instance"""
        url = f"{self.base_url_template.format(instance)}/timelines/public"
        try:
            resp = requests.get(url, params={'limit': limit}, timeout=10)
            statuses = resp.json()
            
            posts = []
            for status in statuses:
                posts.append({
                    'id': status.get('id'),
                    'instance': instance,
                    'content': status.get('content'),
                    'account': status.get('account', {}).get('username'),
                    'created_at': status.get('created_at'),
                    'favourites': status.get('favourites_count'),
                    'replies': status.get('replies_count'),
                    'reblogs': status.get('reblogs_count'),
                    'tags': [t['name'] for t in status.get('tags', [])]
                })
            return posts
        except Exception as e:
            print(f"Error fetching from {instance}: {e}")
            return []
    
    def fetch_trending_tags(self, instance, limit=10):
        """Fetch trending hashtags"""
        url = f"{self.base_url_template.format(instance)}/trends/tags"
        try:
            resp = requests.get(url, params={'limit': limit}, timeout=10)
            tags = resp.json()
            
            trending = []
            for tag in tags:
                trending.append({
                    'name': tag.get('name'),
                    'url': tag.get('url'),
                    'uses': tag.get('history', [{}])[0].get('uses', 0) if tag.get('history') else 0
                })
            return trending
        except Exception as e:
            print(f"Error fetching trends from {instance}: {e}")
            return []
    
    def stream_public_timeline(self, instance):
        """Stream public timeline via WebSocket"""
        ws_url = f"wss://{instance}/api/v1/streaming/public"
        
        def on_message(ws, message):
            data = json.loads(message)
            if data.get('event') == 'update':
                status = json.loads(data.get('payload', '{}'))
                print(f"[{instance}] {status.get('account', {}).get('username')}: {status.get('content')[:50]}")
        
        def on_error(ws, error):
            print(f"WebSocket error: {error}")
        
        ws = websocket.WebSocketApp(ws_url,
                                   on_message=on_message,
                                   on_error=on_error)
        ws.run_forever()

# Usage
collector = MastodonCollector()
for instance in collector.instances:
    timeline = collector.fetch_public_timeline(instance, limit=20)
    print(f"\n=== {instance} ===")
    for post in timeline:
        print(f"{post['account']}: {post['content'][:60]}...")
```

### Rate Limiting Strategy
- 300 requests per 5 minutes per endpoint
- 7500 requests per 5 minutes per IP (hard cap)
- Use exponential backoff for 429 errors
- Stagger requests across instances

### Data Storage Schema
```sql
CREATE TABLE mastodon_posts (
    id TEXT PRIMARY KEY,
    instance TEXT,
    content TEXT,
    author TEXT,
    created_at TIMESTAMP,
    favourites INTEGER,
    replies INTEGER,
    reblogs INTEGER,
    tags TEXT,  -- JSON array
    collected_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE mastodon_trends (
    instance TEXT,
    tag_name TEXT,
    uses INTEGER,
    collected_at TIMESTAMP,
    PRIMARY KEY (instance, tag_name, collected_at)
);
```

---

## 3. RSS Aggregation Pipeline

### Recommended News Outlets
```
Global News:
- BBC: https://feeds.bbci.co.uk/news/rss.xml
- Reuters: https://www.reuters.com/world/
- AP News: https://apnews.com/hub/ap-top-news
- Al Jazeera: https://www.aljazeera.com/xml/rss/all.xml

Tech News:
- TechCrunch: https://techcrunch.com/feed/
- The Verge: https://www.theverge.com/rss/index.xml
- Wired: https://www.wired.com/feed/rss.xml

Business:
- Bloomberg: https://www.bloomberg.com/feed/podcast/etf-report.xml
- Financial Times: https://markets.ft.com/data/indices/tearsheet/summary
```

### Quick Python Implementation
```python
import feedparser
from datetime import datetime
import requests

class RSSCollector:
    def __init__(self, feeds_config):
        """
        feeds_config: dict with outlet_name -> feed_url mapping
        """
        self.feeds = feeds_config
    
    def fetch_feed(self, outlet_name, feed_url):
        """Fetch and parse RSS feed"""
        try:
            feed = feedparser.parse(feed_url)
            articles = []
            
            for entry in feed.entries[:20]:  # Last 20 articles
                articles.append({
                    'outlet': outlet_name,
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'published': datetime(*entry.published_parsed[:6]) 
                               if hasattr(entry, 'published_parsed') else None,
                    'summary': entry.get('summary', '')[:500],
                    'tags': [tag.term for tag in entry.get('tags', [])]
                })
            
            return articles
        except Exception as e:
            print(f"Error fetching {outlet_name}: {e}")
            return []
    
    def aggregate_all(self):
        """Fetch from all configured feeds"""
        all_articles = []
        
        for outlet, url in self.feeds.items():
            articles = self.fetch_feed(outlet, url)
            all_articles.extend(articles)
        
        # Sort by published date
        all_articles.sort(
            key=lambda x: x['published'] or datetime.now(),
            reverse=True
        )
        
        return all_articles

# Configuration
feeds = {
    'BBC': 'https://feeds.bbci.co.uk/news/rss.xml',
    'Reuters': 'https://www.reuters.com/rssFeed/worldNews',
    'TechCrunch': 'https://techcrunch.com/feed/',
    'Al Jazeera': 'https://www.aljazeera.com/xml/rss/all.xml',
}

# Usage
collector = RSSCollector(feeds)
articles = collector.aggregate_all()

for article in articles[:10]:
    print(f"[{article['outlet']}] {article['title']}")
    print(f"  Published: {article['published']}")
    print(f"  {article['summary'][:100]}...\n")
```

### Deployment with FreshRSS (OSS Alternative)
```bash
# Docker compose for FreshRSS
docker run -d \
  --name freshrss \
  -p 8080:80 \
  -e TZ=UTC \
  -v freshrss_data:/var/www/FreshRSS/data \
  freshrss/freshrss:latest

# Access at http://localhost:8080
# Add RSS feeds via UI
# Export data via API
```

### Data Storage Schema
```sql
CREATE TABLE rss_articles (
    id TEXT PRIMARY KEY,
    outlet TEXT,
    title TEXT,
    url TEXT UNIQUE,
    published TIMESTAMP,
    summary TEXT,
    tags TEXT,  -- JSON array
    collected_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_outlet ON rss_articles(outlet);
CREATE INDEX idx_published ON rss_articles(published);
```

---

## Data Normalization Layer

### Unified Data Schema
```python
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass
class NarrativeSignal:
    """Unified representation of narrative signal"""
    source: str  # 'hackernews', 'mastodon', 'rss'
    source_id: str
    title: str
    content: str
    author: str
    timestamp: datetime
    engagement: dict  # {likes, comments, shares, etc}
    tags: List[str]
    url: Optional[str] = None
    instance: Optional[str] = None  # For Mastodon
    
    def to_dict(self):
        return {
            'source': self.source,
            'source_id': self.source_id,
            'title': self.title,
            'content': self.content,
            'author': self.author,
            'timestamp': self.timestamp.isoformat(),
            'engagement': self.engagement,
            'tags': self.tags,
            'url': self.url,
            'instance': self.instance
        }

# Adapters
def hn_to_signal(story: dict) -> NarrativeSignal:
    return NarrativeSignal(
        source='hackernews',
        source_id=str(story['id']),
        title=story['title'],
        content='',
        author=story.get('author', 'unknown'),
        timestamp=story['time'],
        engagement={'score': story['score'], 'comments': story['comments']},
        tags=['tech', 'startup'],
        url=story.get('url')
    )

def mastodon_to_signal(post: dict) -> NarrativeSignal:
    return NarrativeSignal(
        source='mastodon',
        source_id=post['id'],
        title='',
        content=post['content'],
        author=post['account'],
        timestamp=datetime.fromisoformat(post['created_at'].replace('Z', '+00:00')),
        engagement={
            'favourites': post['favourites'],
            'replies': post['replies'],
            'reblogs': post['reblogs']
        },
        tags=post['tags'],
        instance=post['instance']
    )

def rss_to_signal(article: dict) -> NarrativeSignal:
    return NarrativeSignal(
        source='rss',
        source_id=article['link'],
        title=article['title'],
        content=article['summary'],
        author=article['outlet'],
        timestamp=article['published'] or datetime.now(),
        engagement={},
        tags=article['tags'],
        url=article['link']
    )
```

---

## Orchestration Example

### Airflow DAG Structure
```
observatorio_narratives/
├── dags/
│   └── collect_narratives.py
├── operators/
│   ├── hn_operator.py
│   ├── mastodon_operator.py
│   └── rss_operator.py
└── data/
    └── feeds_config.yaml
```

### Simple Polling Script
```python
import schedule
import time
from datetime import datetime

class NarrativeCollector:
    def __init__(self, hn_collector, mastodon_collector, rss_collector, db):
        self.hn = hn_collector
        self.mastodon = mastodon_collector
        self.rss = rss_collector
        self.db = db
    
    def collect_hackernews(self):
        print(f"[{datetime.now()}] Collecting from Hacker News...")
        stories = self.hn.fetch_top_stories(30)
        for story in stories:
            signal = hn_to_signal(story)
            self.db.insert(signal)
    
    def collect_mastodon(self):
        print(f"[{datetime.now()}] Collecting from Mastodon instances...")
        for instance in self.mastodon.instances:
            timeline = self.mastodon.fetch_public_timeline(instance)
            for post in timeline:
                signal = mastodon_to_signal(post)
                self.db.insert(signal)
    
    def collect_rss(self):
        print(f"[{datetime.now()}] Collecting from RSS feeds...")
        articles = self.rss.aggregate_all()
        for article in articles:
            signal = rss_to_signal(article)
            self.db.insert(signal)
    
    def start_scheduler(self):
        """Start polling scheduler"""
        schedule.every(20).seconds.do(self.collect_hackernews)
        schedule.every(2).minutes.do(self.collect_mastodon)
        schedule.every(15).minutes.do(self.collect_rss)
        
        while True:
            schedule.run_pending()
            time.sleep(1)

# Usage
# collector = NarrativeCollector(hn, mastodon, rss, db)
# collector.start_scheduler()
```

---

## Next Steps

1. **Week 1**: Set up HN collector + basic storage
2. **Week 2**: Add Mastodon multi-instance collector
3. **Week 3**: Integrate RSS pipeline
4. **Week 4**: Build narrative clustering layer
5. **Week 5**: Add cross-platform correlation engine

