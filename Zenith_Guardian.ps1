# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: Zenith_Guardian.ps1
# - Role: System Infrastructure Bootstrapper (Dual Ollama & Docker Engine)
# - Ownership: Master LeeTrung
# - Status: Active | Version: SDS v27.0 (AMG v2 Model-Blind Infrastructure)
# [WORKING PRINCIPLES]:
# 1. Manages Dual-Engine Ollama service lifecycles (GPU on 11434, CPU on 11435).
# 2. Smart port check: does NOT restart Ollama if already online.
# 3. Model-Blind Infrastructure: Zero model names, zero model selection semantics.
# 4. Hands off all model decisions to AMG v2 (python -m core.runtime.amg_boot).
# -----------------------------------------------------------------------------
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues['*:Encoding'] = 'utf8'
chcp 65001 | Out-Null

# --- 0. THIET LAP MOI TRUONG VULKAN (RX 6600 - Windows Native) ---
Set-Location "D:\Docker\JKAI"
$env:GGML_VK_VISIBLE_DEVICES  = "0"
$env:OLLAMA_LLM_LIBRARY       = ""
$env:OLLAMA_KEEP_ALIVE        = "-1"

$RULE_FILE = "D:\Docker\JKAI\intelligence\rule_hardware.md"

# Read global env vars from rule_hardware.md [OLLAMA_ENVIRONMENT]
$globalEnv = @{}
$gpuEnv = @{}
$cpuEnv = @{}

if (Test-Path $RULE_FILE) {
    $hwContent = Get-Content $RULE_FILE
    $inEnvSection = $false
    foreach ($line in $hwContent) {
        if ($line -match "\[OLLAMA_ENVIRONMENT\]") { $inEnvSection = $true; continue }
        if ($inEnvSection -and $line -match "^\[" -or ($inEnvSection -and $line -match "^---")) { $inEnvSection = $false; continue }
        if ($inEnvSection -and $line -match "^\s*([A-Z0-9_]+)=(.*)$") {
            $k = $matches[1]
            $v = $matches[2]
            if ($k -match "^GPU_") { $gpuEnv[$k.Substring(4)] = $v }
            elseif ($k -match "^CPU_") { $cpuEnv[$k.Substring(4)] = $v }
            else { $globalEnv[$k] = $v }
        }
    }
}

foreach ($k in $globalEnv.Keys) { Set-Item -Path "Env:$k" -Value $globalEnv[$k] }

$env:OLLAMA_MODELS = "D:\Docker\Ollama_AI\Ollama_model"

$OLLAMA_GPU_HOST = "127.0.0.1:11434"
$OLLAMA_CPU_HOST = "127.0.0.1:11435"
$LOG_FILE = "D:\Docker\JKAI\intelligence\protocols\guardian_logs.txt"
$DOCKER_EXE = "C:\Program Files\Docker\Docker\Docker Desktop.exe"

function Write-KuteLog($msg, $status = "INFO") {
    $time = Get-Date -Format "HH:mm:ss"
    $icon = switch ($status) { 
        "SUCCESS" { ">>" } 
        "PROCESS" { ".." } 
        "WARNING" { "!!" } 
        "ERROR" { "XX" } 
        default { "--" } 
    }
    $color = switch ($status) { 
        "SUCCESS" { "Green" } 
        "PROCESS" { "Cyan" } 
        "WARNING" { "Yellow" } 
        "ERROR" { "Red" } 
        default { "White" } 
    }
    $logLine = "[$time][$status] $msg"
    Write-Host "[$time] $icon $msg" -ForegroundColor $color
    Add-Content -Path $LOG_FILE -Value $logLine -ErrorAction SilentlyContinue
}

