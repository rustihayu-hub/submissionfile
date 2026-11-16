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

Gateway memeriksa format header Bearer dan meneruskan token. Submission Service tetap melakukan validasi token sebenarnya ke Authentication Service. Gateway juga meneruskan upload multipart `assignment_id` dan `file`.

Dokumentasi Gateway dan instruksi tes ada di [gateway/README.md](gateway/README.md) dan [gateway/API_CONTRACT.md](gateway/API_CONTRACT.md).

## Integrasi dependency

Adapter HTTP untuk Authentication, Assignment, dan Notification berada di `app/services/`. Kontrak endpoint mereka perlu diselaraskan dengan kelompok terkait. Nilai `.env.example` adalah placeholder konfigurasi, bukan klaim endpoint sudah tersedia. Bentuk respons auth yang diasumsikan adapter: `{"valid":true,"user":{"id":"..."}}`; adapter assignment mengharapkan respons JSON 200 dan menolak `{"exists":false}` atau `{"success":false}`. Sesuaikan adapter saat kontrak resmi diterima.

Semua panggilan dependency memakai timeout dan meneruskan `X-Request-ID`. Notifikasi dicoba setelah commit metadata; kegagalan dicatat dan tidak membatalkan submission. Akses GET/DELETE juga mewajibkan token; pemeriksaan kepemilikan dan kebijakan role perlu diselaraskan dengan Authentication/Assignment.

## Pengujian Submission Service

```powershell
pytest -q
```

Koleksi Postman Submission ada di `postman/Mini-LMS.postman_collection.json` jika tersedia pada salinan lokal proyek. Atur variabel `base_url`, `token`, dan `assignment_id`. Automated tests menggunakan mock in-process dan tidak membuktikan integrasi kelompok lain berhasil.

## Struktur utama

`app/routes` memuat endpoint, `app/services` adapter dan aturan berkas, `app/database` koneksi/schema, dan `app/middleware` request ID. Kontrak endpoint Submission dirinci di [API_CONTRACT.md](API_CONTRACT.md).
