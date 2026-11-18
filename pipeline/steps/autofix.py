"""BƯỚC 2/4 — Sửa tự động những lỗi bắt buộc mà máy sửa được AN TOÀN.   ★★

Test:  pytest tests/test_autofix.py -q

`fix(ds, issues, cfg) -> list[dict]`: duyệt `issues` (chỉ lỗi severity ERROR), sửa thẳng vào thư mục `ds`,
và trả về danh sách thay đổi; mỗi phần tử có khoá: image, line, action, before, after
(đây chính là file `03_fixes.csv` — bằng chứng pipeline đã làm gì, người có thể kiểm lại).

| code lỗi                                       | cách sửa                                    | action           |
|------------------------------------------------|---------------------------------------------|------------------|
| BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO, DUP_BOX    | xoá dòng đó khỏi file nhãn                  | "drop_line"      |
| BOX_OUT_OF_IMAGE                               | cắt box về trong [0,1] (giữ nguyên lớp)     | "clip_box"       |
| MISSING_LABEL_FILE                             | KHÔNG sửa file (máy không thể bịa nhãn): ghi 1 dòng fix, before="(không có file)", after="chuyển người gán" | "needs_label" |
| BAD_CLASS_NAME                                 | ghi lại `names` trong data.yaml đúng `cfg["classes"]` | "rename_classes" |
| DUP_IMAGE_*, LEAK_TEST, CORRUPT_IMAGE, BAD_SIZE| xoá ảnh + nhãn khỏi `ds`                    | "remove_image"   |
"""
from collections import defaultdict
from pathlib import Path
import yaml

from ..common import ERROR, parse_yolo_line

DROP_CODES = {"BAD_FORMAT", "BAD_CLASS_ID", "BOX_ZERO", "DUP_BOX"}
REMOVE_IMAGE_CODES = {"LEAK_TEST", "CORRUPT_IMAGE", "BAD_SIZE"}


def fix(ds, issues, cfg):
    # Chỉ xử lý lỗi ERROR
    err_issues = [i for i in issues if i.severity == ERROR]
    fixes = []

    # 1. Sửa BAD_CLASS_NAME trong data.yaml
    if any(i.code == "BAD_CLASS_NAME" for i in err_issues):
        if ds.yaml_path.exists():
            try:
                data = yaml.safe_load(ds.yaml_path.read_text(encoding="utf-8")) or {}
            except Exception:
                data = {}
            old_names = data.get("names", [])
            data["names"] = list(cfg["classes"])
            ds.yaml_path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
            fixes.append({
                "image": "data.yaml",
                "line": "",
                "action": "rename_classes",
                "before": str(old_names),
                "after": str(cfg["classes"]),
            })

    # 2. Xoá ảnh + nhãn cho các lỗi cấp ảnh (remove_image)
    removed_stems = set()
    for i in err_issues:
        if i.code in REMOVE_IMAGE_CODES or i.code.startswith("DUP_IMAGE"):
            stem = i.image
            if stem not in removed_stems:
                removed_stems.add(stem)
                img_p = ds.image_path(stem)
                if img_p and img_p.exists():
                    img_p.unlink()
                lbl_p = ds.label_path(stem)
                if lbl_p.exists():
                    lbl_p.unlink()
                fixes.append({
                    "image": stem,
                    "line": "",
                    "action": "remove_image",
                    "before": "exists",
                    "after": "removed",
                })

    # 3. Ghi nhận MISSING_LABEL_FILE (needs_label)
    for i in err_issues:
        if i.code == "MISSING_LABEL_FILE":
            stem = i.image
            if stem in removed_stems:
                continue
            fixes.append({
                "image": stem,
                "line": "",
                "action": "needs_label",
                "before": "(không có file)",
                "after": "chuyển người gán",
            })

    # 4. Sửa các lỗi cấp dòng trong file nhãn (drop_line, clip_box)
    line_issues_by_stem = defaultdict(lambda: defaultdict(list))
    for i in err_issues:
        if i.line is not None and (i.code in DROP_CODES or i.code == "BOX_OUT_OF_IMAGE"):
            if i.image not in removed_stems:
                line_issues_by_stem[i.image][i.line].append(i)

    for stem in sorted(line_issues_by_stem.keys()):
        lbl_p = ds.label_path(stem)
        if not lbl_p.exists():
            continue

        raw_lines = lbl_p.read_text(encoding="utf-8", errors="replace").splitlines()
        file_issues = line_issues_by_stem[stem]
        new_lines = []

        for line_no, line_text in enumerate(raw_lines, 1):
            if line_no not in file_issues:
                new_lines.append(line_text)
                continue

            iss_list = file_issues[line_no]
            codes = {iss.code for iss in iss_list}

            # Nếu có bất kỳ lỗi drop_line nào -> xoá dòng thắng (ưu tiên drop_line)
            if any(c in DROP_CODES for c in codes):
                fixes.append({
                    "image": stem,
                    "line": line_no,
                    "action": "drop_line",
                    "before": line_text,
                    "after": "",
                })
                continue

            # Nếu chỉ có lỗi BOX_OUT_OF_IMAGE -> clip box
            if "BOX_OUT_OF_IMAGE" in codes:
                try:
                    c, x, y, w, h = parse_yolo_line(line_text)
                    left = x - w / 2
                    right = x + w / 2
                    top = y - h / 2
                    bottom = y + h / 2

                    clipped_left = max(0.0, min(1.0, left))
                    clipped_right = max(0.0, min(1.0, right))
                    clipped_top = max(0.0, min(1.0, top))
                    clipped_bottom = max(0.0, min(1.0, bottom))

                    new_w = clipped_right - clipped_left
                    new_h = clipped_bottom - clipped_top

                    if new_w <= 0.0 or new_h <= 0.0:
                        fixes.append({
                            "image": stem,
                            "line": line_no,
                            "action": "drop_line",
                            "before": line_text,
                            "after": "",
                        })
                        continue

                    new_x = clipped_left + new_w / 2
                    new_y = clipped_top + new_h / 2
                    new_line_text = f"{int(c)} {new_x:.6f} {new_y:.6f} {new_w:.6f} {new_h:.6f}"
                    new_lines.append(new_line_text)
                    fixes.append({
                        "image": stem,
                        "line": line_no,
                        "action": "clip_box",
                        "before": line_text,
                        "after": new_line_text,
                    })
                except Exception:
                    fixes.append({
                        "image": stem,
                        "line": line_no,
                        "action": "drop_line",
                        "before": line_text,
                        "after": "",
                    })
                    continue

        lbl_p.write_text("\n".join(new_lines) + ("\n" if new_lines else ""), encoding="utf-8")

    return fixes