try {
    Write-KuteLog "=== ZENITH GUARDIAN: INFRASTRUCTURE BOOTSTRAP (SDS v27.0) ===" "SUCCESS"

    # --- 1. SMART PORT CHECK FOR OLLAMA ENGINES ---
    $gpuAlive = $false
    $cpuAlive = $false

    try {
        $r1 = Invoke-RestMethod -Uri "http://$OLLAMA_GPU_HOST/api/tags" -Method Get -TimeoutSec 3 -ErrorAction SilentlyContinue
        if ($r1) { $gpuAlive = $true }
    } catch {}

    try {
        $r2 = Invoke-RestMethod -Uri "http://$OLLAMA_CPU_HOST/api/tags" -Method Get -TimeoutSec 3 -ErrorAction SilentlyContinue
        if ($r2) { $cpuAlive = $true }
    } catch {}

    if ($gpuAlive -and $cpuAlive) {
        Write-KuteLog "Ollama Dual-Engine services are ALREADY ONLINE (GPU:11434, CPU:11435). Skipping restart." "SUCCESS"
    } else {
        Write-KuteLog "Cleaning stale process memory & resetting engine state..." "PROCESS"
        
        # 1. Force kill stale powershell script runners
        Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe'" -ErrorAction SilentlyContinue | Where-Object {
            $_.CommandLine -match "run_ollama_gpu\.ps1" -or $_.CommandLine -match "run_ollama_cpu\.ps1"
        } | ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }

        # 2. Force kill any lingering Ollama or llama-server processes cleanly
        Get-Process "ollama*", "llama-server*" -ErrorAction SilentlyContinue | Stop-Process -Force
        Start-Sleep -Seconds 2

        # 3. Reset alive state variables so BOTH engines restart cleanly
        $gpuAlive = $false
        $cpuAlive = $false

        # Start GPU Engine if not alive
        if (-not $gpuAlive) {

            $env:OLLAMA_HOST              = $OLLAMA_GPU_HOST
            $env:GGML_VK_VISIBLE_DEVICES  = "0"
            $env:OLLAMA_LLM_LIBRARY       = ""
            $env:OLLAMA_NO_GPU            = ""
            foreach ($k in $gpuEnv.Keys) { Set-Item -Path "Env:$k" -Value $gpuEnv[$k] }
            Write-KuteLog "Starting GPU Engine (Vulkan) on $OLLAMA_GPU_HOST..." "PROCESS"
            $gpuLogPath = "D:\Docker\JKAI\intelligence\protocols\ollama_gpu.log"
            $gpuRunnerPath = "D:\Docker\JKAI\intelligence\protocols\run_ollama_gpu.ps1"
            $ollamaGpu = Start-Process "powershell.exe" -ArgumentList "-NoProfile -NoExit -ExecutionPolicy Bypass -File `"$gpuRunnerPath`" -LogPath `"$gpuLogPath`"" -WindowStyle Minimized -PassThru
            if ($ollamaGpu) { try { $ollamaGpu.PriorityClass = "BelowNormal" } catch {} }
        }

        # Start CPU Engine if not alive
        if (-not $cpuAlive) {
            foreach ($k in $gpuEnv.Keys) {
                if (-not $cpuEnv.ContainsKey($k)) { Remove-Item -Path "Env:$k" -ErrorAction SilentlyContinue }
            }
            $env:OLLAMA_HOST             = $OLLAMA_CPU_HOST
            $env:GGML_VK_VISIBLE_DEVICES = ""
            $env:OLLAMA_LLM_LIBRARY      = ""
            $env:OLLAMA_NO_GPU           = "1"
            foreach ($k in $cpuEnv.Keys) { Set-Item -Path "Env:$k" -Value $cpuEnv[$k] }
            Write-KuteLog "Starting CPU Engine on $OLLAMA_CPU_HOST..." "PROCESS"
            $cpuLogPath = "D:\Docker\JKAI\intelligence\protocols\ollama_cpu.log"
            $cpuRunnerPath = "D:\Docker\JKAI\intelligence\protocols\run_ollama_cpu.ps1"
            $ollamaCpu = Start-Process "powershell.exe" -ArgumentList "-NoProfile -NoExit -ExecutionPolicy Bypass -File `"$cpuRunnerPath`" -LogPath `"$cpuLogPath`"" -WindowStyle Minimized -PassThru
            if ($ollamaCpu) { try { $ollamaCpu.PriorityClass = "BelowNormal" } catch {} }
        }

        Write-KuteLog "Waiting for Ollama endpoints to respond (max 60s)..." "PROCESS"
        $retryCount = 0
        while ($retryCount -lt 12) {
            try {
                $resp1 = Invoke-RestMethod -Uri "http://$OLLAMA_GPU_HOST/api/tags" -Method Get -ErrorAction Stop
                $resp2 = Invoke-RestMethod -Uri "http://$OLLAMA_CPU_HOST/api/tags" -Method Get -ErrorAction Stop
                if ($resp1 -and $resp2) {
                    Write-KuteLog "Ollama Dual-Engine services are READY!" "SUCCESS"
                    
                    # 🚀 [ACTIVE-MODEL-PRELOADER]: Nạp sẵn toàn bộ Active Model từ rule_hardware.md vào VRAM/RAM ngay khi khởi động
                    Write-KuteLog "Parsing rule_hardware.md to preload active models..." "PROCESS"
                    if (Test-Path $RULE_FILE) {
                        $ruleLines = Get-Content $RULE_FILE
                        $modelMap = @{}
                        foreach ($rline in $ruleLines) {
                            if ($rline -match '^\|\s*([A-Z_]+)\s*\|\s*([a-zA-Z0-9\.\:\_-]+)\s*\|\s*\*\*([^\*]+)\*\*') {
                                $rRole = $matches[1].Trim()
                                $rModel = $matches[2].Trim()
                                $rHw = $matches[3].Trim()
                                if ($rModel -ne "auto" -and $rModel -ne "Active Model" -and $rModel -ne "sdxl-turbo-rocm" -and $rModel -ne "faster-whisper") {
                                    $rHost = if ($rHw -match "CPU") { $OLLAMA_CPU_HOST } else { $OLLAMA_GPU_HOST }
                                    if (-not $modelMap.ContainsKey($rModel)) {
                                        $modelMap[$rModel] = [PSCustomObject]@{ model = $rModel; roles = @($rRole); host = $rHost; hw = $rHw }
                                    } else {
                                        $modelMap[$rModel].roles += $rRole
                                    }
                                }
                            }
                        }

                        $uniqueModels = $modelMap.Values
                        Write-KuteLog "Discovered $($uniqueModels.Count) unique active model(s) for preloading." "PROCESS"
                        $idx = 1
                        foreach ($m in $uniqueModels) {
                            $roleList = $m.roles -join ", "
                            $targetName = if ($m.hw -match "CPU") { "CPU RAM (11435)" } else { "GPU VRAM (11434)" }
                            Write-KuteLog "[$idx/$($uniqueModels.Count)] Preloading model '$($m.model)' [$roleList] into $targetName..." "PROCESS"
                            $sw = [System.Diagnostics.Stopwatch]::StartNew()
                            try {
                                if ($m.model -match "embed") {
                                    $bodyObj = @{ model = $m.model; prompt = "warmup"; keep_alive = -1 } | ConvertTo-Json
                                    $endpointUrl = "http://$($m.host)/api/embeddings"
                                } else {
                                    $bodyObj = @{ model = $m.model; prompt = ""; keep_alive = -1; stream = $false } | ConvertTo-Json
                                    $endpointUrl = "http://$($m.host)/api/generate"
                                }
                                $res = Invoke-RestMethod -Uri $endpointUrl -Method Post -Body $bodyObj -ContentType "application/json" -TimeoutSec 60 -ErrorAction Stop
                                $sw.Stop()
                                Write-KuteLog "Model '$($m.model)' loaded successfully into $targetName ($([math]::Round($sw.Elapsed.TotalSeconds, 1))s)." "SUCCESS"
                            } catch {
                                $sw.Stop()
                                Write-KuteLog "Model '$($m.model)' preloading triggered/skipped: $($_.Exception.Message)" "WARNING"
                            }
                            $idx++
                        }
                    }
                    break
                }
            } catch {
                Start-Sleep -Seconds 5
                $retryCount++
            }
        }
    }

    # --- 2. DOCKER ENGINE BOOTSTRAP ---
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        $dockerRunning = $false
        try {
            docker info > $null 2>&1
            if ($LASTEXITCODE -eq 0) { $dockerRunning = $true }
        } catch {}

        if (-not $dockerRunning) {
            if (Test-Path $DOCKER_EXE) {
                Write-KuteLog "Starting Docker Engine..." "PROCESS"
                Start-Process $DOCKER_EXE
                $dockerRetry = 0
                while ($dockerRetry -lt 24) {
                    docker info > $null 2>&1
                    if ($LASTEXITCODE -eq 0) {
                        $dockerRunning = $true
                        Write-KuteLog "Docker Engine READY!" "SUCCESS"
                        break
                    }
                    Start-Sleep -Seconds 5
                    $dockerRetry++
                }
            } else {
                Write-KuteLog "Docker Desktop not found at $DOCKER_EXE" "WARNING"
            }
        } else {
            Write-KuteLog "Docker Engine is running." "SUCCESS"
        }

        Write-KuteLog "Starting container ecosystem (docker compose up -d)..." "PROCESS"
        docker compose -f docker-compose.yml up -d --remove-orphans
    } else {
        Write-KuteLog "Docker CLI not found on system!" "WARNING"
    }

    # --- 3. HOST BRIDGE TELEMETRY ---
    $HostBridgePath = "D:\Docker\JKAI\scripts\host_bridge.py"
    if (Test-Path $HostBridgePath) {
        try {
            Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match "host_bridge\.py" } | ForEach-Object {
                Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
            }
        } catch {}
        Start-Process python -ArgumentList "`"$HostBridgePath`"" -WindowStyle Hidden -ErrorAction SilentlyContinue
        Write-KuteLog "Host Bridge Telemetry online on port 9997." "SUCCESS"
    }

    Write-KuteLog "Infrastructure READY. Handing off to AMG v2 Decision Engine..." "SUCCESS"
    exit 0
}
catch {
    Write-KuteLog "Infrastructure bootstrap error: $($_.Exception.Message)" "ERROR"
    exit 1
}
