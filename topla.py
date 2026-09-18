#!/usr/bin/env python3
"""
GitHub Actions icinde calisir. football-data.co.uk'tan lig dosyalarini indirip
ham/ klasorune yazar ve ham/index.json uretir.

Bu betik SENIN makinende calismaz, GitHub'in sunucusunda calisir.
Yerel makine sadece sonucu raw.githubusercontent.com'dan okur.

PROXY: football-data.co.uk, GitHub Actions'in veri merkezi IP'lerini
ENGELLEMEYE basladigi icin (bkz. sohbet gecmisi, 14 Eylul 2026 sonrasi
"Connection refused"), artik istege bagli bir PROXY_URL ortam degiskeni
destekleniyor. PROXY_URL bos/tanimsizsa davranis ONCEKI ile AYNI (proxy
kullanilmaz). Tanimliysa (orn. "http://kullanici:sifre@host:port")
TUM indirmeler bu proxy uzerinden yapilir. Bu MUTLAKA bir "residential"
(konut tipi) proxy olmali; baska bir veri merkezi proxy'si AYNI
engele carpar, cunku sorunun kaynagi zaten "veri merkezi IP'si olmak".

ESKI SEZONLARI ATLAMA: tamamlanmis (guncel olmayan) sezonlar hic
degismez. Dosya HAM/ icinde zaten mevcutsa, YENIDEN INDIRILMEZ, sadece
mevcut listesine eklenir. Bu, hem gereksiz trafigi (kisitli proxy
kotasi) hem de gereksiz risk yuzeyini azaltir. SADECE guncel sezon ve
fixtures her calistirmada tazelenir.

Ciktilar:
  ham/{LIG}_{SEZON}.csv   orijinal dosya, hicbir sutun atilmadan
  ham/fixtures.csv        yaklasan maclar (tum ligler)
  ham/index.json          neyin mevcut oldugu ve son guncelleme zamani
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

TABAN = "https://www.football-data.co.uk"
HAM = Path("ham")
BASLIK = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}

# Orijinal football-data lig kodlari. Kapanis oranlari 2019/20'den itibaren var.
VARSAYILAN_LIGLER = ["T1", "E0", "D1", "I1", "SP1", "F1",
                     "N1", "P1", "B1", "G1", "E1", "SC0"]


def sezon_kodu(y: int) -> str:
    return f"{y % 100:02d}{(y + 1) % 100:02d}"


def guncel_sezon_baslangici() -> int:
    b = datetime.now(timezone.utc)
    return b.year if b.month >= 7 else b.year - 1


def _acici():
    """PROXY_URL ortam degiskeni varsa proxy'li, yoksa NORMAL bir
    urllib opener dondurur. Boylece indir() PROXY_URL'in varligina
    bakmaz, davranis TEK bir yerden yonetilir."""
    proxy = os.environ.get("PROXY_URL", "").strip()
    if proxy:
        print(f"   (PROXY_URL tanimli, indirmeler proxy uzerinden yapilacak)", flush=True)
        return urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    return urllib.request.build_opener()


ACICI = _acici()


def indir(url: str, deneme: int = 4) -> bytes | None:
    for k in range(deneme):
        try:
            with ACICI.open(urllib.request.Request(url, headers=BASLIK), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            print(f"      HTTP {e.code}, tekrar ({k+1}/{deneme})", flush=True)
        except Exception as e:
            print(f"      hata: {e} ({k+1}/{deneme})", flush=True)
        time.sleep(4 * (k + 1))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sezon", type=int, default=12)
    ap.add_argument("--ligler", nargs="+", default=VARSAYILAN_LIGLER)
    a = ap.parse_args()

    HAM.mkdir(exist_ok=True)
    bas = guncel_sezon_baslangici()
    guncel_kod = sezon_kodu(bas)
    yillar = list(range(bas - a.sezon + 1, bas + 1))

    dizin = {"guncelleme": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "kaynak": TABAN, "ligler": {}}
    toplam = basarisiz = atlandi = 0

    for lg in a.ligler:
        mevcut = []
        for y in yillar:
            kod = sezon_kodu(y)
            hedef = HAM / f"{lg}_{kod}.csv"

            # TAMAMLANMIS (guncel olmayan) sezon, dosya ZATEN varsa:
            # yeniden indirme, o veri artik hic degismez.
            if kod != guncel_kod and hedef.exists():
                mevcut.append(kod)
                atlandi += 1
                continue

            ham = indir(f"{TABAN}/mmz4281/{kod}/{lg}.csv")
            if ham is None:
                continue
            if len(ham) < 200:
                print(f"   {lg} {kod}: dosya sasirtici sekilde kucuk, atlandi", flush=True)
                basarisiz += 1
                continue
            hedef.write_bytes(ham)
            mevcut.append(kod)
            toplam += 1
            time.sleep(0.8)
        dizin["ligler"][lg] = mevcut
        print(f"   {lg:4s} {len(mevcut):2d} sezon", flush=True)

    fx = indir(f"{TABAN}/fixtures.csv")
    if fx and len(fx) > 100:
        (HAM / "fixtures.csv").write_bytes(fx)
        dizin["fixtures"] = True
        print("   fixtures.csv indirildi", flush=True)
    else:
        dizin["fixtures"] = False
        print("   fixtures.csv ALINAMADI", flush=True)

    (HAM / "index.json").write_text(
        json.dumps(dizin, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nToplam {toplam} dosya yeni indirildi, {atlandi} tamamlanmis sezon "
         f"atlandi (zaten vardi), {basarisiz} sorunlu.")
    if toplam == 0 and atlandi == 0:
        sys.exit("Hicbir dosya indirilemedi. Kaynak formati degismis olabilir.")


if __name__ == "__main__":
    main()
