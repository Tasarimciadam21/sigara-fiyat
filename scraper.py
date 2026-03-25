#!/usr/bin/env python3
"""
Türkiye sigara fiyatları scraper.
Haber sitelerinden güncel fiyatları çeker ve prices.json olarak kaydeder.
GitHub Actions ile günde 4 kez otomatik çalışır.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

TIMEOUT = 15
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*",
    "Accept-Language": "tr-TR,tr;q=0.9",
}


def scrape_veryansintv() -> dict[str, float]:
    """veryansintv.com'dan sigara fiyatlarını çeker (HTML tablo formatı)."""
    url = "https://www.veryansintv.com/guncel-sigara-fiyatlari"
    prices: dict[str, float] = {}

    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        r.encoding = "utf-8"
        text = r.text.replace("\xa0", " ")  # non-breaking space temizle

        # HTML tablo: <td>Marka</td><td>₺ XXX,XX</td>
        pattern = re.compile(
            r"<td[^>]*>([^<]+)</td>\s*<td[^>]*>\s*₺?\s*([\d.,\s]+)</td>",
            re.IGNORECASE,
        )

        for m in pattern.finditer(text):
            brand = m.group(1).strip()
            price_str = (
                m.group(2).strip().replace(" ", "").replace(".", "").replace(",", ".")
            )
            try:
                price = float(price_str)
            except ValueError:
                continue
            if brand and 40 < price < 500 and not brand.startswith("<"):
                expanded = expand_brand(brand, price)
                prices.update(expanded)

        print(f"  veryansintv: {len(prices)} marka bulundu")
    except Exception as e:
        print(f"  veryansintv HATA: {e}")

    return prices


def expand_brand(raw: str, price: float) -> dict[str, float]:
    """Gruplanmış marka isimlerini ayrıştırır."""
    result: dict[str, float] = {}

    # "Marka (X/Y/Z)" formatı
    gm = re.match(r"^(.+?)\s*\((.+)\)$", raw)
    if gm:
        base = gm.group(1).strip()
        for v in gm.group(2).split("/"):
            v = v.strip()
            if v.lower() == "tüm ürünler":
                result[base] = price
            else:
                result[f"{base} {v}"] = price
        return result

    # "Marka X/Y/Z" formatı
    sm = re.match(r"^(.+?)\s+(\w+/[\w/]+)$", raw)
    if sm:
        base = sm.group(1).strip()
        for v in sm.group(2).split("/"):
            result[f"{base} {v.strip()}"] = price
        return result

    # "X&Y" formatı
    if "&" in raw:
        am = re.match(r"^(.+?)\s+(\w+)&(\w+)$", raw)
        if am:
            base = am.group(1).strip()
            result[f"{base} {am.group(2).strip()}"] = price
            result[f"{base} {am.group(3).strip()}"] = price
            return result

    # Kısa/Uzun prefix
    for prefix in ("Kısa ", "Uzun "):
        if raw.startswith(prefix):
            name = raw[len(prefix):].strip()
            result[f"{name} {prefix.strip()}"] = price
            return result

    result[raw] = price
    return result


