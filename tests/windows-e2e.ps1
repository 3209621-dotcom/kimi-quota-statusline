#requires -Version 5.1
<#
Windows 真机端到端验收(自动项 + 手动项)。CI 的 windows job 也会跑自动项。

自动项(不需要 Kimi TUI,有 Node 即可):
  A. 真实 spawn 复刻:用本机 Node 照抄 kimi-code status-line-command.ts 的
     spawn(cmd.exe, ['/d','/s','/c', command]) 拉起状态栏,验证带引号路径的
     cmd /S 引号解析 + UTF-8 双向管道 + 首行输出。
  B. 元字符路径压测:把 statusline.py 复制到含 中文/空格/括号/& 的路径,验证
     同一条 spawn 链路不炸(python 自身路径若带空格也一并被真实覆盖)。
  C. detached 刷新:伪造大 wire.jsonl 触发后台刷新进程,验证不闪窗
     (MainWindowHandle=0)、缓存落盘、锁回收。

手动项(需真实 Kimi TUI,脚本尾部打印清单):
  1. 真实安装 + /reload-tui 后状态栏出现 5h/7d 额度条
  2. 盯 60 秒无黑窗闪过
  3. (可选) swarm 水波动效

用法(Windows Terminal / VS Code 终端):
  pwsh -File tests/windows-e2e.ps1
  # PowerShell 5.1:
  powershell -ExecutionPolicy Bypass -File tests/windows-e2e.ps1
#>

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
$script:FAILED = @()

function Check([string]$name, [bool]$cond) {
    $tag = if ($cond) { 'PASS' } else { 'FAIL' }
    Write-Host "$tag $name"
    if (-not $cond) { $script:FAILED += $name }
}

# ---------- 公共工具 ----------

$PROBE_JS = @'
// 照抄 kimi-code apps/kimi-code/src/tui/utils/status-line-command.ts 的 runStatusLineCommand:
// spawn(cmd.exe, ['/d','/s','/c', command]) + UTF-8 stdin payload + 取 stdout 首行。
// 唯一偏离:stderr 也接了管道,仅为诊断;TUI 是 ignore。
const { spawn } = require('child_process');
const input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const t0 = Date.now();
let child;
try {
  // windowsVerbatimArguments + 整条命令再包一层引号:node 默认 quoting 会把内嵌引号
  // 转成 \" 喂给 cmd,cmd 不认反斜杠转义;verbatim+外包引号与本机 kimi.exe 实跑行为一致
  child = spawn(process.env.ComSpec || 'cmd.exe', ['/d', '/s', '/c', '"' + input.command + '"'], {
    stdio: ['pipe', 'pipe', 'pipe'],
    windowsVerbatimArguments: true,
  });
} catch (e) {
  console.log(JSON.stringify({ code: 'spawn-error', err: String(e) }));
  process.exit(0);
}
let out = '';
let err = '';
child.stdout.setEncoding('utf8');
child.stdout.on('data', (d) => { out += d; });
child.stderr.setEncoding('utf8');
child.stderr.on('data', (d) => { err += d; });
child.on('error', (e) => {
  console.log(JSON.stringify({ code: 'error', err: String(e) }));
  process.exit(0);
});
child.stdin.on('error', () => {});
child.stdin.end(input.payload);
const timer = setTimeout(() => {
  try { child.kill(); } catch (e) {}
  console.log(JSON.stringify({ code: 'timeout', ms: Date.now() - t0 }));
  process.exit(0);
}, 3000);
child.on('close', (code) => {
  clearTimeout(timer);
  console.log(JSON.stringify({
    code: code,
    out: out.split('\n')[0],
    err: err.split('\n')[0],
    ms: Date.now() - t0
  }));
});
'@

function Invoke-Probe([string]$command, [string]$payload) {
    # 通过 node 跑 probe.js,输入输出均走 UTF-8 字节流(避开 PS5.1 控制台编码)
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = (Get-Command node).Source
    $psi.Arguments = '"' + $script:probePath + '"'
    $psi.UseShellExecute = $false
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $p = New-Object System.Diagnostics.Process
    $p.StartInfo = $psi
    [void]$p.Start()
    $inBytes = [System.Text.Encoding]::UTF8.GetBytes(
        (@{ command = $command; payload = $payload } | ConvertTo-Json -Compress))
    $p.StandardInput.BaseStream.Write($inBytes, 0, $inBytes.Length)
    $p.StandardInput.BaseStream.Close()
    if (-not $p.WaitForExit(10000)) { try { $p.Kill() } catch { }; return $null }
    $ms = New-Object System.IO.MemoryStream
    $p.StandardOutput.BaseStream.CopyTo($ms)
    $json = [System.Text.Encoding]::UTF8.GetString($ms.ToArray())
    try { return ($json | ConvertFrom-Json) } catch { return $null }
}

