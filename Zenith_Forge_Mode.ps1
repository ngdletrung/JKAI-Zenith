# --------------------------------------------------------
#   [ JKAI ZENITH: FORGE MODE (FLUSH VRAM) ]
#   Giai phong GPU de Master sang tao nghe thuat
# --------------------------------------------------------

function Write-KuteLog($msg, $status = "INFO") {
    $time = Get-Date -Format "HH:mm:ss"
    $icon = switch ($status) { "SUCCESS" { "🎨" }; "PROCESS" { "🧹" }; default { "🤖" } }
    Write-Host "[$time] $icon $msg" -ForegroundColor Cyan
}

Write-KuteLog "Dang kich hoat CHE DO XUONG VE... (^_^)" "PROCESS"

# [DYNAMIC VRAM FLUSH]: Tu dong tim cac model dang chiem GPU thưa Master
$RULE_FILE = "D:\Docker\N8N\intelligence\rule_hardware.md"
$ModelsToUnload = @()

if (Test-Path $RULE_FILE) {
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
                    $ModelsToUnload += $mName
                }
            }
        }
    }
}

# Fallback neu khong tim thay
if ($ModelsToUnload.Count -eq 0) {
    $ModelsToUnload = @("qwen2.5-coder:14b", "moondream:latest", "nomic-embed-text:latest")
}

foreach ($m in $ModelsToUnload) {
    Write-KuteLog "Dang xa model: $m ..." "PROCESS"
    try {
        # Goi API voi keep_alive = 0 de giai phong ngay lap tuc
        $body = @{ model = $m; prompt = ""; keep_alive = 0 } | ConvertTo-Json
        Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/generate" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 10 | Out-Null
        Write-KuteLog "   >> $m DA GIAI PHONG !" "SUCCESS"
    } catch {
        Write-KuteLog "   >> $m da trong hoac co loi nhe." "WARNING"
    }
}

Write-KuteLog "VRAM DA SACH SE. Master co the bat dau ve tranh thong qua SDXL-ROCm!" "SUCCESS"
Write-KuteLog "Luu y: DeepSeek-32B van dang truc chien tren RAM de phuc vu Master." "SUCCESS"
Start-Sleep -Seconds 3
exit
