# CheckList

EDMS'ten inen RIA listesini checklist listesiyle karşılaştırır. Handover'ın kardeşi:
aynı lisans kapısı, aynı otomatik güncelleme, aynı RIA filtresi; arayüz farklı (açık tema).

## Akış
1. **Files** — Excel'leri sürükle-bırak (klasör de olur). Tür başlıktan anlaşılır:
   - `Task Number` + `Related RIA` → checklist
   - `Document Number` + `Document Title` → RIA listesi
   - `Related RIA` var ama `Task Number` yok → lab listesi, kullanılmaz
2. **Filter** — Document Number parçalarını tikle (Handover'daki gibi; seçim saklanır).
   Settings'teki eleme kuralları da uygulanır (varsayılan: `Document Title starts with Reinforcement`).
3. **Result** — `Desktop\CheckList\<tarih>\CheckList Result.xlsx`:
   - `Has Checklist`: RIA'nın tüm sütunları + checklist'in tüm sütunları (her checklist ayrı satır)
   - `Missing Checklist`: checklist'i olmayan RIA'lar, tüm sütunları

Eşleşme: `Document Number` = `Related RIA` (boşluk ve büyük/küçük harf önemsiz).
Checklist durumu (OPEN/CLOSED/REJECTED) şimdilik bakılmıyor.

## Çalıştırma / test
```
pip install -r requirements.txt
python launcher.py        # ya da: python src/main.py
python -m pytest
```

## Yayın (ilk kez yapılacaklar)
- GitHub'da `yavuzzeynulat-cell/CheckList` deposu (updater oradan `releases/latest` okur).
- Lisans panelinde `checklist` programı → üretilen SECRET `license_secret.txt`'ye (gitignore'da).
- Sonra: `Guncelleme-Gonder.bat` ya da `python build/publish.py 0.1.0 "ilk surum" --full`.

Kurallar Handover ile aynı: yeni adım = `src/steps/<ad>.py` + `all_steps()`'e bir satır;
`LAUNCHER_VERSION` artarsa `MIN_LAUNCHER` da artar.
