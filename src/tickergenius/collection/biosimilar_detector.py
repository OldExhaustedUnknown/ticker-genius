"""
Biosimilar Detector - 바이오시밀러 판별
======================================
Wave 2.5: is_biosimilar 필드 수집

판별 순서:
1. 웹서치로 "{drug_name} biosimilar FDA" 검색
2. FDA Purple Book API 조회
3. 접미사 패턴 (-xxxx) 확인
"""

from __future__ import annotations

import re
import logging
from typing import Optional

from tickergenius.schemas.base import StatusField

logger = logging.getLogger(__name__)

# 바이오시밀러 접미사 패턴 (예: adalimumab-adbm)
BIOSIMILAR_SUFFIX_PATTERN = re.compile(r"-[a-z]{4}$", re.IGNORECASE)

# 세포치료제 패턴 (NOT biosimilars)
CELL_THERAPY_PATTERNS = [
    r"autoleucel",      # CAR-T cells
    r"autotemcel",      # Gene-modified cells
    r"-cel",            # -cel suffix (e.g., lovo-cel, beti-cel)
    r"maraleucel",      # lisocabtagene maraleucel
    r"vicleucel",       # idecabtagene vicleucel
    r"deramiocel",      # CAP-1002
    r"lifileucel",      # TIL therapy
    r"tabelecleucel",   # EBV-specific T cells
]
CELL_THERAPY_REGEX = re.compile("|".join(CELL_THERAPY_PATTERNS), re.IGNORECASE)

# 유전자치료제 패턴 (NOT biosimilars)
GENE_THERAPY_PATTERNS = [
    r"parvovec",        # AAV gene therapies
    r"geperpavec",      # Gene-modified virus
    r"AAV",             # Adeno-associated virus
    r"gene therapy",
    r"zamikeracel",     # Gene-modified cells like prademagene
]
GENE_THERAPY_REGEX = re.compile("|".join(GENE_THERAPY_PATTERNS), re.IGNORECASE)

# 백신 패턴 (NOT biosimilars)
VACCINE_PATTERNS = [
    r"vaccine",
    r"vax",
    r"RSVpreF",
    r"mRNA-\d+",       # mRNA vaccines like mRNA-1345
    r"pneumococcal.*conjugate",
    r"meningococcal",
    r"hepatitis.*vaccine",
    r"anthrax.*vaccine",
]
VACCINE_REGEX = re.compile("|".join(VACCINE_PATTERNS), re.IGNORECASE)

# 알려진 바이오시밀러 매핑 (캐시/하드코딩)
KNOWN_BIOSIMILARS = {
    # Adalimumab (Humira) biosimilars
    "adalimumab-adbm": True,  # Cyltezo
    "adalimumab-adaz": True,  # Hyrimoz
    "adalimumab-afzb": True,  # Abrilada
    "adalimumab-atto": True,  # Amjevita
    "adalimumab-bwwd": True,  # Hadlima
    "adalimumab-fkjp": True,  # Hulio
    "adalimumab-aacf": True,  # Idacio
    "adalimumab-aaty": True,  # Yusimry
    "hulio": True,  # Brand name for adalimumab-fkjp
    "chs-1420": True,  # Coherus adalimumab biosimilar

    # Infliximab (Remicade) biosimilars
    "infliximab-dyyb": True,  # Inflectra
    "infliximab-abda": True,  # Renflexis
    "infliximab-qbtx": True,  # Ixifi
    "infliximab-axxq": True,  # Avsola

    # Trastuzumab (Herceptin) biosimilars
    "trastuzumab-dkst": True,  # Ogivri
    "trastuzumab-pkrb": True,  # Herzuma
    "trastuzumab-dttb": True,  # Ontruzant
    "trastuzumab-qyyp": True,  # Trazimera
    "trastuzumab-anns": True,  # Kanjinti

    # Bevacizumab (Avastin) biosimilars
    "bevacizumab-awwb": True,  # Mvasi
    "bevacizumab-bvzr": True,  # Zirabev
    "bevacizumab-vikg": True,  # Lytenava (ONS-5010)
    "lytenava": True,  # ONS-5010 ophthalmic bevacizumab
    "chs-201": True,  # Coherus bevacizumab biosimilar

    # Rituximab (Rituxan) biosimilars
    "rituximab-abbs": True,  # Truxima
    "rituximab-pvvr": True,  # Ruxience
    "rituximab-arrx": True,  # Riabni

    # Pegfilgrastim (Neulasta) biosimilars
    "pegfilgrastim-jmdb": True,  # Fulphila
    "pegfilgrastim-cbqv": True,  # Udenyca
    "pegfilgrastim-apgf": True,  # Nyvepria
    "nyvepria": True,  # Brand name for pegfilgrastim-apgf
    "pegfilgrastim-bmez": True,  # Ziextenzo

    # Epoetin alfa (Epogen/Procrit) biosimilars
    "epoetin alfa-epbx": True,  # Retacrit

    # Insulin glargine (Lantus) biosimilars
    "insulin glargine-yfgn": True,  # Semglee
    "semglee": True,  # Brand name

    # Golimumab (Simponi) biosimilars
    "avt05": True,  # Alvotech golimumab biosimilar

    # Filgrastim (Neupogen) biosimilars
    "filgrastim-sndz": True,  # Zarxio
    "filgrastim-aafi": True,  # Nivestym
    "zarxio": True,

    # Ranibizumab (Lucentis) biosimilars
    "ranibizumab-nuna": True,  # Byooviz
    "byooviz": True,

    # Etanercept (Enbrel) biosimilars
    "etanercept-szzs": True,  # Erelzi
    "etanercept-ykro": True,  # Eticovo
    "erelzi": True,
}

