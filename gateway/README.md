# API Gateway - Kelompok 5

Gateway PHP ini digabungkan sebagai komponen terpisah di repository Submission File Service.

## Menjalankan lokal

Pastikan PHP CLI dan ekstensi cURL aktif. Jalankan Submission File Service terlebih dahulu pada port 8105:

```powershell
# Terminal 1, dari root repository
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8105 --reload
```

Kemudian jalankan Gateway:

```powershell
# Terminal 2, dari root repository
php -S 127.0.0.1:8101 -t gateway
```

- Gateway: http://127.0.0.1:8101
- Health check: http://127.0.0.1:8101/health
- Daftar service: http://127.0.0.1:8101/api/services
- Submission API melalui Gateway: http://127.0.0.1:8101/api/submissions

## Konfigurasi service

Alamat service berada di `gateway/services.json`. Submission File Service diarahkan ke `http://127.0.0.1:8105`, sesuai port default di README utama. Sesuaikan alamat tersebut bila port atau host berubah.

## Autentikasi

Gateway meneruskan header `Authorization` jika disediakan. Endpoint domain memvalidasi token pada service pemilik; login/register tetap publik.

## Upload file

Untuk request `multipart/form-data`, Gateway membangun ulang form dari `$_POST` dan `$_FILES` agar file dapat diteruskan melalui cURL dengan boundary yang benar. Endpoint upload Submission menerima field `assignment_id` dan `file`.

## Pengujian

- Postman collection: `gateway/postman/Mini-LMS.postman_collection.json`
- PowerShell test: `gateway/tests/test_api.ps1`

Jalankan pengujian setelah semua service aktif. Submission memerlukan Authentication, Assignment, dan Notification Service yang sesuai kontrak.
