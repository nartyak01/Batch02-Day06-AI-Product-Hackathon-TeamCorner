"""One-off generator for Vinmec 18 specialties × 3 doctors × slots."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data"

SPECIALTIES: list[tuple[str, str, str]] = [
    (
        "cap_cuu",
        "Cấp cứu",
        "Escalation/cấp cứu: đau ngực dữ dội, khó thở nặng, choáng, ngất, co giật, chảy máu không cầm, sốt cao kèm lơ mơ. Không đặt lịch ngoại trú thường.",
    ),
    (
        "tim_mach",
        "Trung tâm Tim mạch",
        "Đau ngực âm ỉ, hồi hộp, tim đập nhanh, tăng huyết áp, khó thở khi gắng sức (không red flag cấp cứu).",
    ),
    (
        "ung_buou",
        "Trung tâm Ung bướu",
        "Khối u/nốt cứng bất thường, sụt cân không rõ nguyên nhân, ho ra máu lâu ngày, thay đổi ruột/bladder kéo dài — sàng lọc và theo dõi ung thư.",
    ),
    (
        "mien_dich_di_ung",
        "Miễn dịch - Dị ứng",
        "Phát ban, mày đay, viêm mũi họng dị ứng, hen phế quản nhẹ, nghi ngờ dị ứng thực phẩm/thuốc.",
    ),
    (
        "tieu_hoa_gan_mat",
        "Tiêu hoá - Gan mật",
        "Đau bụng, tiêu chảy, nôn, ợ chua, vàng da nhẹ, đầy bụng, men gan cao theo dõi — bệnh đường tiêu hóa và gan mật.",
    ),
    (
        "nhi",
        "Trung tâm Nhi",
        "Trẻ em: sốt, ho, tiêu chảy, phát ban, chậm phát triển, tiêm chủng tư vấn — khám nhi khoa.",
    ),
    (
        "suc_khoe_phu_nu",
        "Trung tâm Sức khoẻ phụ nữ",
        "Khám phụ khoa, kinh nguyệt bất thường, mang thai (thai sản), mãn kinh, u xơ tử cung — sức khỏe sinh sản nữ.",
    ),
    (
        "suc_khoe_tong_quat",
        "Sức khoẻ tổng quát",
        "Khám sức khỏe định kỳ, tầm soát tổng quát, triệu chứng chưa rõ cần sàng lọc ban đầu.",
    ),
    (
        "nha_khoa_view",
        "Vinmec - View Premium Dental Clinic",
        "Đau răng, sâu răng, chỉnh nha, cạo vôi, nha khoa thẩm mỹ — không xử lý cấp cứu nội khoa.",
    ),
    (
        "y_hoc_co_truyen",
        "Trung tâm Y học cổ truyền Vinmec-Sao Phương Đông",
        "Đau mỏi mãn tính, thoái hóa, rối loạn giấc ngủ nhẹ, mong muốn điều trị Đông y phối hợp.",
    ),
    (
        "tai_tao_te_bao",
        "Trung tâm Y học Tái tạo và Trị liệu Tế bào",
        "Tư vấn liệu pháp tế bào/tái tạo theo chỉ định chuyên môn, thường sau khi đã có chẩn đoán nền.",
    ),
    (
        "chan_thuong_the_thao",
        "Trung tâm Chấn thương chỉnh hình - Y học thể thao",
        "Chấn thương khớp, gãy xương sau chấn thương, đau vai/gối, thoái hóa khớp, phục hồi thể thao.",
    ),
    (
        "te_bao_goc_gen",
        "Viện nghiên cứu tế bào gốc và công nghệ Gen",
        "Tư vấn xét nghiệm gen, tế bào gốc theo protocol — không thay khám cấp cứu triệu chứng cấp.",
    ),
    (
        "vacxin",
        "Trung tâm Vacxin",
        "Tư vấn và tiêm chủng theo lịch, nhắc mũi vaccine, phác đồ phòng bệnh.",
    ),
    (
        "vu",
        "Trung tâm Vú",
        "Khối vú, đau vú, dịch núm vú, tầm soát ung thư vú, theo dõi sau phẫu thuật vú.",
    ),
    (
        "than_kinh",
        "Thần kinh",
        "Đau đầu kéo dài, chóng mặt, tê bì tay chân, co giật đã được chẩn đoán, Parkinson, đột quỵ tái khám.",
    ),
    (
        "tam_than",
        "Trung tâm chăm sóc sức khỏe tinh thần tích hợp",
        "Lo âu, trầm cảm, mất ngủ liên quan tâm lý, stress kéo dài — hỗ trợ sức khỏe tâm thần (không thay cấp cứu tự hại).",
    ),
    (
        "duoc",
        "Khối Dược",
        "Tư vấn thuốc, tương tác thuốc, liều dùng, mua thuốc theo đơn — không khám chẩn đoán bệnh lý mới.",
    ),
]

FACILITIES = ("times_city", "smart_city")
SLOT_TIMES = ("08:00", "10:30", "14:00")
SLOT_DATES = ("2026-06-05", "2026-06-06", "2026-06-07")

TITLES = ("Bác sĩ", "Thạc sĩ - Bác sĩ", "BS.CKI")

# 54 tên giả lập (họ + tên đệm + tên)
_DOCTOR_NAMES = [
    "Nguyễn Văn An",
    "Trần Thị Bích",
    "Lê Hữu Cường",
    "Phạm Minh Đức",
    "Hoàng Thị Giang",
    "Vũ Quốc Hải",
    "Đặng Thị Hạnh",
    "Bùi Văn Khải",
    "Đỗ Thị Lan",
    "Ngô Minh Long",
    "Nguyễn Thị Mai",
    "Trần Văn Nam",
    "Lê Thị Oanh",
    "Phạm Đức Phúc",
    "Hoàng Thị Quỳnh",
    "Vũ Văn Sơn",
    "Đặng Thị Thảo",
    "Bùi Minh Tuấn",
    "Đỗ Thị Uyên",
    "Ngô Văn Vinh",
    "Nguyễn Thị Xuân",
    "Trần Hữu Yên",
    "Lê Văn Bảo",
    "Phạm Thị Chi",
    "Hoàng Đức Dũng",
    "Vũ Thị Hương",
    "Đặng Văn Kiên",
    "Bùi Thị Linh",
    "Đỗ Quốc Mạnh",
    "Ngô Thị Nga",
    "Nguyễn Văn Phong",
    "Trần Thị Quyên",
    "Lê Minh Tâm",
    "Phạm Thị Vân",
    "Hoàng Văn Đạt",
    "Vũ Thị Hiền",
    "Đặng Quốc Hùng",
    "Bùi Thị Kim",
    "Đỗ Văn Lộc",
    "Ngô Thị My",
    "Nguyễn Đức Nghĩa",
    "Trần Thị Phượng",
    "Lê Văn Quang",
    "Phạm Thị Sinh",
    "Hoàng Minh Thắng",
    "Vũ Thị Trang",
    "Đặng Văn Uy",
    "Bùi Thị Vy",
    "Đỗ Hữu Xuân",
    "Ngô Thị Yến",
    "Nguyễn Văn Hiếu",
    "Trần Thị Loan",
    "Lê Quốc Thịnh",
    "Phạm Văn Tùng",
    "Hoàng Thị Vui",
]

# (suffix id, availability_status, slot pattern)
# BS 3: status available nhưng slot lẫn — UI cần check chi tiết slot
_DOCTOR_SLOTS = (
    ("01", "available", (True, True, True)),
    ("02", "full", (False, False, False)),
    ("03", "available", (True, False, False)),
)

_name_idx = 0


def _next_doctor_name() -> str:
    global _name_idx
    name = _DOCTOR_NAMES[_name_idx % len(_DOCTOR_NAMES)]
    _name_idx += 1
    return name


def main() -> None:
    global _name_idx
    _name_idx = 0
    DB.mkdir(exist_ok=True)

    spec_path = DB / "specialties.csv"
    with spec_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow(["specialty_id", "name", "description", "active"])
        for sid, name, desc in SPECIALTIES:
            w.writerow([sid, name, desc, "true"])

    doctors_rows: list[list[str]] = []
    slots_rows: list[list[str]] = []

    for spec_i, (sid, _spec_name, _) in enumerate(SPECIALTIES):
        for i, (num, avail_status, slot_flags) in enumerate(_DOCTOR_SLOTS):
            doc_id = f"bs_{sid}_{num}"
            doc_name = f"BS. {_next_doctor_name()}"
            title = TITLES[i % len(TITLES)]
            facility_id = FACILITIES[i % 2]
            doctors_rows.append(
                [doc_id, doc_name, title, sid, facility_id, "true", avail_status]
            )
            for j, (date, time) in enumerate(zip(SLOT_DATES, SLOT_TIMES)):
                available = "true" if slot_flags[j] else "false"
                slots_rows.append(
                    [
                        f"slot_{sid}_{num}_{j+1:02d}",
                        facility_id,
                        sid,
                        doc_id,
                        date,
                        time,
                        available,
                    ]
                )

    doc_path = DB / "doctors.csv"
    with doc_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "doctor_id",
                "name",
                "title",
                "specialty_id",
                "facility_id",
                "active",
                "availability_status",
            ]
        )
        w.writerows(doctors_rows)

    slot_path = DB / "slots.csv"
    with slot_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "slot_id",
                "facility_id",
                "specialty_id",
                "doctor_id",
                "date",
                "time",
                "available",
            ]
        )
        w.writerows(slots_rows)

    print(f"specialties: {len(SPECIALTIES)}")
    print(f"doctors: {len(doctors_rows)}")
    print(f"slots: {len(slots_rows)}")


if __name__ == "__main__":
    main()
