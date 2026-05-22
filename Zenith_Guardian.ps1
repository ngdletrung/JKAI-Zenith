# -----------------------------------------------------------------------------
#   [ JKAI ZENITH: GUARDIAN v33.0 - SINGULARITY SOVEREIGN ]
#   Giao thuc: Tu dong hoa & Dieu phoi (No-Accent Optimized)
# -----------------------------------------------------------------------------
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues['*:Encoding'] = 'utf8'
chcp 65001 | Out-Null

# --- 0. THIET LAP MOI TRUONG ROCm (ULTIMATE OPTIMIZED) ---
Set-Location "D:\Docker\N8N"
$env:HSA_OVERRIDE_GFX_VERSION = "10.3.0"
$env:HIP_VISIBLE_DEVICES = "0"
$env:ROCR_VISIBLE_DEVICES = "0"
$env:OLLAMA_LLM_LIBRARY = "rocm"
$env:OLLAMA_MAX_LOADED_MODELS = "10"       # Giu 10 model hot trong RAM (128GB du suc)
$env:OLLAMA_NUM_PARALLEL = "1"             # Giam tu 4 xuong 2 de chong tran VRAM GPU cho DeepSeek-R1
$env:OLLAMA_KEEP_ALIVE = "-1"              # Giu model trong RAM mai mai (khong tu unload)
$env:OLLAMA_NUM_THREAD = "8"               # Global fallback thread count (Xeon E5-2699 v4)
$env:OPENBLAS_NUM_THREADS = "4"            # Anti-OpenBLAS pool overflow for 44-thread Xeon CPU
$env:OMP_NUM_THREADS = "4"                 # OpenMP thread constraint for stability
$env:OLLAMA_GPU_OVERHEAD = "134217728"
$env:OLLAMA_FLASH_ATTENTION = "1"
# $env:OLLAMA_KV_CACHE_TYPE = "q4_0"
$env:OLLAMA_MODELS = "D:\Docker\Ollama_AI\Ollama_model"
$env:OLLAMA_HOST = "0.0.0.0"

$OLLAMA_GEN_API = "http://127.0.0.1:11434/api/generate"
$OLLAMA_EMB_API = "http://127.0.0.1:11434/api/embeddings"
$RULE_FILE = "D:\Docker\N8N\intelligence\rule_hardware.md"
$LOG_FILE = "D:\Docker\N8N\intelligence\protocols\guardian_logs.txt"
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
    Write-Host "[$time] $icon $msg" -ForegroundColor $color
    "[$time] $icon $msg" | Out-File -FilePath $LOG_FILE -Append -Encoding utf8
}

