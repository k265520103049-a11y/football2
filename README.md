# ⚽ Football Universe

Website mẫu đồ án: bách khoa bóng đá kết hợp minigame tương tác, có ngân hàng câu hỏi được làm mới định kỳ từ Wikipedia và có thể triển khai trên **GitHub Pages**.

## Tính năng
- Giao diện responsive, dark sports UI.
- 12 kiểu minigame: đoán cầu thủ, xây đội hình kéo-thả, nhận diện CLB, penalty, ghép thẻ trí nhớ, sắp xếp lịch sử, tìm kẻ khác biệt, lộ trình sự nghiệp, transfer market, chiến thuật, quiz tốc độ và giải mã huy hiệu.
- Câu hỏi, câu trả lời và thứ tự lựa chọn được xáo trộn trong lúc chơi.
- Football Wiki tìm kiếm Wikipedia qua MediaWiki Action API.
- **Quiz tốc độ ưu tiên ngân hàng câu hỏi tự sinh** trong `data/generated-questions.json`; mỗi câu có đường dẫn bài nguồn và đáp án là tiêu đề của bài Wikipedia tương ứng.
- GitHub Actions tự chạy mỗi tuần và cho phép chạy thủ công để làm mới câu hỏi.
- XP, số lượt chơi và huy hiệu được lưu trong `localStorage` trên trình duyệt.

## Cách câu hỏi tự cập nhật hoạt động

1. `scripts/update_question_bank.py` lấy danh sách bài thuộc các danh mục bóng đá trên Wikipedia, kết hợp một danh sách hạt giống cầu thủ/CLB/giải đấu nổi tiếng.
2. Script truy vấn phần mở đầu dạng văn bản thuần của mỗi bài bằng MediaWiki Action API.
3. Script tạo các câu hỏi dạng nhận diện chủ thể từ phần mô tả đó. Đáp án là tiêu đề bài viết; ba lựa chọn gây nhiễu lấy từ cùng nhóm chủ đề. Mỗi câu đều lưu `sourceUrl`, ngày cập nhật và tiêu đề bài gốc.
4. `.github/workflows/update-questions.yml` chạy định kỳ vào thứ Hai lúc 03:23 UTC (10:23 sáng giờ Việt Nam), hoặc chạy ngay khi chọn **Actions → Refresh Wikipedia football questions → Run workflow**.
5. Workflow ghi thay đổi vào `data/generated-questions.json` rồi commit lên nhánh. Khi GitHub Pages đang triển khai từ nhánh đó, bản website mới sẽ đọc ngân hàng câu hỏi vừa cập nhật.

Câu hỏi được tạo theo mẫu từ dữ liệu bài viết, không dùng AI để bịa thêm sự kiện. Chất lượng câu hỏi phụ thuộc phần giới thiệu trên Wikipedia; nội dung mô tả có thể bằng tiếng Anh. Mỗi lượt, câu hỏi và vị trí các lựa chọn được chọn/xáo ngẫu nhiên. Nếu chưa có ngân hàng mới hoặc tải thất bại, game dùng bộ câu hỏi dự phòng tĩnh.

## Đưa website lên GitHub Pages

1. Tải và giải nén source code.
2. Tạo repository mới, ví dụ `football-universe`.
3. Đưa **toàn bộ nội dung trong thư mục dự án** lên nhánh `main`, bao gồm thư mục ẩn `.github` và file `.nojekyll`.
4. Vào **Settings → Pages**. Trong phần **Build and deployment**, chọn **Deploy from a branch**, chọn `main` và folder `/(root)`, rồi lưu.
5. Mở tab **Actions** và chạy workflow `Refresh Wikipedia football questions` thủ công lần đầu để tạo ngân hàng ban đầu.
6. Nếu workflow báo lỗi quyền `git push`, vào **Settings → Actions → General → Workflow permissions**, bật **Read and write permissions** rồi chạy lại workflow.
7. Website sẽ có URL dạng `https://TEN-TAI-KHOAN.github.io/football-universe/`.

Không cần API key, backend hay cài package để chạy website tĩnh. Tìm kiếm Wikipedia trực tiếp cần kết nối Internet. Workflow chạy trên GitHub-hosted runner nên máy tính cá nhân không cần tự chạy script.

## Chạy script thủ công (tùy chọn)

Cần Python 3.10+ và Internet:

```bash
python scripts/update_question_bank.py
```

Lệnh này sẽ tạo/ghi đè `data/generated-questions.json`. Nếu không lấy được đủ dữ liệu nguồn, script dừng thay vì ghi đè ngân hàng trước đó bằng dữ liệu rỗng.

## Nguồn dữ liệu và giới hạn
- API: https://www.mediawiki.org/wiki/API:Main_page
- Danh mục Wikipedia được dùng để khám phá trang: https://www.mediawiki.org/wiki/API:Categorymembers
- Mỗi câu hỏi hiển thị đường dẫn bài viết Wikipedia làm nguồn. Cần kiểm chứng khi dùng dữ liệu trong môi trường học thuật hoặc thi đấu có giải thưởng.
- Bài Wikipedia có thể thiếu, thay đổi, chuyển hướng hoặc chưa có phần giới thiệu đủ rõ; script bỏ qua bài thiếu mô tả và giữ ngân hàng cũ nếu việc tạo câu hỏi thất bại.
- Dữ liệu của các minigame ngoài Quiz tốc độ và một số câu dự phòng vẫn là dữ liệu demo biên soạn sẵn; workflow hiện chưa tự cập nhật toàn bộ luật chơi, dữ liệu đội hình hay tất cả minigame.
- Bản demo chưa có đăng nhập, bảng xếp hạng trực tuyến hoặc đồng bộ tiến trình qua nhiều thiết bị.

## Cấu trúc dự án

```text
football-universe/
├── index.html
├── README.md
├── LICENSE
├── .nojekyll
├── data/
│   └── generated-questions.json
├── scripts/
│   └── update_question_bank.py
└── .github/
    └── workflows/
        └── update-questions.yml
```

## Hướng phát triển tiếp
- Thêm câu hỏi định lượng từ Wikidata (năm sinh, quốc tịch, danh hiệu) với kiểm tra dữ liệu trước khi phát hành.
- Lọc theo giải đấu, quốc gia, vị trí và thời kỳ.
- Lưu tài khoản, bảng xếp hạng và phòng chơi nhiều người bằng backend.
- Bổ sung kiểm thử tự động cho dữ liệu câu hỏi và thao tác trên điện thoại.
