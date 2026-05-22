# --------------------------------------------------------
#   [ JKAI ZENITH: RESTORE MODE (RELOAD NEURONS) ]
#   Nap lai quan doan theo dung Active Role Mapping
# --------------------------------------------------------

function Write-KuteLog($msg, $status = "INFO") {
    $time = Get-Date -Format "HH:mm:ss"
    $icon = switch ($status) { "SUCCESS" { "💎" }; "PROCESS" { "🚀" }; default { "🤖" } }
    Write-Host "[$time] $icon $msg" -ForegroundColor Green
}

Write-KuteLog "Dang kich hoat CHE DO KHOI PHUC QUAN DOAN... (^_^)" "PROCESS"

# Don gian la goi lai Guardian de dong bo moi thu theo rule_hardware.md
if (Test-Path "D:\Docker\N8N\Zenith_Guardian.ps1") {
    Write-KuteLog "Dang goi Ve si Zenith_Guardian de tai thiet he thong..." "PROCESS"
    powershell.exe -ExecutionPolicy Bypass -File "D:\Docker\N8N\Zenith_Guardian.ps1"
} else {
    Write-KuteLog "Khong tim thay script Guardian! Master vui long kiem tra lai." "ERROR"
}

Write-KuteLog "HE THONG DA QUAY LAI TRANG THAI CHIEN DAU TOI THUONG." "SUCCESS"
Start-Sleep -Seconds 3
exit
