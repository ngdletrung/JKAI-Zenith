# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: Zenith_Guardian.ps1
# - Role: System Startup, Warmup, & Proactive Priority Watchdog
# - Ownership: Mr LeeTrung
# - Status: Active | Version: SDS v20.0 (AMD RX 6600 Optimized)
# [WORKING PRINCIPLES]:
# 1. Manages Dual-Engine Ollama service lifecycles (GPU on 11434, CPU on 11435).
# 2. Synchronizes models from rule_hardware.md dynamically.
# 3. Restricts process PriorityClass to BelowNormal to prevent system lag.
# 4. No emojis are used in the code or system configurations.
# -----------------------------------------------------------------------------
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues['*:Encoding'] = 'utf8'
chcp 65001 | Out-Null

# --- 0. THIET LAP MOI TRUONG VULKAN (RX 6600 - Windows Native) ---
Set-Location "D:\Docker\JKAI"
# Vulkan vars - dung cho Windows (KHONG phai ROCm, ROCm chi chay tren Linux)
$env:GGML_VK_VISIBLE_DEVICES  = "0"    # Vulkan GPU index
$env:OLLAMA_LLM_LIBRARY       = ""     # De Ollama tu chon backend (se chon vulkan)
$env:OLLAMA_KEEP_ALIVE        = "-1"   # Se bi ghi de boi rule_hardware.md


$RULE_FILE = "D:\Docker\JKAI\intelligence\rule_hardware.md"

# --- 0.1 THAU THI CAU HINH PHAN CUNG (SINGLE SOURCE OF TRUTH) ---
# Doc cau hinh tu rule_hardware.md khoi [OLLAMA_ENVIRONMENT]
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

# Tiêm biến Global vào hệ thống
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
    Write-Host "[$time] $icon $msg" -ForegroundColor $color
    "[$time] $icon $msg" | Out-File -FilePath $LOG_FILE -Append -Encoding utf8
}

