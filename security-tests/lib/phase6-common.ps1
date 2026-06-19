Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Net.Http | Out-Null

$script:Phase6Origin = "http://localhost:3000"
$script:Phase6MainProject = "simpagent-phase6"
$script:Phase6TestProject = "simpagent-phase6-test"

function Get-Phase6RepoRoot {
    return [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
}

function Get-Phase6OutputDirectory {
    $path = Join-Path (Get-Phase6RepoRoot) "security-tests\output"
    if (-not (Test-Path -LiteralPath $path)) {
        New-Item -ItemType Directory -Path $path | Out-Null
    }
    return $path
}

function Write-Phase6SummaryFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FileName,
        [Parameter(Mandatory = $true)]
        [object]$Payload
    )

    $path = Join-Path (Get-Phase6OutputDirectory) $FileName
    $Payload | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $path -Encoding utf8
    return $path
}

function Assert-Phase6DockerEngine {
    $null = & docker version --format "{{json .Server}}" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker engine is not available. Start Docker Desktop before running the Phase 6 runners."
    }
}

function New-Phase6ComposeContext {
    $repoRoot = Get-Phase6RepoRoot
    $projectRoot = $repoRoot
    $mappedDrive = $null

    if ($env:OS -eq "Windows_NT") {
        $usedLetters = @{}
        foreach ($drive in Get-PSDrive -PSProvider FileSystem) {
            $usedLetters[$drive.Name.ToUpperInvariant()] = $true
        }

        foreach ($candidate in @("X", "W", "V", "U", "T", "S", "R", "Q")) {
            if ($usedLetters.ContainsKey($candidate)) {
                continue
            }

            $mappedDrive = "$candidate`:"
            & subst $mappedDrive $repoRoot | Out-Null
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to map $mappedDrive to $repoRoot."
            }
            $projectRoot = "$mappedDrive\"
            break
        }

        if ($null -eq $mappedDrive) {
            throw "Unable to reserve a temporary drive letter for Docker Compose."
        }
    }

    return [pscustomobject]@{
        RepoRoot    = $repoRoot
        ProjectRoot = $projectRoot
        MappedDrive = $mappedDrive
    }
}

function Remove-Phase6ComposeContext {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Context
    )

    if ($null -ne $Context.MappedDrive) {
        & subst $Context.MappedDrive /d | Out-Null
    }
}

function Invoke-Phase6Compose {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Context,
        [Parameter(Mandatory = $true)]
        [string]$ProjectName,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [switch]$IgnoreExitCode
    )

    Push-Location -LiteralPath $Context.ProjectRoot
    try {
        & docker compose -p $ProjectName @Arguments
        $exitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }

    if (-not $IgnoreExitCode -and $exitCode -ne 0) {
        throw "docker compose failed for project '$ProjectName' with exit code $exitCode."
    }

    return $exitCode
}

function Ensure-Phase6MainStack {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Context
    )

    Invoke-Phase6Compose -Context $Context -ProjectName $script:Phase6MainProject -Arguments @("up", "--build", "--wait") | Out-Null
}

function New-Phase6Session {
    param(
        [string]$BaseUrl = "http://localhost:8000",
        [int]$TimeoutSeconds = 30
    )

    $handler = [System.Net.Http.HttpClientHandler]::new()
    $handler.UseCookies = $false

    $client = [System.Net.Http.HttpClient]::new($handler)
    $client.BaseAddress = [Uri]$BaseUrl
    $client.Timeout = [TimeSpan]::FromSeconds($TimeoutSeconds)
    $client.DefaultRequestHeaders.TryAddWithoutValidation("Accept", "application/json") | Out-Null

    return [pscustomobject]@{
        Client  = $client
        Handler = $handler
        BaseUri = [Uri]$BaseUrl
    }
}

function Close-Phase6Session {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Session
    )

    if ($null -ne $Session.Client) {
        $Session.Client.Dispose()
    }
    if ($null -ne $Session.Handler) {
        $Session.Handler.Dispose()
    }
}

function New-Phase6HttpMethod {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Method
    )

    switch ($Method.ToUpperInvariant()) {
        "GET" { return [System.Net.Http.HttpMethod]::Get }
        "POST" { return [System.Net.Http.HttpMethod]::Post }
        "PATCH" { return [System.Net.Http.HttpMethod]::new("PATCH") }
        "DELETE" { return [System.Net.Http.HttpMethod]::Delete }
        default { throw "Unsupported method: $Method" }
    }
}

