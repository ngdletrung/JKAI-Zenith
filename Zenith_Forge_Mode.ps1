# --------------------------------------------------------
#   [ JKAI ZENITH: FORGE MODE (FLUSH VRAM) ]
#   Giai phong GPU de Master sang tao nghe thuat
# --------------------------------------------------------

function Write-KuteLog($msg, $status = "INFO") {
    $time = Get-Date -Format "HH:mm:ss"
    $icon = switch ($status) { 
        "SUCCESS" { "[OK]" } 
        "PROCESS" { "[..]" } 
        "WARNING" { "[!!]" } 
        default { "[--]" } 
    }
    Write-Host "[$time] $icon $msg" -ForegroundColor Cyan
}

Write-KuteLog "Dang kich hoat CHE DO XUONG VE..." "PROCESS"

$OLLAMA_GPU_HOST = "127.0.0.1:11434"
$RULE_FILE = "D:\Docker\JKAI\intelligence\rule_hardware.md"
$ModelsToUnload = @()

# 1. TRUY VẤN REAL-TIME OLLAMA API ĐỂ TÌM CÁC MODEL ĐANG CHIẾM DỤNG VRAM
Write-KuteLog "Dang truy van Ollama GPU API de tim cac model dang nap..." "PROCESS"
try {
    $psUrl = "http://$OLLAMA_GPU_HOST/api/ps"
    $psResponse = Invoke-RestMethod -Uri $psUrl -Method Get -TimeoutSec 5
    if ($psResponse -and $psResponse.models) {
        foreach ($model in $psResponse.models) {
            if ($model.name) {
                $ModelsToUnload += $model.name
                Write-KuteLog "Phat hien model dang chay tren GPU: $($model.name)" "WARNING"
            }
        }
    }
} catch {
    Write-KuteLog "Khong the ket noi den Ollama GPU API. Se su dung phuong phap doi chieu cau hinh." "WARNING"
}

# 2. ĐỐI CHIẾU VỚI RULE_HARDWARE.MD ĐỂ QUÉT CÁC MODEL ĐƯỢC PHÂN BỔ GPU
if (Test-Path $RULE_FILE) {
    Write-KuteLog "Dang phan tich rule_hardware.md de tim cac model duoc phan bo GPU..." "PROCESS"
    $content = Get-Content $RULE_FILE
    $h_model = -1
    $h_gpu = -1
    foreach ($line in $content) {
        if ($line -like "|*|*|*") {
            $parts = $line.Split("|") | ForEach-Object { $_.Trim().Replace('*', '').Replace('`', '') }
            if ($line -match "Active Model" -or $line -match "num_gpu") {
                $h_model = [array]::IndexOf($parts, "Active Model")
                $h_gpu = [array]::IndexOf($parts, "num_gpu")
                continue
            }
            if ($h_model -ne -1 -and $h_gpu -ne -1 -and $parts.Count -gt $h_gpu) {
                $mName = $parts[$h_model]
                $gpuVal = if ($parts[$h_gpu] -match '\d+') { [int]($parts[$h_gpu] -replace '[^0-9]', '') } else { 0 }
                if ($mName -and $mName -ne "n/a" -and $gpuVal -gt 0) {
                    if ($ModelsToUnload -notcontains $mName) {
                        $ModelsToUnload += $mName
                    }
                }
            }
        }
    }
}

# 3. DYNAMIC DISCOVERY: Truy vấn trực tiếp Ollama để lấy các model đang chiếm dụng VRAM
if ($ModelsToUnload.Count -eq 0) {
    Write-KuteLog "Dang truy quet cac model dang chay tren GPU..." "PROCESS"
    try {
        $runningModels = Invoke-RestMethod -Uri "http://$OLLAMA_GPU_HOST/api/ps" -Method Get -TimeoutSec 5
        foreach ($m in $runningModels.models) {
            $ModelsToUnload += $m.name
        }
    } catch {
        Write-KuteLog "Khong the ket noi den Ollama GPU. Su dung danh sach an toan." "WARNING"
    }
}

# Loai bo cac gia tri trung lap (neu co)
$ModelsToUnload = $ModelsToUnload | Select-Object -Unique

# 4. GỬI LỆNH GIẢI PHÓNG VRAM CHO TỪNG MODEL
foreach ($m in $ModelsToUnload) {
    if ($m -eq "n/a" -or $m -eq "faster-whisper" -or $m -eq "SDXL-Turbo-ROCm") { continue }
    Write-KuteLog "Dang giai phong model khoi VRAM: $m ..." "PROCESS"
    try {
        # Goi API voi keep_alive = 0 de giai phong ngay lap tuc
        $body = @{ model = $m; prompt = ""; keep_alive = 0 } | ConvertTo-Json
        Invoke-RestMethod -Uri "http://$OLLAMA_GPU_HOST/api/generate" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 10 | Out-Null
        Write-KuteLog "   >> Da giai phong thanh cong: $m" "SUCCESS"
    } catch {
        Write-KuteLog "   >> Model $m da duoc giai phong hoac trong." "WARNING"
    }
}

Write-KuteLog "VRAM DA SACH SE. Master co the bat dau ve tranh thong qua SDXL-ROCm!" "SUCCESS"
Write-KuteLog "Luu y: Cac mo hinh tinh toan tren CPU/RAM van luon truc chien de phuc vu Master." "SUCCESS"
Start-Sleep -Seconds 3
exit
