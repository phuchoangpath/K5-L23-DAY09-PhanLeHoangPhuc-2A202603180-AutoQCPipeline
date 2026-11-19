# Báo cáo Day 09 — Phan Lê Hoàng Phúc, 2A202603180

## 1. Kết luận trước
Sau khi chạy pipeline hoàn chỉnh, hệ thống của mình đưa ra kết luận là Hold với mã thoát là 10. Lô dữ liệu đầu vào có 224 ảnh, qua các bước lọc ở cửa vào thì loại bỏ 21 ảnh hỏng hoặc trùng lặp, còn lại 203 ảnh được đưa vào xử lý và xuất ra thư mục clean_v1. Lý do chính khiến gate quyết định Hold là vì sau khi người duyệt xong 80 ảnh theo ngân sách cho phép, trong tập dữ liệu vẫn còn lại 38 ảnh có cảnh báo chưa được kiểm tra, tương ứng tỷ lệ 18.72% trên tổng số 203 ảnh, vượt quá mức trần an toàn là 10%.

## 2. Lỗi và phân việc
Tổng hợp các lỗi mình thu thập được từ file 02_error_list_v1 trên 203 ảnh sau cửa vào:

| Mã lỗi | Số ảnh/dòng | Ai sửa (máy/người) | Vì sao |
|---|---:|---|---|
| BAD_CLASS_NAME | 2 lỗi | Máy (Autofix) | Tên lớp trong file cấu hình viết hoa sai chuẩn như Person hoặc Bus, máy tự đổi lại theo danh sách lớp chuẩn. |
| BAD_CLASS_ID | 6 dòng | Máy (Autofix) | ID lớp là số lạ nằm ngoài khoảng 0 đến 3, máy tự xóa dòng nhãn hỏng này vì không thể đoán được là xe hay người. |
| BAD_FORMAT | 3 dòng | Máy (Autofix) | Dòng nhãn bị thiếu cột tọa độ hoặc chứa chữ nan, máy tự xóa bỏ dòng lỗi. |
| BOX_ZERO | 4 dòng | Máy (Autofix) | Chiều rộng hoặc chiều cao của khung bao nhỏ hơn hoặc bằng 0, không có diện tích nên máy tự xóa. |
| BOX_OUT_OF_IMAGE | 8 dòng | Máy (Autofix) | Tọa độ khung bao bị tràn ra ngoài mép ảnh, máy tự nắn kẹp lại trong khoảng từ 0.0 đến 1.0. |
| DUP_BOX | 7 dòng | Máy (Autofix) | Hai khung bao cùng một lớp đè khít lên nhau với độ trùng khớp cao, máy tự xóa bớt một khung bị thừa. |
| MISSING_LABEL_FILE | 6 ảnh | Người (Hàng đợi) | Ảnh hoàn toàn không có file nhãn đi kèm, máy không thể tự bịa ra nhãn nên phải chuyển cho người gán nhãn mới. |
| EMPTY_LABEL | 12 ảnh | Người (Hàng đợi) | File nhãn trống không có dữ liệu, cần người xem lại xem đây là ảnh nền không có vật thể hay do người gán bỏ sót. |
| POSSIBLE_WRONG_CLASS | 18 cảnh báo | Người (Hàng đợi) | Mô hình kiểm tra nghi ngờ bị gán sai tên lớp, cần người có chuyên môn nhìn ảnh để phân xử lại. |
| POSSIBLE_MISSING | 53 cảnh báo | Người (Hàng đợi) | Mô hình kiểm tra phát hiện vật thể rõ ràng nhưng nhãn không có, cần người vẽ bổ sung khung bao. |
| POSSIBLE_LOOSE_BOX | 28 cảnh báo | Người (Hàng đợi) | Khung bao bị vẽ quá rộng hoặc lệch nhiều so với vật thể thật, cần người chỉnh lại viền cho khít. |
| POSSIBLE_FALSE_POS | 29 cảnh báo | Người (Hàng đợi) | Nhãn có vẽ khung nhưng mô hình không tìm thấy vật thể nào ở đó, cần người xem lại có phải vẽ nhầm vào nền không. |
| BOX_TINY | 6 cảnh báo | Người (Hàng đợi) | Khung bao quá nhỏ dưới 12 pixel, cần người đánh giá xem vật thể có nhìn rõ để học không. |
| BOX_HUGE | 3 cảnh báo | Người (Hàng đợi) | Khung bao chiếm trên 95% diện tích ảnh, cần người kiểm tra xem có bị vẽ bao trùm sai cả khung cảnh không. |
| CLASS_RARE | 4 cảnh báo | Người (Quản lý) | Cảnh báo về việc lớp có quá ít mẫu trong bộ dữ liệu, cần người quản lý lên kế hoạch thu thập thêm ảnh. |