try {
    # 0.5. THIET LAP DO UU TIEN OLLAMA TRONG REGISTRY (HKLM)
    # Dat CpuPriorityClass = 5 (BelowNormal) de toi uu bang thong CPU, tranh nghen giao dien web.
    # Note: IFEO setting for PerfOptions is only read from HKEY_LOCAL_MACHINE (HKLM).
    $ifeoPath = "HKLM:\Software\Microsoft\Windows NT\CurrentVersion\Image File Execution Options"
    try {
        foreach ($exe in @("ollama.exe", "ollama_llama_server.exe", "llama-server.exe")) {
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

    # 0.6. TRI HOAN KICH HOAT BO THEO DOI DO UU TIEN CHU DONG (DEFERRED PRIORITY WATCHER)
    # Tri hoan de cac tien trinh Ollama co the nap model o do uu tien Normal nhanh nhat, khong bi nghen thua Master
    Write-KuteLog "Tri hoan Bo theo doi Do uu tien chu dong cho den khi hoan tat nap model..." "SUCCESS"


    # 1. DON DEP TIEN TRINH CU
    Write-KuteLog "Dang giai phong vung nho no-ron... (^_^)" "PROCESS"

    # Kill cac cua so PowerShell cu dang chay runner scripts (tranh trung cua so moi lan restart)
    Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe'" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -match "run_ollama_gpu\.ps1" -or $_.CommandLine -match "run_ollama_cpu\.ps1"
    } | ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }

    # Kill tat ca tien trinh Ollama va llama-server
    Get-Process "ollama*", "llama-server*" -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 3

    $portCheckGPU = Get-NetTCPConnection -LocalPort 11434 -ErrorAction SilentlyContinue
    if ($portCheckGPU) { Stop-Process -Id $portCheckGPU.OwningProcess -Force -ErrorAction SilentlyContinue }
    $portCheckCPU = Get-NetTCPConnection -LocalPort 11435 -ErrorAction SilentlyContinue
    if ($portCheckCPU) { Stop-Process -Id $portCheckCPU.OwningProcess -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 2

    # 2. KICH HOAT OLLAMA SERVER (DUAL-ENGINE)
    Write-KuteLog "Kich hoat He thong Ollama Vulkan v34.0 (Dual-Engine Singularity)..." "PROCESS"
    
    # --- DONG CO 1: GPU VRAM ENGINE (Vulkan) ---
    # Set env cho GPU engine TRUOC khi Start-Process (Start-Process ke thua env hien tai)
    $env:OLLAMA_HOST              = $OLLAMA_GPU_HOST
    $env:GGML_VK_VISIBLE_DEVICES  = "0"
    $env:OLLAMA_LLM_LIBRARY       = ""      # De Ollama tu chon vulkan
    $env:OLLAMA_NO_GPU            = ""      # Dam bao GPU duoc phep dung
    foreach ($k in $gpuEnv.Keys) { Set-Item -Path "Env:$k" -Value $gpuEnv[$k] }
    Write-KuteLog "-> Khoi dong GPU Engine (Vulkan) tren $OLLAMA_GPU_HOST..." "PROCESS"
    # Cua so monitor GPU: hien thi output Ollama, thu xuong taskbar
    $gpuLogPath = "D:\Docker\JKAI\intelligence\protocols\ollama_gpu.log"
    $gpuRunnerPath = "D:\Docker\JKAI\intelligence\protocols\run_ollama_gpu.ps1"
    $ollamaGpu = Start-Process "powershell.exe" -ArgumentList "-NoProfile -NoExit -ExecutionPolicy Bypass -File `"$gpuRunnerPath`" -LogPath `"$gpuLogPath`"" -WindowStyle Minimized -PassThru
    if ($ollamaGpu) { try { $ollamaGpu.PriorityClass = "BelowNormal" } catch {} }

    # --- DONG CO 2: CPU RAM ENGINE ---
    # Xoa GPU-specific vars de tranh leak sang CPU engine
    foreach ($k in $gpuEnv.Keys) {
        if (-not $cpuEnv.ContainsKey($k)) {
            Remove-Item -Path "Env:$k" -ErrorAction SilentlyContinue
        }
    }
    # Reset env cho CPU engine (QUAN TRONG: phai set lai truoc Start-Process thu 2)
    $env:OLLAMA_HOST             = $OLLAMA_CPU_HOST
    $env:GGML_VK_VISIBLE_DEVICES = ""      # CPU engine khong dung Vulkan
    $env:OLLAMA_LLM_LIBRARY      = ""      # De Ollama chon CPU backend
    $env:OLLAMA_NO_GPU           = "1"     # Bat buoc CPU-only
    foreach ($k in $cpuEnv.Keys) { Set-Item -Path "Env:$k" -Value $cpuEnv[$k] }
    Write-KuteLog "-> Khoi dong CPU Engine tren $OLLAMA_CPU_HOST..." "PROCESS"
    $cpuLogPath = "D:\Docker\JKAI\intelligence\protocols\ollama_cpu.log"
    $cpuRunnerPath = "D:\Docker\JKAI\intelligence\protocols\run_ollama_cpu.ps1"
    $ollamaCpu = Start-Process "powershell.exe" -ArgumentList "-NoProfile -NoExit -ExecutionPolicy Bypass -File `"$cpuRunnerPath`" -LogPath `"$cpuLogPath`"" -WindowStyle Minimized -PassThru
    if ($ollamaCpu) { try { $ollamaCpu.PriorityClass = "BelowNormal" } catch {} }

    # [OFFLINE-AFFINITY]: Tam dung can thiep phan cung theo y chi Master de tranh treo Windows.
    # Windows se tu dieu phoi phan cung thưa Master.

    Write-KuteLog "Cho phan hoi tu Intelligence Core (Toi da 60s)..." "WARNING"
    $retryCount = 0
    while ($retryCount -lt 12) {
        try {
            $resp1 = Invoke-RestMethod -Uri "http://$OLLAMA_GPU_HOST/api/tags" -Method Get -ErrorAction Stop
            $resp2 = Invoke-RestMethod -Uri "http://$OLLAMA_CPU_HOST/api/tags" -Method Get -ErrorAction Stop
            if ($resp1 -and $resp2) { 
                Write-KuteLog "Intelligence Core (Dual-Engine) da SAN SANG! (^_^)" "SUCCESS"
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
    $EliteRoles = @("EMBEDDER", "RECEPTIONIST", "CHAT", "SUMMARIZER", "DISPATCHER", "CRITIC", "PLANNER", "CRITIC_ALPHA", "CRITIC_BETA", "DATA_SCOUT", "EXECUTOR_ALPHA", "EXECUTOR_BETA", "EXECUTOR", "RESERVE_AGENT", "COMPRESSOR", "VISION", "VOICE", "TRANSLATOR", "GRAPHIC_MASTER", "RECEPT_ASK_USER", "CICE")
    $content = Get-Content $RULE_FILE
    $missions = @{}
    $isInTargetSection = $false
    # Khoi tao chi so cot de tranh loi null index thua Master
    $H_Role = $H_Model = $H_HW = $H_GPU = $H_CTX = $H_Temp = $H_KA = $H_Thread = -1

    foreach ($line in $content) {
        $line = $line.Trim()
        if ($line -match "3.\s+Active\s+Role\s+Mapping") { $isInTargetSection = $true; continue }
        if ($isInTargetSection -and $line -match "^#") { $isInTargetSection = $false; continue }

        if ($isInTargetSection -and $line -match "^\|") {
            $parts = $line.Split("|") | ForEach-Object { $_.Trim().Replace('*', '').Replace('`', '') }
            if ($parts.Contains("Role")) {
                $H_Role = [array]::IndexOf($parts, "Role")
                $H_Model = [array]::IndexOf($parts, "Active Model")
                $H_HW = [array]::IndexOf($parts, "Hardware")
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
                    
                    $hw = if ($H_HW -ge 0) { $parts[$H_HW].ToUpper() } else { "CPU/RAM" }
                    $gpu = if ($H_GPU -ge 0 -and $parts[$H_GPU] -match '\d+') { [int]$matches[0] } else { 0 }
                    $ctx = if ($H_CTX -ge 0 -and $parts[$H_CTX] -match '\d+') { [int]$matches[0] } else { 4096 }
                    $temp = if ($H_Temp -ge 0 -and $parts[$H_Temp] -match '[\d.]+') { [float]$matches[0] } else { 0.7 }
                    $ka = if ($H_KA -ge 0 -and $parts[$H_KA] -match '^-1') { -1 } else { $raw = $parts[$H_KA]; if ($raw -match '^\d+$') { [int]$raw } else { $raw } }
                    $thread = if ($H_Thread -ge 0 -and $parts[$H_Thread] -match '\d+') { [int]$matches[0] } else { 0 }

                    if ($H_Role -ge 0 -and -not $missions.ContainsKey($mName)) { 
                        $missions[$mName] = @{ ctx = $ctx; temp = $temp; gpu = $gpu; hw = $hw; ka = $ka; role = $role; thread = $thread } 
                    }
                    else {
                        # [GPU-PRIORITY]: Neu mot model duoc gan ca GPU va CPU, uu tien GPU thua Master
                        if ($hw -match "GPU") { 
                            $missions[$mName].hw = "GPU"
                            $missions[$mName].gpu = 100 
                        }
                        if ($ctx -gt $missions[$mName].ctx) { $missions[$mName].ctx = $ctx }
                        if ($thread -gt $missions[$mName].thread) { $missions[$mName].thread = $thread }
                    }
                }
            }
        }
    }

    # 4. TRIEU HOI QUAN DOAN
    Write-KuteLog "Bat dau quy trinh trieu hoi Quan doan No-ron (GPU First)..." "PROCESS"

    # [PRE-WARMUP FLUSH]: Giai phong toan bo VRAM/RAM truoc khi load theo thu tu moi
    # Unload tat ca model dang loaded tren ca 2 engine qua API keep_alive=0
    Write-KuteLog "Dang flush sach VRAM/RAM truoc khi nap Quan doan..." "PROCESS"
    foreach ($engineHost in @($OLLAMA_GPU_HOST, $OLLAMA_CPU_HOST)) {
        try {
            $psResp = Invoke-RestMethod -Uri "http://$engineHost/api/ps" -Method Get -ErrorAction SilentlyContinue
            if ($psResp -and $psResp.models) {
                foreach ($loadedModel in $psResp.models) {
                    $unloadBody = @{ model = $loadedModel.name; keep_alive = 0 } | ConvertTo-Json -Compress
                    Invoke-RestMethod -Uri "http://$engineHost/api/generate" -Method Post -Body $unloadBody -ContentType "application/json" -TimeoutSec 10 -ErrorAction SilentlyContinue | Out-Null
                    Write-KuteLog "   Unload: $($loadedModel.name) khoi $engineHost" "PROCESS"
                }
            }
        } catch {}
    }
    # Kill cac llama-server con lai de dam bao VRAM/RAM sach hoan toan
    Get-Process "llama-server" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Write-KuteLog "VRAM/RAM da duoc giai phong. San sang nap Quan doan." "SUCCESS"

    $modelSizes = @{}
    try {
        $tagsResp = Invoke-RestMethod -Uri "http://$OLLAMA_CPU_HOST/api/tags" -Method Get -ErrorAction SilentlyContinue
        if ($tagsResp -and $tagsResp.models) {
            foreach ($mItem in $tagsResp.models) {
                $modelSizes[$mItem.name] = $mItem.size
                if ($mItem.name -match ":latest$") {
                    $cleanName = $mItem.name.Replace(":latest", "")
                    $modelSizes[$cleanName] = $mItem.size
                }
            }
        }
    }
    catch {
        Write-KuteLog "Khong the lay thong tin kich thuoc model tu api tags, se dung uoc luong." "WARNING"
    }

    function Get-ModelSize($name) {
        if ($modelSizes.ContainsKey($name)) { return $modelSizes[$name] }
        $noTag = $name.Split(":")[0]
        if ($modelSizes.ContainsKey($noTag)) { return $modelSizes[$noTag] }
        
        if ($name -match "qwen3.5") { return 20GB }
        if ($name -match "phi4") { return 10GB }
        if ($name -match "moondream") { return 5GB }
        if ($name -match "nomic") { return 1GB }
        if ($name -match "qwen3") { return 1GB }
        return 0
    }

    [string[]]$gpuModels = @($missions.Keys | Where-Object { $missions[$_].hw -match "GPU" } | Sort-Object)
    [string[]]$cpuModels = @($missions.Keys | Where-Object { $missions[$_].hw -match "CPU" } | Sort-Object { Get-ModelSize $_ })
    [string[]]$sortedModels = $gpuModels + $cpuModels

    foreach ($name in $sortedModels) {
        if (-not $name) { continue }
        $m = $missions[$name]
        $role = $m.role
        # [ON-DEMAND-SKIP]: keep_alive=0 = on-demand, ko pre-load, de tranh load roi unload ngay
        if ($m.ka -eq 0) { Write-KuteLog "   BO QUA $role ($name): keep_alive=0 (on-demand)." "PROCESS"; continue }
        $gpuInfo = if ($m.gpu -gt 0) { "GPU ($($m.gpu) layers)" } else { "CPU" }
        Write-KuteLog "Dang load model $role ($name) -> $gpuInfo..." "PROCESS"
        
        $isEmbed = $name -match "embed" -or $name -match "minilm"
        $targetHost = if ($m.hw -match "GPU") { $OLLAMA_GPU_HOST } else { $OLLAMA_CPU_HOST }
        $apiPath = if ($isEmbed) { "embeddings" } else { "generate" }
        $targetApi = "http://${targetHost}/api/${apiPath}"
        
        $opts = @{}
        if ($null -ne $m.gpu) { $opts.Add("num_gpu", [int]$m.gpu) }
        if ($null -ne $m.ctx) { $opts.Add("num_ctx", [int]$m.ctx) }
        if ($null -ne $m.thread -and $m.thread -gt 0) { $opts.Add("num_thread", [int]$m.thread) }
        if ($null -ne $m.temp) { $opts.Add("temperature", [float]$m.temp) }

        # [LOAD & KEEP]: Load model voi prompt toi thieu de Ollama allocate VRAM + KV cache
        # Ollama can prompt de chay allocate context. Khong truyen prompt = model co the bi bo qua.
        # Prompt "." la toi thieu, sinh 1 token, dam bao model duoc giu trong VRAM.
        $body = @{ model = $name; options = $opts; keep_alive = $m.ka }
        if ($isEmbed) {
            $body.Add("prompt", "warmup") | Out-Null
        } else {
            $body.Add("prompt", ".") | Out-Null
        }

        $jsonBody = $body | ConvertTo-Json -Compress
        try {
            $resp = Invoke-RestMethod -Uri $targetApi -Method Post -Body $jsonBody -ContentType "application/json" -TimeoutSec 120
            Write-KuteLog "   >> $role ($name) KICH HOAT THANH CONG !" "SUCCESS"
        }
        catch {
            Write-KuteLog "   XX Loi khi trieu hoi $role ($name): $($_.Exception.Message)" "ERROR"
        }
        # Delay giua cac GPU model de Ollama can bang VRAM
        if ($m.hw -match "GPU") { Start-Sleep -Seconds 2 }
    }

    # 5. KICH HOAT DOCKER ENGINE
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        $dockerRunning = $false
        try {
            & docker info > $null 2>&1
            if ($LASTEXITCODE -eq 0) { $dockerRunning = $true }
        } catch {}

        if (-not $dockerRunning) {
            if (Test-Path $DOCKER_EXE) {
                Write-KuteLog "Khoi chay Docker Engine cho cac dac vu Docker..." "PROCESS"
                Start-Process $DOCKER_EXE
                
                $dockerRetry = 0
                while ($dockerRetry -lt 24) {
                    & docker info > $null 2>&1
                    if ($LASTEXITCODE -eq 0) {
                        $dockerRunning = $true
                        Write-KuteLog "Docker Engine da SAN SANG!" "SUCCESS"
                        break
                    }
                    Start-Sleep -Seconds 5
                    $dockerRetry++
                }
            } else {
                Write-KuteLog "Docker daemon chua chay va khong tim thay Docker Desktop tai $DOCKER_EXE" "WARNING"
            }
        } else {
            Write-KuteLog "Docker Engine dang hoat dong." "SUCCESS"
        }

        Write-KuteLog "Kich hoat toan bo He sinh thai (docker compose up -d)..." "PROCESS"
        & docker compose -f docker-compose.yml up -d --remove-orphans
    } else {
        Write-KuteLog "Khong tim thay lenh docker tren he thong!" "ERROR"
    }
    
    # 5.5 SOVEREIGN HEALTH AUDIT (KIEM TOAN NO-RON)
    Write-KuteLog "Dang tien hanh Kiem toan No-ron (Sovereign Health Audit)..." "PROCESS"
    Start-Sleep -Seconds 5 # Cho phep Ollama on dinh sau khi load
    
    $auditSuccess = $true
    $gpuReality = Invoke-RestMethod -Uri "http://$OLLAMA_GPU_HOST/api/ps" -Method Get
    $cpuReality = Invoke-RestMethod -Uri "http://$OLLAMA_CPU_HOST/api/ps" -Method Get
    
    $loadedGpuModels = if ($gpuReality.models) { $gpuReality.models.name } else { @() }
    $loadedCpuModels = if ($cpuReality.models) { $cpuReality.models.name } else { @() }

    Write-Host "`n--- [ SOVEREIGN HEALTH REPORT ] ---" -ForegroundColor Cyan
    
    foreach ($name in $missions.Keys) {
        $m = $missions[$name]
        $role = $m.role
        $isGpuTarget = $m.gpu -gt 0
        
        # [ON-DEMAND-STATUS]: keep_alive=0 = on-demand, MISSING la binh thuong
        if ($m.ka -eq 0) {
            $status = "ON-DEMAND (skip pre-load)"
            $color = "Gray"
            Write-Host "[$role] $name : $status" -ForegroundColor $color
            continue
        }
        
        $status = "MISSING"
        $color = "Red"
        
        if ($isGpuTarget) {
            if ($loadedGpuModels -contains $name) {
                $modelInfo = $gpuReality.models | Where-Object { $_.name -eq $name }
                $actualGpu = if ($null -ne $modelInfo.size_details -and $null -ne $modelInfo.size_details.gpu_layers) { $modelInfo.size_details.gpu_layers } else { -1 }
                if ($actualGpu -gt 0) {
                    $status = "ONLINE (GPU)"
                    $color = "Green"
                } elseif ($actualGpu -eq -1 -and $modelInfo.size_vram -gt 0) {
                    # Ollama API thieu size_details.gpu_layers, check size_vram > 0 = dang dung VRAM
                    $status = "ONLINE (GPU)"
                    $color = "Green"
                } else {
                    $status = "VRAM OVERFLOW (EVICTED TO CPU)"
                    $color = "Yellow"
                    $auditSuccess = $false
                }
            }
        } else {
            if ($loadedCpuModels -contains $name) {
                $status = "ONLINE (CPU)"
                $color = "Green"
            }
        }
        
        if ($status -eq "MISSING") { $auditSuccess = $false }
        Write-Host "[$role] $name : $status" -ForegroundColor $color
    }
    
    if ($auditSuccess) {
        Write-KuteLog "Kiem toan hoan tat: Tat ca Dac vu da vao vi tri chien dau." "SUCCESS"
    } else {
        Write-KuteLog "CANH BAO: Phat hien su co khi load model. Master vui long kiem tra VRAM/RAM." "WARNING"
    }
    Write-Host "------------------------------------`n" -ForegroundColor Cyan

    Write-KuteLog "HE THONG NEURAL SOVEREIGN DA DONGBO TUYET DOI." "SUCCESS"
    
    # 5.6. KICH HOAT BO THEO DOI DO UU TIEN CHU DONG (PROACTIVE PRIORITY WATCHER) AFTER WARMUP
    # Chi ha do uu tien va bat dau watcher khi toan bo model da duoc nap thanh cong len RAM/VRAM
    # Dieu nay dam bao qua trinh nap model dien ra voi 100% cong suat CPU/RAM khong bi nghen thieu Master!
    Write-KuteLog "Dang khoi chay Bo theo doi Do uu tien chu dong va ha do uu tien cac tien trinh xu ly ve BelowNormal..." "PROCESS"
    
    # Don dep bat ky watcher cu nao dang chay de tranh chong dong tai nguyen CPU
    try {
        Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match "Get-Process" -and $_.CommandLine -match "ollama" -and $_.ProcessId -ne $PID } | ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
    } catch {}

    # Chuyen tat ca cac tien trinh hien co ve BelowNormal thieu Master
    Get-Process "ollama*", "llama-server*" -ErrorAction SilentlyContinue | ForEach-Object {
        try { $_.PriorityClass = "BelowNormal" } catch {}
    }

    $WatcherScript = {
        $logPath = "D:\Docker\JKAI\intelligence\protocols\guardian_logs.txt"
        $deadlockCounterGpu = 0
        $deadlockCounterCpu = 0

        while ($true) {
            # 1. Tối ưu ưu tiên tiến trình CPU về BelowNormal
            Get-Process "ollama*", "llama-server*" -ErrorAction SilentlyContinue | Where-Object { $_.PriorityClass -ne "BelowNormal" -and $_.PriorityClass -ne "Idle" } | ForEach-Object {
                try { $_.PriorityClass = "BelowNormal" } catch {}
            }

            # 2. Giao thức Tự Phục Hồi Ngoại Vi (Sovereign Watchdog Resurrection Protocol)
            try {
                $gpuCheck = Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -Method Head -TimeoutSec 5 -UseBasicParsing -ErrorAction SilentlyContinue
                if ($null -ne $gpuCheck -and $gpuCheck.StatusCode -eq 200) { $deadlockCounterGpu = 0 } else { $deadlockCounterGpu += 2 }
            } catch { $deadlockCounterGpu += 2 }

            try {
                $cpuCheck = Invoke-WebRequest -Uri "http://127.0.0.1:11435/api/tags" -Method Head -TimeoutSec 5 -UseBasicParsing -ErrorAction SilentlyContinue
                if ($null -ne $cpuCheck -and $cpuCheck.StatusCode -eq 200) { $deadlockCounterCpu = 0 } else { $deadlockCounterCpu += 2 }
            } catch { $deadlockCounterCpu += 2 }

            # Ngắt và khôi phục khi phát hiện tiến trình kẹt (Deadlock > 120s)
            if ($deadlockCounterGpu -ge 120 -or $deadlockCounterCpu -ge 120) {
                $time = Get-Date -Format "HH:mm:ss"
                "[$time] !! [RESURRECTION PROTOCOL] Phat hien treo cong Ollama (>120s). Kich hoat tu dong phuc hoi tai nguyen..." | Out-File -FilePath $logPath -Append -Encoding utf8
                
                # Khởi tạo chu kỳ giải phẫu và giải phóng luồng kẹt
                Get-Process "ollama*", "llama-server*" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
                Start-Sleep -Seconds 3
                
                # Khôi phục trạng thái
                $deadlockCounterGpu = 0
                $deadlockCounterCpu = 0
                "[$time] >> [RESURRECTION SUCCESS] Da giua phong VRAM/RAM tren Xeon & RX 6600. Trạng thái sẵn sàng khởi nạp lại." | Out-File -FilePath $logPath -Append -Encoding utf8
            }

            Start-Sleep -Seconds 2
        }
    }
    Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoProfile -Command & { $($WatcherScript.ToString()) }" -ErrorAction SilentlyContinue
    Write-KuteLog "Bo theo doi Do uu tien va Giao thuc Tu phuc hoi Ngoai vi da hoat dong ngam thanh cong." "SUCCESS"

    # --- KICH HOAT HOST BRIDGE (TELEMETRY / DESKTOP ACCESS) ---
    $HostBridgePath = "D:\Docker\JKAI\scripts\host_bridge.py"
    if (Test-Path $HostBridgePath) {
        Write-KuteLog "Kich hoat Cam bien Nhip tim (Hardware Telemetry)..." "PROCESS"
        try {
            Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match "host_bridge\.py" } | ForEach-Object {
                Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
            }
        } catch {}
        Start-Process python -ArgumentList "`"$HostBridgePath`"" -WindowStyle Hidden -ErrorAction SilentlyContinue
        Write-KuteLog "Host Bridge Telemetry da duoc khoi chay ngam tren port 9997." "SUCCESS"
    } else {
        Write-KuteLog "Khong tim thay script host_bridge.py tai $HostBridgePath" "WARNING"
    }
    
    Write-Host "`n[OK] DA HOAN TAT QUY TRINH. HE THONG DA ON DINH." -ForegroundColor Green
    Start-Sleep -Seconds 10
    exit
}
catch {
    Write-KuteLog "Gap su co nghiem trong!" "ERROR"
    Write-KuteLog $_.Exception.Message "ERROR"
    pause
}
