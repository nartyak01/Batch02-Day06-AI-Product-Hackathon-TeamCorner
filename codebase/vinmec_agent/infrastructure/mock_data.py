from __future__ import annotations

from typing import Any


FACILITIES: list[dict[str, Any]] = [
    {
        "facility_id": "times_city",
        "name": "Vinmec Times City",
        "city": "Hà Nội",
        "district": "Hai Bà Trưng",
        "address": "458 Minh Khai, Hai Bà Trưng, Hà Nội",
        "active": True,
    },
    {
        "facility_id": "smart_city",
        "name": "Vinmec Smart City",
        "city": "Hà Nội",
        "district": "Nam Từ Liêm",
        "address": "Tây Mỗ, Nam Từ Liêm, Hà Nội",
        "active": True,
    },
    {
        "facility_id": "vinmec_halong",
        "name": "Vinmec Hạ Long",
        "city": "Quảng Ninh",
        "district": "Hạ Long",
        "address": "Hạ Long, Quảng Ninh",
        "active": True,
    },
]


SPECIALTIES: list[dict[str, Any]] = [
    {
        "specialty_id": "gastro",
        "name": "Tiêu hóa",
        "description": "Đau bụng, buồn nôn, tiêu chảy, rối loạn tiêu hóa",
        "keywords": ["đau bụng", "buồn nôn", "nôn", "tiêu chảy", "táo bón", "đầy bụng", "dạ dày", "tiêu hóa"],
        "active": True,
    },
    {
        "specialty_id": "general_internal",
        "name": "Nội tổng quát",
        "description": "Triệu chứng chung, sốt, mệt mỏi, đau đầu nhẹ",
        "keywords": ["sốt", "mệt", "mệt mỏi", "đau đầu", "chóng mặt", "khám tổng quát", "nội tổng quát"],
        "active": True,
    },
    {
        "specialty_id": "cardiology",
        "name": "Tim mạch",
        "description": "Đau ngực, hồi hộp, tăng huyết áp, khó thở liên quan tim mạch",
        "keywords": ["đau ngực", "hồi hộp", "tim đập", "huyết áp", "tim mạch"],
        "active": True,
    },
    {
        "specialty_id": "respiratory",
        "name": "Hô hấp",
        "description": "Ho, khó thở, đau họng, viêm đường hô hấp",
        "keywords": ["ho", "khó thở", "đau họng", "khò khè", "viêm phổi", "hô hấp"],
        "active": True,
    },
    {
        "specialty_id": "neurology",
        "name": "Thần kinh",
        "description": "Đau đầu, tê bì, yếu liệt, chóng mặt, ngất",
        "keywords": ["đau đầu", "tê", "yếu liệt", "co giật", "ngất", "thần kinh"],
        "active": True,
    },
    {
        "specialty_id": "emergency",
        "name": "Cấp cứu",
        "description": "Dấu hiệu nặng cần liên hệ y tế ngay",
        "keywords": ["cấp cứu", "dữ dội", "ngất", "khó thở nặng", "chảy máu nhiều"],
        "active": True,
    },
]


DOCTORS: list[dict[str, Any]] = [
    {"doctor_id": "bs_gastro_01", "name": "BS Nguyễn Minh An", "title": "Bác sĩ Tiêu hóa", "specialty_id": "gastro", "facility_id": "times_city", "active": True},
    {"doctor_id": "bs_gastro_02", "name": "BS Lê Thu Hà", "title": "Bác sĩ Tiêu hóa", "specialty_id": "gastro", "facility_id": "smart_city", "active": True},
    {"doctor_id": "bs_internal_01", "name": "BS Trần Quốc Việt", "title": "Bác sĩ Nội tổng quát", "specialty_id": "general_internal", "facility_id": "times_city", "active": True},
    {"doctor_id": "bs_cardio_01", "name": "BS Phạm Hoàng Long", "title": "Bác sĩ Tim mạch", "specialty_id": "cardiology", "facility_id": "times_city", "active": True},
    {"doctor_id": "bs_resp_01", "name": "BS Đỗ Mai Linh", "title": "Bác sĩ Hô hấp", "specialty_id": "respiratory", "facility_id": "smart_city", "active": True},
    {"doctor_id": "bs_neuro_01", "name": "BS Vũ Thanh Sơn", "title": "Bác sĩ Thần kinh", "specialty_id": "neurology", "facility_id": "times_city", "active": True},
]


RED_FLAG_KEYWORDS = [
    "đau ngực dữ dội",
    "khó thở",
    "khó thở nặng",
    "ngất",
    "choáng",
    "yếu liệt",
    "liệt",
    "co giật",
    "chảy máu nhiều",
    "nôn ra máu",
    "đi ngoài ra máu",
    "đau đầu dữ dội",
    "mất ý thức",
    "tim đập rất nhanh",
]
