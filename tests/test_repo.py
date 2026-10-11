from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from bot.config import get_settings
from bot.db.connection import init_db
from bot.db.repo import Repo


@pytest.fixture(scope="function")
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Repo:
    settings = get_settings()
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "test.db"))
    asyncio.run(init_db())
    return Repo()


@pytest.mark.asyncio
async def test_user_create_and_count(repo: Repo):
    uid = await repo.get_or_create_user(123, "alice")
    assert uid > 0
    uid2 = await repo.get_or_create_user(123, "alice2")
    assert uid2 == uid
    assert await repo.count_user_tracks(uid) == 0


@pytest.mark.asyncio
async def test_add_list_remove_track(repo: Repo):
    uid = await repo.get_or_create_user(1, "bob")
    ok = await repo.add_track(uid, "https://www.chipdip.by/product/x", "X1", "Title X", 5.0, 6.0)
    assert ok is True
    assert await repo.count_user_tracks(uid) == 1
    tracks = await repo.list_user_tracks(uid)
    assert len(tracks) == 1
    tid = tracks[0]["id"]
    removed = await repo.remove_track(tid, uid)
    assert removed is True
    assert await repo.count_user_tracks(uid) == 0


@pytest.mark.asyncio
async def test_duplicate_track_rejected(repo: Repo):
    uid = await repo.get_or_create_user(2, "carol")
    await repo.add_track(uid, "https://www.chipdip.by/product/y", "Y1", "Y", 5.0, 6.0)
    ok = await repo.add_track(uid, "https://www.chipdip.by/product/y", "Y1", "Y", 5.0, 6.0)
    assert ok is False


@pytest.mark.asyncio
async def test_price_history_and_update(repo: Repo):
    uid = await repo.get_or_create_user(3, "dan")
    tid = await repo.add_track(uid, "https://www.chipdip.by/product/z", "Z1", "Z", 5.0, 6.0)
    await repo.update_track_price(tid, 4.0, set_notified=True)
    history = await repo.price_history(tid)
    assert len(history) == 2
    assert history[0]["price"] == 4.0


@pytest.mark.asyncio
async def test_fail_increment_and_deactivate(repo: Repo):
    uid = await repo.get_or_create_user(4, "eve")
    tid = await repo.add_track(uid, "https://www.chipdip.by/product/w", "W1", "W", 5.0, 6.0)
    fails = 0
    for _ in range(5):
        fails = await repo.increment_track_fail(tid)
    assert fails == 5
    await repo.deactivate_track(tid)
    active = await repo.active_tracks()
    assert all(t["id"] != tid for t in active)


@pytest.mark.asyncio
async def test_cache_set_get(repo: Repo):
    await repo.cache_set("k1", "<html>", 3600)
    assert await repo.cache_get("k1") == "<html>"
    assert await repo.cache_get("missing") is None
