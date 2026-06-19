[CmdletBinding()]
param(
    [string]$BaseUrl = "http://localhost:8000",
    [switch]$SkipComposeUp,
    [string]$AdminEmail = "demo.admin@simpagent.test",
    [string]$AdminPassword = "ThayDoiMatKhauDemoAdmin123"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$commonPath = Join-Path $PSScriptRoot "lib\phase6-common.ps1"
. $commonPath

$context = $null
$results = @()
$failed = $false

try {
    $context = New-Phase6ComposeContext
    Assert-Phase6DockerEngine
    if (-not $SkipComposeUp) {
        Ensure-Phase6MainStack -Context $context
    }

    $scenarios = @(
        @{ Name = "refresh-replay"; Path = (Join-Path $PSScriptRoot "attacks\invoke-refresh-replay.ps1"); RequiresAdmin = $true },
        @{ Name = "bola"; Path = (Join-Path $PSScriptRoot "attacks\invoke-bola.ps1"); RequiresAdmin = $false },
        @{ Name = "guardrail-abuse"; Path = (Join-Path $PSScriptRoot "attacks\invoke-guardrail-abuse.ps1"); RequiresAdmin = $true },
        @{ Name = "ssrf-internal-reachability"; Path = (Join-Path $PSScriptRoot "attacks\invoke-ssrf-probe.ps1"); RequiresAdmin = $true },
        @{ Name = "python-escape"; Path = (Join-Path $PSScriptRoot "attacks\invoke-python-escape.ps1"); RequiresAdmin = $true },
        @{ Name = "brute-force-rate-limit"; Path = (Join-Path $PSScriptRoot "attacks\invoke-brute-force.ps1"); RequiresAdmin = $false }
    )

    foreach ($scenario in $scenarios) {
        try {
            Invoke-Phase6Compose -Context $context -ProjectName $script:Phase6MainProject -Arguments @("restart", "kong") | Out-Null
            Invoke-Phase6Compose -Context $context -ProjectName $script:Phase6MainProject -Arguments @("up", "--wait", "kong") | Out-Null

            $arguments = @{
                BaseUrl = $BaseUrl
            }
            if ($scenario.RequiresAdmin) {
                $arguments["AdminEmail"] = $AdminEmail
                $arguments["AdminPassword"] = $AdminPassword
            }

            $result = & $scenario.Path @arguments
            $results += $result
            Write-Host ("[PASS] {0}" -f $scenario.Name)
        }
        catch {
            $failed = $true
            $results += [pscustomobject]@{
                name = $scenario.Name
                status = "failed"
                error = $_.Exception.Message
            }
            Write-Host ("[FAIL] {0}: {1}" -f $scenario.Name, $_.Exception.Message)
        }
    }

    $summary = [pscustomobject]@{
        generated_at = (Get-Date).ToString("o")
        base_url = $BaseUrl
        scenarios = $results
    }
    $summaryPath = Write-Phase6SummaryFile -FileName "phase6-attacks-summary.json" -Payload $summary

    Write-Host ""
    Write-Host ("Attack summary written to {0}" -f $summaryPath)

    if ($failed) {
        throw "One or more Phase 6 attack scenarios failed."
    }
}
finally {
    if ($null -ne $context) {
        Remove-Phase6ComposeContext -Context $context
    }
}
