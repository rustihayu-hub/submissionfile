# Submission File Service

REST service pengelolaan metadata submission dan unggahan berkas untuk Mini LMS. Service ini menangani hanya domain Submission File. SQLite menyimpan metadata; berkas disimpan lokal di `storage/uploads/`.

## Menjalankan

Gunakan Python 3.11 atau lebih baru.

```powershell
cd submission-file-service
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8105 --reload
```

Health check tersedia di `http://127.0.0.1:8105/health`; OpenAPI UI di `/docs`. Ubah `.env` untuk alamat dependency, batas upload, ekstensi, dan lokasi penyimpanan. Jangan commit `.env` atau data upload.

## Integrasi

Adapter HTTP untuk Authentication, Assignment, dan Notification berada di `app/services/`. Kontrak endpoint mereka belum disediakan oleh kelompok terkait. Nilai `.env.example` adalah placeholder konfigurasi yang harus diselaraskan dengan kontrak kelompok tersebut, bukan klaim endpoint yang sudah tersedia. Bentuk respons auth yang diasumsikan adapter: `{"valid":true,"user":{"id":"..."}}`; adapter assignment mengharapkan respons JSON 200 dan menolak `{"exists":false}` atau `{"success":false}`. Sesuaikan adapter saat kontrak resmi diterima.

Semua panggilan dependency memakai timeout dan meneruskan `X-Request-ID`. Notifikasi dicoba setelah commit metadata; kegagalan dicatat dan tidak membatalkan submission. Akses GET/DELETE juga mewajibkan token; pemeriksaan kepemilikan dan kebijakan role perlu diselaraskan dengan Authentication/Assignment.

## Pengujian

```powershell
pytest -q
```

Koleksi Postman ada di `postman/Mini-LMS.postman_collection.json`. Atur variabel `base_url`, `token`, dan `assignment_id`; skenario domain memerlukan Authentication dan Assignment yang kompatibel. Automated tests menggunakan mock in-process dan tidak menyatakan integrasi kelompok lain berhasil. Hasil verifikasi runtime dan batas pengujian dicatat di [docs/TESTING.md](docs/TESTING.md).

Field `assignment_id` pada endpoint upload diterima sebagai bagian `multipart/form-data` (`Form(...)`). Kirim bersama `file` pada form body, bukan sebagai query parameter. Pemeriksaan import aplikasi berhasil. Suite test belum dapat diverifikasi ulang di sandbox saat ini karena pytest gagal mengakses direktori temporary Windows; jalankan `python -m pytest -vv --tb=short` dari terminal proyek.

## Struktur utama

`app/routes` memuat endpoint, `app/services` adapter dan aturan berkas, `app/database` koneksi/schema, dan `app/middleware` request ID. ERD, alur, seluruh status HTTP dan batasan integrasi dirinci di [API_CONTRACT.md](API_CONTRACT.md).
