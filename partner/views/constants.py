# django_ma/partner/views/constants.py
# ------------------------------------------------------------
# ✅ 공용 상수 모음
# ------------------------------------------------------------

from typing import Dict, List

# NOTE:
# - 기존 코드에서는 BRANCH_PARTS를 고정 딕셔너리로 두고, 실제 part/branch 목록은
#   CustomUser 데이터를 통해 얻는 경우가 많습니다.
# - 기존 구조를 유지하되, 필요하면 여기에서만 수정하도록 분리합니다.

BRANCH_PARTS: Dict[str, List[str]] = {
    "MA사업1부": [],
    "MA사업2부": [],
    "MA사업3부": [],
    "MA사업4부": [],
    "MA사업5부": [],
}
