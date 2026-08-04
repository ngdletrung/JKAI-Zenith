# run_ollama_cpu.ps1 - CPU Engine Monitor Window (100% CPU RAM Isolation)
param([string]$LogPath)

$env:OLLAMA_HOST             = "127.0.0.1:11435"
$env:OLLAMA_NO_GPU           = "1"
$env:GGML_VK_VISIBLE_DEVICES = ""
$env:OLLAMA_LLM_LIBRARY      = "cpu"

$Host.UI.RawUI.WindowTitle = "[OLLAMA-CPU :11435]"

# Strip ANSI escape codes cua Ollama (nguon goc lam font do/tim)
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
