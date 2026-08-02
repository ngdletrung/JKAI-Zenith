# run_ollama_gpu.ps1 - GPU Engine (Vulkan) Monitor Window
# Env vars (OLLAMA_HOST, GGML_VK_VISIBLE_DEVICES...) ke thua tu Zenith_Guardian.ps1
param([string]$LogPath)

$Host.UI.RawUI.WindowTitle = "[OLLAMA-GPU :11434]"

# Strip ANSI escape codes cua Ollama (nguon goc lam font do/tim)
# Dung [char]27 thay vi backtick-e de tranh loi escape khi o trong .ps1 file
$esc = [char]27
$ansiPattern = "$esc\[[0-9;]*[mKHJFGA-Za-z]"

if ($LogPath) {
    $null = New-Item -ItemType File -Path $LogPath -Force -ErrorAction SilentlyContinue
    ollama serve 2>&1 | ForEach-Object {
        $_ -replace $ansiPattern, ''
    } | Tee-Object -FilePath $LogPath
} else {
    ollama serve 2>&1 | ForEach-Object {
        $_ -replace $ansiPattern, ''
    }
}
