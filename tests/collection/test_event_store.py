"""
Tests for EventStore
=====================
Phase 1: 이벤트 저장소 테스트 (TDD)

테스트 우선순위:
1. 기본 CRUD
2. 조회 기능
3. 파일 시스템 구조
"""

import pytest
import sys
import json
import tempfile
import shutil
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@pytest.fixture
def temp_dir():
    """임시 디렉토리 생성/정리."""
    d = tempfile.mkdtemp()
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def sample_event():
    """테스트용 샘플 이벤트."""
    from tickergenius.collection.event_models import PDUFAEvent

    return PDUFAEvent(
        ticker="AXSM",
        drug_name="AXS-05",
        pdufa_date="20220819",
        result="approved",
        btd=True,
        priority_review=True,
        sequence_number=3,
        submission_type="resubmission"
    )


class TestEventStoreCRUD:
    """기본 CRUD 테스트."""

    def test_save_creates_file(self, temp_dir, sample_event):
        """save()가 파일을 생성하는지."""
        from tickergenius.collection.event_store import EventStore

        store = EventStore(base_dir=temp_dir)
        event_id = store.save(sample_event)

        assert event_id == sample_event.event_id

        # 파일이 존재하는지
        event_file = temp_dir / "by_event" / f"{event_id}.json"
        assert event_file.exists()

    def test_load_returns_same_event(self, temp_dir, sample_event):
        """save 후 load하면 동일한 이벤트."""
        from tickergenius.collection.event_store import EventStore

        store = EventStore(base_dir=temp_dir)
        event_id = store.save(sample_event)
        loaded = store.load(event_id)

        assert loaded is not None
        assert loaded.event_id == sample_event.event_id
        assert loaded.ticker == sample_event.ticker
        assert loaded.drug_name == sample_event.drug_name
        assert loaded.pdufa_date == sample_event.pdufa_date
        assert loaded.result == sample_event.result
        assert loaded.btd == sample_event.btd

    def test_load_nonexistent_returns_none(self, temp_dir):
        """존재하지 않는 ID는 None 반환."""
        from tickergenius.collection.event_store import EventStore

        store = EventStore(base_dir=temp_dir)
        loaded = store.load("nonexistent_id_12345")

        assert loaded is None

    def test_exists_returns_correct_value(self, temp_dir, sample_event):
        """exists()가 올바른 값 반환."""
        from tickergenius.collection.event_store import EventStore

        store = EventStore(base_dir=temp_dir)

        assert store.exists(sample_event.event_id) is False

        store.save(sample_event)

        assert store.exists(sample_event.event_id) is True

    def test_delete_removes_file(self, temp_dir, sample_event):
        """delete()가 파일을 삭제."""
        from tickergenius.collection.event_store import EventStore

        store = EventStore(base_dir=temp_dir)
        event_id = store.save(sample_event)

        assert store.exists(event_id) is True

        result = store.delete(event_id)

        assert result is True
        assert store.exists(event_id) is False

    def test_delete_nonexistent_returns_false(self, temp_dir):
        """존재하지 않는 ID 삭제 시 False."""
        from tickergenius.collection.event_store import EventStore

        store = EventStore(base_dir=temp_dir)
        result = store.delete("nonexistent_id")

        assert result is False

    def test_save_overwrites_existing(self, temp_dir):
        """같은 event_id로 저장 시 덮어쓰기."""
        from tickergenius.collection.event_models import PDUFAEvent
        from tickergenius.collection.event_store import EventStore

        store = EventStore(base_dir=temp_dir)

        event1 = PDUFAEvent(
            ticker="TEST",
            drug_name="DRUG",
            pdufa_date="20250101",
            result="pending"
        )
        store.save(event1)

        # 같은 event_id, 다른 result
        event2 = PDUFAEvent(
            ticker="TEST",
            drug_name="DRUG",
            pdufa_date="20250101",
            result="approved"  # 변경됨
        )
        store.save(event2)

        loaded = store.load(event1.event_id)
        assert loaded.result == "approved"


