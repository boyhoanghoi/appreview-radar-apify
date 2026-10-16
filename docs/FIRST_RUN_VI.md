# Chạy thử AppReview Radar

Công cụ lấy đánh giá công khai của ứng dụng Android/iOS, lọc theo câu hỏi bạn đang nghiên cứu, rồi xuất CSV và báo cáo Markdown có dẫn chứng từ đánh giá gốc.

## 1. Mở Actor và giới hạn chi phí

Mở [AppReview Radar trên Apify](https://apify.com/reliable_quatrain/google-play-app-store-review-radar), chọn **Try for free**, rồi chuyển phần Input sang **JSON**. Kiểm tra giá hiện hành ở tab **Pricing**. Với mẫu nhỏ bên dưới, có thể đặt **Maximum total charge = $0.02**. Nếu chạm giới hạn phí, kết quả có thể ít hơn mức bạn yêu cầu.

## 2. Dán cấu hình mẫu

```json
{
  "appPreset": "chatgpt",
  "country": "gb",
  "language": "en",
  "maxReviews": 20,
  "maxReviewsPerApp": 10,
  "maxPagesPerApp": 1,
  "maxRating": 3
}
```

Mẫu này đọc đánh giá công khai của ChatGPT trên Google Play (`com.openai.chatgpt`) và App Store (`6448311069`). Đây là công cụ độc lập, không thuộc OpenAI, Google hay Apple.

- `maxRating: 3`: chỉ giữ đánh giá từ 1 đến 3 sao.
- `maxReviews: 20`: lưu tối đa 20 đánh giá trong cả lần chạy.
- `maxReviewsPerApp: 10`: lưu tối đa 10 đánh giá cho mỗi ứng dụng.
- `maxPagesPerApp: 1`: chỉ kiểm tra một trang nguồn cho mỗi ứng dụng.

**20 là giới hạn trên, không phải số chắc chắn nhận được.** Có thể chỉ tìm thấy vài đánh giá phù hợp hoặc không có kết quả. Nguồn lỗi sẽ được ghi trong chẩn đoán; không được hiểu là ứng dụng không có đánh giá.

## 3. Bấm Start và xem kết quả

Sau khi chạy xong, mở dataset để xem từng đánh giá. Đọc nội dung gốc, số sao, nguồn, ngày/phiên bản nếu có, cùng từ/cụm từ khiến công cụ gắn nhãn chủ đề.

Trong tab **Output**, mở hoặc tải các tệp được liên kết bên dưới. Bản ghi riêng
`OUTPUT` chứa báo cáo JSON đầy đủ.

| Kết quả | Dùng để làm gì |
| --- | --- |
| `results.csv` | Mở bằng Excel/Google Sheets hoặc nhập vào hệ thống riêng |
| `feedback-report.md` | Đọc số lượng, phân bố sao, chủ đề và trích đoạn dẫn chứng |
| `TOPICS` | Xem số lượt khớp từng chủ đề cùng dẫn chứng |
| `SUMMARY` | Xem tổng kết lần chạy |
| `DIAGNOSTICS` | Xem nguồn lỗi, bộ lọc và giới hạn trang |
| `KNOWN_REVIEW_IDS` | Lấy danh sách mã đã lưu để truyền sang lần chạy sau |

Báo cáo chỉ thống kê **những đánh giá đã lưu**. Điểm trung bình trong báo cáo không phải điểm tổng của ứng dụng trên store. Một đánh giá có thể khớp nhiều chủ đề, nên không cộng số từng chủ đề để suy ra tổng số người.

## 4. Thay bằng ứng dụng bạn muốn nghiên cứu

Đặt `appPreset` thành `none`, rồi nhập ID hoặc đường dẫn trang ứng dụng vào `googlePlayApps` và/hoặc `appStoreApps`. Có thể chọn tối đa 10 ứng dụng sau khi gộp và bỏ trùng.

Ví dụ nghiên cứu đánh giá 1–2 sao của hai ứng dụng Android:

```json
{
  "appPreset": "none",
  "googlePlayApps": ["com.spotify.music", "com.soundcloud.android"],
  "country": "us",
  "language": "en",
  "maxReviews": 30,
  "maxReviewsPerApp": 15,
  "maxPagesPerApp": 2,
  "maxRating": 2
}
```

Muốn tìm vấn đề thanh toán, thêm `topicFilters: ["billing"]`. Muốn giữ đánh giá chứa ít nhất một từ cụ thể, thêm `includeKeywords: ["subscription", "refund"]`. Các bộ lọc kết hợp với nhau, nên thêm điều kiện sẽ làm giảm số kết quả.

Các chủ đề hỗ trợ: `stability`, `performance`, `billing`, `login`, `ads`, `privacy`, `feature-request`. Đây là luật khớp từ/cụm từ tiếng Anh và tiếng Việt. Công cụ không dùng AI, có thể bỏ sót cách diễn đạt khác hoặc khớp câu phủ định. `featureRequestsOnly: true` chỉ tìm cụm từ yêu cầu tính năng; bạn vẫn cần đọc lại để hiểu ý người viết.

`country` là thị trường bạn yêu cầu đọc, không xác minh nơi cư trú của người viết. `language` là gợi ý ngôn ngữ cho Google Play, không đảm bảo mọi đánh giá sẽ viết bằng ngôn ngữ đó.

## 5. Tránh lưu lại đánh giá cũ

Sao chép mảng trong `KNOWN_REVIEW_IDS` của lần chạy trước vào trường `knownReviewIds` của lần chạy tiếp theo. Khóa có dạng `{store}:{appId}:{reviewId}`.

Đánh giá có khóa đã biết được bỏ qua trước khi lưu và tính phí. Chỉ đánh giá thực sự lưu thành công mới được thêm vào lịch sử; tối đa giữ 10.000 khóa. Khi vượt giới hạn, khóa cũ có thể rơi khỏi danh sách.

**Tạo lịch chạy không tự truyền lịch sử này.** Workflow gọi Actor phải tự đọc danh sách cũ rồi gửi vào input mới. Nếu người dùng sửa một đánh giá nhưng ID giữ nguyên, công cụ vẫn bỏ qua; đây là chống trùng, không phải theo dõi nội dung đã chỉnh sửa.

Nếu chạy trên máy bằng CLI:

```powershell
reviewradar --input examples/first-run.json --output output
reviewradar --input examples/first-run.json --previous-ids output/known_review_ids.json --output output-next
```

Lần sau vẫn có thể nhận kết quả vì xuất hiện đánh giá mới hoặc cửa sổ nguồn thay đổi.

## Phí và giới hạn cần hiểu

Giá đã cấu hình khi ra mắt: **$0.50/1.000 đánh giá phù hợp được lưu**, không có phí sự kiện khởi động Actor. Với tối đa 20 kết quả, phần phí sự kiện đánh giá là tối đa $0.01 ở mức giá đó. Giá đang áp dụng phải xem trong tab **Pricing**; chi phí nền tảng tuân theo gói/mô hình Apify tương ứng.

Đánh giá bị lọc, trùng, có trong danh sách đã biết hoặc nguồn lỗi không tạo sự kiện tính phí đánh giá. Nguồn web/feed chỉ cung cấp một phần dữ liệu; công cụ đọc tối đa 10 trang cho mỗi ứng dụng, và các trang có thể ít đánh giá hoặc trống. Không được coi đây là toàn bộ lịch sử hay mẫu đại diện cho mọi người dùng.

Xem [SOURCES.md](SOURCES.md) để hiểu nguồn truy cập, ý nghĩa ngày, trường còn thiếu và chính sách đọc nguồn. Báo cáo có ích để tìm điểm cần kiểm tra tiếp; nó không tự chứng minh nhu cầu trả tiền hoặc lỗi của ứng dụng.