# 오리지널 생물학적 제제 (바이오시밀러가 아님)
KNOWN_ORIGINATOR_BIOLOGICS = {
    # Major monoclonal antibodies
    "humira", "remicade", "herceptin", "avastin", "rituxan",
    "neulasta", "epogen", "procrit", "enbrel", "neupogen",
    "lantus", "lucentis", "eylea",
    # Checkpoint inhibitors
    "opdivo", "keytruda", "tecentriq", "imfinzi", "libtayo", "yervoy",
    # Other major biologics
    "dupixent", "cosentyx", "nucala", "darzalex", "sarclisa",
    "repatha", "blincyto", "reblozyl", "tepezza",
    "entyvio", "spinraza", "leqembi", "vyvgart",
    # Original CAR-T (not biosimilars, but originators)
    "abecma", "breyanzi", "carvykti", "kymriah", "yescarta", "tecartus",
}

# 오리지네이터 키워드 (약물명에 포함된 경우)
ORIGINATOR_KEYWORDS = [
    "opdivo", "keytruda", "dupixent", "darzalex", "nucala",
    "cosentyx", "reblozyl", "repatha", "blincyto", "tepezza",
    "vyvgart", "padcev", "sarclisa", "entyvio", "spinraza",
    "leqembi", "winrevair", "anktiva", "rybrevant",
]


