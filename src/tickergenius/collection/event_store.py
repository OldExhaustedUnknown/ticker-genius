"""
Event Store
============
Phase 1: PDUFA 이벤트 저장소

단일 책임: 이벤트 CRUD 전담
- 다른 로직(추출, 예측) 포함하지 않음
- 파일 시스템 기반 저장
- JSON 형식

참조: docs/M3_BLUEPRINT_v2.md
"""

import json
import logging
from pathlib import Path
from typing import Optional
from collections import defaultdict

from .event_models import PDUFAEvent

logger = logging.getLogger(__name__)


class EventStore:
    """
    PDUFA 이벤트 저장소.

    파일 구조:
        base_dir/
        ├── by_event/               # 이벤트별 파일
        │   ├── {event_id}.json
        │   └── ...
        ├── by_drug/                # 약물별 인덱스
        │   ├── {ticker}_{drug}.json
        │   └── ...
        └── manifest.json           # 전체 현황 (선택적)

    Usage:
        store = EventStore()
        store.save(event)
        event = store.load(event_id)
        ids = store.list_all()
    """

    def __init__(self, base_dir: Path = None):
        """
        Args:
            base_dir: 저장 디렉토리. 기본값은 data/events
        """
        self.base_dir = Path(base_dir) if base_dir else Path("data/events")
        self.by_event_dir = self.base_dir / "by_event"
        self.by_drug_dir = self.base_dir / "by_drug"

        # 디렉토리 생성은 첫 저장 시에만
        self._initialized = False

    def _ensure_dirs(self):
        """디렉토리 구조 생성 (lazy initialization)."""
        if self._initialized:
            return

        self.by_event_dir.mkdir(parents=True, exist_ok=True)
        self.by_drug_dir.mkdir(parents=True, exist_ok=True)
        self._initialized = True

    # ==================== Core CRUD ====================

    def save(self, event: PDUFAEvent) -> str:
        """
        이벤트 저장.

        같은 event_id가 있으면 덮어씁니다.

        Args:
            event: 저장할 PDUFAEvent

        Returns:
            저장된 event_id
        """
        self._ensure_dirs()

        # 이벤트 파일 저장
        event_file = self.by_event_dir / f"{event.event_id}.json"
        with open(event_file, "w", encoding="utf-8") as f:
            json.dump(event.to_dict(), f, ensure_ascii=False, indent=2)

        # 약물별 인덱스 업데이트
        self._update_drug_index(event)

        logger.debug(f"Saved event: {event.event_id}")
        return event.event_id

    def load(self, event_id: str) -> Optional[PDUFAEvent]:
        """
        이벤트 로드.

        Args:
            event_id: 이벤트 ID

        Returns:
            PDUFAEvent 또는 None (없으면)
        """
        event_file = self.by_event_dir / f"{event_id}.json"

        if not event_file.exists():
            return None

        try:
            with open(event_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return PDUFAEvent.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load event {event_id}: {e}")
            return None

    def exists(self, event_id: str) -> bool:
        """
        이벤트 존재 여부.

        Args:
            event_id: 이벤트 ID

        Returns:
            존재하면 True
        """
        event_file = self.by_event_dir / f"{event_id}.json"
        return event_file.exists()

    def delete(self, event_id: str) -> bool:
        """
        이벤트 삭제.

        Args:
            event_id: 이벤트 ID

        Returns:
            삭제 성공 여부
        """
        event_file = self.by_event_dir / f"{event_id}.json"

        if not event_file.exists():
            return False

        try:
            # 삭제 전 정보 로드 (인덱스 업데이트용)
            event = self.load(event_id)

            # 파일 삭제
            event_file.unlink()

            # 인덱스에서 제거
            if event:
                self._remove_from_drug_index(event)

            logger.debug(f"Deleted event: {event_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete event {event_id}: {e}")
            return False

    # ==================== Query ====================

    def list_all(self) -> list[str]:
        """
        모든 이벤트 ID 목록.

        Returns:
            event_id 리스트
        """
        if not self.by_event_dir.exists():
            return []

        return [
            f.stem
            for f in self.by_event_dir.glob("*.json")
        ]

    def list_by_ticker(self, ticker: str) -> list[str]:
        """
        특정 티커의 이벤트 ID 목록.

        Args:
            ticker: 주식 티커

        Returns:
            event_id 리스트
        """
        result = []
        ticker_lower = ticker.lower()

        # 모든 약물 인덱스에서 해당 티커 찾기
        if not self.by_drug_dir.exists():
            return []

        for index_file in self.by_drug_dir.glob("*.json"):
            if index_file.stem.startswith(ticker_lower + "_"):
                try:
                    with open(index_file, "r", encoding="utf-8") as f:
                        index = json.load(f)
                    result.extend(index.get("events", []))
                except Exception:
                    pass

        return result

    def list_by_drug(self, ticker: str, drug_name: str) -> list[str]:
        """
        특정 약물의 이벤트 ID 목록.

        Args:
            ticker: 주식 티커
            drug_name: 약물 이름

        Returns:
            event_id 리스트
        """
        index_key = self._make_drug_index_key(ticker, drug_name)
        index_file = self.by_drug_dir / f"{index_key}.json"

        if not index_file.exists():
            return []

        try:
            with open(index_file, "r", encoding="utf-8") as f:
                index = json.load(f)
            return index.get("events", [])
        except Exception:
            return []

    def count(self) -> int:
        """
        전체 이벤트 개수.

        Returns:
            이벤트 개수
        """
        return len(self.list_all())

    # ==================== Bulk ====================

    def save_many(self, events: list[PDUFAEvent]) -> int:
        """
        여러 이벤트 일괄 저장.

        Args:
            events: PDUFAEvent 리스트

        Returns:
            저장된 개수
        """
        count = 0
        for event in events:
            try:
                self.save(event)
                count += 1
            except Exception as e:
                logger.error(f"Failed to save event {event.event_id}: {e}")

        return count

    def load_many(self, event_ids: list[str]) -> list[PDUFAEvent]:
        """
        여러 이벤트 일괄 로드.

        Args:
            event_ids: event_id 리스트

        Returns:
            PDUFAEvent 리스트 (로드 실패한 것은 제외)
        """
        result = []
        for event_id in event_ids:
            event = self.load(event_id)
            if event:
                result.append(event)

        return result

    # ==================== Stats ====================

    def get_stats(self) -> dict:
        """
        전체 통계 반환.

        Returns:
            {
                "total": int,
                "by_ticker": {"AXSM": 3, "ABBV": 1, ...},
                "by_result": {"approved": 10, "crl": 5, "pending": 3}
            }
        """
        stats = {
            "total": 0,
            "by_ticker": defaultdict(int),
            "by_result": defaultdict(int),
        }

        for event_id in self.list_all():
            event = self.load(event_id)
            if event:
                stats["total"] += 1
                stats["by_ticker"][event.ticker] += 1
                if event.result:
                    stats["by_result"][event.result] += 1

        # defaultdict를 일반 dict로 변환
        stats["by_ticker"] = dict(stats["by_ticker"])
        stats["by_result"] = dict(stats["by_result"])

        return stats

    # ==================== Internal ====================

    def _make_drug_index_key(self, ticker: str, drug_name: str) -> str:
        """약물 인덱스 키 생성."""
        # 파일명에 안전한 문자로 변환
        safe_drug = drug_name.lower().replace(" ", "-").replace("/", "-")
        return f"{ticker.lower()}_{safe_drug}"

    def _update_drug_index(self, event: PDUFAEvent):
        """약물별 인덱스 업데이트."""
        index_key = self._make_drug_index_key(event.ticker, event.drug_name)
        index_file = self.by_drug_dir / f"{index_key}.json"

        # 기존 인덱스 로드 또는 새로 생성
        if index_file.exists():
            with open(index_file, "r", encoding="utf-8") as f:
                index = json.load(f)
        else:
            index = {
                "ticker": event.ticker,
                "drug_name": event.drug_name,
                "events": []
            }

        # 이벤트 ID 추가 (중복 방지)
        if event.event_id not in index["events"]:
            index["events"].append(event.event_id)

        # 저장
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def _remove_from_drug_index(self, event: PDUFAEvent):
        """약물별 인덱스에서 제거."""
        index_key = self._make_drug_index_key(event.ticker, event.drug_name)
        index_file = self.by_drug_dir / f"{index_key}.json"

        if not index_file.exists():
            return

        try:
            with open(index_file, "r", encoding="utf-8") as f:
                index = json.load(f)

            if event.event_id in index["events"]:
                index["events"].remove(event.event_id)

            # 인덱스 업데이트 또는 삭제
            if index["events"]:
                with open(index_file, "w", encoding="utf-8") as f:
                    json.dump(index, f, ensure_ascii=False, indent=2)
            else:
                index_file.unlink()  # 빈 인덱스 삭제
        except Exception as e:
            logger.warning(f"Failed to update drug index: {e}")
