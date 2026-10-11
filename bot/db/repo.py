from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import aiosqlite

from bot.db.connection import get_connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Repo:
    async def get_or_create_user(self, tg_id: int, username: str | None) -> int:
        async with get_connection() as db:
            row = await (await db.execute("SELECT id FROM users WHERE tg_id=?", (tg_id,))).fetchone()
            if row:
                if username and row["id"]:
                    await db.execute("UPDATE users SET username=? WHERE id=?", (username, row["id"]))
                    await db.commit()
                return row["id"]
            cur = await db.execute(
                "INSERT INTO users(tg_id, username, created_at) VALUES(?,?,?)",
                (tg_id, username, _now()),
            )
            await db.commit()
            return cur.lastrowid  # type: ignore[return-value]

    async def count_user_tracks(self, user_id: int) -> int:
        async with get_connection() as db:
            row = await (
                await db.execute("SELECT COUNT(*) AS c FROM tracks WHERE user_id=?", (user_id,))
            ).fetchone()
            return int(row["c"]) if row else 0

    async def add_track(
        self,
        user_id: int,
        url: str,
        article: str | None,
        title: str | None,
        threshold: float,
        last_price: float | None,
    ) -> bool:
        async with get_connection() as db:
            try:
                cur = await db.execute(
                    "INSERT INTO tracks(user_id, url, article, title, threshold, last_price, "
                    "last_checked, created_at) VALUES(?,?,?,?,?,?,?,?)",
                    (user_id, url, article, title, threshold, last_price, _now(), _now()),
                )
                if last_price is not None:
                    await db.execute(
                        "INSERT INTO price_history(track_id, price, checked_at) VALUES(?,?,?)",
                        (cur.lastrowid, last_price, _now()),
                    )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def remove_track(self, track_id: int, user_id: int) -> bool:
        async with get_connection() as db:
            cur = await db.execute(
                "DELETE FROM tracks WHERE id=? AND user_id=?", (track_id, user_id)
            )
            await db.commit()
            return cur.rowcount > 0

    async def list_user_tracks(self, user_id: int) -> list[dict[str, Any]]:
        async with get_connection() as db:
            rows = await (
                await db.execute(
                    "SELECT id, url, article, title, threshold, last_price, active "
                    "FROM tracks WHERE user_id=? ORDER BY id DESC",
                    (user_id,),
                )
            ).fetchall()
            return [dict(r) for r in rows]

    async def get_track(self, track_id: int) -> dict[str, Any] | None:
        async with get_connection() as db:
            row = await (await db.execute("SELECT * FROM tracks WHERE id=?", (track_id,))).fetchone()
            return dict(row) if row else None

    async def active_tracks(self) -> list[dict[str, Any]]:
        async with get_connection() as db:
            rows = await (
                await db.execute(
                    "SELECT t.id, t.user_id, t.url, t.threshold, t.last_price, "
                    "t.fail_count, u.tg_id FROM tracks t "
                    "JOIN users u ON u.id=t.user_id WHERE t.active=1"
                )
            ).fetchall()
            return [dict(r) for r in rows]

    async def update_track_price(
        self,
        track_id: int,
        price: float | None,
        *,
        reset_fail: bool = True,
        set_notified: bool = False,
    ) -> None:
        async with get_connection() as db:
            await db.execute(
                "UPDATE tracks SET last_price=?, last_checked=?, "
                "fail_count=0, notified_below=? WHERE id=?",
                (price, _now(), 1 if set_notified else 0, track_id),
            )
            if price is not None:
                await db.execute(
                    "INSERT INTO price_history(track_id, price, checked_at) VALUES(?,?,?)",
                    (track_id, price, _now()),
                )
            await db.commit()

    async def increment_track_fail(self, track_id: int) -> int:
        async with get_connection() as db:
            await db.execute(
                "UPDATE tracks SET fail_count=fail_count+1, last_checked=? WHERE id=?",
                (_now(), track_id),
            )
            await db.commit()
            row = await (await db.execute("SELECT fail_count FROM tracks WHERE id=?", (track_id,))).fetchone()
            return int(row["fail_count"]) if row else 0

    async def deactivate_track(self, track_id: int) -> None:
        async with get_connection() as db:
            await db.execute("UPDATE tracks SET active=0 WHERE id=?", (track_id,))
            await db.commit()

    async def reset_notified(self, track_id: int) -> None:
        async with get_connection() as db:
            await db.execute("UPDATE tracks SET notified_below=0 WHERE id=?", (track_id,))
            await db.commit()

    async def price_history(self, track_id: int, limit: int = 50) -> list[dict[str, Any]]:
        async with get_connection() as db:
            rows = await (
                await db.execute(
                    "SELECT price, checked_at FROM price_history WHERE track_id=? "
                    "ORDER BY id DESC LIMIT ?",
                    (track_id, limit),
                )
            ).fetchall()
            return [dict(r) for r in rows]

    async def cache_get(self, key: str) -> str | None:
        async with get_connection() as db:
            row = await (await db.execute("SELECT html FROM cache WHERE key=?", (key,))).fetchone()
            return row["html"] if row else None

    async def cache_set(self, key: str, html: str, ttl_seconds: int) -> None:
        expires = (datetime.now(timezone.utc).timestamp() + ttl_seconds)
        expires_iso = datetime.fromtimestamp(expires, timezone.utc).isoformat()
        async with get_connection() as db:
            await db.execute(
                "INSERT OR REPLACE INTO cache(key, html, expires_at) VALUES(?,?,?)",
                (key, html, expires_iso),
            )
            await db.commit()

    async def cache_cleanup(self) -> None:
        async with get_connection() as db:
            await db.execute("DELETE FROM cache WHERE expires_at < ?", (_now(),))
            await db.commit()


repo = Repo()