class BiosimilarDetector:
    """바이오시밀러 판별기."""

    def __init__(self):
        pass

    async def detect(
        self,
        drug_name: str,
        generic_name: Optional[str] = None,
        approval_type: Optional[str] = None,
    ) -> StatusField[bool]:
        """
        바이오시밀러 여부 판별.

        Args:
            drug_name: 약물명 (예: "Cyltezo", "adalimumab-adbm")
            generic_name: 성분명 (예: "adalimumab-adbm")
            approval_type: 신청 유형 (예: "bla", "biosimilar")

        Returns:
            StatusField[bool]: is_biosimilar
        """
        drug_lower = drug_name.lower().strip()
        generic_lower = (generic_name or "").lower().strip()
        combined_text = f"{drug_lower} {generic_lower}"

        # 1. approval_type이 명시적으로 biosimilar인 경우
        if approval_type and "biosimilar" in approval_type.lower():
            return StatusField.found(
                value=True,
                source="approval_type",
                confidence=0.99,
                tier=1,
            )

        # 2. generic_name에 "biosimilar" 포함
        if "biosimilar" in generic_lower:
            return StatusField.found(
                value=True,
                source="generic_name_contains_biosimilar",
                confidence=0.95,
                tier=2,
                evidence=[f"generic_name contains biosimilar: {generic_lower}"],
            )

        # 3. 알려진 바이오시밀러 목록 확인
        if generic_lower in KNOWN_BIOSIMILARS:
            return StatusField.found(
                value=True,
                source="known_biosimilars_db",
                confidence=0.99,
                tier=1,
                evidence=[f"matched: {generic_lower}"],
            )

        if drug_lower in KNOWN_BIOSIMILARS:
            return StatusField.found(
                value=True,
                source="known_biosimilars_db",
                confidence=0.99,
                tier=1,
                evidence=[f"matched: {drug_lower}"],
            )

        # 4. 알려진 오리지널 생물학적 제제 확인 (정확한 매칭)
        if drug_lower in KNOWN_ORIGINATOR_BIOLOGICS:
            return StatusField.found(
                value=False,
                source="known_originators_db",
                confidence=0.95,
                tier=1,
                evidence=[f"originator: {drug_lower}"],
            )

        # 5. 오리지네이터 키워드 포함 여부 (부분 매칭)
        for keyword in ORIGINATOR_KEYWORDS:
            if keyword in drug_lower:
                return StatusField.found(
                    value=False,
                    source="originator_keyword_match",
                    confidence=0.9,
                    tier=2,
                    evidence=[f"contains originator keyword: {keyword}"],
                )

        # 6. 세포치료제 패턴 (NOT biosimilar)
        if CELL_THERAPY_REGEX.search(combined_text):
            match = CELL_THERAPY_REGEX.search(combined_text)
            return StatusField.found(
                value=False,
                source="cell_therapy_pattern",
                confidence=0.95,
                tier=2,
                evidence=[f"cell therapy pattern: {match.group() if match else 'matched'}"],
            )

        # 7. 유전자치료제 패턴 (NOT biosimilar)
        if GENE_THERAPY_REGEX.search(combined_text):
            match = GENE_THERAPY_REGEX.search(combined_text)
            return StatusField.found(
                value=False,
                source="gene_therapy_pattern",
                confidence=0.95,
                tier=2,
                evidence=[f"gene therapy pattern: {match.group() if match else 'matched'}"],
            )

        # 8. 백신 패턴 (NOT biosimilar)
        if VACCINE_REGEX.search(combined_text):
            match = VACCINE_REGEX.search(combined_text)
            return StatusField.found(
                value=False,
                source="vaccine_pattern",
                confidence=0.95,
                tier=2,
                evidence=[f"vaccine pattern: {match.group() if match else 'matched'}"],
            )

        # 9. 접미사 패턴 확인 (-xxxx)
        for name in [generic_lower, drug_lower]:
            if name and BIOSIMILAR_SUFFIX_PATTERN.search(name):
                return StatusField.found(
                    value=True,
                    source="suffix_pattern",
                    confidence=0.85,
                    tier=3,
                    evidence=[f"suffix match: {name}"],
                )

        # 10. NDA/sNDA/510k/DMG는 바이오시밀러 아님
        if approval_type and approval_type.lower() in ["nda", "snda", "505b2", "anda", "510k", "dmg"]:
            return StatusField.found(
                value=False,
                source="approval_type_non_bla",
                confidence=0.95,
                tier=2,
                evidence=[f"approval_type={approval_type}"],
            )

        # 11. BLA인 경우, 일반 monoclonal antibody 패턴으로 False 추정
        # (mab suffix without biosimilar suffix => likely originator)
        if approval_type and approval_type.lower() == "bla":
            # Check for mab suffix (monoclonal antibody)
            for name in [generic_lower, drug_lower]:
                if name.endswith("mab") or "mumab" in name or "zumab" in name or "ximab" in name:
                    # This is a monoclonal antibody without biosimilar suffix
                    return StatusField.found(
                        value=False,
                        source="mab_without_biosimilar_suffix",
                        confidence=0.8,
                        tier=3,
                        evidence=[f"monoclonal antibody without -xxxx suffix: {name}"],
                    )

        # 12. 판별 불가
        return StatusField.not_found(["known_db", "patterns", "suffix_pattern", "approval_type"])

    def detect_sync(
        self,
        drug_name: str,
        generic_name: Optional[str] = None,
        approval_type: Optional[str] = None,
    ) -> StatusField[bool]:
        """동기 버전 (async 불필요한 경우)."""
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self.detect(drug_name, generic_name, approval_type)
        )


async def detect_biosimilar(
    drug_name: str,
    generic_name: Optional[str] = None,
    approval_type: Optional[str] = None,
) -> StatusField[bool]:
    """편의 함수: 바이오시밀러 판별."""
    detector = BiosimilarDetector()
    return await detector.detect(drug_name, generic_name, approval_type)


__all__ = ["BiosimilarDetector", "detect_biosimilar", "KNOWN_BIOSIMILARS"]
