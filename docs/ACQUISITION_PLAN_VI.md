# Tìm người dùng đầu tiên cho AppReview Radar

Người nên thử là nhà phát triển app độc lập, người làm sản phẩm và agency ASO
đang đọc review thủ công. Một câu hỏi cụ thể giúp demo rõ hơn: sau một bản cập
nhật, người dùng đang nhắc đến đăng nhập, thanh toán hay hiệu năng như thế nào?

## Demo để đưa cho người dùng

1. Dùng [hướng dẫn lần đầu](FIRST_RUN_VI.md) với giới hạn nhỏ.
2. Thay ID mẫu bằng ứng dụng họ quan tâm, chọn thị trường và mức sao phù hợp.
3. Tải CSV và `feedback-report.md`; đối chiếu vài review với nguồn và đọc dẫn
   chứng. Số khớp từ khóa không chứng minh có lỗi hay nhu cầu xây tính năng.
4. Chạy lại với `KNOWN_REVIEW_IDS` để xem các review đã lấy bị bỏ qua.

## Kiểm chứng trong một tuần

| Việc | Điều cần tìm hiểu |
| --- | --- |
| Chia sẻ một demo ở kênh cho phép giới thiệu công cụ | Người xem có đang làm đúng việc đọc/phân tích review không? |
| Mời ba người phù hợp tự dùng thử nếu họ đồng ý | Họ nhập đúng app và tải được đầu ra có ích không? |
| Ghi lại trở ngại | Thiếu nguồn, thiếu thị trường, từ khóa khớp sai, hay CSV khó dùng? |
| Hỏi sau lần dùng | Họ có dùng bản xuất để quyết định hoặc giao việc gì không? |
| Theo dõi lần quay lại | Họ có cần thu thập tiếp theo lịch hay chỉ thử một lần? |

Đây là kế hoạch thử nghiệm, không phải cam kết sẽ có ba người dùng hay khách
trả tiền. Có [bài đăng Anh/Việt](LAUNCH_POSTS.md) và ảnh minh họa tại
`assets/launch/review-radar-preview.png`. Nêu rõ bạn làm công cụ và tuân theo quy
định của nơi đăng. Chưa có bài đăng, email hay tin nhắn quảng bá nào được gửi.

Nếu người thử thường gặp feed trống, ưu tiên giải thích đúng nguồn/thị trường
hoặc sửa khả năng truy cập có bằng chứng. Nếu họ muốn theo dõi review chỉnh sửa,
đó là tính năng khác với cơ chế bỏ qua mã hiện tại và cần thiết kế riêng.

## Đọc số liệu tiền đúng chỗ

Insights → Monetization cho biết người dùng trả phí và lợi nhuận được ghi nhận.
Payouts cho biết khoản thanh toán; Usage và Cost per 1,000 results là chi phí.
Giá cấu hình là $0.50/1.000 review phù hợp được lưu. Số kết quả, số người dùng,
lượt kiểm thử của chủ tài khoản và doanh thu là những số khác nhau.

Mục tiêu sau khi đăng sản phẩm là một khách thật thấy đầu ra hữu ích và có lý
do chạy lại. Sau đó mới có cơ sở mở rộng nguồn hay đầu tư thêm quảng bá.
