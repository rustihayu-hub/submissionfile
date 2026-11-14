# Pengujian

## Automated

Jalankan `python -m pytest -vv --tb=short`. Test API mengisolasi HTTP Authentication, Assignment, dan Notification memakai mock transport di dalam proses test; hasilnya memverifikasi perilaku service terhadap mock, bukan keberhasilan integrasi dengan service kelompok lain. Test mencakup health, autentikasi, list kosong dan setelah upload, upload sukses, file kosong, ekstensi/MIME tidak didukung, ukuran berlebih, assignment invalid/unavailable, notification gagal, DELETE sukses/404, dan penghapusan file fisik.

Endpoint upload menerima `assignment_id` sebagai field `multipart/form-data`, bersama `file`. Implementasi memakai `Form(...)` agar field tidak diperlakukan sebagai query parameter.

## Postman

Import `postman/Mini-LMS.postman_collection.json`. Atur `base_url` (default `http://127.0.0.1:8105`), `token`, `assignment_id`, dan `submission_id`. Koleksi menyediakan health, GET daftar, POST valid, POST file kosong, ekstensi tidak didukung, MIME mismatch, ukuran berlebih, DELETE berhasil/404, dan GET tanpa token (401). Semua request domain mengirim `Authorization: Bearer {{token}}`, kecuali request yang memang menguji token hilang. Untuk tiap request upload, pilih file yang cocok dari file picker Postman.

Jalankan `Upload valid submission` lebih dahulu; script menyimpan `submission_id` hasil 201 untuk request DELETE. Untuk validasi 400/413/415, request tetap melewati Authentication dan Assignment terlebih dahulu. Karena kelompok terkait belum menyediakan service resmi, skenario manual tersebut hanya bisa mencapai validasi berkas jika adapter diarahkan ke dependency lokal yang kompatibel atau test dijalankan melalui mock in-process pytest. Jangan menggunakan token dummy untuk menyimpulkan autentikasi berhasil.

Koleksi menyimpan `submission_id` dari respons upload untuk DELETE. Gunakan berkas melebihi `MAX_UPLOAD_BYTES` untuk skenario 413 dan ekstensi/MIME di luar allowlist untuk 415. Health dapat diuji tanpa dependency.

## Bukti

## Hasil verifikasi terakhir

- Automated tests: **11 passed, 0 failed** (`python -m pytest -vv --tb=short`). Ada satu warning deprecation dari Starlette terkait pemakaian httpx di TestClient.
- Runtime lokal di `127.0.0.1:8105`: `/health` **200**, `/docs` **200**, `/openapi.json` **200**. OpenAPI memuat `GET` dan `POST /api/submissions`, serta `DELETE /api/submissions/{submission_id}`.
- Melalui mock in-process, GET, POST, DELETE, token hilang, ukuran/tipe berkas, file kosong, assignment invalid/unavailable, dan kegagalan notifikasi diuji.
- Tidak ada kegagalan automated test pada run terakhir.
- **Tertunda:** request Postman yang memerlukan token nyata/Authentication Service, validasi Assignment terhadap data layanan nyata, dan pengiriman Notification nyata. Ketiga kelompok belum menyediakan layanan resmi. Health/docs runtime tidak membuktikan integrasi dependency tersebut.

Direktori `docs/bukti/` disediakan untuk menyimpan tangkapan layar Postman setelah layanan dependency tersedia atau lingkungan mock manual disiapkan. Belum ada tangkapan layar Postman yang diklaim sebagai bukti.
