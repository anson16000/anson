$dir = "M:\BaiduSyncdisk\单量提升计划\同城配送加盟体系优化版文档包\配送分析系统\anson-main"
$gbk = [System.Text.Encoding]::GetEncoding("GBK")

$files = @(
    "01-一键导入数据.bat",
    "01-一键强制重建.bat",
    "02-一键启动看板.bat",
    "03-运行测试.bat",
    "00-初始化环境.bat",
    "00-bootstrap-environment.bat"
)

foreach ($name in $files) {
    $path = Join-Path $dir $name
    if (Test-Path -LiteralPath $path) {
        $bytes = [System.IO.File]::ReadAllBytes($path)
        $text = $gbk.GetString($bytes)

        # Remove chcp line and any trailing newline
        $pattern = "chcp\s+65001[^\r\n]*\r?\n?"
        $newText = $text -replace $pattern, ""

        if ($text -ne $newText) {
            $newBytes = $gbk.GetBytes($newText)
            [System.IO.File]::WriteAllBytes($path, $newBytes)
            Write-Host "$name - REMOVED chcp line"
        } else {
            Write-Host "$name - already clean"
        }

        # Verify: show first 3 lines
        $verify = $gbk.GetString([System.IO.File]::ReadAllBytes($path))
        $vlines = $verify -split "`r`n"
        Write-Host "  Line1: $($vlines[0])"
        Write-Host "  Line2: $($vlines[1])"
        Write-Host "  Line3: $($vlines[2])"
        Write-Host ""
    }
}
