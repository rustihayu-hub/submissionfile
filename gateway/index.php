<?php
// API Gateway Kelompok 5 - integrated with Submission File Service.
header('Content-Type: application/json');

$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$rid = $_SERVER['HTTP_X_REQUEST_ID'] ?? bin2hex(random_bytes(8));
$method = $_SERVER['REQUEST_METHOD'];

// GET /health
if ($path === '/health' && $method === 'GET') {
    http_response_code(200);
    echo json_encode([
        'success' => true,
        'data' => ['service' => 'gateway', 'status' => 'healthy'],
        'meta' => ['request_id' => $rid],
    ]);
    exit;
}

// GET /api/services
if ($path === '/api/services' && $method === 'GET') {
    $services = json_decode(file_get_contents(__DIR__ . '/services.json'), true);
    http_response_code(200);
    echo json_encode([
        'success' => true,
        'data' => $services,
        'meta' => ['request_id' => $rid],
    ]);
    exit;
}

$routes = [
    'auth' => 'auth',
    'courses' => 'course',
    'assignments' => 'assignment',
    'submissions' => 'submission',
    'notifications' => 'notification',
    'monitoring' => 'monitoring',
];

if (strpos($path, '/api/') === 0) {
    $segments = explode('/', trim($path, '/'));
    $resource = $segments[1] ?? '';
    $services = json_decode(file_get_contents(__DIR__ . '/services.json'), true);

    if (!isset($routes[$resource]) || !isset($services[$routes[$resource]])) {
        http_response_code(404);
        echo json_encode([
            'success' => false,
            'error' => ['code' => 'service_not_found', 'message' => 'Service tidak ditemukan'],
            'meta' => ['request_id' => $rid],
        ]);
        exit;
    }

    $auth = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
    $contentType = $_SERVER['CONTENT_TYPE'] ?? '';
    $isMultipart = stripos($contentType, 'multipart/form-data') === 0;
    $input = $isMultipart ? '' : file_get_contents('php://input');

    // Validate JSON bodies without interfering with multipart file uploads.
    if (in_array($method, ['POST', 'PUT', 'PATCH'], true)
        && $input !== ''
        && stripos($contentType, 'application/json') === 0) {
        json_decode($input);
        if (json_last_error() !== JSON_ERROR_NONE) {
            http_response_code(400);
            echo json_encode([
                'success' => false,
                'error' => ['code' => 'invalid_json', 'message' => 'Isi request bukan JSON yang valid'],
                'meta' => ['request_id' => $rid],
            ]);
            exit;
        }
    }

    $url = rtrim($services[$routes[$resource]], '/') . $path;
    if (!empty($_SERVER['QUERY_STRING'])) {
        $url .= '?' . $_SERVER['QUERY_STRING'];
    }

    $headers = ['X-Request-ID: ' . $rid, 'Accept: application/json'];
    if (!$isMultipart && $contentType !== '') {
        $headers[] = 'Content-Type: ' . $contentType;
    }
    if ($auth !== '') {
        $headers[] = 'Authorization: ' . $auth;
    }

    $options = [
        CURLOPT_CUSTOMREQUEST => $method,
        CURLOPT_HTTPHEADER => $headers,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CONNECTTIMEOUT => 2,
        CURLOPT_TIMEOUT => 5,
    ];

    if ($isMultipart && in_array($method, ['POST', 'PUT', 'PATCH'], true)) {
        // PHP parses multipart fields into $_POST/$_FILES. Rebuild the form
        // so cURL can generate a fresh boundary for the upstream request.
        $formData = $_POST;
        foreach ($_FILES as $field => $file) {
            if (is_array($file['name'])) {
                http_response_code(400);
                echo json_encode([
                    'success' => false,
                    'error' => ['code' => 'unsupported_upload', 'message' => 'Upload banyak file dalam satu field belum didukung'],
                    'meta' => ['request_id' => $rid],
                ]);
                exit;
            }
            if ($file['error'] === UPLOAD_ERR_OK) {
                $formData[$field] = new CURLFile(
                    $file['tmp_name'],
                    $file['type'] ?: 'application/octet-stream',
                    $file['name']
                );
            } elseif ($file['error'] !== UPLOAD_ERR_NO_FILE) {
                http_response_code(400);
                echo json_encode([
                    'success' => false,
                    'error' => ['code' => 'upload_error', 'message' => 'File gagal diterima oleh Gateway'],
                    'meta' => ['request_id' => $rid],
                ]);
                exit;
            }
        }
        $options[CURLOPT_POSTFIELDS] = $formData;
    } elseif ($input !== '') {
        $options[CURLOPT_POSTFIELDS] = $input;
    }

    $ch = curl_init($url);
    curl_setopt_array($ch, $options);
    $body = curl_exec($ch);
    $errno = curl_errno($ch);
    $status = curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
    curl_close($ch);

    if ($errno !== 0) {
        $timeout = ($errno === 28);
        http_response_code($timeout ? 504 : 503);
        echo json_encode([
            'success' => false,
            'error' => [
                'code' => $timeout ? 'gateway_timeout' : 'service_unavailable',
                'message' => $timeout ? 'Service terlalu lama menjawab' : 'Service tidak dapat dihubungi',
            ],
            'meta' => ['request_id' => $rid],
        ]);
        exit;
    }

    if (!is_array(json_decode($body, true))) {
        http_response_code(502);
        echo json_encode([
            'success' => false,
            'error' => ['code' => 'bad_gateway', 'message' => 'Respons service bukan JSON yang valid'],
            'meta' => ['request_id' => $rid],
        ]);
        exit;
    }

    http_response_code($status);
    echo $body;
    exit;
}

http_response_code(404);
echo json_encode([
    'success' => false,
    'error' => ['code' => 'not_found', 'message' => 'Endpoint tidak ditemukan'],
    'meta' => ['request_id' => $rid],
]);
