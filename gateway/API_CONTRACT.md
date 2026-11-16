# API Contract: API Gateway (Kelompok 5)

## Informasi umum

- Port default: 8101
- URL dasar: http://127.0.0.1:8101
- Format respons: JSON
- Setiap respons menyertakan `meta.request_id`.

## Endpoint

### GET /health

Tidak memerlukan autentikasi. Mengembalikan status Gateway.

### GET /api/services

Tidak memerlukan autentikasi. Mengembalikan daftar URL service dari `services.json`.

### ANY /api/{resource}/{path}

Meneruskan request ke service tujuan berdasarkan resource:

| Resource | Service | Port default |
|---|---|---:|
| auth | Authentication | 8102 |
| courses | Course | 8103 |
| assignments | Assignment | 8104 |
| submissions | Submission File | 8105 |
| notifications | Notification | 8106 |
| monitoring | Monitoring | 8107 |

Semua resource memerlukan header `Authorization: Bearer <token>`, kecuali `POST /api/auth/login` dan `POST /api/auth/register`.

Gateway meneruskan `Authorization`, `X-Request-ID`, query string, dan body request. JSON divalidasi sebelum diteruskan. Request multipart dibangun ulang dari field form dan file upload supaya file tetap terkirim ke Submission Service.

## Integrasi Submission File

- `GET /api/submissions?assignment_id=...` diteruskan ke Submission File Service.
- `POST /api/submissions` meneruskan multipart form dengan field `assignment_id` dan `file`.
- `DELETE /api/submissions/{submission_id}` diteruskan ke Submission File Service.
- Gateway hanya memeriksa format Bearer. Submission File Service tetap memvalidasi token dengan Authentication Service. Otorisasi kepemilikan submission/assignment tetap harus ditegakkan oleh service domain.

## Status error Gateway

| Status | Kode | Penyebab |
|---:|---|---|
| 400 | invalid_json | Body JSON tidak valid |
| 401 | unauthorized | Header Bearer tidak ada atau format salah |
| 404 | service_not_found / not_found | Resource atau endpoint tidak dikenal |
| 502 | bad_gateway | Respons upstream bukan JSON valid |
| 503 | service_unavailable | Service tujuan tidak dapat dihubungi |
| 504 | gateway_timeout | Service tujuan melewati timeout |

Timeout koneksi default 2 detik dan timeout total default 5 detik. Sesuaikan untuk kebutuhan deployment.
