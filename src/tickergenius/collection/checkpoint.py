"""
Checkpoint Manager
===================
체크포인트 시스템: 데이터 수집/보강 진행 상태 관리

핵심 기능:
- 상태 저장/복구 (JSON 파일 기반)
- 원자적 저장 (임시 파일 -> 이름 변경)
- 필드별 진행 상황 추적
- 실패한 이벤트 큐 관리
- 자동 백업 (10분마다 또는 100건마다)

참조: docs/DATA_COLLECTION_DESIGN.md
"""

import json
import logging
import os
import shutil
import tempfile
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class FieldProgress:
    """필드별 진행 상황."""
    field_name: str
    total: int = 0
    completed: int = 0
    found: int = 0
    confirmed_none: int = 0
    not_found: int = 0
    not_searched: int = 0
    last_updated: Optional[datetime] = None

    @property
    def completion_rate(self) -> float:
        """완료율 (0.0 ~ 1.0)."""
        if self.total == 0:
            return 0.0
        return self.completed / self.total

    @property
    def success_rate(self) -> float:
        """검색 성공률 (found / (found + not_found))."""
        searched = self.found + self.not_found
        if searched == 0:
            return 0.0
        return self.found / searched

    def to_dict(self) -> dict:
        return {
            "field_name": self.field_name,
            "total": self.total,
            "completed": self.completed,
            "found": self.found,
            "confirmed_none": self.confirmed_none,
            "not_found": self.not_found,
            "not_searched": self.not_searched,
            "completion_rate": round(self.completion_rate, 4),
            "success_rate": round(self.success_rate, 4),
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FieldProgress":
        last_updated = data.get("last_updated")
        if isinstance(last_updated, str):
            last_updated = datetime.fromisoformat(last_updated)

        return cls(
            field_name=data["field_name"],
            total=data.get("total", 0),
            completed=data.get("completed", 0),
            found=data.get("found", 0),
            confirmed_none=data.get("confirmed_none", 0),
            not_found=data.get("not_found", 0),
            not_searched=data.get("not_searched", 0),
            last_updated=last_updated,
        )


@dataclass
class FailedEvent:
    """실패한 이벤트 정보."""
    event_id: str
    field_name: str
    error_message: str
    retry_count: int = 0
    max_retries: int = 3
    first_failed_at: datetime = field(default_factory=datetime.now)
    last_failed_at: datetime = field(default_factory=datetime.now)

    @property
    def should_retry(self) -> bool:
        """재시도 해야 하는지."""
        return self.retry_count < self.max_retries

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "field_name": self.field_name,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "first_failed_at": self.first_failed_at.isoformat(),
            "last_failed_at": self.last_failed_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FailedEvent":
        return cls(
            event_id=data["event_id"],
            field_name=data["field_name"],
            error_message=data["error_message"],
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            first_failed_at=datetime.fromisoformat(data["first_failed_at"]),
            last_failed_at=datetime.fromisoformat(data["last_failed_at"]),
        )


@dataclass
class WaveProgress:
    """웨이브별 진행 상황."""
    wave_id: int
    name: str
    status: str = "pending"  # pending, in_progress, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_events: int = 0
    processed_events: int = 0

    @property
    def completion_rate(self) -> float:
        if self.total_events == 0:
            return 0.0
        return self.processed_events / self.total_events

    def to_dict(self) -> dict:
        return {
            "wave_id": self.wave_id,
            "name": self.name,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_events": self.total_events,
            "processed_events": self.processed_events,
            "completion_rate": round(self.completion_rate, 4),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WaveProgress":
        started_at = data.get("started_at")
        completed_at = data.get("completed_at")

        if isinstance(started_at, str):
            started_at = datetime.fromisoformat(started_at)
        if isinstance(completed_at, str):
            completed_at = datetime.fromisoformat(completed_at)

        return cls(
            wave_id=data["wave_id"],
            name=data["name"],
            status=data.get("status", "pending"),
            started_at=started_at,
            completed_at=completed_at,
            total_events=data.get("total_events", 0),
            processed_events=data.get("processed_events", 0),
        )


@dataclass
class CheckpointState:
    """
    체크포인트 상태.

    JSON 구조:
    {
        "version": "1.0",
        "created_at": "...",
        "updated_at": "...",
        "current_wave": 2,
        "current_task": "2.1_phase",
        "status": "in_progress",
        "waves": {...},
        "field_progress": {...},
        "failed_events": [...],
        "retry_queue": [...],
        "resume_command": "..."
    }
    """
    version: str = "1.0"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # 진행 상태
    current_wave: int = 0
    current_task: str = ""
    status: str = "not_started"  # not_started, in_progress, completed, paused, failed

    # 웨이브별 진행 상황
    waves: dict[int, WaveProgress] = field(default_factory=dict)

    # 필드별 진행 상황
    field_progress: dict[str, FieldProgress] = field(default_factory=dict)

    # 실패 이벤트
    failed_events: list[FailedEvent] = field(default_factory=list)
    retry_queue: list[str] = field(default_factory=list)  # event_id 리스트

    # 재개 정보
    resume_command: str = ""
    last_processed_event_id: str = ""

    # 통계
    total_events: int = 0
    processed_events: int = 0
    api_calls: int = 0

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "current_wave": self.current_wave,
            "current_task": self.current_task,
            "status": self.status,
            "waves": {
                str(k): v.to_dict() for k, v in self.waves.items()
            },
            "field_progress": {
                k: v.to_dict() for k, v in self.field_progress.items()
            },
            "failed_events": [e.to_dict() for e in self.failed_events],
            "retry_queue": self.retry_queue,
            "resume_command": self.resume_command,
            "last_processed_event_id": self.last_processed_event_id,
            "total_events": self.total_events,
            "processed_events": self.processed_events,
            "api_calls": self.api_calls,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CheckpointState":
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")

        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        else:
            created_at = datetime.now()

        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        else:
            updated_at = datetime.now()

        # 웨이브 파싱
        waves = {}
        for k, v in data.get("waves", {}).items():
            waves[int(k)] = WaveProgress.from_dict(v)

        # 필드 진행 상황 파싱
        field_progress = {}
        for k, v in data.get("field_progress", {}).items():
            field_progress[k] = FieldProgress.from_dict(v)

        # 실패 이벤트 파싱
        failed_events = [
            FailedEvent.from_dict(e) for e in data.get("failed_events", [])
        ]

        return cls(
            version=data.get("version", "1.0"),
            created_at=created_at,
            updated_at=updated_at,
            current_wave=data.get("current_wave", 0),
            current_task=data.get("current_task", ""),
            status=data.get("status", "not_started"),
            waves=waves,
            field_progress=field_progress,
            failed_events=failed_events,
            retry_queue=data.get("retry_queue", []),
            resume_command=data.get("resume_command", ""),
            last_processed_event_id=data.get("last_processed_event_id", ""),
            total_events=data.get("total_events", 0),
            processed_events=data.get("processed_events", 0),
            api_calls=data.get("api_calls", 0),
        )


class CheckpointManager:
    """
    체크포인트 관리자.

    데이터 수집/보강 진행 상태를 관리합니다.

    주요 기능:
    - 상태 저장/복구 (JSON 파일 기반)
    - 원자적 저장 (임시 파일 -> 이름 변경)
    - 필드별 진행 상황 추적
    - 실패한 이벤트 큐 관리
    - 자동 백업 (10분마다 또는 100건마다)

    Usage:
        manager = CheckpointManager()

        # 상태 복구 또는 새로 시작
        if manager.has_checkpoint():
            manager.load()
        else:
            manager.create()

        # 진행 중 업데이트
        manager.update_progress(event_id="...", field="btd", status="found")

        # 자동 저장 (100건마다 또는 10분마다)
        # 또는 명시적 저장
        manager.save()
    """

    DEFAULT_STATE_FILE = Path("data/enrichment_state.json")
    BACKUP_INTERVAL_SECONDS = 600  # 10분
    BACKUP_INTERVAL_EVENTS = 100

    def __init__(
        self,
        state_file: Path = None,
        auto_save: bool = True,
        backup_interval_seconds: int = None,
        backup_interval_events: int = None,
    ):
        """
        Args:
            state_file: 상태 파일 경로. 기본값은 data/enrichment_state.json
            auto_save: 자동 저장 활성화
            backup_interval_seconds: 자동 백업 간격 (초)
            backup_interval_events: 자동 백업 간격 (이벤트 수)
        """
        self.state_file = Path(state_file) if state_file else self.DEFAULT_STATE_FILE
        self.auto_save = auto_save
        self.backup_interval_seconds = backup_interval_seconds or self.BACKUP_INTERVAL_SECONDS
        self.backup_interval_events = backup_interval_events or self.BACKUP_INTERVAL_EVENTS

        self._state: Optional[CheckpointState] = None
        self._lock = threading.Lock()
        self._events_since_save = 0
        self._last_save_time = time.time()
        self._dirty = False

        # 백업 디렉토리
        self._backup_dir = self.state_file.parent / "checkpoints_backup"

    # ==================== Core Operations ====================

    def create(self, total_events: int = 0) -> CheckpointState:
        """
        새 체크포인트 생성.

        Args:
            total_events: 총 이벤트 수

        Returns:
            새 CheckpointState
        """
        with self._lock:
            self._state = CheckpointState(
                total_events=total_events,
                status="not_started",
            )
            self._dirty = True

            if self.auto_save:
                self._save_internal()

            logger.info(f"Created new checkpoint: {self.state_file}")
            return self._state

    def load(self) -> Optional[CheckpointState]:
        """
        체크포인트 로드.

        Returns:
            CheckpointState 또는 None (파일 없음)
        """
        if not self.state_file.exists():
            logger.warning(f"Checkpoint file not found: {self.state_file}")
            return None

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            with self._lock:
                self._state = CheckpointState.from_dict(data)
                self._dirty = False
                self._last_save_time = time.time()
                self._events_since_save = 0

            logger.info(f"Loaded checkpoint: {self._state.status}, wave={self._state.current_wave}")
            return self._state

        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None

    def save(self, force: bool = False) -> bool:
        """
        체크포인트 저장.

        원자적 저장: 임시 파일에 먼저 쓰고 이름 변경.

        Args:
            force: 강제 저장 (dirty 체크 무시)

        Returns:
            저장 성공 여부
        """
        with self._lock:
            if not force and not self._dirty:
                return True

            return self._save_internal()

    def _save_internal(self) -> bool:
        """
        내부 저장 (락 보유 상태에서 호출).

        원자적 저장을 위해:
        1. 임시 파일에 저장
        2. 임시 파일을 대상 파일로 이름 변경
        """
        if self._state is None:
            return False

        # 디렉토리 생성
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            # 업데이트 시간 갱신
            self._state.updated_at = datetime.now()

            # 임시 파일에 저장 (같은 디렉토리에)
            fd, temp_path = tempfile.mkstemp(
                suffix=".json",
                prefix="checkpoint_",
                dir=self.state_file.parent
            )

            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(self._state.to_dict(), f, ensure_ascii=False, indent=2)

                # 원자적 이름 변경 (Windows에서는 덮어쓰기 필요)
                temp_path = Path(temp_path)
                if os.name == "nt":  # Windows
                    if self.state_file.exists():
                        self.state_file.unlink()
                    temp_path.rename(self.state_file)
                else:  # Unix
                    temp_path.rename(self.state_file)

                self._dirty = False
                self._last_save_time = time.time()
                self._events_since_save = 0

                logger.debug(f"Saved checkpoint: {self.state_file}")
                return True

            except Exception:
                # 실패 시 임시 파일 정리
                try:
                    Path(temp_path).unlink()
                except Exception:
                    pass
                raise

        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            return False

    def has_checkpoint(self) -> bool:
        """체크포인트 파일 존재 여부."""
        return self.state_file.exists()

    @property
    def state(self) -> Optional[CheckpointState]:
        """현재 상태."""
        return self._state

    # ==================== Progress Updates ====================

    def start_wave(self, wave_id: int, name: str, total_events: int = 0):
        """웨이브 시작."""
        with self._lock:
            if self._state is None:
                return

            wave = WaveProgress(
                wave_id=wave_id,
                name=name,
                status="in_progress",
                started_at=datetime.now(),
                total_events=total_events,
            )
            self._state.waves[wave_id] = wave
            self._state.current_wave = wave_id
            self._state.status = "in_progress"
            self._dirty = True

        self._maybe_auto_save()
        logger.info(f"Started wave {wave_id}: {name}")

    def complete_wave(self, wave_id: int):
        """웨이브 완료."""
        with self._lock:
            if self._state is None or wave_id not in self._state.waves:
                return

            wave = self._state.waves[wave_id]
            wave.status = "completed"
            wave.completed_at = datetime.now()
            self._dirty = True

        self._maybe_auto_save()
        logger.info(f"Completed wave {wave_id}")

    def start_task(self, task_name: str):
        """태스크 시작."""
        with self._lock:
            if self._state is None:
                return

            self._state.current_task = task_name
            self._dirty = True

        logger.debug(f"Started task: {task_name}")

    def update_field_progress(
        self,
        field_name: str,
        total: int = None,
        completed: int = None,
        found: int = None,
        confirmed_none: int = None,
        not_found: int = None,
        not_searched: int = None,
    ):
        """
        필드별 진행 상황 업데이트.

        Args:
            field_name: 필드 이름
            total, completed, ...: 증가시킬 값 (None이면 변경 없음)
        """
        with self._lock:
            if self._state is None:
                return

            if field_name not in self._state.field_progress:
                self._state.field_progress[field_name] = FieldProgress(field_name=field_name)

            fp = self._state.field_progress[field_name]

            if total is not None:
                fp.total = total
            if completed is not None:
                fp.completed = completed
            if found is not None:
                fp.found = found
            if confirmed_none is not None:
                fp.confirmed_none = confirmed_none
            if not_found is not None:
                fp.not_found = not_found
            if not_searched is not None:
                fp.not_searched = not_searched

            fp.last_updated = datetime.now()
            self._dirty = True

    def increment_field_stat(
        self,
        field_name: str,
        found: int = 0,
        confirmed_none: int = 0,
        not_found: int = 0,
    ):
        """
        필드 통계 증가.

        Args:
            field_name: 필드 이름
            found, confirmed_none, not_found: 증가량
        """
        with self._lock:
            if self._state is None:
                return

            if field_name not in self._state.field_progress:
                self._state.field_progress[field_name] = FieldProgress(field_name=field_name)

            fp = self._state.field_progress[field_name]
            fp.found += found
            fp.confirmed_none += confirmed_none
            fp.not_found += not_found
            fp.completed = fp.found + fp.confirmed_none + fp.not_found
            fp.last_updated = datetime.now()

            self._events_since_save += 1
            self._dirty = True

        self._maybe_auto_save()

    def update_event_progress(self, event_id: str):
        """
        이벤트 처리 완료.

        Args:
            event_id: 처리된 이벤트 ID
        """
        with self._lock:
            if self._state is None:
                return

            self._state.processed_events += 1
            self._state.last_processed_event_id = event_id

            # 현재 웨이브 업데이트
            if self._state.current_wave in self._state.waves:
                self._state.waves[self._state.current_wave].processed_events += 1

            self._events_since_save += 1
            self._dirty = True

        self._maybe_auto_save()

    def increment_api_calls(self, count: int = 1):
        """API 호출 횟수 증가."""
        with self._lock:
            if self._state is None:
                return

            self._state.api_calls += count
            self._dirty = True

    # ==================== Failed Events ====================

    def add_failed_event(
        self,
        event_id: str,
        field_name: str,
        error_message: str,
    ):
        """
        실패한 이벤트 추가.

        Args:
            event_id: 이벤트 ID
            field_name: 실패한 필드
            error_message: 에러 메시지
        """
        with self._lock:
            if self._state is None:
                return

            # 기존 실패 이벤트 찾기
            existing = None
            for fe in self._state.failed_events:
                if fe.event_id == event_id and fe.field_name == field_name:
                    existing = fe
                    break

            if existing:
                existing.retry_count += 1
                existing.last_failed_at = datetime.now()
                existing.error_message = error_message
            else:
                self._state.failed_events.append(FailedEvent(
                    event_id=event_id,
                    field_name=field_name,
                    error_message=error_message,
                ))

            self._dirty = True

        self._maybe_auto_save()

    def get_retry_queue(self) -> list[FailedEvent]:
        """재시도 가능한 실패 이벤트 목록."""
        with self._lock:
            if self._state is None:
                return []

            return [fe for fe in self._state.failed_events if fe.should_retry]

    def remove_from_failed(self, event_id: str, field_name: str):
        """실패 목록에서 제거 (성공 시)."""
        with self._lock:
            if self._state is None:
                return

            self._state.failed_events = [
                fe for fe in self._state.failed_events
                if not (fe.event_id == event_id and fe.field_name == field_name)
            ]
            self._dirty = True

    def add_to_retry_queue(self, event_id: str):
        """재시도 큐에 추가."""
        with self._lock:
            if self._state is None:
                return

            if event_id not in self._state.retry_queue:
                self._state.retry_queue.append(event_id)
                self._dirty = True

    def pop_from_retry_queue(self) -> Optional[str]:
        """재시도 큐에서 하나 꺼내기."""
        with self._lock:
            if self._state is None or not self._state.retry_queue:
                return None

            event_id = self._state.retry_queue.pop(0)
            self._dirty = True
            return event_id

    # ==================== Status ====================

    def pause(self, resume_command: str = ""):
        """일시 중지."""
        with self._lock:
            if self._state is None:
                return

            self._state.status = "paused"
            self._state.resume_command = resume_command
            self._dirty = True

        self.save(force=True)
        logger.info(f"Paused checkpoint. Resume: {resume_command}")

    def resume(self):
        """재개."""
        with self._lock:
            if self._state is None:
                return

            self._state.status = "in_progress"
            self._dirty = True

        logger.info("Resumed checkpoint")

    def complete(self):
        """완료 처리."""
        with self._lock:
            if self._state is None:
                return

            self._state.status = "completed"
            self._dirty = True

        self.save(force=True)
        logger.info("Checkpoint completed")

    def fail(self, error_message: str = ""):
        """실패 처리."""
        with self._lock:
            if self._state is None:
                return

            self._state.status = "failed"
            self._dirty = True

        self.save(force=True)
        logger.error(f"Checkpoint failed: {error_message}")

    # ==================== Backup ====================

    def create_backup(self, suffix: str = "") -> Optional[Path]:
        """
        백업 생성.

        Args:
            suffix: 백업 파일명에 추가할 접미사

        Returns:
            백업 파일 경로 또는 None
        """
        if not self.state_file.exists():
            return None

        self._backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"checkpoint_{timestamp}{suffix}.json"
        backup_path = self._backup_dir / backup_name

        try:
            shutil.copy2(self.state_file, backup_path)
            logger.info(f"Created backup: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None

    def restore_from_backup(self, backup_path: Path) -> bool:
        """
        백업에서 복구.

        Args:
            backup_path: 백업 파일 경로

        Returns:
            복구 성공 여부
        """
        if not backup_path.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return False

        try:
            shutil.copy2(backup_path, self.state_file)
            return self.load() is not None
        except Exception as e:
            logger.error(f"Failed to restore from backup: {e}")
            return False

    def list_backups(self) -> list[Path]:
        """백업 목록."""
        if not self._backup_dir.exists():
            return []

        return sorted(
            self._backup_dir.glob("checkpoint_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

    def cleanup_old_backups(self, keep_count: int = 10):
        """
        오래된 백업 삭제.

        Args:
            keep_count: 유지할 백업 수
        """
        backups = self.list_backups()

        for old_backup in backups[keep_count:]:
            try:
                old_backup.unlink()
                logger.debug(f"Deleted old backup: {old_backup}")
            except Exception as e:
                logger.warning(f"Failed to delete backup {old_backup}: {e}")

    # ==================== Auto Save ====================

    def _maybe_auto_save(self):
        """자동 저장 조건 확인 및 실행."""
        if not self.auto_save:
            return

        should_save = False

        # 이벤트 수 기반
        if self._events_since_save >= self.backup_interval_events:
            should_save = True

        # 시간 기반
        if time.time() - self._last_save_time >= self.backup_interval_seconds:
            should_save = True

        if should_save:
            self.save()

    # ==================== Reports ====================

    def get_summary(self) -> dict:
        """현재 상태 요약."""
        with self._lock:
            if self._state is None:
                return {"error": "No checkpoint loaded"}

            return {
                "status": self._state.status,
                "current_wave": self._state.current_wave,
                "current_task": self._state.current_task,
                "total_events": self._state.total_events,
                "processed_events": self._state.processed_events,
                "completion_rate": (
                    self._state.processed_events / self._state.total_events
                    if self._state.total_events > 0 else 0
                ),
                "failed_events": len(self._state.failed_events),
                "retry_queue": len(self._state.retry_queue),
                "api_calls": self._state.api_calls,
                "updated_at": self._state.updated_at.isoformat(),
            }

    def get_field_summary(self) -> dict[str, dict]:
        """필드별 진행 요약."""
        with self._lock:
            if self._state is None:
                return {}

            return {
                name: {
                    "completion_rate": round(fp.completion_rate * 100, 1),
                    "success_rate": round(fp.success_rate * 100, 1),
                    "found": fp.found,
                    "confirmed_none": fp.confirmed_none,
                    "not_found": fp.not_found,
                }
                for name, fp in self._state.field_progress.items()
            }

    def print_report(self):
        """진행 상황 리포트 출력."""
        summary = self.get_summary()
        field_summary = self.get_field_summary()

        lines = [
            "=" * 60,
            "Checkpoint Status Report",
            "=" * 60,
            "",
            f"Status: {summary.get('status', 'unknown')}",
            f"Wave: {summary.get('current_wave', 0)}",
            f"Task: {summary.get('current_task', 'N/A')}",
            "",
            f"Progress: {summary.get('processed_events', 0)}/{summary.get('total_events', 0)} "
            f"({summary.get('completion_rate', 0)*100:.1f}%)",
            f"Failed: {summary.get('failed_events', 0)}",
            f"Retry Queue: {summary.get('retry_queue', 0)}",
            f"API Calls: {summary.get('api_calls', 0)}",
            "",
            "--- Field Progress ---",
        ]

        for field_name, fs in field_summary.items():
            bar = "#" * int(fs["completion_rate"] / 10) + "-" * (10 - int(fs["completion_rate"] / 10))
            lines.append(
                f"{field_name:<25} [{bar}] {fs['completion_rate']:5.1f}% "
                f"(found={fs['found']}, none={fs['confirmed_none']}, miss={fs['not_found']})"
            )

        lines.extend([
            "",
            f"Updated: {summary.get('updated_at', 'N/A')}",
            "=" * 60,
        ])

        print("\n".join(lines))


__all__ = [
    "CheckpointManager",
    "CheckpointState",
    "FieldProgress",
    "FailedEvent",
    "WaveProgress",
]
