# Sigara Fiyat API

Türkiye güncel sigara fiyatlarını otomatik çeken ve JSON olarak sunan sistem.

## Nasıl Çalışır

1. GitHub Actions günde 4 kez `scraper.py`'ı çalıştırır
2. Scraper 3 farklı haber sitesinden fiyat çeker (veryansintv, ensonhaber, ntv)
3. Fiyatlar birleştirilip `prices.json`'a yazılır
4. Mobil uygulama `prices.json`'ı raw.githubusercontent.com üzerinden çeker

## API Endpoint

```
https://raw.githubusercontent.com/tasarimcidam/sigara-fiyat/main/prices.json
```

## Manuel Çalıştırma

```bash
pip install -r requirements.txt
python scraper.py
```

## Kurulum (GitHub Repo)

1. Bu klasörün içeriğini `tasarimcidam/sigara-fiyat` reposuna kopyala
2. GitHub Actions otomatik çalışmaya başlayacak
3. İlk çalıştırma için Actions sekmesinden "Run workflow" tıkla
