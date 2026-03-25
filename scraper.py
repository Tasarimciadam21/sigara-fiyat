#!/usr/bin/env python3
"""
Türkiye sigara fiyatları scraper.
Birden fazla haber sitesinden güncel fiyatları çeker.
Zam haberlerini otomatik tespit eder.
GitHub Actions ile günde 4 kez otomatik çalışır.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests

TIMEOUT = 15
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*",
    "Accept-Language": "tr-TR,tr;q=0.9",
}

OUT_PATH = Path(__file__).parent / "prices.json"


# ═══════════════════════════════════════════
# KAYNAK 1: veryansintv.com (sabit sayfa)
# ═══════════════════════════════════════════

def scrape_veryansintv() -> dict[str, float]:
    url = "https://www.veryansintv.com/guncel-sigara-fiyatlari"
    prices: dict[str, float] = {}
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        r.encoding = "utf-8"
        text = r.text.replace("\xa0", " ")

        pattern = re.compile(
            r"<td[^>]*>([^<]+)</td>\s*<td[^>]*>\s*₺?\s*([\d.,\s]+)</td>",
            re.IGNORECASE,
        )
        for m in pattern.finditer(text):
            brand = m.group(1).strip()
            ps = m.group(2).strip().replace(" ", "").replace(".", "").replace(",", ".")
            try:
                price = float(ps)
            except ValueError:
                continue
            if brand and 40 < price < 500 and not brand.startswith("<"):
                prices.update(expand_brand(brand, price))
        print(f"  [veryansintv] {len(prices)} marka")
    except Exception as e:
        print(f"  [veryansintv] HATA: {e}")
    return prices


# ═══════════════════════════════════════════
# KAYNAK 2: Google News'den zam haberi tara
# ═══════════════════════════════════════════

def scrape_zam_haberleri() -> dict[str, float]:
    """Google News'den 'sigara zam' haberlerini arar,
    bulunan haber sayfalarından fiyat çeker."""
    prices: dict[str, float] = {}
    search_queries = [
        "sigara+zam+fiyat+2026",
        "sigara+fiyatları+güncel+2026",
        "sigara+zamlandı+yeni+fiyat",
    ]

    found_urls: set[str] = set()

    for query in search_queries:
        try:
            # Google News RSS
            rss_url = f"https://news.google.com/rss/search?q={query}&hl=tr&gl=TR&ceid=TR:tr"
            r = requests.get(rss_url, headers=HEADERS, timeout=TIMEOUT)
            if r.status_code != 200:
                continue

            # RSS'den haber URL'lerini çek
            urls = re.findall(r"<link>(https?://[^<]+)</link>", r.text)
            for url in urls[:5]:  # ilk 5 haber yeterli
                if url not in found_urls and "news.google" not in url:
                    found_urls.add(url)
        except Exception:
            continue

    # Bulunan haber sayfalarından fiyat çek
    for url in list(found_urls)[:8]:
        try:
            page_prices = scrape_generic_page(url)
            if page_prices:
                prices.update(page_prices)
        except Exception:
            continue

    if prices:
        print(f"  [zam haberleri] {len(prices)} marka ({len(found_urls)} haber tarandı)")
    else:
        print(f"  [zam haberleri] fiyat bulunamadı ({len(found_urls)} haber tarandı)")

    return prices


def scrape_generic_page(url: str) -> dict[str, float]:
    """Herhangi bir haber sayfasından sigara fiyatı çeker."""
    prices: dict[str, float] = {}
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.encoding = "utf-8"
        text = r.text.replace("\xa0", " ")

        # Tablo formatı
        table_pat = re.compile(
            r"<td[^>]*>([^<]+)</td>\s*<td[^>]*>\s*₺?\s*([\d.,\s]+)\s*(?:TL)?</td>",
            re.IGNORECASE,
        )
        for m in table_pat.finditer(text):
            brand = m.group(1).strip()
            ps = m.group(2).strip().replace(" ", "").replace(".", "").replace(",", ".")
            try:
                price = float(ps)
            except ValueError:
                continue
            if brand and 40 < price < 500:
                prices.update(expand_brand(brand, price))

        # Düz metin formatı: "Marka ₺ XXX" veya "Marka XXX TL"
        text_pat = re.compile(
            r"([A-Za-zÇçĞğİıÖöŞşÜü&\s\d.\-()/']+?)\s*₺\s*([\d.,\s]+)",
        )
        for m in text_pat.finditer(text):
            brand = m.group(1).strip()
            ps = m.group(2).strip().replace(" ", "").replace(".", "").replace(",", ".")
            try:
                price = float(ps)
            except ValueError:
                continue
            if brand and 40 < price < 500 and len(brand) > 2:
                prices.update(expand_brand(brand, price))

    except Exception:
        pass
    return prices


# ═══════════════════════════════════════════
# Marka ismi genişletme
# ═══════════════════════════════════════════

def expand_brand(raw: str, price: float) -> dict[str, float]:
    result: dict[str, float] = {}

    # "Marka (X/Y/Z)"
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

    # "Marka X/Y/Z"
    sm = re.match(r"^(.+?)\s+(\w+/[\w/]+)$", raw)
    if sm:
        base = sm.group(1).strip()
        for v in sm.group(2).split("/"):
            result[f"{base} {v.strip()}"] = price
        return result

    # "X&Y"
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


# ═══════════════════════════════════════════
# Akıllı birleştirme
# ═══════════════════════════════════════════

def smart_merge(
    previous: dict[str, float],
    *sources: dict[str, float],
) -> dict[str, float]:
    """
    Birden fazla kaynağı akıllıca birleştirir.

    Kural: Her marka için EN GÜNCEL fiyatı al.
    - Birden fazla kaynak aynı markayı farklı fiyatla veriyorsa
      → en yüksek fiyatı al (zam gelmiş demektir)
    - Önceki prices.json'daki fiyattan düşük gelen fiyat
      → öncekini koru (site eski kalmış olabilir)
    - Önceki fiyattan yüksek gelen fiyat
      → yeniyi al (zam gelmiş)
    """
    merged: dict[str, float] = {}

    # Tüm kaynaklardan topla
    for src in sources:
        for brand, price in src.items():
            if brand not in merged or price > merged[brand]:
                merged[brand] = price

    # Önceki fiyatlarla karşılaştır
    for brand, prev_price in previous.items():
        if brand not in merged:
            # Kaynaklarda yok → öncekini koru
            merged[brand] = prev_price
        elif merged[brand] < prev_price:
            # Kaynak daha düşük fiyat veriyor → öncekini koru
            # (site henüz güncellenmemiş olabilir)
            merged[brand] = prev_price

    return merged


# ═══════════════════════════════════════════
# Önceki fiyatları yükle
# ═══════════════════════════════════════════

def load_previous() -> dict[str, float]:
    """Mevcut prices.json'dan önceki fiyatları yükle."""
    prices: dict[str, float] = {}
    try:
        if OUT_PATH.exists():
            with open(OUT_PATH, encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                if k != "_meta" and isinstance(v, (int, float)):
                    prices[k] = float(v)
    except Exception:
        pass
    return prices


# ═══════════════════════════════════════════
# Ana fonksiyon
# ═══════════════════════════════════════════

def main():
    print(f"Sigara fiyat scraper - {datetime.now()}")
    print(f"{'=' * 50}\n")

    # Önceki fiyatları yükle
    previous = load_previous()
    if previous:
        print(f"  Önceki prices.json: {len(previous)} marka\n")

    # Kaynak 1: veryansintv
    src_veryans = scrape_veryansintv()

    # Kaynak 2: Zam haberleri (Google News)
    src_haberler = scrape_zam_haberleri()

    # Akıllı birleştirme
    print(f"\n{'=' * 50}")
    merged = smart_merge(previous, src_veryans, src_haberler)

    # Geçersizleri temizle
    merged = {k: v for k, v in merged.items() if v > 0 and len(k) > 1}

    # Değişiklikleri raporla
    changes = []
    for brand in sorted(merged):
        old = previous.get(brand)
        new = merged[brand]
        if old and old != new:
            changes.append(f"  {'↑' if new > old else '↓'} {brand}: {old} → {new} TL")

    if changes:
        print(f"\n  Fiyat değişiklikleri ({len(changes)}):")
        for c in changes[:20]:
            print(c)
        if len(changes) > 20:
            print(f"  ... ve {len(changes) - 20} değişiklik daha")
    else:
        print("\n  Fiyat değişikliği yok")

    # JSON oluştur
    output = {
        "_meta": {
            "updated": datetime.now(timezone.utc).isoformat(),
            "sources": {
                "veryansintv": len(src_veryans),
                "zam_haberleri": len(src_haberler),
            },
            "total": len(merged),
            "changes": len(changes),
        }
    }
    output.update(dict(sorted(merged.items())))

    # Kaydet
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✓ {len(merged)} marka → prices.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
