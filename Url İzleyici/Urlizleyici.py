import argparse, csv, os, sys, json
from datetime import datetime
from urllib.parse import urlparse
from pathlib import Path
import requests

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Genel ayarlar
ZAMAN_ASIMI = 25  # İstek zaman aşımı (saniye)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

# Çıktıların kaydedileceği ana dizin
CIKTI_KOK = Path(r"Users/EYLÜL/Desktop")

# Güvenli dosya adı oluşturma (özel karakterleri temizler)
def guvenli_dosya_adi(s: str) -> str:
    izin = "-_.() "
    return "".join(c for c in str(s) if c.isalnum() or c in izin).strip().replace(" ", "_")

# URL yönlendirme zincirini çözme ve HTTP başlıklarını toplama
def yonlendirmeleri_coz(url: str, zaman_asimi=ZAMAN_ASIMI):
    oturum = requests.Session()
    oturum.headers.update({"User-Agent": UA, "Accept": "*/*"})
    sonuc = {"giris_url": url, "zincir": [], "son_url": None, "son_durum": None, "hops": []}
    try:
        yanit = oturum.get(url, allow_redirects=True, timeout=zaman_asimi)
        # Yönlendirme geçmişini kaydet
        for h in yanit.history:
            sonuc["hops"].append({"url": h.url, "durum": h.status_code, "basliklar": dict(list(h.headers.items())[:50])})
            sonuc["zincir"].append(h.url)
        # Son URL ve başlık bilgileri
        sonuc["hops"].append({"url": yanit.url, "durum": yanit.status_code, "basliklar": dict(list(yanit.headers.items())[:50])})
        sonuc["zincir"].append(yanit.url)
        sonuc["son_url"], sonuc["son_durum"] = yanit.url, yanit.status_code
    except Exception as e:
        sonuc["hata"] = str(e)
    return sonuc

# Headless (görünmez) Chrome tarayıcı oluşturma
def tarayici_olustur():
    secenek = Options()
    secenek.add_argument("--headless=new")
    secenek.add_argument("--no-sandbox")
    secenek.add_argument("--disable-dev-shm-usage")
    secenek.add_argument("--disable-gpu")
    secenek.add_argument("--window-size=1920,1080")
    secenek.add_argument(f"--user-agent={UA}")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=secenek)

# Verilen URL’nin ekran görüntüsünü alma
def ekran_goruntusu_al(url: str, png_yol: str):
    bilgi = {"baslik": None, "png": None, "hata": None}
    d = None
    try:
        d = tarayici_olustur()
        d.set_page_load_timeout(ZAMAN_ASIMI)
        d.get(url)
        # Sayfa yüksekliğini dinamik olarak ayarlama
        try:
            yukseklik = d.execute_script("""
                return Math.max(
                  document.body.scrollHeight, document.documentElement.scrollHeight,
                  document.body.offsetHeight, document.documentElement.offsetHeight,
                  document.body.clientHeight, document.documentElement.clientHeight
                );
            """) or 1080
            d.set_window_size(1920, max(1080, int(yukseklik)))
        except Exception:
            pass
        bilgi["baslik"] = d.title
        if d.save_screenshot(png_yol):
            bilgi["png"] = png_yol
        else:
            bilgi["hata"] = "save_screenshot False döndü"
    except Exception as e:
        bilgi["hata"] = str(e)
    finally:
        try:
            d.quit()
        except Exception:
            pass
    return bilgi

# CSV dosyası yazma
def csv_yaz(satirlar, yol, alanlar):
    with open(yol, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=alanlar)
        w.writeheader()
        for s in satirlar:
            w.writerow(s)

