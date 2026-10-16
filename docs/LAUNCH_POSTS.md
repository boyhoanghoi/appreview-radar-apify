# Launch drafts — not posted

These drafts are prepared for the creator to review and publish in places that permit relevant self-promotion. No outreach, direct messages, emails, or community posts have been sent. Recheck each community's current rules before posting. Do not add invented trial users, ratings, revenue, performance figures, or testimonials.

## English: founder / product research audience

I built **AppReview Radar**, an Apify tool for turning public Google Play and App Store reviews into a small feedback shortlist.

If you're building a mobile app or researching competitors, you can select apps, filter by stars/words/date, and export CSV plus a Markdown report with source excerpts. It also tags literal mentions of login, billing, crashes/performance, ads, privacy, and feature requests using transparent English/Vietnamese keyword rules.

The goal is to reduce the spreadsheet work between “download reviews” and “which feedback should I read next?” It doesn't use an LLM or claim that a phrase match is a verified bug or feature request.

There's a small Android+iOS ChatGPT demo preset. Coverage is limited by the source windows and page caps; it isn't a full-history or representative-sample guarantee. You can pass saved review keys into a later run to skip exported reviews, but your calling workflow must carry those keys explicitly.

I'm the developer. I'm looking for feedback from app founders, product/ASO analysts, or agencies: **would the report help with a real task, and what would make the output more useful?**

Actor: https://apify.com/reliable_quatrain/google-play-app-store-review-radar

Guide and open-source code: https://github.com/boyhoanghoi/appreview-radar-apify

Launch target is $0.50/1,000 saved matching reviews, with no Actor start fee; check the live Pricing tab. Filters and supplied known review keys are applied before review charges. This post does not claim existing customer traction.

## Vietnamese: cộng đồng phát triển sản phẩm / ứng dụng

Mình vừa làm **AppReview Radar** trên Apify: lấy đánh giá công khai từ Google Play và App Store, lọc thành danh sách phản hồi cần đọc, rồi xuất CSV và báo cáo Markdown có dẫn chứng gốc.

Bạn có thể chọn ứng dụng của mình/đối thủ, lọc số sao, từ khóa và ngày; xem các cụm từ liên quan đăng nhập, thanh toán, hiệu năng, quảng cáo, quyền riêng tư hoặc yêu cầu tính năng. Phần gắn nhãn dùng luật từ khóa tiếng Anh/Việt, không dùng AI và không tự khẳng định người dùng báo lỗi đúng hay có nhu cầu mua tính năng.

Có mẫu nhỏ với ChatGPT trên Android+iOS để thử định dạng. Dữ liệu bị giới hạn theo cửa sổ nguồn và số trang; không phải toàn bộ lịch sử hay khảo sát đại diện. Có thể truyền danh sách mã đã lưu để tránh xuất lại; workflow gọi công cụ phải tự truyền danh sách giữa các lần chạy.

Mình là người phát triển và muốn xin phản hồi từ bạn làm app, product, ASO hoặc agency: **báo cáo này có giúp bạn trả lời câu hỏi thực tế nào không, và còn thiếu gì để dùng thường xuyên?**

Actor: https://apify.com/reliable_quatrain/google-play-app-store-review-radar

Hướng dẫn và mã nguồn: https://github.com/boyhoanghoi/appreview-radar-apify

Giá đã cấu hình $0.50/1.000 đánh giá phù hợp được lưu, không có phí sự kiện khởi động; xem giá hiện hành ở tab Pricing. Đánh giá bị lọc hoặc có mã trong lịch sử được bỏ qua trước khi tính phí đánh giá. Mình chưa dùng số lượt tự chạy để tuyên bố có khách hàng trả tiền.

## Short product listing

AppReview Radar combines public Android and iOS reviews into a filtered feedback shortlist. Export CSV and a source-backed Markdown report, inspect transparent keyword/topic matches, and pass saved keys into later runs to skip duplicates. For indie app founders, product/ASO teams, and agencies. Public data only; bounded source coverage; no LLM key needed.

## Before publishing a draft

Confirm the Actor is public, its live rate matches the text, and its first-run input succeeds or clearly reports source failures. Attach `assets/launch/review-radar-preview.png` as an **illustrative workflow**, not a performance result. Disclose that you built it. Respect posting rules and ask a focused question; avoid unsolicited repeated promotion.
