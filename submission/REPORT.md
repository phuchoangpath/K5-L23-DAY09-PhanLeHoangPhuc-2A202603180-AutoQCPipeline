# Báo cáo Day 09 — Phan Lê Hoàng Phúc, 2A202603180

## 1. Kết luận trước
Pipeline kiểm nhãn tự động đưa ra kết luận: **Hold** (mã thoát 10).
Tổng số ảnh đầu vào là **224 ảnh**, trong đó **21 ảnh bị loại** ở cửa vào (gồm 2 ảnh hỏng, 3 ảnh kích thước nhỏ dưới 250px, 11 ảnh trùng lặp và 5 ảnh rò rỉ từ tập test), còn lại **203/224 ảnh** được nạp vào xử lý và xuất dataset bản nháp tại `submission/export/clean_v1/`.
Lý do chính khiến pipeline rơi vào trạng thái Hold: Mặc dù toàn bộ 36 lỗi bắt buộc (ERROR) đã được khắc phục hoàn toàn (máy tự sửa 35 lỗi cú pháp, người duyệt xử lý 6 ảnh thiếu nhãn), nhưng tỷ lệ ảnh còn cảnh báo nghi vấn ngữ nghĩa chưa được người duyệt là **18.72% (38/203 ảnh)**, vượt quá ngưỡng an toàn cho phép là **10.00%** do ngân sách duyệt người bị giới hạn ở mức 80 ảnh.

---

## 2. Lỗi và phân việc
Tổng hợp các lỗi phát hiện từ `submission/reports/02_error_list_v1` (tổng cộng 203 ảnh được quét):

| Mã lỗi | Số ảnh/dòng | Ai sửa (máy/người) | Vì sao |
|---|---:|---|---|
| `CORRUPT_IMAGE` | 2 ảnh | Máy (Intake) | File ảnh bị hỏng cấu trúc nhị phân, không thể đọc được dữ liệu pixel nên máy loại bỏ ngay từ đầu. |
| `BAD_SIZE` | 3 ảnh | Máy (Intake) | Cạnh ngắn ảnh nhỏ hơn 250px, không đạt chuẩn tối thiểu của dự án, máy loại bỏ tự động. |
| `DUP_IMAGE_EXACT` | 8 ảnh | Máy (Intake) | Ảnh trùng khớp 100% từng byte với ảnh đã có, máy tự động xóa bản sao thừa. |
| `DUP_IMAGE_NEAR` | 3 ảnh | Máy (Intake) | Ảnh gần trùng (thu nhỏ/nén nhẹ) dựa trên pHash, máy tự động loại bỏ để tránh thiên lệch dữ liệu. |
| `LEAK_TEST` | 5 ảnh | Máy (Intake) | Ảnh bị trùng lặp với kho dữ liệu test/val, máy loại bỏ để ngăn chặn hiện tượng rò rỉ dữ liệu (học vẹt). |
| `BAD_CLASS_NAME` | 2 lỗi | Máy (Autofix) | Tên lớp trong `data.yaml` bị viết hoa sai chuẩn (`Person`, `Bus`), máy tự chuẩn hóa theo `cfg["classes"]`. |
| `BAD_CLASS_ID` | 6 dòng | Máy (Autofix) | ID lớp lạ ngoài dải 0..3 (ví dụ: 93, 4, -1), máy tự động xóa dòng nhãn hỏng. |
| `BAD_FORMAT` | 3 dòng | Máy (Autofix) | Dòng thiếu cột hoặc chứa giá trị không hợp lệ (`nan`), máy tự động xóa dòng hỏng. |
| `BOX_ZERO` | 4 dòng | Máy (Autofix) | Bounding box có chiều rộng hoặc chiều cao $\le 0$, máy tự động xóa dòng không có diện tích. |
| `BOX_OUT_OF_IMAGE` | 8 dòng | Máy (Autofix) | Box tràn mép ảnh quá ngưỡng dung sai, máy tự động cắt kẹp (clip) tọa độ về dải hợp lệ `[0.0, 1.0]`. |
| `DUP_BOX` | 7 dòng | Máy (Autofix) | Hai box cùng lớp đè khít lên nhau trong cùng 1 ảnh (IoU > 0.9), máy tự động xóa box trùng phía sau. |
| `MISSING_LABEL_FILE` | 6 ảnh | Người (Queue) | Ảnh hoàn toàn không có file nhãn; máy không thể tự bịa đặt nhãn nên đẩy ưu tiên cho người gán mới. |
| `EMPTY_LABEL` | 12 ảnh | Người (Queue) | File nhãn rỗng 0 byte; cần con người xác nhận là ảnh nền thực sự (background) hay do người gán bỏ quên. |
| `POSSIBLE_WRONG_CLASS` | 18 cảnh báo | Người (Queue) | Model lớn nghi ngờ nhầm lớp (IoU cao nhưng khác nhãn); cần người phân xử ngữ nghĩa. |
| `POSSIBLE_MISSING` | 53 cảnh báo | Người (Queue) | Model lớn phát hiện đối tượng rõ nét nhưng nhãn thiếu; cần người kiểm tra và vẽ bổ sung box. |
| `POSSIBLE_LOOSE_BOX` | 28 cảnh báo | Người (Queue) | Nhãn đúng lớp nhưng box vẽ quá lỏng lẻo/lệch (IoU thấp); cần người nắn chỉnh lại viền. |
| `POSSIBLE_FALSE_POS` | 29 cảnh báo | Người (Queue) | Box nhãn không khớp với bất kỳ dự đoán nào của model lớn; cần người kiểm tra có phải gán nhầm nền. |
| `BOX_TINY` | 6 cảnh báo | Người (Queue) | Box có cạnh ngắn < 12px; cần người đánh giá xem vật thể có đủ nhận diện hay nên bỏ. |
| `BOX_HUGE` | 3 cảnh báo | Người (Queue) | Box chiếm diện tích > 95% ảnh; cần người xem lại có bị vẽ bao trùm sai toàn cảnh. |
| `CLASS_RARE` | 4 cảnh báo | Người (Quản lý) | Cảnh báo mất cân bằng dữ liệu ở cấp dataset khi lớp có quá ít box đại diện. |

