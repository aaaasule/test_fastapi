import ezdxf


def collect_attribs_by_id_short(doc, id_short_value: str) -> list[dict[str, str]]:
    target = (id_short_value or "").strip()
    results: list[dict[str, str]] = []

    def process_msp(msp):
        for insert in msp.query("INSERT"):
            row: dict[str, str] = {}
            id_short_ok = False
            for attrib in getattr(insert, "attribs", []):
                tag = str(getattr(attrib.dxf, "tag", "") or "").strip()
                text = str(getattr(attrib.dxf, "text", "") or "")
                row[tag] = text
                if tag.upper() == "ID_SHORT" and text.strip() == target:
                    id_short_ok = True
            if id_short_ok:
                results.append(row)

    process_msp(doc.modelspace())
    # 若还要布局：
    # for layout in doc.layouts:
    #     if layout.name != "Model":
    #         process_msp(layout)

    return results


if __name__ == "__main__":
    doc = ezdxf.readfile("doc/write_fid/YMTC^FID.ES^FAB2^F2.dxf")
    rows = collect_attribs_by_id_short(doc, "F21-1-1GPB-N3-01-20Q22")
    for i, d in enumerate(rows):
        print(f"match {i}:", d)
