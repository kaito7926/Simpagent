[CmdletBinding()]
param(
    [string]$BaseUrl = "http://localhost:8000"
)

Set-StrictMode -Version Latest
$commonPath = Join-Path $PSScriptRoot "..\lib\phase6-common.ps1"
. $commonPath

$session = New-Phase6Session -BaseUrl $BaseUrl

try {
    $statusCodes = New-Object System.Collections.Generic.List[int]
    $lastResponse = $null

    foreach ($index in 1..8) {
        $lastResponse = Invoke-Phase6Request `
            -Session $session `
            -Method "POST" `
            -Path "/api/auth/login" `
            -Headers @{ Origin = $script:Phase6Origin } `
            -Json @{
                email = ("phase6-rate-limit-{0}@example.test" -f $index)
                password = "WrongPassword123!"
            }

        $statusCodes.Add([int]$lastResponse.StatusCode)
        if ($lastResponse.StatusCode -eq 429) {
            break
        }
    }

    Assert-Phase6True -Condition ($statusCodes.Contains(429)) -Message "Brute-force probe did not hit Kong rate limiting."
    Assert-Phase6True -Condition (-not $statusCodes.Contains(200)) -Message "Brute-force probe unexpectedly succeeded."

    $remainingHeaderPresent = $false
    foreach ($headerName in @("RateLimit-Remaining", "X-RateLimit-Remaining-Minute")) {
        if ($lastResponse.Headers.ContainsKey($headerName)) {
            $remainingHeaderPresent = $true
            break
        }
    }
    Assert-Phase6True -Condition $remainingHeaderPresent -Message "Rate-limit response did not expose the expected metadata headers."

    [pscustomobject]@{
        name = "brute-force-rate-limit"
        status = "passed"
        evidence = [ordered]@{
            status_codes = @($statusCodes)
            final_status = $lastResponse.StatusCode
            headers = $lastResponse.Headers
        }
    }
}
finally {
    Close-Phase6Session -Session $session
}