Về việc sắp xếp thứ tự trong hàng đợi 05_review_queue.csv:
Script sắp xếp các ảnh có điểm ưu tiên từ cao xuống thấp dựa trên độ nghiêm trọng của lỗi. Nhóm 6 ảnh hoàn toàn không có file nhãn như img_0031, img_0053, img_0126, img_0135, img_0170, img_0219 được xếp lên hàng đầu với điểm ưu tiên là 10.0 vì thiếu nhãn là lỗi bắt buộc phải sửa trước khi xuất xưởng. Ảnh img_0020 đứng đầu danh sách với điểm ưu tiên là 11.524 vì ảnh này dính nhiều lỗi cùng lúc, vừa bị xóa dòng nhãn hỏng vừa bị mô hình cảnh báo thiếu nhãn và nghi ngờ sai lớp.
Với ngân sách cố định là 80 ảnh, người duyệt mô phỏng đã xem được 80 ảnh có điểm ưu tiên cao nhất trong tổng số 125 ảnh có cảnh báo. Qua đó đã xử lý xong toàn bộ 6 ảnh thiếu file nhãn, 50 lỗi thiếu nhãn, 18 lỗi gán sai lớp, 12 lỗi nhãn thừa và 8 lỗi khung bao lỏng.

## 3. Calibration (2 ngưỡng)
Bảng kết quả hiệu chuẩn hai tham số trên bộ dữ liệu mẫu data/calib gồm 39 ảnh:

| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước → sau) | Lý do (đánh đổi) |
|---|---|---|---|---|
| duplicates.phash_dist | 2 | 8 | Ảnh gần trùng: 1.00 / 0.50 → 1.00 / 0.67 | Ngưỡng ban đầu là 2 quá chặt nên chỉ bắt được một nửa số ảnh gần trùng. Khi mình nâng lên 8 thì khả năng phát hiện tăng thêm 17% mà độ chuẩn xác vẫn giữ trọn vẹn 1.00, giúp lọc được các ảnh bị thu nhỏ hoặc nén nhẹ mà không xóa nhầm ảnh khác biệt. |
| second_opinion.conf | 0.25 | 0.60 | Sai lớp: 0.56 / 0.83 → 0.62 / 0.83<br>Thiếu nhãn: 0.50 / 1.00 → 0.57 / 1.00 | Ngưỡng 0.25 quá thấp khiến mô hình dự đoán lung tung và sinh ra nhiều cảnh báo rác. Khi nâng lên 0.60, độ chuẩn xác tăng lên rõ rệt, bớt được 18 cảnh báo giả trên tập dữ liệu thật, giúp người duyệt đỡ quá tải trong khi độ bao phủ vẫn giữ nguyên 100% cho lỗi thiếu nhãn và 83% cho lỗi sai lớp. |

Chỗ calibration có thể đánh lừa mình:
Khi chạy thử trên 39 ảnh calib, nếu chọn phash_dist bằng 16 thì điểm F1 lên tới 0.91, cao nhất trong bảng quét. Tuy nhiên đây là một cái bẫy vì tập calib quá nhỏ và các ảnh trùng nhân tạo bị bóp méo quá nhiều. Khi mình mang ngưỡng 16 áp dụng vào 224 ảnh thật trong data/raw thì ngưỡng này quá lỏng, làm hệ thống nhận nhầm 7 cặp ảnh khác nhau là trùng lặp, ví dụ như ảnh img_0011 chỉ có một người lại bị coi là trùng với img_0008 có hai người, đồng thời báo nhầm 11 ảnh là rò rỉ từ tập test. Nếu tin vào điểm số cao trên tập calib thì mình đã xóa oan rất nhiều ảnh tốt của tập train. Vì vậy mình chọn ngưỡng an toàn thực tế là 8.

