import os
import re
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

from utils import load_draws, save_base_to_file
from strategies import generate_base

MAX_DAYS_BACK = 60  # Hanya 60 hari terakhir
URL_TEMPLATE = "http://live4d.jaguar20.biz/jaguarlive4d/?date={date}"


def get_1st_prize_9pm(date_str: str) -> str | None:
    """
    Scrape 1st prize Jaguar G (9pm) untuk tarikh YYYY-MM-DD.
    Pulangkan string 4-digit jika jumpa, else None.
    """
    url = URL_TEMPLATE.format(date=date_str)
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if resp.status_code != 200:
            print(f"❌ Status bukan 200 untuk {date_str}: {resp.status_code}")
            return None

        html = resp.text
        soup = BeautifulSoup(html, "html.parser")

        # Cari teks 'Jaguar G (9pm)' dan ambil blok ada '首獎'
        for node in soup.find_all(string=re.compile(r"Jaguar\s*G", re.I)):
            ancestor = node.parent
            for _ in range(6):  # naik parent 6 kali maksimum
                if ancestor is None:
                    break
                text = ancestor.get_text(separator=" ", strip=True)
                if "首獎" in text:
                    m = re.search(r"首獎[^0-9A-Za-z]*([A-Z]?\d{4})", text)
                    if not m:
                        m = re.search(r"首獎.*?([A-Z]?\s*\d{4})", text)
                    if m:
                        raw = m.group(1)
                        digits = "".join(ch for ch in raw if ch.isdigit())
                        if len(digits) == 4:
                            print(f"✅ {date_str} → Jaguar G (9pm): {digits}")
                            return digits
                ancestor = ancestor.parent

        # fallback regex
        m = re.search(r"Jaguar G\s*\(9pm\).*?首獎.*?([A-Z]?\d{4})", html, re.S | re.I)
        if m:
            raw = m.group(1)
            digits = "".join(ch for ch in raw if ch.isdigit())
            if len(digits) == 4:
                print(f"✅ {date_str} → Jaguar G (9pm): {digits}")
                return digits

        print(f"❌ Tidak jumpa 1st Prize Jaguar G (9pm) untuk {date_str}")
    except Exception as e:
        print(f"❌ Ralat semasa request untuk {date_str}: {e}")
    return None


def update_draws_60days(file_path: str = "data/draws.txt", update_base: bool = False) -> str:
    """
    Update 'data/draws.txt' dengan draw Jaguar G (9pm) baru
    untuk 60 hari terakhir sahaja. Disimpan dalam urutan lama → baru.
    """
    draws = load_draws(file_path)
    existing = {d["date"] for d in draws}

    # Masa semasa ikut waktu Malaysia
    tz = ZoneInfo("Asia/Kuala_Lumpur")
    now_my = datetime.now(tz)

    # Tentukan tarikh mula dan tarikh akhir (60 hari terakhir)
    start_date = (now_my - timedelta(days=MAX_DAYS_BACK - 1)).date()
    end_date = now_my.date()

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    added = []

    # Simpan semua rekod baru ke list sementara
    new_records = []
    current = start_date
    while current <= end_date:
        ds = current.strftime("%Y-%m-%d")
        current += timedelta(days=1)
        if ds in existing:
            continue
        prize = get_1st_prize_9pm(ds)
        if prize:
            new_records.append({"date": ds, "number": prize})
            added.append(ds)

    # Gabung lama + baru
    all_draws = draws + new_records
    # Sort ikut tarikh ascending (lama di atas, baru di bawah)
    all_draws_sorted = sorted(all_draws, key=lambda x: x["date"])

    # Tulis semula ke file
    with open(file_path, "w", encoding="utf-8") as f:
        for d in all_draws_sorted:
            f.write(f"{d['date']} {d['number']}\n")

    # Update base_last.txt jika ada draw baru
    if added:
        if len(all_draws_sorted) >= 51:
            base_before = generate_base(all_draws_sorted[:-1], method="break", recent_n=50)
            save_base_to_file(base_before, "data/base_last.txt")

    # Update base.txt jika diminta
    if update_base:
        if len(all_draws_sorted) >= 50:
            base_now = generate_base(all_draws_sorted, method="break", recent_n=50)
            save_base_to_file(base_now, "data/base.txt")

    return f"✔️ {len(added)} draw baru Jaguar G (9pm) ditambah." if added else "✔️ Tiada draw baru."


if __name__ == "__main__":
    msg = update_draws_60days()
    print(msg)
