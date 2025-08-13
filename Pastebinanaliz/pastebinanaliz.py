import requests

# Analiz edilecek Pastebin linki
paste_url = "https://pastebin.com/ux4knNGX"  

# Aranacak anahtar kelimeler
ANAHTAR_KELIMELER = ["password", "confidential", "leak"]

try:
    # İçeriği çek
    r = requests.get(paste_url, timeout=10)
    if r.status_code == 200:
        icerik = r.text.lower()
        # Eşleşme kontrolü
        bulunanlar = [k for k in ANAHTAR_KELIMELER if k in icerik]
        if bulunanlar:
            print(f"[!] Potansiyel sızıntı bulundu! Eşleşen kelimeler: {bulunanlar}")
        else:
            print("[+] Belirtilen anahtar kelimeler bulunamadı.")
    else:
        print(f"[!] Pastebin bağlantısı başarısız, durum kodu: {r.status_code}")
except Exception as e:
    print("[!] Hata oluştu:", e)