## 4. Cửa chặn và điều pipeline KHÔNG bắt được
(a) Chứng minh Quality Gate chặn đúng:
Để kiểm tra xem cửa chặn có làm việc nghiêm túc hay không, mình chạy thử pipeline với ngân sách người duyệt bằng 0 theo lệnh python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb. Kết quả là 6 ảnh bị thiếu file nhãn không có ai sửa nên lỗi bắt buộc vẫn còn nguyên. Cửa chặn đã kết luận là Rework với mã thoát là 20 và kiên quyết không tạo ra thư mục dữ liệu xuất xưởng work/exp_nb. Điều này chứng minh cửa chặn hoạt động đúng và ngăn chặn hoàn toàn việc xuất dữ liệu hỏng.

(b) Những điểm mù pipeline không bắt được:
Thứ nhất là trường hợp nhầm lẫn giữa các lớp có hình dáng tương tự nhau mà cả người gán lẫn mô hình lớn đều nhận định sai. Ví dụ xe bán tải bị gán là xe con hoặc xe khách nhỏ bị gán là xe tải. Khi cả hai bên cùng đoán giống nhau thì mô hình kiểm tra sẽ đồng thuận và im lặng bỏ qua.
Thứ hai là trường hợp khung bao bị vẽ hơi lỏng nhẹ. Nếu người gán vẽ khung hơi rộng một chút nhưng độ trùng khớp IoU với khung chuẩn vẫn lớn hơn hoặc bằng 0.50 thì hệ thống vẫn coi là hợp lệ và không đưa ra cảnh báo.
Thứ ba là các vật thể lạ nằm ngoài 4 lớp quy định. Ở ảnh img_0005, có một cái trụ đá bên đường bị gán nhãn là người. Hệ thống chỉ phát hiện cảnh báo gián tiếp là nhãn thừa vì không thấy người ở đó, chứ không thể hiểu được vật thể thực tế trong ảnh là cái trụ đá.

## 5. Train: raw vs clean (tùy chọn, chấm riêng)
Bảng kết quả chạy thực nghiệm huấn luyện trên Google Colab với mô hình yolo26n, 20 epochs, batch size 16, ảnh kích thước 640px, đánh giá trên 100 ảnh của data/test:

| Biến thể | #Ảnh train | Số seed | map50 (TB ± độ lệch) | map50_95 (TB ± độ lệch) | precision (TB ± độ lệch) | recall (TB ± độ lệch) |
|---|---|---|---|---|---|---|
| raw | 224 | 2 | 0.726 ± 0.000 | 0.512 ± 0.004 | 0.764 ± 0.061 | 0.649 ± 0.028 |
| clean | 203 | 2 | 0.699 ± 0.025 | 0.486 ± 0.013 | 0.796 ± 0.050 | 0.596 ± 0.049 |

Chênh lệch map50 giữa clean và raw là -0.027.