**Giải thích về hàng đợi duyệt `05_review_queue.csv`:**
Script `review_queue.py` xếp các ảnh lên đầu hàng đợi dựa trên tổng trọng số ưu tiên. 
- Nhóm ảnh `NEEDS_LABEL` (`img_0031`, `img_0053`, `img_0126`, `img_0135`, `img_0170`, `img_0219`) được gán trọng số cao nhất (10.0) vì đây là lỗi bắt buộc làm thiếu hụt nhãn hoàn toàn.
- Ảnh `img_0020` đứng đầu bảng (ưu tiên 11.524) vì dồn nhiều lỗi nghiêm trọng: vừa bị xóa dòng cú pháp (`FIXED_DROP_LINE`), vừa bị model cảnh báo thiếu nhãn (`POSSIBLE_MISSING`) và nghi ngờ sai lớp (`POSSIBLE_WRONG_CLASS`).
Với ngân sách cố định 80 ảnh, người duyệt mô phỏng đã xử lý được **80/125 ảnh** trong hàng đợi, giải quyết được toàn bộ 6 ảnh thiếu nhãn (`NEEDS_LABEL`), 50 lỗi thiếu nhãn (`POSSIBLE_MISSING`), 18 lỗi sai nhãn (`POSSIBLE_WRONG_CLASS`), 12 lỗi nhãn thừa (`POSSIBLE_FALSE_POS`), 8 lỗi box lỏng và 11 ảnh nhãn rỗng.

---

## 3. Calibration (2 ngưỡng)
Bảng đối chiếu kết quả hiệu chuẩn trên bộ chuẩn `data/calib/` (39 ảnh):

| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước → sau) | Lý do (đánh đổi) |
|---|---|---|---|---|
| `duplicates.phash_dist` | 2 | 8 | DUP_IMAGE_NEAR: 1.00 / 0.50 $\rightarrow$ 1.00 / 0.67 (F1: 0.67 $\rightarrow$ 0.80) | Ngưỡng 2 quá chặt, bỏ sót một nửa số ảnh gần trùng. Nâng lên 8 giúp tăng khả năng bắt trúng thêm 17% mà Precision vẫn đạt 1.00 tuyệt đối, bắt được các ảnh thu nhỏ/nén (như `img_0223`). |
| `second_opinion.conf` | 0.25 | 0.60 | WRONG_CLASS: 0.56 / 0.83 $\rightarrow$ 0.62 / 0.83 (F1: 0.67 $\rightarrow$ 0.71)<br>MISSING: 0.50 / 1.00 $\rightarrow$ 0.57 / 1.00 (F1: 0.67 $\rightarrow$ 0.73) | Ngưỡng 0.25 quá thấp làm phát sinh nhiều cảnh báo giả. Nâng lên 0.60 giúp tăng độ chuẩn xác đáng kể, cắt giảm 18 cảnh báo rác trên dữ liệu thật, giảm tải cho hàng đợi người duyệt mà Recall vẫn giữ nguyên vẹn 100% cho missing và 83% cho wrong class. |

**Một chỗ calibration có thể đánh lừa bạn (Bẫy Calibration):**
Trên tập chuẩn `data/calib/`, nếu chọn `phash_dist = 16` thì F1 đạt tới **0.91** (Recall 0.83). Tuy nhiên, đây là một "cái bẫy" nguy hiểm do tập calib chỉ có 39 ảnh và lỗi gần trùng được tạo nhân tạo với độ biến dạng lớn. 
Khi áp dụng ngưỡng `16` vào tập dữ liệu thật `data/raw` (224 ảnh), ngưỡng này quá lỏng khiến cho **7 ảnh hoàn toàn khác nhau bị phán là trùng lặp** (ví dụ ảnh `img_0011` chụp 1 người bị nhận nhầm là trùng với `img_0008` chụp 2 người) và **11 ảnh bị phán nhầm là rò rỉ từ tập test** (`LEAK_TEST`). Nếu tin vào điểm số cao trên calib mà chọn ngưỡng 16, pipeline sẽ xóa oan hàng loạt ảnh hợp lệ của tập huấn luyện. Vì vậy, giá trị cân bằng thực tế an toàn nhất là `phash_dist = 8`.

---

## 4. Cửa chặn và điều pipeline KHÔNG bắt được

**(a) Chứng minh Quality Gate chặn đúng kịch bản nghiêm ngặt:**
Thực hiện chạy thử nghiệm ngắt quyền can thiệp của con người với ngân sách duyệt bằng 0:
```powershell
python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb
```
- Kết quả thu được: Do không có người duyệt (`budget = 0`), 6 ảnh ban đầu thiếu file nhãn (`MISSING_LABEL_FILE`) không được gán nhãn nên còn nguyên 6 lỗi cấp độ ERROR.
- Cửa chặn tại `pipeline/steps/gate.py` đã phát hiện các lỗi bắt buộc này và đưa ra quyết định **Rework**, trả về mã thoát hệ thống **20** (`ExitCode: 20`).
- Pipeline **hoàn toàn không xuất bản** dataset ra thư mục `work/exp_nb/clean_v1/` (`Test-Path work\exp_nb\clean_v1` trả về `False`). Điều này chứng minh cửa chặn hoạt động độc lập, không cho phép dữ liệu lỗi lọt qua nếu chưa có sự xử lý của con người.

