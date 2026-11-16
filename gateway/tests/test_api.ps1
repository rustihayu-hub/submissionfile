# tests\test_api.ps1 : pengujian API Gateway Kelompok 5
# Jalankan setelah Gateway aktif di port 8101.
# Uji nomor 5 memerlukan service Course aktif di port 8103.

$base  = "http://127.0.0.1:8101"
$token = "Bearer abc123"
$lulus = 0
$gagal = 0

function Uji($nama, $diharapkan, $argumen) {
    $kode = & curl.exe -s -o NUL -w '%{http_code}' --max-time 10 @argumen
    if ($diharapkan -contains [int]$kode) {
        Write-Host "[LULUS] $nama -> $kode" -ForegroundColor Green
        $script:lulus++
    } else {
        Write-Host "[GAGAL] $nama -> $kode (diharapkan: $($diharapkan -join ' atau '))" -ForegroundColor Red
        $script:gagal++
    }
}

Write-Host "=== Pengujian API Gateway Kelompok 5 ===" -ForegroundColor Cyan

Uji "1. GET /health"                       @(200)      @("$base/health")
Uji "2. GET /api/services"                 @(200)      @("$base/api/services")
Uji "3. Nama service salah -> 404"         @(404)      @("-H", "Authorization: $token", "$base/api/abc")
Uji "4. Tanpa token -> 401"                @(401)      @("$base/api/submissions")
Uji "5. Submission mati -> 503 atau 504"   @(503, 504) @("-H", "Authorization: $token", "$base/api/submissions")

Write-Host ""
Write-Host "Lulus: $lulus   Gagal: $gagal" -ForegroundColor Cyan