function Invoke-Phase6Request {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Session,
        [Parameter(Mandatory = $true)]
        [string]$Method,
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [hashtable]$Headers,
        [hashtable]$CookiePairs,
        [object]$Json
    )

    $request = [System.Net.Http.HttpRequestMessage]::new((New-Phase6HttpMethod -Method $Method), $Path)

    if ($null -ne $Headers) {
        foreach ($entry in $Headers.GetEnumerator()) {
            $null = $request.Headers.TryAddWithoutValidation([string]$entry.Key, [string]$entry.Value)
        }
    }

    if ($null -ne $CookiePairs -and $CookiePairs.Count -gt 0) {
        $cookieHeader = [string]::Join(
            "; ",
            @(
                foreach ($entry in $CookiePairs.GetEnumerator()) {
                    "{0}={1}" -f [string]$entry.Key, [string]$entry.Value
                }
            )
        )
        $null = $request.Headers.TryAddWithoutValidation("Cookie", $cookieHeader)
    }

    if ($PSBoundParameters.ContainsKey("Json")) {
        $jsonText = $Json | ConvertTo-Json -Depth 20 -Compress
        $request.Content = [System.Net.Http.StringContent]::new(
            $jsonText,
            [System.Text.Encoding]::UTF8,
            "application/json"
        )
    }

    $response = $Session.Client.SendAsync($request).GetAwaiter().GetResult()
    try {
        $bodyText = ""
        if ($null -ne $response.Content) {
            $bodyText = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        }

        $jsonBody = $null
        if ($bodyText) {
            try {
                $jsonBody = $bodyText | ConvertFrom-Json
            }
            catch {
                $jsonBody = $null
            }
        }

        $setCookieHeaders = @()
        try {
            $cookieValues = $null
            if ($response.Headers.TryGetValues("Set-Cookie", [ref]$cookieValues)) {
                $setCookieHeaders = @($cookieValues)
            }
        }
        catch {
            $setCookieHeaders = @()
        }

        $headerMap = @{}
        foreach ($header in $response.Headers) {
            $headerMap[$header.Key] = [string]::Join(", ", $header.Value)
        }
        foreach ($header in $response.Content.Headers) {
            $headerMap[$header.Key] = [string]::Join(", ", $header.Value)
        }

        return [pscustomobject]@{
            StatusCode      = [int]$response.StatusCode
            IsSuccessStatus = $response.IsSuccessStatusCode
            Headers         = $headerMap
            SetCookieHeaders = $setCookieHeaders
            BodyText        = $bodyText
            Json            = $jsonBody
        }
    }
    finally {
        $response.Dispose()
    }
}

function Get-Phase6SetCookieValue {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Response,
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    foreach ($header in @($Response.SetCookieHeaders)) {
        if ($header -match ("^{0}=([^;]+)" -f [Regex]::Escape($Name))) {
            return $Matches[1]
        }
    }
    return $null
}

function Assert-Phase6Status {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Response,
        [Parameter(Mandatory = $true)]
        [int]$ExpectedStatus,
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    if ($Response.StatusCode -ne $ExpectedStatus) {
        throw "{0}. Expected {1}, received {2}. Body: {3}" -f $Message, $ExpectedStatus, $Response.StatusCode, $Response.BodyText
    }
}

function Assert-Phase6True {
    param(
        [Parameter(Mandatory = $true)]
        [bool]$Condition,
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    if (-not $Condition) {
        throw $Message
    }
}

function New-Phase6CorrelationId {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Prefix
    )

    return "{0}-{1}" -f $Prefix, [Guid]::NewGuid().ToString("N").Substring(0, 12)
}

function New-Phase6Email {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Prefix
    )

    return "{0}-{1}@example.test" -f $Prefix, [Guid]::NewGuid().ToString("N").Substring(0, 12)
}

function Register-Phase6User {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Session,
        [Parameter(Mandatory = $true)]
        [string]$Email,
        [Parameter(Mandatory = $true)]
        [string]$Password
    )

    $response = Invoke-Phase6Request `
        -Session $Session `
        -Method "POST" `
        -Path "/api/auth/register" `
        -Headers @{ Origin = $script:Phase6Origin } `
        -Json @{ email = $Email; password = $Password }

    Assert-Phase6Status -Response $response -ExpectedStatus 202 -Message "User registration failed"
    return $response
}

function Login-Phase6User {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Session,
        [Parameter(Mandatory = $true)]
        [string]$Email,
        [Parameter(Mandatory = $true)]
        [string]$Password,
        [string]$CorrelationId
    )

    $headers = @{ Origin = $script:Phase6Origin }
    if ($CorrelationId) {
        $headers["X-Correlation-Id"] = $CorrelationId
    }

    $response = Invoke-Phase6Request `
        -Session $Session `
        -Method "POST" `
        -Path "/api/auth/login" `
        -Headers $headers `
        -Json @{ email = $Email; password = $Password }

    Assert-Phase6Status -Response $response -ExpectedStatus 200 -Message "User login failed"

    $refreshToken = Get-Phase6SetCookieValue -Response $response -Name "__Host-simpagent_refresh"
    $csrfToken = Get-Phase6SetCookieValue -Response $response -Name "__Host-simpagent_csrf"

    Assert-Phase6True -Condition ([string]::IsNullOrWhiteSpace($refreshToken) -eq $false) -Message "Login response did not include the refresh cookie."
    Assert-Phase6True -Condition ([string]::IsNullOrWhiteSpace($csrfToken) -eq $false) -Message "Login response did not include the CSRF cookie."

    return [pscustomobject]@{
        AccessToken  = [string]$response.Json.access_token
        RefreshToken = $refreshToken
        CsrfToken    = $csrfToken
        Response     = $response
    }
}

