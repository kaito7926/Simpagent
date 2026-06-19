[CmdletBinding()]
param(
    [string]$BaseUrl = "http://localhost:8000"
)

Set-StrictMode -Version Latest
$commonPath = Join-Path $PSScriptRoot "..\lib\phase6-common.ps1"
. $commonPath

$ownerSession = New-Phase6Session -BaseUrl $BaseUrl
$attackerSession = New-Phase6Session -BaseUrl $BaseUrl

try {
    $ownerEmail = New-Phase6Email -Prefix "phase6-owner"
    $attackerEmail = New-Phase6Email -Prefix "phase6-attacker"
    $password = "MatKhauBolaPhase6123"

    Register-Phase6User -Session $ownerSession -Email $ownerEmail -Password $password | Out-Null
    Register-Phase6User -Session $attackerSession -Email $attackerEmail -Password $password | Out-Null

    $ownerLogin = Login-Phase6User -Session $ownerSession -Email $ownerEmail -Password $password
    $attackerLogin = Login-Phase6User -Session $attackerSession -Email $attackerEmail -Password $password

    $created = Invoke-Phase6Request `
        -Session $ownerSession `
        -Method "POST" `
        -Path "/api/conversations" `
        -Headers (New-Phase6AuthHeaders -AccessToken $ownerLogin.AccessToken) `
        -Json @{ title = "Owner private conversation" }

    Assert-Phase6Status -Response $created -ExpectedStatus 201 -Message "Owner conversation creation failed"
    $conversationId = [string]$created.Json.id

    $attackerList = Invoke-Phase6Request `
        -Session $attackerSession `
        -Method "GET" `
        -Path "/api/conversations?limit=10" `
        -Headers (New-Phase6AuthHeaders -AccessToken $attackerLogin.AccessToken)

    Assert-Phase6Status -Response $attackerList -ExpectedStatus 200 -Message "Attacker conversation list should be allowed but empty"
    Assert-Phase6True -Condition (@($attackerList.Json.items).Count -eq 0) -Message "Attacker should not see the owner's conversation in list results."

    $retrieve = Invoke-Phase6Request `
        -Session $attackerSession `
        -Method "GET" `
        -Path "/api/conversations/$conversationId" `
        -Headers (New-Phase6AuthHeaders -AccessToken $attackerLogin.AccessToken)

    $append = Invoke-Phase6Request `
        -Session $attackerSession `
        -Method "POST" `
        -Path "/api/conversations/$conversationId/messages" `
        -Headers (New-Phase6AuthHeaders -AccessToken $attackerLogin.AccessToken) `
        -Json @{
            client_message_id = "phase6-attacker-append"
            content = "Cross-user append attempt"
        }

    $retry = Invoke-Phase6Request `
        -Session $attackerSession `
        -Method "POST" `
        -Path "/api/conversations/$conversationId/messages/phase6-attacker-append/retry" `
        -Headers (New-Phase6AuthHeaders -AccessToken $attackerLogin.AccessToken)

    $delete = Invoke-Phase6Request `
        -Session $attackerSession `
        -Method "DELETE" `
        -Path "/api/conversations/$conversationId" `
        -Headers (New-Phase6AuthHeaders -AccessToken $attackerLogin.AccessToken)

    $undo = Invoke-Phase6Request `
        -Session $attackerSession `
        -Method "POST" `
        -Path "/api/conversations/$conversationId/undo-delete" `
        -Headers (New-Phase6AuthHeaders -AccessToken $attackerLogin.AccessToken)

    foreach ($response in @($retrieve, $append, $retry, $delete, $undo)) {
        Assert-Phase6Status -Response $response -ExpectedStatus 404 -Message "Cross-user BOLA request should fail closed with 404"
        Assert-Phase6True -Condition ($response.Json.error.code -eq "conversation_not_found") -Message "BOLA denial should return conversation_not_found."
        Assert-Phase6True -Condition ($response.BodyText -notmatch "Owner private conversation") -Message "BOLA denial leaked the owner's conversation title."
    }

    $ownerReload = Invoke-Phase6Request `
        -Session $ownerSession `
        -Method "GET" `
        -Path "/api/conversations/$conversationId" `
        -Headers (New-Phase6AuthHeaders -AccessToken $ownerLogin.AccessToken)

    Assert-Phase6Status -Response $ownerReload -ExpectedStatus 200 -Message "Owner should still be able to load the conversation after BOLA attempts"
    Assert-Phase6True -Condition ($ownerReload.Json.title -eq "Owner private conversation") -Message "Owner conversation should remain unchanged after attacker probes."

    [pscustomobject]@{
        name = "bola"
        status = "passed"
        evidence = [ordered]@{
            conversation_id = $conversationId
            attacker_statuses = @($retrieve.StatusCode, $append.StatusCode, $retry.StatusCode, $delete.StatusCode, $undo.StatusCode)
            owner_reload_status = $ownerReload.StatusCode
        }
    }
}
finally {
    Close-Phase6Session -Session $ownerSession
    Close-Phase6Session -Session $attackerSession
}