# ---------- 环境准备 ----------

$repoRoot = Split-Path -Parent $PSScriptRoot
$workDir = Join-Path $env:TEMP 'kqs-windows-e2e'
if (Test-Path $workDir) { Remove-Item -Recurse -Force $workDir }
New-Item -ItemType Directory -Force -Path $workDir | Out-Null
$script:probePath = Join-Path $workDir 'probe.js'
Set-Content -Path $script:probePath -Value $PROBE_JS -Encoding UTF8

$env:KIMI_SL_NOCOLOR = '1'   # 纯文本便于断言
$savedUserProfile = $env:USERPROFILE
$savedHome = $env:HOME
# 隔离插件运行时目录;CPython 的 expanduser('~') 在 Windows 上取 USERPROFILE 或 HOME
# (版本/环境而异),两个都指到 fake-home 才稳
$env:USERPROFILE = Join-Path $workDir 'fake-home'
$env:HOME = $env:USERPROFILE

Write-Host "== 环境:repo=$repoRoot  workdir=$workDir"

$py = $null
try { $py = (Get-Command python -ErrorAction Stop).Source } catch { }
Check 'python 可用' ($null -ne $py)
$node = $null
try { $node = (Get-Command node -ErrorAction Stop).Source } catch { }
Check 'node 可用(真实 spawn 复刻依赖)' ($null -ne $node)

if ($null -eq $py -or $null -eq $node) {
    Write-Host '缺少 python 或 node,自动项无法继续,请先安装后重跑。'
    exit 1
}

$payloadCN = '{"model":"K3","cwd":"C:/用户/我的项目","gitBranch":"main","permissionMode":"auto","planMode":false,"contextUsage":0.1,"contextTokens":1000,"maxContextTokens":1048576,"sessionId":"","version":"e2e"}'

# ---------- A. 常规路径真实 spawn ----------

$statusline = Join-Path $repoRoot 'statusline.py'
$cmdA = '"' + $py + '" "' + $statusline + '"'
$rA = Invoke-Probe $cmdA $payloadCN
$okA = ($null -ne $rA -and $rA.code -eq 0 -and $rA.out -like '*AUTO*' -and $rA.out -like '*[1M]*')
Check 'A 常规路径:cmd /d /s /c spawn 出状态栏(code=0 且含 AUTO/[1M])' $okA
if (-not $okA) {
    Write-Host ('  cmd: ' + $cmdA)
    if ($null -ne $rA) { Write-Host ('  code=' + $rA.code + ' out=' + $rA.out + ' err=' + $rA.err) }
}
if ($null -ne $rA -and $rA.ms) {
    Check ('A 耗时 ' + $rA.ms + 'ms < 3000ms(TUI 预算 300ms 的宽松上限)') ([int]$rA.ms -lt 3000)
}

# ---------- B. 元字符路径压测(中文/空格/括号/&) ----------

$stressDir = Join-Path $workDir '我的 项目 (x86) & 测试'
$stressScript = Join-Path $stressDir 'kimi-quota-statusline\statusline.py'
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $stressScript) | Out-Null
Copy-Item $statusline $stressScript -Force
# 运行时 command = TOML 解析后的值:引号包住解释器与脚本路径(安装器 build_command 生成、
# kimi-code 的 TOML 解析器还原后的形态;TOML 转义本身由回归测试锁死)
$cmdB = '"' + $py + '" "' + $stressScript + '"'
$rB = Invoke-Probe $cmdB $payloadCN
$okB = ($null -ne $rB -and $rB.code -eq 0 -and $rB.out -like '*AUTO*' -and
        $rB.out -like '*我的项目*' -and $rB.out -notlike '*Traceback*')
Check 'B 元字符路径(中文+空格+括号+&):spawn 出状态栏且中文目录不乱码' $okB
if (-not $okB) {
    Write-Host ('  cmd: ' + $cmdB)
    if ($null -ne $rB) { Write-Host ('  code=' + $rB.code + ' out=' + $rB.out + ' err=' + $rB.err) }
}