So sánh với độ nhiễu và phân tích trung thực:
Độ lệch chuẩn của biến thể clean giữa hai seed là 0.025. Mức chênh lệch -0.027 này xấp xỉ bằng độ lệch chuẩn ngẫu nhiên, cho thấy sự khác biệt về điểm số nằm trong khoảng nhiễu thống kê và chưa thể khẳng định mô hình nào vượt trội chỉ qua 2 seed trên 100 ảnh test.
Tuy nhiên khi nhìn sâu vào các chỉ số, mình thấy có những nguyên nhân giải thích rất rõ ràng:
Một là tập raw bị rò rỉ đề thi do có 6 ảnh trùng lặp trực tiếp với tập test như ghi nhận trong file 04_leak_matrix.csv. Mô hình raw đã học lỏm các ảnh này trong lúc train nên điểm test bị thổi phồng ảo. Tập clean đã loại bỏ các ảnh này để giữ tính liêm chính.
Hai là độ chính xác precision của clean cao hơn raw rõ rệt, đạt 0.796 so với 0.764 của raw. Điều này chứng minh mô hình học từ dữ liệu sạch bắt đối tượng chắc chắn hơn và ít bị báo động giả.
Ba là tập clean bị giảm mất 21 ảnh hỏng ở cửa vào, từ 224 ảnh giảm còn 203 ảnh. Việc mất gần 10% dữ liệu trên một tập nhỏ khiến chỉ số recall bị giảm từ 0.649 xuống 0.596.
Bốn là do ngân sách duyệt giới hạn 80 ảnh nên tập clean vẫn còn 38 ảnh có cảnh báo nghi ngờ chưa được người sửa.
Hướng xử lý tiếp theo của mình là bổ sung thêm ảnh sạch mới để bù lại 21 ảnh đã bị loại, đồng thời chạy thêm biến thể oracle và thử nghiệm với 5 seed trên tập test lớn hơn để giảm độ nhiễu.

## 6. Quyết định và ghi chú AI
(a) Quyết định cuối:
Quyết định cuối cùng cho lô dữ liệu này là Hold. Để chuyển sang Release thì dự án cần tăng ngân sách duyệt người từ 80 ảnh lên ít nhất 125 ảnh để xử lý nốt 38 ảnh còn tồn đọng trong danh sách cảnh báo. Khi người đã xem xong các ảnh này, mình chạy lại pipeline với cờ resume-after-review thì tỷ lệ cảnh báo sẽ về 0%, lúc đó gate sẽ tự động chuyển sang Release với mã thoát 0.

(b) Ghi chú sử dụng AI:
Quy trình phối hợp hiệu quả với AI được mình chia thành các bước rõ ràng:
Bước 1, lập kế hoạch và nhận diện rủi ro: Mình yêu cầu AI đọc toàn bộ cấu trúc repo, các file hướng dẫn và quy định làm bài để lập kế hoạch chi tiết từng giai đoạn, đồng thời liệt kê các điều cấm kỵ cần tránh như không can thiệp thư mục data gốc, không sửa các file mã nguồn có sẵn và không hardcode kết quả.
Bước 2, thực thi và tinh chỉnh có kiểm soát: Mình phối hợp với AI lập trình 4 module cốt lõi theo phương pháp TDD bám sát docstring và các ca test. Ở bước hiệu chuẩn, mình yêu cầu AI quét dải tham số rồi mình chất vấn kỹ về sự đánh đổi giữa precision và recall để tự quyết định chốt ngưỡng an toàn cho phash_dist và conf. Khi huấn luyện trên Colab, mình yêu cầu AI giải thích cặn kẽ ý nghĩa của từng tập dữ liệu và bản chất hiện tượng rò rỉ đề thi khiến điểm raw bị thổi phồng ảo.
Bước 3, kiểm tra và rà soát toàn diện: Mình yêu cầu Agent kiểm tra lại toàn bộ bài làm bằng lệnh pytest 79 bài test, chạy script thẩm định độc lập check_submission và rà soát kỹ lưỡng lịch sử git diff để bảo đảm bài nộp hoàn toàn sạch sẽ, không sót file lạ hay vi phạm quy chế.
Những lần AI sai và mình điều chỉnh: Thứ nhất là khi hiệu chuẩn ảnh trùng, AI ban đầu đề xuất phash_dist bằng 16 vì điểm F1 trên 39 ảnh calib đạt cao nhất 0.91, nhưng khi mình yêu cầu thử trên 224 ảnh raw thật thì phát hiện ngưỡng 16 xóa nhầm ảnh khác biệt và báo nhầm rò rỉ test, nên mình quyết định chốt ngưỡng 8. Thứ hai là AI từng tự ý thêm dòng cấu hình vào file .gitignore để lưu bản nháp, mình phát hiện đây là file gốc của đề bài không được phép chỉnh sửa nên đã bắt khôi phục về nguyên bản ngay lập tức.
