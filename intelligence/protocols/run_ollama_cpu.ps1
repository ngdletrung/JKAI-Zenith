# run_ollama_cpu.ps1 - CPU Engine Monitor Window
# Env vars (OLLAMA_HOST=11435, OLLAMA_NO_GPU=1...) ke thua tu Zenith_Guardian.ps1
param([string]$LogPath)

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
