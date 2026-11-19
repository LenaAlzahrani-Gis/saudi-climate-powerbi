"""
تنزيل بيانات المناخ الشهرية للمناطق الإدارية الـ13 في السعودية من NASA POWER
وتجهيزها لـ Power BI.

التشغيل:
    pip install requests pandas
    python saudi_climate_download.py

المخرجات (في نفس المجلد):
    climate_monthly.csv  -> جدول الحقائق (منطقة × شهر)
    regions.csv          -> جدول المناطق (للربط والخريطة)

ملاحظة: كل منطقة ممثلة بنقطة عند عاصمتها الإدارية (دقة NASA POWER تقريباً 0.5°).
"""

import time
import calendar
import requests
import pandas as pd

START_YEAR = 1981
END_YEAR = 2025

# المتغيرات المطلوبة
PARAMS = {
    "T2M": "temp_avg_c",          # متوسط الحرارة
    "T2M_MAX": "temp_max_c",      # متوسط الحرارة العظمى
    "T2M_MIN": "temp_min_c",      # متوسط الحرارة الصغرى
    "PRECTOTCORR": "precip_mm_day",  # الأمطار (مم/يوم كمتوسط للشهر)
    "RH2M": "humidity_pct",       # الرطوبة النسبية
    "WS2M": "wind_ms",            # سرعة الرياح
}

# المناطق الإدارية الـ13 (العاصمة الإدارية كنقطة تمثيل)
REGIONS = [
    # id, الاسم بالعربي, الاسم بالإنجليزي, العاصمة, lat, lon
    (1,  "الرياض",            "Riyadh",            "الرياض",   24.7136, 46.6753),
    (2,  "مكة المكرمة",        "Makkah",            "مكة المكرمة", 21.3891, 39.8579),
    (3,  "المدينة المنورة",     "Madinah",           "المدينة المنورة", 24.5247, 39.5692),
    (4,  "القصيم",            "Qassim",            "بريدة",    26.3260, 43.9750),
    (5,  "المنطقة الشرقية",    "Eastern Province",  "الدمام",   26.4207, 50.0888),
    (6,  "عسير",              "Asir",              "أبها",     18.2164, 42.5053),
    (7,  "تبوك",              "Tabuk",             "تبوك",     28.3835, 36.5662),
    (8,  "حائل",              "Hail",              "حائل",     27.5114, 41.7208),
    (9,  "الحدود الشمالية",    "Northern Borders",  "عرعر",     30.9753, 41.0381),
    (10, "جازان",             "Jazan",             "جازان",    16.8892, 42.5511),
    (11, "نجران",             "Najran",            "نجران",    17.5656, 44.2289),
    (12, "الباحة",            "Al Bahah",          "الباحة",   20.0129, 41.4677),
    (13, "الجوف",             "Al Jouf",           "سكاكا",    29.9697, 40.2064),
]

API_URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"


def fetch_region(lat, lon, retries=3):
    """يجلب البيانات الشهرية لنقطة واحدة."""
    query = {
        "parameters": ",".join(PARAMS),
        "community": "AG",
        "latitude": lat,
        "longitude": lon,
        "start": START_YEAR,
        "end": END_YEAR,
        "format": "JSON",
    }
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(API_URL, params=query, timeout=120)
            r.raise_for_status()
            return r.json()["properties"]["parameter"]
        except Exception as e:
            print(f"   محاولة {attempt} فشلت: {e}")
            time.sleep(5 * attempt)
    raise RuntimeError("تعذر جلب البيانات بعد عدة محاولات")


def to_rows(region_id, data):
    """يحوّل رد الـ API إلى صفوف (منطقة، سنة، شهر، القيم)."""
    rows = {}
    for api_name, col in PARAMS.items():
        for key, value in data[api_name].items():
            year, month = int(key[:4]), int(key[4:])
            if month == 13:  # الشهر 13 = المتوسط السنوي، نتجاهله
                continue
            row = rows.setdefault((year, month), {
                "region_id": region_id,
                "date": pd.Timestamp(year=year, month=month, day=1),
                "year": year,
                "month": month,
            })
            row[col] = None if value == -999 else value
    return list(rows.values())


def main():
    all_rows = []
    for rid, name_ar, name_en, capital, lat, lon in REGIONS:
        print(f"تنزيل: {name_ar} ({capital}) ...")
        data = fetch_region(lat, lon)
        all_rows.extend(to_rows(rid, data))
        time.sleep(1)  # تخفيف الضغط على الخادم

    df = pd.DataFrame(all_rows).sort_values(["region_id", "date"])

    # مجموع الأمطار الشهري (مم) = المتوسط اليومي × عدد أيام الشهر
    days = df.apply(lambda r: calendar.monthrange(r.year, r.month)[1], axis=1)
    df["precip_mm_month"] = (df["precip_mm_day"] * days).round(2)

    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    df.to_csv("climate_monthly.csv", index=False, encoding="utf-8-sig")

    regions = pd.DataFrame(REGIONS, columns=[
        "region_id", "region_ar", "region_en", "capital_ar", "lat", "lon"])
    regions.to_csv("regions.csv", index=False, encoding="utf-8-sig")

    print(f"\nتم ✅  {len(df):,} صف في climate_monthly.csv")
    print("و regions.csv للمناطق")


if __name__ == "__main__":
    main()
