$caseDir = "K:\WIP Projects\Case Creator REDUX"
$port    = 6040

$logFile = "$caseDir\caseserver.log"
$errFile = "$caseDir\caseserver.err.log"

function Log($msg) {
    "$(Get-Date -Format s)  $msg" | Out-File -FilePath $logFile -Append -Encoding utf8
}

$mimeMap = @{
    ".html" = "text/html"; ".htm"  = "text/html"
    ".css"  = "text/css"
    ".js"   = "application/javascript"
    ".json" = "application/json"
    ".png"  = "image/png"; ".jpg" = "image/jpeg"; ".jpeg" = "image/jpeg"
    ".gif"  = "image/gif"; ".svg" = "image/svg+xml"; ".ico" = "image/x-icon"
    ".txt"  = "text/plain"
    ".pdf"  = "application/pdf"
    ".wav"  = "audio/wav"; ".mp3" = "audio/mpeg"
}

try {
    $listener = New-Object System.Net.HttpListener
    $listener.Prefixes.Add("http://+:$port/")
    $listener.Start()
    Log "Listening on port $port, serving $caseDir"
}
catch {
    "$(Get-Date -Format s)  FAILED to start listener: $_" | Out-File -FilePath $errFile -Append -Encoding utf8
    exit 1
}

while ($listener.IsListening) {
    try {
        $context  = $listener.GetContext()
        $request  = $context.Request
        $response = $context.Response

        $relPath = [System.Uri]::UnescapeDataString($request.Url.AbsolutePath).TrimStart("/")
        if ([string]::IsNullOrWhiteSpace($relPath)) { $relPath = "index.html" }

        $fullPath = [System.IO.Path]::GetFullPath((Join-Path $caseDir $relPath))

        # Prevent path traversal outside $caseDir
        if (-not $fullPath.StartsWith([System.IO.Path]::GetFullPath($caseDir), [System.StringComparison]::OrdinalIgnoreCase)) {
            $response.StatusCode = 403
            $response.Close()
            continue
        }

        if (Test-Path $fullPath -PathType Container) {
            $fullPath = Join-Path $fullPath "index.html"
        }

        if (Test-Path $fullPath -PathType Leaf) {
            $ext = [System.IO.Path]::GetExtension($fullPath).ToLower()
            $contentType = $mimeMap[$ext]
            if (-not $contentType) { $contentType = "application/octet-stream" }

            $bytes = [System.IO.File]::ReadAllBytes($fullPath)
            $response.ContentType = $contentType
            $response.ContentLength64 = $bytes.Length
            $response.OutputStream.Write($bytes, 0, $bytes.Length)
        }
        else {
            $response.StatusCode = 404
            $notFound = [System.Text.Encoding]::UTF8.GetBytes("404 Not Found")
            $response.OutputStream.Write($notFound, 0, $notFound.Length)
        }

        $response.Close()
    }
    catch {
        "$(Get-Date -Format s)  Request error: $_" | Out-File -FilePath $errFile -Append -Encoding utf8
    }
}
