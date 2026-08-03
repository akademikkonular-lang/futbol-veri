#!/usr/bin/env python3
"""
GitHub Actions icinde calisir. football-data.co.uk'tan lig dosyalarini indirip
ham/ klasorune yazar ve ham/index.json uretir.

Bu betik SENIN makinende calismaz, GitHub'in sunucusunda calisir.
Yerel makine sadece sonucu raw.githubusercontent.com'dan okur.

Ciktilar:
  ham/{LIG}_{SEZON}.csv   orijinal dosya, hicbir sutun atilmadan
  ham/fixtures.csv        yaklasan maclar (tum ligler)
  ham/index.json          neyin mevcut oldugu ve son guncelleme zamani
"""

from __future__ import annotations

import argparse
import json
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


def indir(url: str, deneme: int = 4) -> bytes | None:
    for k in range(deneme):
        try:
            with urllib.request.urlopen(
                    urllib.request.Request(url, headers=BASLIK), timeout=60) as r:
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
    yillar = list(range(bas - a.sezon + 1, bas + 1))

    dizin = {"guncelleme": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "kaynak": TABAN, "ligler": {}}
    toplam = basarisiz = 0

    for lg in a.ligler:
        mevcut = []
        for y in yillar:
            kod = sezon_kodu(y)
            hedef = HAM / f"{lg}_{kod}.csv"
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

    print(f"\nToplam {toplam} dosya yazildi, {basarisiz} sorunlu.")
    if toplam == 0:
        sys.exit("Hicbir dosya indirilemedi. Kaynak formati degismis olabilir.")


if __name__ == "__main__":
    main()