# CSV'den URL okuma (url sütunu zorunlu)
def csvden_url_oku(yol: str):
    if not os.path.exists(yol):
        print(f"[!] CSV yok: {yol}")
        sys.exit(1)
    urller = []
    with open(yol, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        if not r.fieldnames or "url" not in r.fieldnames:
            print("[!] CSV 'url' kolonu içermeli")
            sys.exit(1)
        for satir in r:
            u = (satir.get("url") or "").strip()
            if u:
                urller.append(u)
    return urller

# Tek bir URL'yi işleme (yönlendirme çözme, başlık bilgisi, ekran görüntüsü)
def tek_url_isle(url: str, klasorler: dict):
    kayit = {
        "giris_url": url, "son_url": None, "son_durum": None, "yonlendirme_zinciri": None,
        "son_alan": None, "sunucu": None, "icerik_turu": None, "icerik_uzunlugu": None,
        "tarih_basligi": None, "sayfa_baslik": None, "screenshot": None, "hata": None
    }
    # Yönlendirmeleri çöz
    res = yonlendirmeleri_coz(url)
    # JSON olarak kaydet
    with open(os.path.join(klasorler["hops"], f"{guvenli_dosya_adi(url)}.json"), "w", encoding="utf-8") as jf:
        json.dump(res, jf, ensure_ascii=False, indent=2)

    if "hata" in res:
        kayit["hata"] = res["hata"]
        return kayit

    kayit["son_url"], kayit["son_durum"] = res.get("son_url"), res.get("son_durum")
    kayit["yonlendirme_zinciri"] = " -> ".join(res.get("zincir", [])) if res.get("zincir") else None

    # Son başlık bilgileri
    son_b = res.get("hops", [{}])[-1].get("basliklar", {})
    kayit["sunucu"] = son_b.get("Server")
    kayit["icerik_turu"] = son_b.get("Content-Type")
    kayit["icerik_uzunlugu"] = son_b.get("Content-Length")
    kayit["tarih_basligi"] = son_b.get("Date")

    # Ekran görüntüsü alma
    if kayit["son_url"]:
        kayit["son_alan"] = urlparse(kayit["son_url"]).netloc or None
        png_ad = f"{guvenli_dosya_adi(kayit['son_alan'] or 'final')}.png"
        png_yol = os.path.join(klasorler["screens"], png_ad)
        shot = ekran_goruntusu_al(kayit["son_url"], png_yol)
        kayit["sayfa_baslik"], kayit["screenshot"] = shot.get("baslik"), shot.get("png")
        if shot.get("hata"):
            kayit["hata"] = (kayit["hata"] + " | " if kayit["hata"] else "") + f"shot: {shot['hata']}"
    return kayit

# Ana çalışma fonksiyonu
def main():
    ap = argparse.ArgumentParser(description="Kısaltılmış Link İzleyici")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--url", help="Tek URL")
    g.add_argument("--girdi", help="CSV dosyası (kolon: url)")
    args = ap.parse_args()

    # Çıktı klasörlerini oluşturma
    CIKTI_KOK.mkdir(parents=True, exist_ok=True)
    damga = datetime.now().strftime("%Y%m%d_%H%M%S")
    kosu = CIKTI_KOK / f"kosu_{damga}"
    screens = kosu / "screenshots"
    hops = kosu / "hops_json"
    screens.mkdir(parents=True, exist_ok=True)
    hops.mkdir(parents=True, exist_ok=True)

    klasorler = {"kok": str(kosu), "screens": str(screens), "hops": str(hops)}

    # CSV alan adları
    alanlar = ["giris_url","son_url","son_durum","yonlendirme_zinciri","son_alan",
               "sunucu","icerik_turu","icerik_uzunlugu","tarih_basligi",
               "sayfa_baslik","screenshot","hata"]
    rapor_yol = kosu / "rapor.csv"

    # Tek URL veya CSV'den okuma
    if args.url:
        urller = [args.url.strip()]
    else:
        urller = csvden_url_oku(args.girdi)

    satirlar = []
    # URL’leri sırayla işle
    for i, u in enumerate(urller, 1):
        print(f"[{i}/{len(urller)}] {u}")
        try:
            satirlar.append(tek_url_isle(u, klasorler))
        except Exception as e:
            satirlar.append({"giris_url": u, "hata": f"isleme_hatasi: {e}"})

    # Raporu CSV olarak yaz
    csv_yaz(satirlar, str(rapor_yol), alanlar)

    # Özet çıktı
    print("\n[✓] Bitti.")
    print("Rapor:    ", rapor_yol.resolve())
    print("Screens:  ", screens.resolve())
    print("Hop JSON: ", hops.resolve())
    print("Kök:      ", CIKTI_KOK.resolve())

# Komut satırından çalıştırma
if __name__ == "__main__":
    main()
