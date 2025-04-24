# Sistem Integrasi Antar Layanan

Proyek ini merupakan implementasi sistem terintegrasi antar layanan menggunakan pendekatan service-to-service communication.

## Struktur Proyek
```
services/
  ├── user_service/
  │   └── app.py
  ├── product_service/
  │   └── app.py
  └── order_service/
      └── app.py
```

## Persyaratan
- Python 3.7+
- pip

## Instalasi
1. Clone repositori ini
2. Install dependensi:
   ```bash
   pip install -r requirements.txt
   ```

## Menjalankan Layanan
Jalankan setiap layanan di terminal terpisah:

1. UserService (Port 5001):
   ```bash
   cd services/user_service
   python app.py
   ```

2. ProductService (Port 5002):
   ```bash
   cd services/product_service
   python app.py
   ```

3. OrderService (Port 5003):
   ```bash
   cd services/order_service
   python app.py
   ```

## Dokumentasi API
Lihat file `API_DOCUMENTATION.md` untuk detail lengkap tentang endpoint API yang tersedia.