# Yerel yedek fiyatlar — web'deki gerçek fiyatlarla eşit tutulur.
# Sadece web çalışmadığında kullanılır.
FALLBACK_PRICES: dict[str, float] = {
    "Marlboro Edge": 108, "Marlboro Red": 110, "Marlboro Red Long": 110,
    "Marlboro Touch": 110, "Marlboro Touch Blue": 110,
    "Marlboro Touch Grey": 110, "Marlboro Touch White": 110,
    "Marlboro Touch 4": 110, "Marlboro Touch 6": 110,
    "Marlboro Touch XL": 110, "Marlboro Roll 50": 140,
    "Marlboro Classic": 110, "Marlboro Filter Plus": 110,
    "Marlboro Gold Original": 110, "Marlboro Micro Touch": 110,
    "Marlboro Micro Fine Touch": 110, "Marlboro Micro Emerald Touch": 110,
    "Marlboro XL Touch": 110, "Marlboro XL Fine Touch": 110,
    "Parliament Night Blue": 110, "Parliament Aqua Blue": 115,
    "Parliament Aqua Blue Slims": 115, "Parliament Midnight Blue": 110,
    "Parliament Reserve": 115,
    "Chesterfield Black": 105, "Chesterfield Blue": 105,
    "L&M Red": 105, "L&M Blue": 105, "L&M Red Label": 105,
    "Lark Blue": 105, "Lark Gold": 105, "Lark Silver": 105,
    "Muratti Rosso": 107, "Muratti Blue": 107, "Muratti Silver": 107,
    "Winston Classic": 110, "Winston Blue": 110, "Winston Blue 100": 110,
    "Winston Classic 100": 110, "Winston Deep Blue": 105,
    "Winston Dark Blue": 105, "Winston Slender": 105, "Winston Slims": 115,
    "Winston X sence Black": 115, "Winston X sence Gray": 115,
    "Winston Nova Blue 100": 110, "Winston Nova Gold": 110,
    "Camel Yellow": 105, "Camel Brown": 105, "Camel Black": 102,
    "Camel White": 102, "Camel Deep Blue": 102, "Camel Slender": 100,
    "Camel Compact Black": 102, "Camel Filters": 105,
    "LD": 100, "LD Slims": 100,
    "Kent Blue": 105, "Kent Grey": 105, "Kent White": 105,
    "Kent Dark Blue": 95, "Kent Dark Blue Long": 95,
    "Kent D Range Grey": 95, "Kent D Range Blue": 95,
    "Kent D Range Blue Long": 97, "Kent D Range Grey Long": 97,
    "Kent Slims Black": 105, "Kent Slims Grey": 105,
    "Lucky Strike Red": 95, "Lucky Strike Blue": 95,
    "Rothmans Blue": 90, "Rothmans Red": 90,
    "Pall Mall Red": 95, "Pall Mall Blue": 95,
    "Dunhill Double Blue": 89, "Viceroy Red": 95, "Viceroy Blue": 95,
    "Davidoff Classic": 100, "Davidoff Gold": 100, "Davidoff Slims": 100,
    "Davidoff C Line Blue": 95, "Davidoff Burgundy": 100,
    "Davidoff Ivory": 100, "Davidoff White": 100,
    "West Navy": 88, "West Grey": 88, "West White": 88,
    "Tekel 2000": 90, "Tekel 2001": 95,
    "Samsun Kısa": 95, "Samsun Uzun": 95, "Samsun 216": 95,
    "Maltepe Kısa": 95, "Maltepe Uzun": 95,
    "Monte Carlo": 100, "Monte Carlo Slender": 100, "Bianca": 101,
    "Polo Blue": 90, "Polo Grey": 90, "Imperial Classic Red": 54,
    "Violet Slims": 105,
    "Winner Slims Blue": 92, "Winner Slims Dore": 92, "Winner Slims Red": 92,
    "HD Slims Blue": 90, "HD Red": 90, "HD Blue": 90, "HD Sky": 90,
    "President": 90, "Vigor Cerulean": 92, "Point Blue Slims": 90,
    "Medley": 87, "MMC": 87, "Hazar": 87, "Toros 2005": 87,
    "Raison T-Black": 70, "Esse Brown": 82, "Esse Blue": 90,
    "Esse Black": 90, "Esse White": 90, "Esse Reserv": 73, "Esse Xmell": 72,
}


def main():
    print(f"Sigara fiyat scraper - {datetime.now()}\n")

    # Web'den çek
    scraped = scrape_veryansintv()

    # Birleştir: fallback temel, web üzerine yazar (web her zaman öncelikli)
    merged: dict[str, float] = {}

    # Önce fallback'i koy (temel)
    merged.update(FALLBACK_PRICES)

    # Web fiyatlarını üzerine yaz (web her zaman doğrudur)
    if scraped:
        merged.update(scraped)
        print(f"\n  ✓ Web'den {len(scraped)} fiyat alındı")
    else:
        print("\n  ⚠ Web'den fiyat alınamadı, yedek fiyatlar kullanılıyor")

    # Geçersizleri temizle
    merged = {k: v for k, v in merged.items() if v > 0 and len(k) > 1}

    # JSON oluştur
    output = {
        "_meta": {
            "updated": datetime.now(timezone.utc).isoformat(),
            "source": "veryansintv" if scraped else "fallback",
            "scraped_count": len(scraped),
            "total": len(merged),
        }
    }
    output.update(dict(sorted(merged.items())))

    # Kaydet
    out_path = Path(__file__).parent / "prices.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✓ {len(merged)} marka → prices.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
