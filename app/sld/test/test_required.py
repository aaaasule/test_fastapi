"""RequiredRule：无 tag vs 有 tag 但值为空。"""
from __future__ import annotations

import unittest

from app.sld.models import SldDevice, SldFileContext
from app.sld.validators.specs.required import RequiredRule


def _run(devices: list[SldDevice]) -> list:
    ctx = SldFileContext(
        file_path="/tmp/x.dxf",
        filename_stem="C^SLD^B^L",
        company_token="C",
        building_token="B",
        level_token="L",
        allowed_owner_codes=frozenset(),
    )
    return RequiredRule().check(ctx, devices)


class RequiredRuleTest(unittest.TestCase):
    def test_id_equ_tag_present_empty_is_required_not_missing(self):
        d = SldDevice(
            id_equ=None,
            id_equ_sub_short="PUMP",
            owner="AL Lab",
            vendor="Edwards",
            model="XDS35i",
            raw_attrib_tags=["ID_EQU", "ID_EQUSUBSHORT", "OWNER", "VENDOR", "MODEL"],
        )
        issues = _run([d])
        required = [i for i in issues if i.name == "必填项缺失" and "ID_EQU" in i.description]
        missing_id_equ = [
            i for i in issues if i.name == "关键属性缺失" and "ID_EQU" in i.description
        ]
        self.assertEqual(len(required), 1)
        self.assertIn("必填项未填写：ID_EQU", required[0].description)
        self.assertEqual(missing_id_equ, [])

    def test_id_equ_no_tag_is_missing(self):
        d = SldDevice(
            id_equ=None,
            id_equ_sub_short="PUMP",
            raw_attrib_tags=["ID_EQUSUBSHORT"],
        )
        issues = _run([d])
        missing = [i for i in issues if i.name == "关键属性缺失" and "ID_EQU" in i.description]
        self.assertEqual(len(missing), 1)
        self.assertIn("缺少关键业务属性：ID_EQU", missing[0].description)

    def test_vendor_tag_present_empty_is_required_warning(self):
        d = SldDevice(
            id_equ="EQ01",
            id_equ_sub_short="PUMP",
            vendor=None,
            raw_attrib_tags=["ID_EQU", "ID_EQUSUBSHORT", "VENDOR"],
        )
        issues = _run([d])
        warnings = [i for i in issues if i.type == "warning" and i.name == "必填项缺失"]
        self.assertTrue(any("VENDOR" in i.description for i in warnings))

    def test_vendor_no_tag_is_missing_warning(self):
        d = SldDevice(
            id_equ="EQ01",
            id_equ_sub_short="PUMP",
            vendor=None,
            raw_attrib_tags=["ID_EQU", "ID_EQUSUBSHORT"],
        )
        issues = _run([d])
        warnings = [i for i in issues if i.type == "warning" and i.name == "关键属性缺失"]
        self.assertTrue(any("VENDOR" in i.description for i in warnings))


if __name__ == "__main__":
    unittest.main()
