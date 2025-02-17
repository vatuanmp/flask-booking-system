from datetime import datetime
from flask import Flask, render_template, request
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2 import service_account
from flask import jsonify

app = Flask(__name__)

# Đọc đường dẫn file credentials từ thư mục /secrets/
credentials_path = '/etc/secrets/credentials.json'

# Kết nối Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
#creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
creds = service_account.Credentials.from_service_account_file(credentials_path, scopes=scope)
client = gspread.authorize(creds)

# Mở Google Sheets
SPREADSHEET_NAME = "Lich_Kham_Benh"
spreadsheet = client.open(SPREADSHEET_NAME)

# Hàm lấy danh sách giờ khám
def get_available_times(date_str):
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return []  # Ngày không hợp lệ, trả về danh sách trống

    weekday = date_obj.weekday()
    start_time, end_time = (17, 19) if weekday < 5 else (8, 17)

    available_times = []
    time = start_time * 60
    while time < end_time * 60:
        hours = time // 60
        minutes = time % 60
        available_times.append(f"{hours:02}:{minutes:02}")
        time += 15  # Mỗi ca khám kéo dài 15 phút

    return available_times

@app.route("/get_available_times", methods=["GET"])
def get_times():
    ngay_kham = request.args.get("date")
    if not ngay_kham:
        return jsonify({"available_times": []})  # Không có ngày thì trả về rỗng

    available_times = get_available_times(ngay_kham)

    try:
        sheet_ngay_kham = spreadsheet.worksheet(ngay_kham)
        booked_times = sheet_ngay_kham.col_values(4)[1:]  # Lấy giờ khám đã đặt (bỏ tiêu đề)
        booked_times = [t.strip() for t in booked_times if t.strip()]  # Xóa khoảng trắng, bỏ trống
    except gspread.exceptions.WorksheetNotFound:
        booked_times = []  # Nếu chưa có sheet ngày đó thì coi như chưa có ai đặt

    free_times = [time for time in available_times if time not in booked_times]

    return jsonify({"available_times": free_times})

@app.route('/', methods=['GET', 'POST'])
def dang_ky():
    if request.method == "POST":
        ten = request.form.get("name")
        ngay_sinh = request.form.get("dob")
        ngay_kham = request.form.get("date")
        gio_kham = request.form.get("time")

        if not ngay_kham or not gio_kham:
            return "Vui lòng chọn ngày và giờ khám hợp lệ!"

        try:
            sheet_ngay_kham = spreadsheet.worksheet(ngay_kham)
        except gspread.exceptions.WorksheetNotFound:
            sheet_ngay_kham = spreadsheet.add_worksheet(title=ngay_kham, rows="100", cols="4")
            sheet_ngay_kham.append_row(["Họ tên", "Ngày sinh", "Ngày khám", "Giờ khám"])

        booked_times = sheet_ngay_kham.col_values(4)[1:]  # Lấy danh sách giờ khám đã đặt
        booked_times = [t.strip() for t in booked_times if t.strip()]

        if gio_kham in booked_times:
            return f"Giờ {gio_kham} vào ngày {ngay_kham} đã có người đặt. Vui lòng chọn giờ khác!"

        try:
            sheet_tong_hop = spreadsheet.worksheet("Tong_Hop")
        except gspread.exceptions.WorksheetNotFound:
            sheet_tong_hop = spreadsheet.add_worksheet(title="Tong_Hop", rows="1000", cols="4")
            sheet_tong_hop.append_row(["Họ tên", "Ngày sinh", "Ngày khám", "Giờ khám"])

        sheet_tong_hop.append_row([ten, ngay_sinh, ngay_kham, gio_kham])
        sheet_ngay_kham.append_row([ten, ngay_sinh, ngay_kham, gio_kham])

        #return f"Đăng ký thành công cho {ten} vào ngày {ngay_kham} lúc {gio_kham}!"
        return jsonify({
            "message": f"Đăng ký thành công cho {ten} vào ngày {ngay_kham} lúc {gio_kham}!"
        })


    return render_template("index.html")

#if __name__ == "__main__":
#    app.run(debug=True, host="127.0.0.1", port=5000)
if __name__ == "__main__":
    # Lắng nghe trên tất cả các địa chỉ IP và cổng do Render cung cấp
    port = int(os.environ.get("PORT", 5000))  # Cổng mặc định là 5000 nếu không có biến môi trường
    app.run(debug=True, host="0.0.0.0", port=port)

