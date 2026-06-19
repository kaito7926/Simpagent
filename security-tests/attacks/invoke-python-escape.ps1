[CmdletBinding()]
param(
    [string]$BaseUrl = "http://localhost:8000",
    [string]$AdminEmail = "demo.admin@simpagent.test",
    [string]$AdminPassword = "ThayDoiMatKhauDemoAdmin123"
)

Set-StrictMode -Version Latest
$commonPath = Join-Path $PSScriptRoot "..\lib\phase6-common.ps1"
. $commonPath

$userSession = New-Phase6Session -BaseUrl $BaseUrl -TimeoutSeconds 60
$adminSession = New-Phase6Session -BaseUrl $BaseUrl -TimeoutSeconds 60

try {
    $email = New-Phase6Email -Prefix "phase6-escape"
    $password = "MatKhauEscapePhase6123"
    Register-Phase6User -Session $userSession -Email $email -Password $password | Out-Null
    $userLogin = Login-Phase6User -Session $userSession -Email $email -Password $password
    $correlationId = New-Phase6CorrelationId -Prefix "corr-p6-python-escape"
    $probeContent = [string]::Join(
        "`n",
        @(
            'Chay Python trong sandbox.'
            '```python'
            'import os'
            "os.system('whoami')"
            '```'
        )
    )

    $probe = Invoke-Phase6Request `
        -Session $userSession `
        -Method "POST" `
        -Path "/api/conversations" `
        -Headers (New-Phase6AuthHeaders -AccessToken $userLogin.AccessToken -CorrelationId $correlationId) `
        -Json @{
            initial_message = @{
                client_message_id = "phase6-python-escape"
                tool_mode = "python"
                content = $probeContent
            }
        }

    Assert-Phase6Status -Response $probe -ExpectedStatus 201 -Message "Sandbox escape probe request failed"
    $pythonResult = $probe.Json.messages[1].metadata.python_result
    Assert-Phase6True -Condition ($pythonResult.status -eq "policy_error") -Message "Escape probe should fail with policy_error."
    Assert-Phase6True -Condition ($pythonResult.policy_error_code -eq "disallowed_behavior") -Message "Escape probe should be denied as disallowed_behavior."
    Assert-Phase6True -Condition (@($pythonResult.artifacts).Count -eq 0) -Message "Denied escape probe should not create artifacts."

    $adminLogin = Login-Phase6User `
        -Session $adminSession `
        -Email $AdminEmail `
        -Password $AdminPassword `
        -CorrelationId (New-Phase6CorrelationId -Prefix "corr-p6-admin-login")

    $toolExecution = Find-Phase6ToolExecutionByCorrelationId `
        -Session $adminSession `
        -AccessToken $adminLogin.AccessToken `
        -CorrelationId $correlationId

    Assert-Phase6True -Condition ($toolExecution.tool_name -eq "python") -Message "Escape probe should be recorded as a Python tool execution."
    Assert-Phase6True -Condition ($toolExecution.status -eq "policy_error") -Message "Admin evidence should keep policy_error for escape probe."

    [pscustomobject]@{
        name = "python-escape"
        status = "passed"
        evidence = [ordered]@{
            correlation_id = $correlationId
            python_status = $pythonResult.status
            policy_error_code = $pythonResult.policy_error_code
            tool_execution_status = $toolExecution.status
        }
    }
}
finally {
    Close-Phase6Session -Session $userSession
    Close-Phase6Session -Session $adminSession
}
