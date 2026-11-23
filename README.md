# Submission File Service

REST service pengelolaan metadata submission dan unggahan berkas untuk Mini LMS. Service ini menangani hanya domain Submission File. SQLite menyimpan metadata; berkas disimpan lokal di `storage/uploads/`.

## Menjalankan Submission Service

Gunakan Python 3.11 atau lebih baru.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8105 --reload
```

Health check tersedia di `http://127.0.0.1:8105/health`; OpenAPI UI di `/docs`. Ubah `.env` untuk alamat dependency, batas upload, ekstensi, dan lokasi penyimpanan. Jangan commit `.env` atau data upload.

Alamat `127.0.0.1` di `.env.example` adalah konfigurasi demo satu mesin. Untuk deployment, set `HOST`, `AUTH_SERVICE_URL`, `ASSIGNMENT_SERVICE_URL`, dan `NOTIFICATION_SERVICE_URL` ke alamat yang dapat dijangkau antar-container/host; jangan gunakan loopback kecuali dependency berjalan di lingkungan network namespace yang sama.

## API Gateway (PHP)

Repository ini juga menyertakan API Gateway Kelompok 5 di folder `gateway/`. Gateway menjadi pintu masuk untuk service-service Mini LMS dan meneruskan request `/api/submissions` ke Submission File Service pada port 8105.

Pastikan PHP CLI dan ekstensi cURL aktif. Jalankan Gateway pada terminal kedua:

```powershell
php -S 127.0.0.1:8101 -t gateway
```

- Gateway base URL: `http://127.0.0.1:8101`
- Gateway health: `http://127.0.0.1:8101/health`
- Submission melalui Gateway: `http://127.0.0.1:8101/api/submissions`

Konfigurasi alamat service ada di `gateway/services.json`. Jika host atau port Submission Service berubah, perbarui nilai `submission` di file tersebut.

Gateway meneruskan request tanpa mewajibkan autentikasi. Gateway juga meneruskan upload multipart `assignment_id` dan `file`.

Dokumentasi Gateway dan instruksi tes ada di [gateway/README.md](gateway/README.md) dan [gateway/API_CONTRACT.md](gateway/API_CONTRACT.md).

## Integrasi dependency

Adapter HTTP untuk Authentication, Assignment, dan Notification berada di `app/services/`. Endpoint domain memvalidasi token, mengambil user ID dari Authentication, lalu memeriksa Assignment sebelum menyimpan berkas.

Semua panggilan dependency memakai timeout dan meneruskan `X-Request-ID`. Notifikasi dicoba setelah commit metadata; kegagalan dicatat dan tidak membatalkan submission.

## Pengujian Submission Service

```powershell
python -m pytest -q
```

Tes memakai fixture `tmp_path` standar pytest untuk database dan upload terisolasi. Jika Windows membatasi akses ke TEMP, periksa nilai `$env:TEMP` dan `$env:TMP`, lalu jalankan `python -m pytest -q --basetemp <direktori-yang-dapat-diakses>` dari PowerShell. Jangan arahkan ke folder yang tidak bisa dienumerasi atau dihapus oleh akun Windows Anda.

Koleksi Postman Submission ada di `postman/Mini-LMS.postman_collection.json` jika tersedia pada salinan lokal proyek. Atur variabel `base_url`, `token`, dan `assignment_id`. Automated tests menggunakan mock in-process dan tidak membuktikan integrasi kelompok lain berhasil.

## Struktur utama

`app/routes` memuat endpoint, `app/services` adapter dan aturan berkas, `app/database` koneksi/schema, dan `app/middleware` request ID. Kontrak endpoint Submission dirinci di [API_CONTRACT.md](API_CONTRACT.md).
