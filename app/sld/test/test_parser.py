from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import patch

from app.sld import parser


class _FakeEntity:
    def __init__(self, attrs: dict[str, str]) -> None:
        self.dxf = SimpleNamespace(
            layer="100_DBS 5K",
            name="DEVICE_BLOCK",
            insert=SimpleNamespace(x=1.0, y=2.0, z=0.0),
            rotation=0.0,
            color=256,
            handle=f"H{len(attrs)}",
        )
        self.attribs = [
            SimpleNamespace(dxf=SimpleNamespace(tag=tag, text=text))
            for tag, text in attrs.items()
        ]

    def dxftype(self) -> str:
        return "INSERT"


class _FakeDoc:
    blocks = {"DEVICE_BLOCK"}

    def __init__(self, entities: list[_FakeEntity]) -> None:
        self._entities = entities

    def modelspace(self) -> list[_FakeEntity]:
        return self._entities


class ParseSldDxfTest(TestCase):
    def test_keeps_blocks_with_id_equ_sub_short_tag_even_when_empty(self) -> None:
        with TemporaryDirectory() as tmp:
            dxf_path = Path(tmp) / "sample.dxf"
            dxf_path.write_text("0\nEOF\n", encoding="utf-8")

            doc = _FakeDoc(
                [
                    _FakeEntity({"ID_EQU": "EQP001"}),
                    _FakeEntity({"ID_EQUSUBSHORT": "SUB001"}),
                    _FakeEntity({"ID_EQU_SUB_SHORT": ""}),
                    _FakeEntity({"TOOL_ID": "TOOL_ONLY"}),
                    _FakeEntity({"MODEL": "MODEL_ONLY"}),
                ]
            )

            with (
                patch.object(parser.ezdxf, "readfile", return_value=doc),
                patch.object(parser.bbox, "extents", return_value=None),
            ):
                devices = parser.parse_sld_dxf(dxf_path)

        self.assertEqual(
            [(d.id_equ, d.id_equ_sub_short, d.tool_id) for d in devices],
            [
                (None, "SUB001", None),
                (None, None, None),
            ],
        )


if __name__ == "__main__":
    main()
