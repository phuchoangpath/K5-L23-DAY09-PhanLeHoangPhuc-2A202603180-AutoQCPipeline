"""CHECK 2 — Dòng nhãn YOLO: sai định dạng, ID lớp lạ, box tràn ảnh, box rỗng, box lặp.   (Script 2 trong slide)   ★★

Test:  pytest tests/test_label_format.py -q

Mỗi dòng nhãn: `id cx cy w h` (5 số, toạ độ 0–1). Trả về list[Issue]; `Issue.line` = số dòng (đếm từ 1).

| code             | severity | khi nào                                                                  |
|------------------|----------|--------------------------------------------------------------------------|
| BAD_FORMAT       | ERROR    | không đúng 5 cột số (dùng `parse_yolo_line`, bắt `ValueError`)           |
| BAD_CLASS_ID     | ERROR    | id lớp ngoài 0..len(ds.classes)-1                                        |
| BOX_ZERO         | ERROR    | w <= 0 hoặc h <= 0                                                       |
| BOX_OUT_OF_IMAGE | ERROR    | mép box vượt [0,1] quá `cfg["label_format"]["overflow_tol"]`; extra={"overflow": mức tràn} |
| DUP_BOX          | ERROR    | cùng lớp với một dòng TRƯỚC ĐÓ và IoU > `dup_box_iou`; báo ở dòng SAU    |
| BOX_TINY         | WARN     | cạnh ngắn của box (px) < `min_box_px`  (cần `ds.image_size(stem)`)       |
| BOX_HUGE         | WARN     | w*h > `max_box_frac`                                                     |
"""
from ..common import ERROR, WARN, Issue, iou_xywh, parse_yolo_line


def run(ds, cfg):
    cfg_lf = cfg.get("label_format", {})
    overflow_tol = cfg_lf.get("overflow_tol", 0.002)
    min_box_px = cfg_lf.get("min_box_px", 12)
    max_box_frac = cfg_lf.get("max_box_frac", 0.95)
    dup_box_iou = cfg_lf.get("dup_box_iou", 0.9)
    num_classes = len(ds.classes)

    issues = []

    for p in ds.label_files():
        stem = p.stem
        lines = ds.read_label_lines(stem)
        if lines is None:
            continue

        img_size = ds.image_size(stem)
        prev_boxes = []

        for line_no, text in lines:
            try:
                c, x, y, w, h = parse_yolo_line(text)
            except ValueError:
                issues.append(Issue("label_format", ERROR, "BAD_FORMAT", stem, f"dòng {line_no} sai định dạng: {text!r}", line_no))
                continue

            if not (0 <= c < num_classes):
                issues.append(Issue("label_format", ERROR, "BAD_CLASS_ID", stem, f"id lớp {c} không hợp lệ (hợp lệ 0..{num_classes - 1})", line_no, extra={"class_id": c}))
                continue

            if w <= 0 or h <= 0:
                issues.append(Issue("label_format", ERROR, "BOX_ZERO", stem, f"kích thước w={w}, h={h} <= 0", line_no))
                continue

            # Kiểm tra tràn ảnh (BOX_OUT_OF_IMAGE)
            left = x - w / 2
            right = x + w / 2
            top = y - h / 2
            bottom = y + h / 2

            overflow = max(0.0, -left, right - 1.0, -top, bottom - 1.0)
            if overflow > overflow_tol:
                issues.append(Issue("label_format", ERROR, "BOX_OUT_OF_IMAGE", stem, f"box tràn mép {overflow:.4f} > {overflow_tol}", line_no, extra={"overflow": overflow}))

            # Kiểm tra box trùng lặp (DUP_BOX)
            for prev_line_no, prev_c, prev_box in prev_boxes:
                if prev_c == c and iou_xywh((x, y, w, h), prev_box) > dup_box_iou:
                    issues.append(Issue("label_format", ERROR, "DUP_BOX", stem, f"box trùng với dòng {prev_line_no}", line_no))
                    break
            prev_boxes.append((line_no, c, (x, y, w, h)))

            # Cảnh báo box quá nhỏ (BOX_TINY)
            if img_size is not None:
                W, H = img_size
                short_side_px = min(w * W, h * H)
                if short_side_px < min_box_px:
                    issues.append(Issue("label_format", WARN, "BOX_TINY", stem, f"cạnh ngắn {short_side_px:.1f}px < {min_box_px}px", line_no, extra={"short_side_px": short_side_px}))

            # Cảnh báo box quá lớn (BOX_HUGE)
            area_frac = w * h
            if area_frac > max_box_frac:
                issues.append(Issue("label_format", WARN, "BOX_HUGE", stem, f"diện tích box {area_frac:.2f} > {max_box_frac}", line_no, extra={"area_frac": area_frac}))

    return issues
