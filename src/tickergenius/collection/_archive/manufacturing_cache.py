"""
Manufacturing Cache - 제조 정보 캐시 레이어
==========================================
Wave 2.5: 30일 갱신 캐시

필드:
- warning_letter_date: FDA Warning Letters DB
- fda_483_date: FDA 483 DB
- fda_483_observations: 관찰 수
- cdmo_name: SEC 10-K manufacturing agreement
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

from tickergenius.schemas.base import StatusField

logger = logging.getLogger(__name__)

# 캐시 설정
CACHE_TTL_DAYS = 30
CACHE_DIR = Path("data/cache/manufacturing")


class ManufacturingCache:
    """회사별 제조 정보 캐시."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, company_name: str) -> Path:
        """회사별 캐시 파일 경로."""
        safe_name = "".join(c if c.isalnum() else "_" for c in company_name.lower())
        return self.cache_dir / f"{safe_name}.json"

    def _is_cache_valid(self, cache_data: dict) -> bool:
        """캐시 유효성 확인 (30일 이내)."""
        cached_at = cache_data.get("cached_at")
        if not cached_at:
            return False

        try:
            cached_dt = datetime.fromisoformat(cached_at)
            age = datetime.utcnow() - cached_dt
            return age < timedelta(days=CACHE_TTL_DAYS)
        except (ValueError, TypeError):
            return False

    def get_cached(self, company_name: str) -> Optional[dict]:
        """캐시된 제조 정보 조회."""
        cache_path = self._cache_path(company_name)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if self._is_cache_valid(data):
                logger.debug(f"Cache hit for {company_name}")
                return data
            else:
                logger.debug(f"Cache expired for {company_name}")
                return None

        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Cache read error for {company_name}: {e}")
            return None

    def set_cached(self, company_name: str, data: dict) -> None:
        """제조 정보 캐시 저장."""
        cache_path = self._cache_path(company_name)

        cache_data = {
            "company_name": company_name,
            "cached_at": datetime.utcnow().isoformat(),
            **data,
        }

        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, default=str)
            logger.debug(f"Cached manufacturing data for {company_name}")
        except IOError as e:
            logger.warning(f"Cache write error for {company_name}: {e}")

    async def get_or_fetch(
        self,
        company_name: str,
        fetch_func: Optional[callable] = None,
    ) -> dict:
        """
        캐시에서 조회하거나 새로 수집.

        Returns:
            {
                "warning_letter_date": StatusField[date],
                "fda_483_date": StatusField[date],
                "fda_483_observations": StatusField[int],
                "cdmo_name": StatusField[str],
            }
        """
        # 캐시 확인
        cached = self.get_cached(company_name)
        if cached:
            return self._parse_cached(cached)

        # 수집 함수가 없으면 not_searched 반환
        if not fetch_func:
            return self._empty_result()

        # 새로 수집
        try:
            data = await fetch_func(company_name)
            self.set_cached(company_name, data)
            return self._parse_cached(data)
        except Exception as e:
            logger.error(f"Manufacturing fetch error for {company_name}: {e}")
            return self._empty_result(error=str(e))

    def _parse_cached(self, data: dict) -> dict:
        """캐시 데이터를 StatusField로 변환."""
        result = {}

        # Warning Letter
        wl_date = data.get("warning_letter_date")
        if wl_date:
            if isinstance(wl_date, str):
                wl_date = date.fromisoformat(wl_date)
            result["warning_letter_date"] = StatusField.found(
                value=wl_date,
                source="fda_warning_letters_db",
                confidence=0.95,
                tier=1,
            )
        elif data.get("warning_letter_searched"):
            result["warning_letter_date"] = StatusField.confirmed_none("fda_warning_letters_db")
        else:
            result["warning_letter_date"] = StatusField.not_searched()

        # FDA 483
        fda_483_date = data.get("fda_483_date")
        if fda_483_date:
            if isinstance(fda_483_date, str):
                fda_483_date = date.fromisoformat(fda_483_date)
            result["fda_483_date"] = StatusField.found(
                value=fda_483_date,
                source="fda_483_db",
                confidence=0.95,
                tier=1,
            )
        elif data.get("fda_483_searched"):
            result["fda_483_date"] = StatusField.confirmed_none("fda_483_db")
        else:
            result["fda_483_date"] = StatusField.not_searched()

        # FDA 483 Observations
        obs_count = data.get("fda_483_observations")
        if obs_count is not None:
            result["fda_483_observations"] = StatusField.found(
                value=obs_count,
                source="fda_483_db",
                confidence=0.95,
                tier=1,
            )
        else:
            result["fda_483_observations"] = StatusField.not_searched()

        # CDMO Name
        cdmo = data.get("cdmo_name")
        if cdmo:
            result["cdmo_name"] = StatusField.found(
                value=cdmo,
                source="sec_10k",
                confidence=0.8,
                tier=2,
            )
        elif data.get("cdmo_searched"):
            result["cdmo_name"] = StatusField.confirmed_none("sec_10k")
        else:
            result["cdmo_name"] = StatusField.not_searched()

        return result

    def _empty_result(self, error: Optional[str] = None) -> dict:
        """빈 결과 반환."""
        return {
            "warning_letter_date": StatusField.not_searched(),
            "fda_483_date": StatusField.not_searched(),
            "fda_483_observations": StatusField.not_searched(),
            "cdmo_name": StatusField.not_searched(),
            "error": error,
        }

    def invalidate(self, company_name: str) -> bool:
        """캐시 무효화."""
        cache_path = self._cache_path(company_name)
        if cache_path.exists():
            cache_path.unlink()
            logger.info(f"Invalidated cache for {company_name}")
            return True
        return False

    def clear_all(self) -> int:
        """전체 캐시 삭제."""
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
            count += 1
        logger.info(f"Cleared {count} cache files")
        return count


# 편의 함수
_cache_instance: Optional[ManufacturingCache] = None


def get_manufacturing_cache() -> ManufacturingCache:
    """싱글톤 캐시 인스턴스."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ManufacturingCache()
    return _cache_instance


async def get_manufacturing_info(company_name: str) -> dict:
    """편의 함수: 회사별 제조 정보 조회."""
    cache = get_manufacturing_cache()
    return await cache.get_or_fetch(company_name)


__all__ = [
    "ManufacturingCache",
    "get_manufacturing_cache",
    "get_manufacturing_info",
    "CACHE_TTL_DAYS",
]
