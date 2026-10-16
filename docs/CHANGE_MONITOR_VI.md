# Theo dõi review đã sửa

Bản mới cho phép so sánh review với **snapshot bạn truyền vào**, thay vì chỉ bỏ
qua mã đã thấy. Công cụ nhận biết thay đổi trong tiêu đề/nội dung, số sao,
phiên bản app và phản hồi nhà phát triển mà nguồn có cung cấp.

1. Dùng `examples/change-monitor.json`: bật `changedOnly`, để `previousSnapshot`
   rỗng và giữ `knownReviewIds` là mảng rỗng.
2. Sau lần chạy, lưu toàn bộ bản ghi **SNAPSHOT**.
3. Lần sau đưa đối tượng đó vào `previousSnapshot`, cùng `country` và `language`.
4. Đọc `reviewChange`: `NEW` là chưa có trong baseline đã truyền, `UPDATED` là
   nội dung được so sánh đã đổi; `UNCHANGED` bị bỏ qua trước khi lưu/tính phí
   nếu bật `changedOnly`.

`NEW` không đồng nghĩa vừa đăng. Lần chạy bị giới hạn hoặc lọc có thể chưa thấy
hết review cũ. Nguồn chỉ cho một cửa sổ dữ liệu; review nằm ngoài cửa sổ không
được kiểm tra. Công cụ không kết luận review bị xóa từ sự vắng mặt.

Chỉ review thực sự được lưu mới cập nhật hash. Review lỗi, bị lọc hoặc chưa đủ
phí giữ nguyên baseline. Snapshot giữ tối đa 10.000 mã và 2 MiB JSON UTF-8;
nếu đầy, mã lưu cũ nhất bị bỏ và `snapshotTruncated` báo rõ. Mã bị bỏ có thể
được coi là `NEW` lần sau. Công cụ so sánh tối đa 8.000 ký tự review; lượt bình
chọn, ngày nguồn và thời điểm quan sát tự đổi không được coi là sửa nội dung.

**Không dùng đồng thời danh sách mã cũ nếu muốn bắt review đã sửa:**
`knownReviewIds` có quyền ưu tiên và vẫn bỏ qua mọi review cùng mã. Mặc định
`changedOnly: false` vẫn lưu/tính phí các review khớp dù không đổi. Tạo lịch
không tự truyền snapshot; workflow của bạn phải lưu và gửi SNAPSHOT mới nhất.

## Chạy trên máy

```powershell
reviewradar --input examples/change-monitor.json --output output/monitor-first
reviewradar --input examples/change-monitor.json --previous-snapshot output/monitor-first/snapshot.json --output output/monitor-next
```

File truyền qua `--previous-snapshot` thay đối tượng `previousSnapshot` trong
input và phải cùng thị trường/ngôn ngữ. File `snapshot.json` được thay nguyên
tử sau khi xuất xong các tệp khác. Lần sau vẫn có thể nhận review khác chưa có
trong snapshot, nên không cam kết kết quả bằng không.

## Lọc phiên bản và trạng thái phản hồi

- `appVersionKeywords`: giữ review có phiên bản nguồn chứa ít nhất một chuỗi
  đã nhập, không phân biệt hoa/thường. Review thiếu phiên bản bị loại khi bật.
- `replyFilter: "with-reply"`: Google Play có phản hồi nhà phát triển được hiển thị.
- `replyFilter: "without-visible-reply"`: Google Play không hiển thị phản hồi
  trong nguồn này, không chứng minh tình trạng ở mọi giao diện.
- Hai bộ lọc phản hồi loại review Apple vì RSS không cung cấp trạng thái đó.
  Dùng `all` để giữ hành vi cũ.

Các trường mới dùng được cho hàng đợi hỗ trợ và theo dõi một phiên bản app,
nhưng bạn vẫn cần đọc dẫn chứng trước khi kết luận nguyên nhân lỗi.
