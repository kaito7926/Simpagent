[CmdletBinding()]
param(
    [switch]$SkipComposeUp
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

    Invoke-Phase6Compose -Context $context -ProjectName $script:Phase6TestProject -Arguments @("-f", "compose.test.yaml", "down", "-v") -IgnoreExitCode | Out-Null
    Invoke-Phase6Compose -Context $context -ProjectName $script:Phase6TestProject -Arguments @("-f", "compose.test.yaml", "build", "backend-test") | Out-Null

    $checks = @(
        @{
            Name = "TEST-01 auth session matrix"
            Requirement = "TEST-01"
            Project = $script:Phase6TestProject
            Args = @(
                "-f", "compose.test.yaml",
                "run", "--rm",
                "backend-test",
                "python", "-m", "pytest", "-q",
                "tests/integration/auth/test_registration.py",
                "tests/integration/auth/test_login.py",
                "tests/integration/auth/test_me.py",
                "tests/integration/auth/test_session_flow.py",
                "tests/security/test_jwt_profile.py"
            )
        },
        @{
            Name = "TEST-02 BOLA ownership matrix"
            Requirement = "TEST-02"
            Project = $script:Phase6TestProject
            Args = @(
                "-f", "compose.test.yaml",
                "run", "--rm",
                "backend-test",
                "python", "-m", "pytest", "-q",
                "tests/integration/chat/test_conversation_crud.py",
                "tests/security/test_chat_authorization.py",
                "tests/smoke/test_private_direct_chat.py"
            )
        },
        @{
            Name = "TEST-03 role scope and tool denial matrix"
            Requirement = "TEST-03"
            Project = $script:Phase6TestProject
            Args = @(
                "-f", "compose.test.yaml",
                "run", "--rm",
                "backend-test",
                "python", "-m", "pytest", "-q",
                "tests/integration/admin/test_admin_evidence.py",
                "tests/integration/admin/test_admin_write.py",
                "tests/integration/search/test_search_authz.py",
                "tests/integration/python/test_python_authorization.py"
            )
        },
        @{
            Name = "TEST-04 chat behavior matrix"
            Requirement = "TEST-04"
            Project = $script:Phase6TestProject
            Args = @(
                "-f", "compose.test.yaml",
                "run", "--rm",
                "backend-test",
                "python", "-m", "pytest", "-q",
                "tests/integration/chat/test_message_send.py",
                "tests/security/test_chat_idempotency.py",
                "tests/security/test_chat_provider_failure.py"
            )
        },
        @{
            Name = "TEST-05 search matrix"
            Requirement = "TEST-05"
            Project = $script:Phase6TestProject
            Args = @(
                "-f", "compose.test.yaml",
                "run", "--rm",
                "backend-test",
                "python", "-m", "pytest", "-q",
                "tests/integration/search",
                "tests/security/test_search_guardrails.py",
                "tests/security/test_search_prompt_injection.py",
                "tests/security/test_search_retention_allowlist.py"
            )
        },
        @{
            Name = "TEST-06 sandbox matrix"
            Requirement = "TEST-06"
            Project = $script:Phase6TestProject
            Args = @(
                "-f", "compose.test.yaml",
                "run", "--rm",
                "backend-test",
                "python", "-m", "pytest", "-q",
                "tests/integration/python",
                "tests/security/test_python_network_denial.py",
                "tests/security/test_python_policy_denials.py",
                "tests/security/test_python_side_effects.py",
                "tests/security/test_python_cleanup.py"
            )
        },
        @{
            Name = "TEST-09 side-effect evidence matrix"
            Requirement = "TEST-09"
            Project = $script:Phase6TestProject
            Args = @(
                "-f", "compose.test.yaml",
                "run", "--rm",
                "backend-test",
                "python", "-m", "pytest", "-q",
                "tests/security/test_python_side_effects.py",
                "tests/security/test_search_guardrails.py"
            )
        },
        @{
            Name = "TEST-10 canary secret matrix"
            Requirement = "TEST-10"
            Project = $script:Phase6TestProject
            Args = @(
                "-f", "compose.test.yaml",
                "run", "--rm",
                "backend-test",
                "python", "-m", "pytest", "-q",
                "tests/security/test_secret_leakage.py",
                "tests/security/test_search_secret_leakage.py"
            )
        },
        @{
            Name = "Smoke log redaction"
            Requirement = "TEST-09, TEST-10"
            Project = $script:Phase6MainProject
            Args = @(
                "run", "--rm",
                "-e", "SIMPAGENT_RUN_SMOKE=true",
                "backend",
                "python", "-m", "pytest", "-q",
                "tests/smoke/test_logging_flow.py"
            )
        },
        @{
            Name = "Frontend regression subset"
            Requirement = "supporting-ui"
            Project = $script:Phase6MainProject
            Args = @(
                "run", "--rm",
                "frontend",
                "npm", "test", "--",
                "tests/account-access-oauth.test.tsx",
                "tests/admin-evidence.test.tsx",
                "tests/chat-workspace.test.ts",
                "tests/python-result-card.test.tsx",
                "tests/search-rendering.test.tsx"
            )
        }
    )

    foreach ($check in $checks) {
        $startedAt = Get-Date
        try {
            Invoke-Phase6Compose -Context $context -ProjectName $check.Project -Arguments $check.Args | Out-Null
            $durationSeconds = [Math]::Round(((Get-Date) - $startedAt).TotalSeconds, 2)
            $results += [pscustomobject]@{
                name = $check.Name
                requirement = $check.Requirement
                status = "passed"
                duration_seconds = $durationSeconds
            }
            Write-Host ("[PASS] {0}" -f $check.Name)
        }
        catch {
            $failed = $true
            $durationSeconds = [Math]::Round(((Get-Date) - $startedAt).TotalSeconds, 2)
            $results += [pscustomobject]@{
                name = $check.Name
                requirement = $check.Requirement
                status = "failed"
                duration_seconds = $durationSeconds
                error = $_.Exception.Message
            }
            Write-Host ("[FAIL] {0}: {1}" -f $check.Name, $_.Exception.Message)
        }
    }

    $summary = [pscustomobject]@{
        generated_at = (Get-Date).ToString("o")
        checks = $results
    }
    $summaryPath = Write-Phase6SummaryFile -FileName "phase6-matrix-summary.json" -Payload $summary

    Write-Host ""
    Write-Host ("Matrix summary written to {0}" -f $summaryPath)

    if ($failed) {
        throw "One or more Phase 6 matrix checks failed."
    }
}
finally {
    if ($null -ne $context) {
        Invoke-Phase6Compose -Context $context -ProjectName $script:Phase6TestProject -Arguments @("-f", "compose.test.yaml", "down", "-v") -IgnoreExitCode | Out-Null
        Remove-Phase6ComposeContext -Context $context
    }
}
