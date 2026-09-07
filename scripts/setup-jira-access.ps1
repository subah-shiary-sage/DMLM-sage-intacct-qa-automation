[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$JiraUrl = "https://jira.sage.com"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

if (-not $IsWindows -and $PSVersionTable.PSEdition -eq "Core") {
    throw "This installer requires Windows because it uses DPAPI CurrentUser encryption."
}

$uri = $null
if (-not [Uri]::TryCreate($JiraUrl, [UriKind]::Absolute, [ref]$uri)) {
    throw "JiraUrl must be an absolute URL."
}
if ($uri.Scheme -ne "https") {
    throw "JiraUrl must use HTTPS."
}
if ($uri.Query -or $uri.Fragment) {
    throw "JiraUrl must not contain a query string or fragment."
}

$normalizedJiraUrl = $JiraUrl.TrimEnd("/")
$credentialDirectory = Join-Path $env:LOCALAPPDATA "SageIntacctQA"
$credentialPath = Join-Path $credentialDirectory "jira-auth.json"
$repoRoot = Split-Path -Parent $PSScriptRoot
$agentTemplate = Join-Path $repoRoot "agent_templates\intacct_qa_workflow.toml"
$agentDirectory = Join-Path $repoRoot ".codex\agents"
$agentPath = Join-Path $agentDirectory "intacct_qa_workflow.toml"

Write-Host "Jira URL: $normalizedJiraUrl"
$securePat = Read-Host "Enter a NEW Jira PAT (input is masked)" -AsSecureString
if ($securePat.Length -eq 0) {
    throw "The Jira PAT cannot be empty."
}

$bstr = [IntPtr]::Zero
$plainPat = $null
$plainBytes = $null
$entropyBytes = [Text.Encoding]::UTF8.GetBytes("SageIntacctQA:JiraPAT:v1")

try {
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePat)
    $plainPat = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)

    $headers = @{
        Authorization = "Bearer $plainPat"
        Accept = "application/json"
    }

    try {
        $profile = Invoke-RestMethod `
            -Method Get `
            -Uri "$normalizedJiraUrl/rest/api/2/myself" `
            -Headers $headers `
            -TimeoutSec 20
    }
    catch {
        throw "Jira verification failed. Check VPN/network access, the Jira URL, PAT validity, and Jira permissions. No credential was saved."
    }

    Add-Type -AssemblyName System.Security
    $plainBytes = [Text.Encoding]::UTF8.GetBytes($plainPat)
    $protectedBytes = [System.Security.Cryptography.ProtectedData]::Protect(
        $plainBytes,
        $entropyBytes,
        [System.Security.Cryptography.DataProtectionScope]::CurrentUser
    )

    New-Item -ItemType Directory -Force -Path $credentialDirectory | Out-Null
    $payload = [ordered]@{
        version = 1
        jira_url = $normalizedJiraUrl
        protected_pat = [Convert]::ToBase64String($protectedBytes)
        created_at_utc = [DateTime]::UtcNow.ToString("o")
    }
    $payload | ConvertTo-Json | Set-Content -LiteralPath $credentialPath -Encoding UTF8

    try {
        $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
        $acl = Get-Acl -LiteralPath $credentialPath
        $acl.SetAccessRuleProtection($true, $false)
        foreach ($rule in @($acl.Access)) {
            [void]$acl.RemoveAccessRuleAll($rule)
        }
        $accessRule = [System.Security.AccessControl.FileSystemAccessRule]::new(
            $identity,
            [System.Security.AccessControl.FileSystemRights]::FullControl,
            [System.Security.AccessControl.AccessControlType]::Allow
        )
        $acl.SetAccessRule($accessRule)
        Set-Acl -LiteralPath $credentialPath -AclObject $acl
    }
    catch {
        Remove-Item -LiteralPath $credentialPath -Force -ErrorAction SilentlyContinue
        throw "The PAT was encrypted, but the credential file permissions could not be restricted. Nothing was retained."
    }

    if (-not (Test-Path -LiteralPath $agentTemplate)) {
        throw "Local agent template not found: $agentTemplate"
    }
    New-Item -ItemType Directory -Force -Path $agentDirectory | Out-Null
    Copy-Item -LiteralPath $agentTemplate -Destination $agentPath -Force

    $displayName = if ($profile.displayName) { $profile.displayName } elseif ($profile.name) { $profile.name } else { "authenticated Jira user" }
    Write-Host "Jira access verified for $displayName."
    Write-Host "Encrypted credential installed for the current Windows account."
    Write-Host "Local Codex agent installed at $agentPath"
}
finally {
    if ($plainBytes) {
        [Array]::Clear($plainBytes, 0, $plainBytes.Length)
    }
    if ($bstr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
    $plainPat = $null
    $securePat = $null
}
