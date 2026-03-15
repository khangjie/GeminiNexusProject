param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectId,

    [string]$Region = "us-central1",
    [string]$RepoName = "nexushub",
    [string]$ServiceName = "nexushub-backend",
    [switch]$AllowUnauthenticated
)

$ErrorActionPreference = "Stop"

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found in PATH."
    }
}

function Get-GcloudCommand {
    $fromPath = Get-Command gcloud -ErrorAction SilentlyContinue
    if ($fromPath) {
        return $fromPath.Source
    }

    $candidates = @(
        "$Env:ProgramFiles\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        "$Env:LocalAppData\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        "$Env:ProgramFiles(x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    throw "gcloud was not found. Install Google Cloud SDK first."
}

function Invoke-Gcloud {
    param([Parameter(ValueFromRemainingArguments = $true)] [string[]]$Args)
    & $script:GcloudExe @Args
}

if ($ProjectId -eq "your-gcp-project-id") {
    throw "ProjectId is still placeholder. Pass your real GCP project id."
}

if ([string]::IsNullOrWhiteSpace($ServiceName)) {
    throw "ServiceName cannot be empty."
}

Require-Command "docker"
$script:GcloudExe = Get-GcloudCommand

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$image = "$Region-docker.pkg.dev/$ProjectId/$RepoName/$ServiceName:latest"

Write-Host "Using image: $image"

Set-Location $repoRoot

Invoke-Gcloud auth login
Invoke-Gcloud config set project $ProjectId

Invoke-Gcloud services enable run.googleapis.com artifactregistry.googleapis.com

# Create Artifact Registry repo if missing (idempotent)
try {
    Invoke-Gcloud artifacts repositories describe $RepoName --location=$Region --project=$ProjectId | Out-Null
    Write-Host "Artifact Registry repo '$RepoName' already exists."
} catch {
    Invoke-Gcloud artifacts repositories create $RepoName --repository-format=docker --location=$Region --project=$ProjectId
}

Invoke-Gcloud auth configure-docker "$Region-docker.pkg.dev" --project $ProjectId

docker build -f backend/Dockerfile -t $image .
docker push $image

$deployArgs = @(
    "run", "deploy", $ServiceName,
    "--image", $image,
    "--region", $Region,
    "--platform", "managed",
    "--project", $ProjectId
)

if ($AllowUnauthenticated) {
    $deployArgs += "--allow-unauthenticated"
}

Invoke-Gcloud @deployArgs

$url = Invoke-Gcloud run services describe $ServiceName --region $Region --format="value(status.url)" --project=$ProjectId
Write-Host "Cloud Run URL: $url"

if (-not [string]::IsNullOrWhiteSpace($url)) {
    Invoke-RestMethod -Uri "$url/health" -Method Get | ConvertTo-Json -Compress
}
