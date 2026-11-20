"""Generate 10 synthetic document images (utility bills, receipts, khata ledgers) for OCR eval."""

import json
from pathlib import Path

from PIL import Image, ImageDraw

IMG_DIR = Path(__file__).resolve().parent / "images"
IMG_DIR.mkdir(parents=True, exist_ok=True)

LABELS_PATH = Path(__file__).resolve().parent / "labels.json"

DOCUMENTS = [
    {
        "filename": "bill_01_desco.jpg",
        "type": "utility_bill",
        "title": "DESCO ELECTRICITY BILL / বিদ্যুৎ বিল",
        "lines": [
            "Dhaka Electric Supply Company Limited",
            "Customer Name: Shathi Akter",
            "Account No: 12984012 / Meter: MTR-982103",
            "Bill Month: October 2026",
            "Payable Amount BDT: 1450.00",
            "Due Date: 2026-11-25",
            "Status: UNPAID",
        ],
        "expected": {
            "document_type": "utility_bill",
            "provider": "DESCO",
            "amount_bdt": 1450.0,
            "due_date": "2026-11-25",
        },
    },
    {
        "filename": "bill_02_dpdc.jpg",
        "type": "utility_bill",
        "title": "DPDC BILL / বিদ্যুৎ বিল",
        "lines": [
            "Dhaka Power Distribution Company",
            "Customer: Md. Rafiqul Islam",
            "Bill Month: October 2026",
            "Payable Amount BDT: 2200.00",
            "Due Date: 2026-11-20",
        ],
        "expected": {
            "document_type": "utility_bill",
            "provider": "DPDC",
            "amount_bdt": 2200.0,
            "due_date": "2026-11-20",
        },
    },
    {
        "filename": "bill_03_wasa.jpg",
        "type": "utility_bill",
        "title": "DHAKA WASA WATER BILL / পানির বিল",
        "lines": [
            "Dhaka Water Supply and Sewerage Authority",
            "Billing Zone: 05 Mirpur",
            "Payable Amount BDT: 750.00",
            "Due Date: 2026-11-28",
        ],
        "expected": {
            "document_type": "utility_bill",
            "provider": "WASA",
            "amount_bdt": 750.0,
            "due_date": "2026-11-28",
        },
    },
    {
        "filename": "bill_04_titas.jpg",
        "type": "utility_bill",
        "title": "TITAS GAS TRANSMISSION BILL / গ্যাস বিল",
        "lines": [
            "Titas Gas Transmission and Distribution Co",
            "Burner: 2 Non-Metered",
            "Payable Amount BDT: 1080.00",
            "Due Date: 2026-11-15",
        ],
        "expected": {
            "document_type": "utility_bill",
            "provider": "Titas",
            "amount_bdt": 1080.0,
            "due_date": "2026-11-15",
        },
    },
    {
        "filename": "bill_05_nesco.jpg",
        "type": "utility_bill",
        "title": "NESCO BILL / নেসকো বিদ্যুৎ বিল",
        "lines": [
            "Northern Electricity Supply Company PLC",
            "Division: Rajshahi",
            "Total Amount BDT: 950.00",
            "Due Date: 2026-11-22",
        ],
        "expected": {
            "document_type": "utility_bill",
            "provider": "NESCO",
            "amount_bdt": 950.0,
            "due_date": "2026-11-22",
        },
    },
    {
        "filename": "receipt_01_shwapno.jpg",
        "type": "receipt",
        "title": "SHWAPNO SUPERSTORE / স্বপ্ন",
        "lines": [
            "Branch: Dhanmondi 27",
            "Date: 2026-10-20 18:30",
            "Items: Rice, Dal, Mustard Oil",
            "Total Payable BDT: 1850.00",
            "TrxID: POS778899",
        ],
        "expected": {
            "document_type": "receipt",
            "merchant_or_platform": "Shwapno Superstore",
            "amount_bdt": 1850.0,
            "date": "2026-10-20",
        },
    },
    {
        "filename": "receipt_02_aarong.jpg",
        "type": "receipt",
        "title": "AARONG / আড়ং",
        "lines": [
            "Branch: Uttara Outlet",
            "Date: 2026-10-22 15:45",
            "Total BDT: 3200.00",
            "Payment Method: bKash MFS",
        ],
        "expected": {
            "document_type": "receipt",
            "merchant_or_platform": "Aarong",
            "amount_bdt": 3200.0,
            "date": "2026-10-22",
        },
    },
    {
        "filename": "receipt_03_pharmacy.jpg",
        "type": "receipt",
        "title": "LAZZ PHARMA / লাজ ফার্মা",
        "lines": [
            "Medical Prescription Cash Memo",
            "Date: 2026-10-25 11:20",
            "Total Amount BDT: 640.00",
        ],
        "expected": {
            "document_type": "receipt",
            "merchant_or_platform": "Lazz Pharma",
            "amount_bdt": 640.0,
            "date": "2026-10-25",
        },
    },
    {
        "filename": "khata_01_grocery.jpg",
        "type": "khata_page",
        "title": "BHAI BHAI GENERAL STORE / বাকি খাতা",
        "lines": [
            "হালখাতা পাতা নং: ১২",
            "রহিম উদ্দিন - বাকি ১২০০ টাকা",
            "করিম মিয়া - জমা ২২০০ টাকা",
            "মোট হিসাব BDT: 3400.00",
        ],
        "expected": {
            "document_type": "khata_page",
            "shop_name": "Bhai Bhai General Store",
            "page_total_bdt": 3400.0,
        },
    },
    {
        "filename": "khata_02_tea_stall.jpg",
        "type": "khata_page",
        "title": "MA BABAR DOA STORE / বাকি খাতা",
        "lines": [
            "দোকান হিসাব পাতা: ০৫",
            "চা ও বিস্কুট বাকি হিসাব",
            "মোট বাকি BDT: 1850.00",
        ],
        "expected": {
            "document_type": "khata_page",
            "shop_name": "Ma Babar Doa Store",
            "page_total_bdt": 1850.0,
        },
    },
]


def create_sample_images():
    labels_data = []
    for doc in DOCUMENTS:
        img = Image.new("RGB", (800, 1000), color=(248, 249, 250))
        draw = ImageDraw.Draw(img)

        # Border
        draw.rectangle([20, 20, 780, 980], outline=(180, 180, 180), width=3)

        # Header box
        draw.rectangle([40, 40, 760, 120], fill=(230, 235, 245), outline=(100, 120, 160), width=2)
        draw.text((60, 65), doc["title"], fill=(20, 40, 80))

        # Body text lines
        y = 160
        for line in doc["lines"]:
            draw.text((60, y), line, fill=(40, 40, 40))
            y += 45

        # Footer stamp / barcode
        draw.rectangle([60, 850, 740, 930], fill=(240, 240, 240), outline=(200, 200, 200))
        draw.text(
            (80, 880), f"Digital Hash / QR: TL-{doc['filename'][:8].upper()}", fill=(120, 120, 120)
        )

        img_path = IMG_DIR / doc["filename"]
        img.save(img_path, "JPEG", quality=90)

        labels_data.append(
            {
                "filename": doc["filename"],
                "type": doc["type"],
                "expected": doc["expected"],
            }
        )

    with open(LABELS_PATH, "w", encoding="utf-8") as f:
        json.dump(labels_data, f, indent=2)

    print(f"Generated 10 synthetic OCR sample images in {IMG_DIR} and labels in {LABELS_PATH}")


if __name__ == "__main__":
    create_sample_images()