**(b) Các điểm mù mà pipeline không thể bắt được:**
1. **Lệch nhãn ở các ca khó mà cả mô hình lớn cũng nhầm lẫn (Shared Confusion):** Giữa các lớp xe có hình dáng tương tự (như xe bán tải gán là `car` hay `truck`, xe bus nhỏ gán là `truck`). Nếu cả người gán lẫn mô hình YOLO26l đều nhầm lẫn, `second_opinion` sẽ thấy hai bên đồng thuận và hoàn toàn im lặng.
2. **Box lỏng nhẹ (Minor loose box):** Khi người gán nhãn vẽ khung bao quanh người hoặc xe hơi rộng một chút nhưng chỉ số trùng khớp IoU với box chuẩn vẫn $\ge 0.50$ (ngưỡng `iou_match` và `iou_loose`), pipeline sẽ coi là nhãn hợp lệ và bỏ qua.
3. **Đối tượng lạ ngoài danh mục 4 lớp:** Ở ảnh `img_0005`, trụ đá bên đường bị gán nhãn là `person` (người). Máy chỉ có thể phát hiện cảnh báo gián tiếp `POSSIBLE_FALSE_POS` do không thấy người ở đó, nhưng không thể hiểu được ngữ nghĩa thực sự đó là trụ đá hay đồ vật gì khác.

---

## 5. Train: raw vs clean (tùy chọn, chấm riêng)
Chưa chạy — do môi trường máy tính cục bộ không trang bị GPU chuyên dụng. Phần kiểm định cốt lõi của pipeline (Intake, Autofix, Calibration, Quality Gate và Data Provenance) đã được hoàn thiện đầy đủ và xác thực 100% bằng bộ unit test và pipeline một lệnh.

---

## 6. Quyết định và ghi chú AI

**(a) Quyết định cuối cùng:**
Quyết định cuối cùng của lô dữ liệu là **Hold**.
Để chuyển quyết định từ **Hold** thành **Release**, dự án cần:
1. Mở rộng ngân sách duyệt con người từ 80 ảnh lên tối thiểu 125 ảnh (hoặc bố trí thêm 1 nhân sự kiểm duyệt nốt 38 ảnh còn lại trong `submission/reports/05_review_queue.csv`).
2. Khi con người đã duyệt xong 38 ảnh này, chạy lại pipeline với cờ `--resume-after-review`. Khi đó số ảnh có cảnh báo chưa duyệt sẽ giảm về 0 (tỷ lệ 0.00% < 10.00%), và Cửa chặn sẽ tự động chuyển sang **Release** (mã thoát 0) để xuất bản chính thức dataset.

**(b) Ghi chú sử dụng AI:**
- *Prompt chính:* "Hãy lập trình 4 module `label_format.py`, `gate.py`, `autofix.py`, `second_opinion.py` theo phương pháp TDD, tuân thủ đúng docstring, bảo đảm tính bất biến của dữ liệu gốc `data/raw/` và vượt qua toàn bộ 79 tests của bộ kiểm thử."
- *Cách kiểm tra code AI:* Chạy kiểm thử tự động `pytest -q` cho từng module, kiểm tra kỹ lưỡng các ca khó (như dòng rỗng ở giữa, một dòng dính nhiều lỗi cùng lúc, tọa độ âm hoặc tràn viền, chia cho 0 khi dataset rỗng), kiểm tra các file mã băm bảo vệ qua `scripts/_protected.json` và chạy thẩm định nộp bài bằng `python scripts/check_submission.py --no-train`.
- *Một lần AI sai:* Khi phân tích hiệu chuẩn cho `phash_dist`, thuật toán gợi ý chọn giá trị 16 vì điểm F1 trên tập 39 ảnh calib đạt cao nhất (0.91). Tuy nhiên, khi kiểm tra trực tiếp trên tập 224 ảnh `raw`, giá trị 16 đã xóa nhầm ảnh hợp lệ (`img_0011` khác hoàn toàn `img_0008`) và báo nhầm 11 ảnh rò rỉ test. Qua đó đã điều chỉnh lại giá trị thực tế an toàn là 8.
