import sys, requests
#kısa link 
DEFAULT_URL = "http://bc.vc/NEBXKTD"
SECILI = {
    "Server": "Sunucu",
    "X-Powered-By": "Uygulama",
    "Via": "Proxy",
    "CF-Cache-Status": "CF-Cache",
    "Content-Type": "İçerik",
    "Set-Cookie": "Çerez (ilk)"
}

u = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
u = u if "://" in u else "http://" + u

r = requests.get(u, allow_redirects=True, timeout=15,
                 headers={"User-Agent":"Arastirma/1.0 (+kisa_kontrol)"})

# Yönlendirme zinciri (HTTP seviyesinde)
if r.history:
    print("[Yönlendirme Zinciri]")
    for h in r.history:
        hedef = h.headers.get("Location", "")
        print(f" {h.status_code} {h.url}  →  {hedef}")

# Final durum
print("\n[Son (Final) Yanıt]")
print(f" Durum: {r.status_code}")
print(f" Final URL: {r.url}")

# Seçili başlıklar
print("\n[Seçili HTTP Başlıkları]")
for k, tr in SECILI.items():
    if k in r.headers:
        val = r.headers[k]
        if k == "Set-Cookie":  # çok uzunsa kısalt
            val = val.split(",")[0][:200]
        print(f" {tr}: {val}")

print(f"\n[İçerik] Boyut: {len(r.content)} bayt")
