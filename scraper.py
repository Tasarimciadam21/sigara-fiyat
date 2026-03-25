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


# Yerel yedek fiyatlar (API çalışmazsa kullanılır)
FALLBACK_PRICES: dict[str, float] = {
    "Marlboro Edge": 118, "Marlboro Red": 120, "Marlboro Red Long": 120,
    "Marlboro Touch": 120, "Marlboro Touch Blue": 120,
    "Marlboro Touch Grey": 120, "Marlboro Touch White": 120,
    "Marlboro Roll 50": 150, "Marlboro Classic": 120,
    "Marlboro Filter Plus": 120, "Marlboro Gold Original": 120,
    "Marlboro Micro Touch": 120, "Marlboro XL Touch": 120,
    "Parliament Night Blue": 120, "Parliament Aqua Blue": 125,
    "Parliament Aqua Blue Slims": 125, "Parliament Midnight Blue": 120,
    "Parliament Reserve": 125,
    "Chesterfield Black": 115, "Chesterfield Blue": 115,
    "L&M Red": 115, "L&M Blue": 115, "L&M Red Label": 115,
    "Lark Blue": 115, "Lark Gold": 115, "Lark Silver": 115,
    "Muratti Rosso": 117, "Muratti Blue": 117, "Muratti Silver": 117,
    "Winston Classic": 120, "Winston Blue": 120, "Winston Deep Blue": 115,
    "Winston Dark Blue": 115, "Winston Slender": 115, "Winston Slims": 125,
    "Winston X sence Black": 125, "Winston X sence Gray": 125,
    "Camel Yellow": 115, "Camel Brown": 115, "Camel Black": 112,
    "Camel White": 112, "Camel Deep Blue": 112, "Camel Slender": 110,
    "Camel Filters": 115, "LD": 110, "LD Slims": 110,
    "Kent Blue": 115, "Kent Grey": 115, "Kent White": 115,
    "Kent Dark Blue": 105, "Kent Dark Blue Long": 105,
    "Kent D Range Grey": 105, "Kent D Range Blue": 105,
    "Kent D Range Blue Long": 107, "Kent D Range Grey Long": 107,
    "Kent Slims Black": 115, "Kent Slims Grey": 115,
    "Lucky Strike Red": 105, "Lucky Strike Blue": 105,
    "Rothmans Blue": 100, "Rothmans Red": 100,
    "Pall Mall Red": 105, "Pall Mall Blue": 105,
    "Dunhill Double Blue": 99, "Viceroy Red": 105, "Viceroy Blue": 105,
    "Davidoff Classic": 110, "Davidoff Gold": 110, "Davidoff Slims": 110,
    "Davidoff C Line Blue": 105, "Davidoff Burgundy": 110,
    "Davidoff Ivory": 110, "Davidoff White": 110,
    "West Navy": 98, "West Grey": 98, "West White": 98,
    "Tekel 2000": 100, "Tekel 2001": 105,
    "Samsun Kısa": 105, "Samsun Uzun": 105, "Samsun 216": 105,
    "Maltepe Kısa": 105, "Maltepe Uzun": 105,
    "Monte Carlo": 110, "Monte Carlo Slender": 110, "Bianca": 111,
    "Polo Blue": 100, "Polo Grey": 100, "Imperial Classic Red": 64,
    "Violet Slims": 115,
    "Winner Slims Blue": 102, "Winner Slims Dore": 102, "Winner Slims Red": 102,
    "HD Slims Blue": 100, "HD Red": 100, "HD Blue": 100, "HD Sky": 100,
    "President": 100, "Vigor Cerulean": 102, "Point Blue Slims": 100,
    "Medley": 97, "MMC": 97, "Hazar": 97, "Toros 2005": 97,
    "Raison T-Black": 80, "Esse Brown": 92, "Esse Blue": 100,
    "Esse Black": 100, "Esse White": 100, "Esse Reserv": 83, "Esse Xmell": 82,
}


def main():
    print(f"Sigara fiyat scraper - {datetime.now()}\n")

    # Web'den çek
    scraped = scrape_veryansintv()

    # Birleştir: web + fallback (her marka için en yüksek fiyatı al)
    # Çünkü zam geldiğinde web siteleri geç güncellenebilir
    merged: dict[str, float] = {}

    # Önce web fiyatlarını koy
    if scraped:
        merged.update(scraped)
        print(f"\n  ✓ Web'den {len(scraped)} fiyat alındı")
    else:
        print("\n  ⚠ Web'den fiyat alınamadı")

    # Fallback'ten eksik olanları ekle, varsa yüksek olanı al
    for brand, price in FALLBACK_PRICES.items():
        if brand not in merged:
            merged[brand] = price
        elif price > merged[brand]:
            # Fallback daha yüksekse zam gelmiş, onu kullan
            merged[brand] = price

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
