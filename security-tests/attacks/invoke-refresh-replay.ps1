[CmdletBinding()]
param(
    [string]$BaseUrl = "http://localhost:8000",
    [string]$AdminEmail = "demo.admin@simpagent.test",
    [string]$AdminPassword = "ThayDoiMatKhauDemoAdmin123"
)

Set-StrictMode -Version Latest
$commonPath = Join-Path $PSScriptRoot "..\lib\phase6-common.ps1"
. $commonPath

$userSession = New-Phase6Session -BaseUrl $BaseUrl
$adminSession = New-Phase6Session -BaseUrl $BaseUrl

try {
    $email = New-Phase6Email -Prefix "phase6-replay"
    $password = "MatKhauReplayPhase6123"
    Register-Phase6User -Session $userSession -Email $email -Password $password | Out-Null
    $login = Login-Phase6User -Session $userSession -Email $email -Password $password

    $rotateCorrelationId = New-Phase6CorrelationId -Prefix "corr-p6-refresh-rotate"
    $replayCorrelationId = New-Phase6CorrelationId -Prefix "corr-p6-refresh-replay"

    $rotated = Invoke-Phase6RefreshSession `
        -Session $userSession `
        -RefreshToken $login.RefreshToken `
        -CsrfToken $login.CsrfToken `
        -CorrelationId $rotateCorrelationId

    Assert-Phase6Status -Response $rotated.Response -ExpectedStatus 200 -Message "Refresh rotation should succeed before replay"
    Assert-Phase6True -Condition ($rotated.RefreshToken -ne $login.RefreshToken) -Message "Refresh rotation did not issue a new refresh token."

    $replay = Invoke-Phase6RefreshSession `
        -Session $userSession `
        -RefreshToken $login.RefreshToken `
        -CsrfToken $login.CsrfToken `
        -CorrelationId $replayCorrelationId

    Assert-Phase6Status -Response $replay.Response -ExpectedStatus 401 -Message "Refresh-token replay should be rejected"
    Assert-Phase6True -Condition ($replay.Response.Json.error.code -eq "session_invalid") -Message "Replay should fail with session_invalid."

    $familyRevoked = Invoke-Phase6RefreshSession `
        -Session $userSession `
        -RefreshToken $rotated.RefreshToken `
        -CsrfToken $rotated.CsrfToken `
        -CorrelationId (New-Phase6CorrelationId -Prefix "corr-p6-refresh-after-replay")

    Assert-Phase6Status -Response $familyRevoked.Response -ExpectedStatus 401 -Message "Refresh family should be revoked after replay"

    $adminLogin = Login-Phase6User `
        -Session $adminSession `
        -Email $AdminEmail `
        -Password $AdminPassword `
        -CorrelationId (New-Phase6CorrelationId -Prefix "corr-p6-admin-login")

    $event = Find-Phase6SecurityEventByCorrelationId `
        -Session $adminSession `
        -AccessToken $adminLogin.AccessToken `
        -CorrelationId $replayCorrelationId

    Assert-Phase6True -Condition ($event.event_type -eq "refresh_reuse") -Message "Replay should create a refresh_reuse security event."

    [pscustomobject]@{
        name = "refresh-replay"
        status = "passed"
        evidence = [ordered]@{
            email = $email
            replay_correlation_id = $replayCorrelationId
            rotated_refresh_changed = ($rotated.RefreshToken -ne $login.RefreshToken)
            replay_status = $replay.Response.StatusCode
            family_status_after_replay = $familyRevoked.Response.StatusCode
            security_event = $event.event_type
        }
    }
}
finally {
    Close-Phase6Session -Session $userSession
    Close-Phase6Session -Session $adminSession
}