# ---------- C. detached 刷新:不闪窗 + 缓存落盘 ----------

$sid = 'e2e_test_session'
$wireDir = Join-Path $env:USERPROFILE ('.kimi-code\sessions\wd_e2e\' + $sid + '\agents\main')
New-Item -ItemType Directory -Force -Path $wireDir | Out-Null
$line = '{"type":"usage.record","usage":{"inputOther":1,"output":0,"inputCacheRead":0,"inputCacheCreation":0},"time":1}'
$chunk = ([string]::Join("`r`n", (1..5000 | ForEach-Object { $line })) + "`r`n")
$sw = New-Object System.IO.StreamWriter((Join-Path $wireDir 'wire.jsonl'), $false,
    (New-Object System.Text.UTF8Encoding($false)))
try {
    for ($i = 0; $i -lt 40; $i++) { $sw.Write($chunk) }   # 20 万行,保证刷新进程存活 >1s
} finally { $sw.Close() }

$payloadC = '{"model":"K3","cwd":"C:/x","sessionId":"' + $sid + '","version":"e2e"}'
$payloadC | & python $statusline *> $null

$pyName = Split-Path $py -Leaf
$found = $null
for ($i = 0; $i -lt 50 -and $null -eq $found; $i++) {
    Start-Sleep -Milliseconds 100
    $procs = @(Get-CimInstance Win32_Process -Filter "Name='$pyName'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like '*statusline.py --refresh*' })
    if ($procs.Count -gt 0) { $found = $procs[0] }
}
if ($null -ne $found) {
    $gp = Get-Process -Id $found.ProcessId -ErrorAction SilentlyContinue
    Check 'C detached 刷新进程:存活且无窗口(MainWindowHandle=0,不闪窗)' (
        $null -ne $gp -and $gp.MainWindowHandle -eq 0)
} else {
    Check 'C detached 刷新进程:存活且无窗口(MainWindowHandle=0,不闪窗)' $false
    Write-Host '  未抓到 --refresh 子进程(可能秒退);缓存断言仍会兜底判定'
}

$cache = Join-Path $env:USERPROFILE '.kimi-code\statusline-tokens.json'
$cacheOk = $false
for ($i = 0; $i -lt 60 -and -not $cacheOk; $i++) {
    Start-Sleep -Milliseconds 500
    if (Test-Path $cache) {
        try {
            $d = Get-Content $cache -Raw -Encoding UTF8 | ConvertFrom-Json
            $entry = $null
            if ($d.sessions) { $entry = $d.sessions.PSObject.Properties[$sid].Value }
            if ($null -ne $entry -and $entry.tokens -eq 200000) { $cacheOk = $true }
        } catch { }
    }
}
Check 'C 刷新进程完成:缓存落盘且会话 token=200000' $cacheOk

$lock = Join-Path $env:USERPROFILE '.kimi-code\statusline-refresh.lock'
Start-Sleep -Seconds 2
Check 'C 刷新锁回收(LOCK 文件删除)' (-not (Test-Path $lock))

$env:USERPROFILE = $savedUserProfile
$env:HOME = $savedHome

# ---------- 收尾 ----------

Write-Host ''
Write-Host '==== 手动项(需真实 Kimi TUI,自动项跑完后照做) ===='
Write-Host '1. 真实安装:在本目录运行  python install.py  (写入真实 ~\.kimi-code\tui.toml)'
Write-Host '   然后在 Kimi TUI 里运行 /reload-tui,确认底部出现 5h/7d 额度条、权限模式、git 分支'
Write-Host '2. 盯 60 秒:状态栏每秒刷新期间不得有黑色控制台窗口闪过'
Write-Host '3. (可选)进入 swarm 模式,看品牌蓝水波动效;退出后标记收敛为静态蓝标'
Write-Host '4. 卸载还原:python uninstall.py 后再 /reload-tui,恢复默认状态栏'
Write-Host '5. 若开着 0.36.0 实验性全屏模式(KIMI_CODE_TUI_FULL_SCREEN=1),顺手扫一眼状态栏渲染'
Write-Host ''

Remove-Item -Recurse -Force $workDir -ErrorAction SilentlyContinue

if ($script:FAILED.Count -gt 0) {
    Write-Host ('FAILED: ' + ($script:FAILED -join ' | '))
    exit 1
}
Write-Host '自动项全部通过;手动项结果请人工确认。'
exit 0
