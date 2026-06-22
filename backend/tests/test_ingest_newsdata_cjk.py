"""East-Asia (CJK) ingestion path — diversification lever for #230.

zh/ja/ko were entirely absent from the corpus (measured 0 of 146K, 2026-06-22),
so China/Japan/Korea were only ever seen through Western-English reporting.
These tests prove the mechanism end-to-end at the parse layer: the batch is
wired, and a Chinese/Japanese NewsData article lands with a normalized ISO
source_lang — without needing the live API key.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.services import ingest_newsdata
from app.services.ingest_newsdata import LANGUAGE_BATCHES, LANGUAGE_CODES, _fetch_batch


def test_east_asia_batch_is_wired():
    cjk = [b for b in LANGUAGE_BATCHES if "zh" in b["language"]]
    assert cjk, "East-Asia CJK batch missing from LANGUAGE_BATCHES"
    b = cjk[0]
    assert set(b["language"].split(",")) == {"zh", "jp", "ko"}
    # NewsData free plan caps a request at 5 countries.
    assert len(b["country"].split(",")) <= 5
    assert "cn" in b["country"]


def test_batch_count_within_quota():
    # NewsData fires every 4th GDELT cycle (~hourly) → batch_count * 24 req/day,
    # free-plan cap 200. Adding the CJK batch must not blow the budget.
    assert len(LANGUAGE_BATCHES) * 24 <= 200


def test_japanese_code_normalized_to_iso():
    # NewsData returns non-ISO "jp" for Japanese; we store ISO "ja".
    assert LANGUAGE_CODES.get("jp") == "ja"
    assert LANGUAGE_CODES.get("chinese") == "zh"
    assert LANGUAGE_CODES.get("korean") == "ko"


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload
        self.status = 200

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def json(self):
        return self._payload

    async def text(self):
        return ""


class _FakeSession:
    def __init__(self, payload):
        self._payload = payload

    def get(self, *a, **k):
        return _FakeResp(self._payload)


def test_cjk_articles_parse_with_normalized_lang(monkeypatch):
    pub = "2026-06-22 08:00:00"
    payload = {
        "status": "success",
        "results": [
            {"title": "中国经济数据公布", "description": "最新报道",
             "link": "https://example.cn/a1", "language": "chinese",
             "country": ["cn"], "pubDate": pub, "source_id": "xinhua"},
            {"title": "日本の選挙結果", "description": "速報",
             "link": "https://example.jp/a2", "language": "jp",
             "country": ["jp"], "pubDate": pub, "source_id": "nhk"},
            {"title": "한국 뉴스 속보", "description": "최신",
             "link": "https://example.kr/a3", "language": "ko",
             "country": ["kr"], "pubDate": pub, "source_id": "yonhap"},
        ],
    }
    session = _FakeSession(payload)
    since = datetime(2020, 1, 1, tzinfo=timezone.utc)

    signals = asyncio.run(
        _fetch_batch(session, {"language": "zh,jp,ko", "country": "cn,tw,hk,jp,kr"}, since)
    )

    by_lang = {s["source_lang"]: s for s in signals}
    assert set(by_lang) == {"zh", "ja", "ko"}, by_lang
    assert by_lang["zh"]["country_code"] == "CN"
    assert by_lang["ja"]["country_code"] == "JP"
    assert by_lang["ko"]["country_code"] == "KR"
    # Headlines preserved (not mangled / not dropped).
    assert by_lang["zh"]["headline"] == "中国经济数据公布"