try {
    # 0.5. THIET LAP DO UU TIEN OLLAMA TRONG REGISTRY (HKLM)
    # Dat CpuPriorityClass = 5 (Below Normal) de luon nhuong quyen cho WSL2/Docker khi bi 100% CPU.
    # Note: IFEO setting for PerfOptions is only read from HKEY_LOCAL_MACHINE (HKLM).
    $ifeoPath = "HKLM:\Software\Microsoft\Windows NT\CurrentVersion\Image File Execution Options"
    try {
        foreach ($exe in @("ollama.exe", "ollama_llama_server.exe")) {
            $exePath = "$ifeoPath\$exe"
            $perfPath = "$exePath\PerfOptions"
            if (-not (Test-Path $exePath)) { New-Item -Path $ifeoPath -Name $exe -Force -ErrorAction Stop | Out-Null }
            if (-not (Test-Path $perfPath)) { New-Item -Path $exePath -Name "PerfOptions" -Force -ErrorAction Stop | Out-Null }
            New-ItemProperty -Path $perfPath -Name "CpuPriorityClass" -Value 5 -PropertyType DWORD -Force -ErrorAction Stop | Out-Null
        }
        Write-KuteLog "Thiet lap do uu tien BelowNormal cho Ollama trong Registry HKLM thanh cong." "SUCCESS"
    }
    catch {
        Write-KuteLog "Loi khi ghi Registry HKLM (Yeu cau Admin): $($_.Exception.Message)" "WARNING"
    }

    # 0.6. KICH HOAT BO THEO DOI DO UU TIEN CHU DONG (PROACTIVE PRIORITY WATCHER)
    # Start a hidden background watcher that checks running ollama processes and forces BelowNormal priority
    # This acts as an iron-clad backup if registry writing fails or new runners are dynamically spawned.
    Write-KuteLog "Kich hoat Bo theo doi Do uu tien chu dong..." "PROCESS"
    $WatcherScript = {
        while ($true) {
            Get-Process "ollama*" -ErrorAction SilentlyContinue | Where-Object { $_.PriorityClass -ne "BelowNormal" -and $_.PriorityClass -ne "Idle" } | ForEach-Object {
                try { $_.PriorityClass = "BelowNormal" } catch {}
            }
            Start-Sleep -Seconds 2
        }
    }
    Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoProfile -Command & { $($WatcherScript.ToString()) }" -ErrorAction SilentlyContinue
    Write-KuteLog "Bo theo doi Do uu tien chu dong da hoat dong ngam." "SUCCESS"

    # 1. DON DEP TIEN TRINH CU
    Write-KuteLog "Dang giai phong vung nho no-ron... (^_^)" "PROCESS"
    Get-Process "ollama*" -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 3

    $portCheck = Get-NetTCPConnection -LocalPort 11434 -ErrorAction SilentlyContinue
    if ($portCheck) {
        Write-KuteLog "Port 11434 van dang bi chiem boi PID $($portCheck.OwningProcess). Dang giai phong..." "WARNING"
        Stop-Process -Id $portCheck.OwningProcess -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }

    # 2. KICH HOAT OLLAMA SERVER
    Write-KuteLog "Kich hoat He thong Ollama ROCm v33.0 (Singularity)..." "PROCESS"
    $ollamaProc = Start-Process "ollama" -ArgumentList "serve" -WindowStyle Minimized -PassThru
    
    # Kich hoat do uu tien thap cho tien trinh vua khoi tao
    if ($ollamaProc) {
        try { $ollamaProc.PriorityClass = "BelowNormal" } catch {}
    }
    
    # [OFFLINE-AFFINITY]: Tam dung can thiep phan cung theo y chi Master de tranh treo Windows.
    # Windows se tu dieu phoi phan cung thưa Master.

    Write-KuteLog "Cho phan hoi tu Intelligence Core (Toi da 60s)..." "WARNING"
    $retryCount = 0
    while ($retryCount -lt 12) {
        try {
            $response = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get -ErrorAction Stop
            if ($response) { 
                Write-KuteLog "Intelligence Core da SAN SANG! (^_^)" "SUCCESS"
                break 
            }
        }
        catch {
            Start-Sleep -Seconds 5
            $retryCount++
        }
    }

    # 3. THAU THI CAU HINH SOVEREIGN
    # [NGUON TRI THUC DUY NHAT]: Dong bo chinh xac voi bang '3. Active Role Mapping' trong rule_hardware.md
    # VOICE (faster-whisper) va GRAPHIC_MASTER (SDXL-ROCm) la External Services - se bi skip tu dong.
    $EliteRoles = @("EMBEDDER", "RECEPTIONIST", "CHAT", "SUMMARIZER", "DISPATCHER", "CRITIC", "PLANNER", "CRITIC_ALPHA", "CRITIC_BETA", "DATA_SCOUT", "EXECUTOR_ALPHA", "EXECUTOR_BETA", "EXECUTOR", "RESERVE_AGENT", "COMPRESSOR", "VISION", "VOICE", "TRANSLATOR", "GRAPHIC_MASTER")
    $content = Get-Content $RULE_FILE
    $missions = @{}
    $isInTargetSection = $false

    foreach ($line in $content) {
        $line = $line.Trim()
        if ($line -match "3.\s+Active\s+Role\s+Mapping") { $isInTargetSection = $true; continue }
        if ($isInTargetSection -and $line -match "^#") { $isInTargetSection = $false; continue }

        if ($isInTargetSection -and $line -match "^\|") {
            $parts = $line.Split("|") | ForEach-Object { $_.Trim().Replace('*', '').Replace('`', '') }
            if ($parts.Contains("Role")) {
                $H_Role = [array]::IndexOf($parts, "Role")
                $H_Model = [array]::IndexOf($parts, "Active Model")
                $H_GPU = [array]::IndexOf($parts, "num_gpu")
                $H_CTX = [array]::IndexOf($parts, "num_ctx")
                $H_Temp = [array]::IndexOf($parts, "Temp")
                $H_KA = [array]::IndexOf($parts, "KEEP_ALIVE")
                $H_Thread = [array]::IndexOf($parts, "num_thread")
                continue
            }
            if ($H_Role -ge 0 -and $H_Model -ge 0 -and $parts[$H_Role] -ne "Role" -and $parts[$H_Role] -notmatch "^:") {
                $role = $parts[$H_Role].ToUpper()
                $mName = $parts[$H_Model]
                
                if ($EliteRoles -contains $role -and $mName -and $mName -ne "n/a") {
                    # [EXTERNAL-SKIP]: Bo qua cac External Services - khong qua Ollama API
                    if ($role -eq "VOICE" -and $mName -match "whisper") { continue }
                    if ($role -eq "GRAPHIC_MASTER" -or $mName -match "SDXL") { continue }
                    $gpu = if ($parts[$H_GPU] -match '\d+') { [int]$matches[0] } else { 0 }
                    $ctx = if ($parts[$H_CTX] -match '\d+') { [int]$matches[0] } else { 2048 }
                    $temp = if ($parts[$H_Temp] -match '[\d.]+') { [float]$matches[0] } else { 0.7 }
                    $ka = if ($parts[$H_KA] -match '^-1') { -1 } else { $parts[$H_KA] }
                    $thread = if ($parts[$H_Thread] -match '\d+') { [int]$matches[0] } else { 0 }

                    if (-not $missions.ContainsKey($mName)) { 
                        $missions[$mName] = @{ ctx = $ctx; temp = $temp; gpu = $gpu; ka = $ka; role = $role; thread = $thread } 
                    }
                    else {
                        if ($gpu -gt $missions[$mName].gpu) { $missions[$mName].gpu = $gpu }
                        if ($ctx -gt $missions[$mName].ctx) { $missions[$mName].ctx = $ctx }
                        if ($thread -gt $missions[$mName].thread) { $missions[$mName].thread = $thread }
                    }
                }
            }
        }
    }

    # 4. TRIEU HOI QUAN DOAN
    Write-KuteLog "Bat dau quy trinh trieu hoi Quan doan No-ron (GPU First)..." "PROCESS"
    
    [string[]]$gpuModels = @($missions.Keys | Where-Object { $missions[$_].gpu -gt 0 } | Sort-Object)
    [string[]]$cpuModels = @($missions.Keys | Where-Object { $missions[$_].gpu -le 0 } | Sort-Object)
    [string[]]$sortedModels = $gpuModels + $cpuModels

    foreach ($name in $sortedModels) {
        if (-not $name) { continue }
        $m = $missions[$name]
        $role = $m.role
        $gpuInfo = if ($m.gpu -gt 0) { "GPU ($($m.gpu) layers)" } else { "CPU" }
        Write-KuteLog "Dang load model $role ($name) -> $gpuInfo..." "PROCESS"
        
        # Thiet lap BelowNormal cho tat ca cac process ollama truoc khi gui request
        Get-Process "ollama*" -ErrorAction SilentlyContinue | ForEach-Object {
            try { $_.PriorityClass = "BelowNormal" } catch {}
        }
        
        $isEmbed = $name -match "embed"
        $targetApi = if ($isEmbed) { $OLLAMA_EMB_API } else { $OLLAMA_GEN_API }
        
        $opts = @{}
        if ($null -ne $m.gpu) { $opts.Add("num_gpu", [int]$m.gpu) }
        if ($null -ne $m.ctx) { $opts.Add("num_ctx", [int]$m.ctx) }
        if ($null -ne $m.thread -and $m.thread -gt 0) { $opts.Add("num_thread", [int]$m.thread) }
        if ($null -ne $m.temp) { $opts.Add("temperature", [float]$m.temp) }

        $body = @{ model = $name; options = $opts; keep_alive = $m.ka }
        if ($isEmbed) { $body.Add("prompt", "warmup") | Out-Null } else { $body.Add("prompt", "hi") | Out-Null; $body.Add("stream", $false) | Out-Null }

        $jsonBody = $body | ConvertTo-Json -Compress
        try {
            $resp = Invoke-RestMethod -Uri $targetApi -Method Post -Body $jsonBody -ContentType "application/json" -TimeoutSec 600
            Write-KuteLog "   >> $role ($name) KICH HOAT THANH CONG !" "SUCCESS"
        }
        catch {
            Write-KuteLog "   XX Loi khi trieu hoi $role ($name): $($_.Exception.Message)" "ERROR"
        }
        
        # Thiet lap lai de dam bao child process (ollama_llama_server.exe) vua sinh ra duoc chuyen ve BelowNormal ngay lap tuc
        Get-Process "ollama*" -ErrorAction SilentlyContinue | ForEach-Object {
            try { $_.PriorityClass = "BelowNormal" } catch {}
        }
        
        if ($m.gpu -gt 0) { Start-Sleep -Seconds 8 } else { Start-Sleep -Seconds 2 }
    }

    # 5. KICH HOAT DOCKER ENGINE
    if (Test-Path $DOCKER_EXE) {
        Write-KuteLog "Khoi chay Docker Engine cho cac dac vu Docker..." "PROCESS"
        Start-Process $DOCKER_EXE
        
        $dockerRetry = 0
        while ($dockerRetry -lt 24) {
            & docker info > $null 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-KuteLog "Docker Engine da SAN SANG!" "SUCCESS"
                break
            }
            Start-Sleep -Seconds 5
            $dockerRetry++
        }
        Write-KuteLog "Kich hoat toan bo He sinh thai (docker compose up -d)..." "PROCESS"
        & docker compose up -d
    }
    
    Write-KuteLog "HE THONG NEURAL SOVEREIGN DA DONGBO TUYET DOI." "SUCCESS"
    Write-KuteLog "Kich hoat Cam bien Nhip tim (Hardware Telemetry)..." "PROCESS"
    
    Write-Host "`n[OK] DA HOAN TAT QUY TRINH. HE THONG DA ON DINH." -ForegroundColor Green
    Start-Sleep -Seconds 5
    exit
}
catch {
    Write-KuteLog "Gap su co nghiem trong!" "ERROR"
    Write-KuteLog $_.Exception.Message "ERROR"
    pause
}
