# run_ollama_gpu.ps1 - GPU Engine (Vulkan) Monitor Window (100% GPU VRAM Isolation)
param([string]$LogPath)

$env:OLLAMA_HOST             = "127.0.0.1:11434"
$env:GGML_VK_VISIBLE_DEVICES = "0"
$env:OLLAMA_NO_GPU           = ""
$env:OLLAMA_KEEP_ALIVE        = "-1"

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
