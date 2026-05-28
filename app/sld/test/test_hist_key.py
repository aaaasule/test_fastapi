"""历史业务键：EFMS 字段别名兼容测试。"""
from __future__ import annotations

import unittest

from app.sld.validators.changes.added import AddedRule
from app.sld.validators.changes.common import build_history_index, hist_key
from app.sld.models import SldDevice


EFMS_ELD_ROW = {
    "equipmentCode": "ARCAA03",
    "equSubShort": "Fire Extinguisher",
    "status": "add",
    "centerPointX": "275272.3438",
    "centerPointY": "166997.9624",
}


class TestHistKey(unittest.TestCase):
    def test_efms_equipment_code_and_equ_sub_short(self) -> None:
        self.assertEqual(hist_key(EFMS_ELD_ROW), "ARCAA03+Fire Extinguisher")

    def test_legacy_id_equ_fields(self) -> None:
        row = {"idEqu": "A01", "idEquSubShort": "PUMP"}
        self.assertEqual(hist_key(row), "A01+PUMP")

    def test_code_only_fallback(self) -> None:
        self.assertEqual(hist_key({"code": "ESH"}), "ESH+")

    def test_added_rule_not_marked_when_efms_history_matches(self) -> None:
        history = build_history_index([EFMS_ELD_ROW])
        device = SldDevice(id_equ="ARCAA03", id_equ_sub_short="Fire Extinguisher")
        issues = AddedRule().check([device], history)
        self.assertEqual(issues, [])
        self.assertIsNone(device.operation)


if __name__ == "__main__":
    unittest.main()
