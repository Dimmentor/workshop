from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional
from src.config import settings


@dataclass
class ConversationRecord:
    conversation_id: str
    branch_path: Optional[str] = None
    data: Dict[str, Any] | None = None
    updated_at: float = 0.0
    last_access_at: float = 0.0


class ConversationStore:
    """
    Хранилище данных в памяти для каждого диалога.
    - Ограничение: max_items + TTL.
    - TODO: перенести на In-Memory DB
    """

    def __init__(self, *, ttl_seconds: int = 60 * 60, max_items: int = 10_000):
        self._ttl_seconds = max(1, int(ttl_seconds))
        self._max_items = max(1, int(max_items))
        self._items: Dict[str, ConversationRecord] = {}

    def _now(self) -> float:
        return time.time()

    def _is_expired(self, rec: ConversationRecord, now: float) -> bool:
        return (now - (rec.last_access_at or rec.updated_at or now)) > self._ttl_seconds

    def _evict_if_needed(self, now: float) -> None:
        # 1) Expire by TTL
        expired = [cid for cid, rec in self._items.items() if self._is_expired(rec, now)]
        for cid in expired:
            self._items.pop(cid, None)

        # 2) Bound by size: evict LRU-ish (oldest last_access_at)
        if len(self._items) <= self._max_items:
            return
        victims = sorted(self._items.values(), key=lambda r: (r.last_access_at or r.updated_at or 0.0))
        over = len(self._items) - self._max_items
        for rec in victims[:over]:
            self._items.pop(rec.conversation_id, None)

    def touch(self, conversation_id: str) -> None:
        cid = (conversation_id or "").strip()
        if not cid:
            return
        now = self._now()
        self._evict_if_needed(now)
        rec = self._items.get(cid)
        if rec is None:
            rec = ConversationRecord(conversation_id=cid, updated_at=now, last_access_at=now, data={})
            self._items[cid] = rec
        else:
            rec.last_access_at = now
        self._evict_if_needed(now)

    def set_branch_path(self, conversation_id: str, branch_path: Optional[str]) -> None:
        cid = (conversation_id or "").strip()
        if not cid:
            return
        now = self._now()
        self._evict_if_needed(now)
        rec = self._items.get(cid) or ConversationRecord(conversation_id=cid, data={})
        rec.branch_path = branch_path or None
        rec.updated_at = now
        rec.last_access_at = now
        if rec.data is None:
            rec.data = {}
        self._items[cid] = rec
        self._evict_if_needed(now)

    def get_branch_path(self, conversation_id: str) -> Optional[str]:
        cid = (conversation_id or "").strip()
        if not cid:
            return None
        now = self._now()
        rec = self._items.get(cid)
        if rec is None:
            return None
        if self._is_expired(rec, now):
            self._items.pop(cid, None)
            return None
        rec.last_access_at = now
        return rec.branch_path or None

    def clear(self, conversation_id: str) -> None:
        cid = (conversation_id or "").strip()
        if not cid:
            return
        self._items.pop(cid, None)

    def stats(self) -> Dict[str, int]:
        return {"items": len(self._items), "ttl_seconds": self._ttl_seconds, "max_items": self._max_items}


try:
    _store = ConversationStore(
        ttl_seconds=int(getattr(settings, "CONVERSATION_TTL_SECONDS", 60 * 60) or 60 * 60),
        max_items=int(getattr(settings, "CONVERSATION_MAX_ITEMS", 10_000) or 10_000),
    )
except Exception:
    _store = ConversationStore()


def get_conversation_store() -> ConversationStore:
    return _store

