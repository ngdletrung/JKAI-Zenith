$c = Get-CimInstance Win32_VideoController | Where-Object { $_.Name -like "*Radeon*" -or $_.Name -like "*AMD*" -or $_.Name -like "*NVIDIA*" } | Select-Object -First 1
if (-not $c) {
    $c = Get-CimInstance Win32_VideoController | Select-Object -First 1
}
$name = $c.Name
$total = [math]::round($c.AdapterRAM / 1MB)
if ($name -like "*6600*" -or $total -eq 4095) {
    $total = 8192
}

# Single combined performance counter query for maximum speed (reduces time from 8s to 1.7s)
$samples = (Get-Counter -Counter '\GPU Adapter Memory(*)\Dedicated Usage', '\GPU Engine(*engtype_3D)\Utilization Percentage' -ErrorAction SilentlyContinue).CounterSamples

# Filter dedicated usage
$used_raw = $samples | Where-Object { $_.Path -like "*dedicated usage*" } | Measure-Object -Property CookedValue -Max | Select-Object -ExpandProperty Maximum
if (-not $used_raw) { $used_raw = 0 }
$used = [math]::round($used_raw / 1MB)

# Filter utilization
$util_raw = $samples | Where-Object { $_.Path -like "*utilization percentage*" } | Measure-Object -Property CookedValue -Sum | Select-Object -ExpandProperty Sum
if (-not $util_raw) { $util_raw = 0 }
$u = [math]::round($util_raw)

# Query Host CPU and RAM
$cpu = [math]::round((Get-CimInstance Win32_Processor).LoadPercentage)
$os = Get-CimInstance Win32_OperatingSystem
$ram = [math]::round((($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / $os.TotalVisibleMemorySize) * 100)

Write-Output "$name, $total, $used, $u, $cpu, $ram"