class TestEventStoreQuery:
    """조회 기능 테스트."""

    def test_list_all_returns_all_events(self, temp_dir):
        """list_all()이 모든 이벤트 반환."""
        from tickergenius.collection.event_models import PDUFAEvent
        from tickergenius.collection.event_store import EventStore

        store = EventStore(base_dir=temp_dir)

        events = [
            PDUFAEvent(ticker="AXSM", drug_name="AXS-05", pdufa_date="20210108"),
            PDUFAEvent(ticker="AXSM", drug_name="AXS-05", pdufa_date="20220819"),
            PDUFAEvent(ticker="ABBV", drug_name="EMRELIS", pdufa_date="20250514"),
        ]

        for e in events:
            store.save(e)

        all_ids = store.list_all()

        assert len(all_ids) == 3
        for e in events:
            assert e.event_id in all_ids

    def test_list_by_ticker(self, temp_dir):
        """list_by_ticker()가 해당 티커만 반환."""
        from tickergenius.collection.event_models import PDUFAEvent
        from tickergenius.collection.event_store import EventStore

        store = EventStore(base_dir=temp_dir)

        events = [
            PDUFAEvent(ticker="AXSM", drug_name="AXS-05", pdufa_date="20210108"),
            PDUFAEvent(ticker="AXSM", drug_name="AXS-05", pdufa_date="20220819"),
            PDUFAEvent(ticker="ABBV", drug_name="EMRELIS", pdufa_date="20250514"),
        ]

        for e in events:
            store.save(e)

        axsm_ids = store.list_by_ticker("AXSM")

        assert len(axsm_ids) == 2
        assert events[2].event_id not in axsm_ids

    def test_list_by_drug(self, temp_dir):
        """list_by_drug()가 해당 약물만 반환."""
        from tickergenius.collection.event_models import PDUFAEvent
        from tickergenius.collection.event_store import EventStore

        store = EventStore(base_dir=temp_dir)

        events = [
            PDUFAEvent(ticker="AXSM", drug_name="AXS-05", pdufa_date="20210108"),
            PDUFAEvent(ticker="AXSM", drug_name="AXS-05", pdufa_date="20220819"),
            PDUFAEvent(ticker="AXSM", drug_name="AXS-07", pdufa_date="20230101"),
        ]

        for e in events:
            store.save(e)

        axs05_ids = store.list_by_drug("AXSM", "AXS-05")

        assert len(axs05_ids) == 2

    def test_count_returns_correct_number(self, temp_dir):
        """count()가 정확한 개수 반환."""
        from tickergenius.collection.event_models import PDUFAEvent
        from tickergenius.collection.event_store import EventStore

        store = EventStore(base_dir=temp_dir)

        assert store.count() == 0

        events = [
            PDUFAEvent(ticker="AXSM", drug_name="AXS-05", pdufa_date="20210108"),
            PDUFAEvent(ticker="AXSM", drug_name="AXS-05", pdufa_date="20220819"),
        ]

        for e in events:
            store.save(e)

        assert store.count() == 2


class TestEventStoreBulk:
    """대량 처리 테스트."""

    def test_save_many_saves_all(self, temp_dir):
        """save_many()가 모든 이벤트 저장."""
        from tickergenius.collection.event_models import PDUFAEvent
        from tickergenius.collection.event_store import EventStore

        store = EventStore(base_dir=temp_dir)

        events = [
            PDUFAEvent(ticker="AXSM", drug_name="AXS-05", pdufa_date="20210108"),
            PDUFAEvent(ticker="AXSM", drug_name="AXS-05", pdufa_date="20220819"),
            PDUFAEvent(ticker="ABBV", drug_name="EMRELIS", pdufa_date="20250514"),
        ]

        count = store.save_many(events)

        assert count == 3
        assert store.count() == 3

    def test_load_many_loads_all(self, temp_dir):
        """load_many()가 모든 이벤트 로드."""
        from tickergenius.collection.event_models import PDUFAEvent
        from tickergenius.collection.event_store import EventStore

        store = EventStore(base_dir=temp_dir)

        events = [
            PDUFAEvent(ticker="AXSM", drug_name="AXS-05", pdufa_date="20210108"),
            PDUFAEvent(ticker="AXSM", drug_name="AXS-05", pdufa_date="20220819"),
        ]

        store.save_many(events)

        ids = [e.event_id for e in events]
        loaded = store.load_many(ids)

        assert len(loaded) == 2


class TestEventStoreFileStructure:
    """파일 구조 테스트."""

    def test_creates_directory_structure(self, temp_dir):
        """저장 시 디렉토리 구조 생성."""
        from tickergenius.collection.event_models import PDUFAEvent
        from tickergenius.collection.event_store import EventStore

        store = EventStore(base_dir=temp_dir)

        event = PDUFAEvent(ticker="TEST", drug_name="DRUG", pdufa_date="20250101")
        store.save(event)

        assert (temp_dir / "by_event").is_dir()

    def test_updates_drug_index(self, temp_dir):
        """약물별 인덱스 파일 업데이트."""
        from tickergenius.collection.event_models import PDUFAEvent
        from tickergenius.collection.event_store import EventStore

        store = EventStore(base_dir=temp_dir)

        events = [
            PDUFAEvent(ticker="AXSM", drug_name="AXS-05", pdufa_date="20210108"),
            PDUFAEvent(ticker="AXSM", drug_name="AXS-05", pdufa_date="20220819"),
        ]

        for e in events:
            store.save(e)

        # by_drug 인덱스 확인
        index_file = temp_dir / "by_drug" / "axsm_axs-05.json"
        assert index_file.exists()

        with open(index_file, encoding="utf-8") as f:
            index = json.load(f)

        assert len(index["events"]) == 2

    def test_get_stats_returns_summary(self, temp_dir):
        """get_stats()가 요약 정보 반환."""
        from tickergenius.collection.event_models import PDUFAEvent
        from tickergenius.collection.event_store import EventStore

        store = EventStore(base_dir=temp_dir)

        events = [
            PDUFAEvent(ticker="AXSM", drug_name="AXS-05", pdufa_date="20210108"),
            PDUFAEvent(ticker="AXSM", drug_name="AXS-05", pdufa_date="20220819"),
            PDUFAEvent(ticker="ABBV", drug_name="EMRELIS", pdufa_date="20250514"),
        ]

        for e in events:
            store.save(e)

        stats = store.get_stats()

        assert stats["total"] == 3
        assert "AXSM" in stats["by_ticker"]
        assert stats["by_ticker"]["AXSM"] == 2
        assert stats["by_ticker"]["ABBV"] == 1
