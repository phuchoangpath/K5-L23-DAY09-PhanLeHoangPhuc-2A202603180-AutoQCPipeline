"""CHECK 6 — Ý kiến thứ hai: so nhãn với một model LỚN HƠN (yolo26l).   ★★★ (khó nhất, đáng điểm nhất)

Test:  pytest tests/test_second_opinion.py -q

Máy kiểm quy tắc, người kiểm ý nghĩa (slide). Các lỗi như thiếu nhãn / gán nhầm lớp hợp lệ / box lỏng
KHÔNG bắt được bằng quy tắc cú pháp. Ta nhờ một model mạnh hơn "nhìn lại" và CHỈ CẢNH BÁO (model cũng có thể sai):
những ảnh bị cờ sẽ vào hàng đợi cho NGƯỜI duyệt.

`preds[stem]` = list `[id_lớp, conf, cx, cy, w, h]` của model (lấy qua `get_preds(ds, cfg, "checker")` nếu preds=None).
`L = ds.valid_boxes(stem)` = list `(id_lớp, cx, cy, w, h)` của nhãn (đã bỏ dòng hỏng).
Ngưỡng ở `cfg["second_opinion"]`: conf, min_area_px, fp_conf, iou_missing, iou_match, iou_loose.
"""
from ..common import WARN, Issue, iou_xywh, parse_yolo_line
from ..model_cache import get_preds


def run(ds, cfg, preds=None):
    if preds is None:
        preds = get_preds(ds, cfg, "checker")

    cfg_so = cfg.get("second_opinion", {})
    conf_thresh = cfg_so.get("conf", 0.25)
    min_area_px = cfg_so.get("min_area_px", 600)
    fp_conf = cfg_so.get("fp_conf", 0.1)
    iou_missing = cfg_so.get("iou_missing", 0.3)
    iou_match = cfg_so.get("iou_match", 0.5)
    iou_loose = cfg_so.get("iou_loose", 0.5)
    classes = ds.classes

    issues = []

    for img_p in ds.image_files():
        stem = img_p.stem
        if stem not in preds:
            continue
        if not ds.label_path(stem).exists():
            continue

        raw_lines = ds.read_label_lines(stem)
        if raw_lines is None:
            continue

        img_size = ds.image_size(stem)
        W, H = img_size if img_size else (640, 640)

        # Parse valid labels keeping line numbers
        valid_labels = []
        for line_no, text in raw_lines:
            try:
                c, x, y, w, h = parse_yolo_line(text)
            except ValueError:
                continue
            if 0 <= c < len(classes):
                valid_labels.append((line_no, c, (x, y, w, h)))

        stem_preds = preds.get(stem, [])

        # Filter predictions for P: conf >= conf_thresh AND area_px >= min_area_px
        P = []
        for r in stem_preds:
            p_c, p_conf, p_x, p_y, p_w, p_h = r[0], r[1], r[2], r[3], r[4], r[5]
            area_px = (p_w * W) * (p_h * H)
            if p_conf >= conf_thresh and area_px >= min_area_px:
                P.append(r)

        # Đánh giá từng dự đoán trong P
        for r in P:
            p_c, p_conf, p_box = int(r[0]), float(r[1]), (r[2], r[3], r[4], r[5])
            cands = []
            for lbl in valid_labels:
                iou = iou_xywh(p_box, lbl[2])
                if iou >= iou_missing:
                    cands.append((lbl, iou))

            if not cands:
                issues.append(
                    Issue(
                        "second_opinion",
                        WARN,
                        "POSSIBLE_MISSING",
                        stem,
                        f"model thấy {classes[p_c] if 0 <= p_c < len(classes) else p_c} (conf {p_conf:.2f}) nhưng nhãn không có",
                        line=None,
                        extra={"conf": p_conf, "pred": [p_c, p_conf, *p_box]},
                    )
                )
            else:
                same_class_cands = [c for c in cands if c[0][1] == p_c]
                if same_class_cands:
                    best_same_iou = max(c[1] for c in same_class_cands)
                    if best_same_iou < iou_loose:
                        issues.append(
                            Issue(
                                "second_opinion",
                                WARN,
                                "POSSIBLE_LOOSE_BOX",
                                stem,
                                f"box nhãn cùng lớp {classes[p_c] if 0 <= p_c < len(classes) else p_c} nhưng lệch (IoU {best_same_iou:.2f} < {iou_loose})",
                                line=None,
                                extra={"iou": best_same_iou, "conf": p_conf},
                            )
                        )
                else:
                    diff_class_cands = [c for c in cands if c[0][1] != p_c]
                    if diff_class_cands:
                        best_diff_iou = max(c[1] for c in diff_class_cands)
                        if best_diff_iou >= iou_match:
                            issues.append(
                                Issue(
                                    "second_opinion",
                                    WARN,
                                    "POSSIBLE_WRONG_CLASS",
                                    stem,
                                    f"model dự đoán {classes[p_c] if 0 <= p_c < len(classes) else p_c} (conf {p_conf:.2f}), nhãn gán lớp khác (IoU {best_diff_iou:.2f})",
                                    line=None,
                                    extra={"iou": best_diff_iou, "conf": p_conf},
                                )
                            )

        # Kiểm tra POSSIBLE_FALSE_POS cho từng dòng nhãn hợp lệ
        fp_preds = [r for r in stem_preds if r[1] >= fp_conf]
        for line_no, l_c, l_box in valid_labels:
            has_match = any(iou_xywh(l_box, (r[2], r[3], r[4], r[5])) >= iou_missing for r in fp_preds)
            if not has_match:
                issues.append(
                    Issue(
                        "second_opinion",
                        WARN,
                        "POSSIBLE_FALSE_POS",
                        stem,
                        f"box nhãn dòng {line_no} không khớp dự đoán nào của model",
                        line=line_no,
                        extra={"line": line_no},
                    )
                )

    return issues