function Invoke-Phase6RefreshSession {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Session,
        [Parameter(Mandatory = $true)]
        [string]$RefreshToken,
        [Parameter(Mandatory = $true)]
        [string]$CsrfToken,
        [Parameter(Mandatory = $true)]
        [string]$CorrelationId
    )

    $response = Invoke-Phase6Request `
        -Session $Session `
        -Method "POST" `
        -Path "/api/auth/refresh" `
        -Headers @{
            Origin = $script:Phase6Origin
            "X-CSRF-Token" = $CsrfToken
            "X-Correlation-Id" = $CorrelationId
        } `
        -CookiePairs @{
            "__Host-simpagent_refresh" = $RefreshToken
            "__Host-simpagent_csrf" = $CsrfToken
        }

    $accessToken = $null
    if ($null -ne $response.Json -and $response.Json.PSObject.Properties.Match("access_token").Count -gt 0) {
        $accessToken = [string]$response.Json.access_token
    }

    return [pscustomobject]@{
        Response     = $response
        AccessToken  = $accessToken
        RefreshToken = Get-Phase6SetCookieValue -Response $response -Name "__Host-simpagent_refresh"
        CsrfToken    = Get-Phase6SetCookieValue -Response $response -Name "__Host-simpagent_csrf"
    }
}

function Invoke-Phase6LogoutSession {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Session,
        [Parameter(Mandatory = $true)]
        [string]$RefreshToken,
        [Parameter(Mandatory = $true)]
        [string]$CsrfToken
    )

    return Invoke-Phase6Request `
        -Session $Session `
        -Method "POST" `
        -Path "/api/auth/logout" `
        -Headers @{
            Origin = $script:Phase6Origin
            "X-CSRF-Token" = $CsrfToken
        } `
        -CookiePairs @{
            "__Host-simpagent_refresh" = $RefreshToken
            "__Host-simpagent_csrf" = $CsrfToken
        }
}

function New-Phase6AuthHeaders {
    param(
        [Parameter(Mandatory = $true)]
        [string]$AccessToken,
        [string]$CorrelationId
    )

    $headers = @{ Authorization = "Bearer $AccessToken" }
    if ($CorrelationId) {
        $headers["X-Correlation-Id"] = $CorrelationId
    }
    return $headers
}

function Find-Phase6AdminUserByEmail {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Session,
        [Parameter(Mandatory = $true)]
        [string]$AccessToken,
        [Parameter(Mandatory = $true)]
        [string]$Email
    )

    $offset = 0
    while ($true) {
        $response = Invoke-Phase6Request `
            -Session $Session `
            -Method "GET" `
            -Path ("/api/admin/users?limit=100&offset={0}" -f $offset) `
            -Headers (New-Phase6AuthHeaders -AccessToken $AccessToken)

        Assert-Phase6Status -Response $response -ExpectedStatus 200 -Message "Admin users query failed"

        foreach ($item in @($response.Json.items)) {
            if ($item.email -eq $Email) {
                return $item
            }
        }

        if (-not $response.Json.page.has_more) {
            break
        }
        $offset = [int]$response.Json.page.next_offset
    }

    throw "Admin user list did not include $Email."
}

function Find-Phase6SecurityEventByCorrelationId {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Session,
        [Parameter(Mandatory = $true)]
        [string]$AccessToken,
        [Parameter(Mandatory = $true)]
        [string]$CorrelationId
    )

    $offset = 0
    while ($true) {
        $response = Invoke-Phase6Request `
            -Session $Session `
            -Method "GET" `
            -Path ("/api/admin/security-events?limit=100&offset={0}" -f $offset) `
            -Headers (New-Phase6AuthHeaders -AccessToken $AccessToken)

        Assert-Phase6Status -Response $response -ExpectedStatus 200 -Message "Admin security-events query failed"

        foreach ($item in @($response.Json.items)) {
            if ($item.correlation_id -eq $CorrelationId) {
                return $item
            }
        }

        if (-not $response.Json.page.has_more) {
            break
        }
        $offset = [int]$response.Json.page.next_offset
    }

    throw "Admin security-events did not include correlation id $CorrelationId."
}

function Find-Phase6ToolExecutionByCorrelationId {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Session,
        [Parameter(Mandatory = $true)]
        [string]$AccessToken,
        [Parameter(Mandatory = $true)]
        [string]$CorrelationId
    )

    $offset = 0
    while ($true) {
        $response = Invoke-Phase6Request `
            -Session $Session `
            -Method "GET" `
            -Path ("/api/admin/tool-executions?limit=100&offset={0}" -f $offset) `
            -Headers (New-Phase6AuthHeaders -AccessToken $AccessToken)

        Assert-Phase6Status -Response $response -ExpectedStatus 200 -Message "Admin tool-executions query failed"

        foreach ($item in @($response.Json.items)) {
            if ($item.correlation_id -eq $CorrelationId) {
                return $item
            }
        }

        if (-not $response.Json.page.has_more) {
            break
        }
        $offset = [int]$response.Json.page.next_offset
    }

    throw "Admin tool-executions did not include correlation id $CorrelationId."
}
