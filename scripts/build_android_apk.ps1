# CartMate Android APK Automated Build Script
# Usage: .\scripts\build_android_apk.ps1 -BackendOrigin "https://cartmate.yourdomain.com"

param (
    [Parameter(Mandatory = $true, HelpMessage = "The private or cloud HTTPS backend origin (e.g. https://cartmate.yourdomain.com)")]
    [string]$BackendOrigin
)

$ErrorActionPreference = "Stop"

# 1. Validation: this value is compiled into the APK and will receive bearer tokens.
$parsedOrigin = $null
if (
    $BackendOrigin -ne $BackendOrigin.Trim() -or
    $BackendOrigin -match '[\s\\]' -or
    -not [System.Uri]::TryCreate($BackendOrigin, [System.UriKind]::Absolute, [ref]$parsedOrigin) -or
    $parsedOrigin.Scheme -ne 'https' -or
    -not $parsedOrigin.Host -or
    $parsedOrigin.UserInfo -or
    $parsedOrigin.AbsolutePath -ne '/' -or
    $parsedOrigin.Query -or
    $parsedOrigin.Fragment
) {
    throw 'BackendOrigin must be a clean HTTPS origin with no credentials, path, query, fragment, or whitespace.'
}
$BackendOrigin = $parsedOrigin.GetLeftPart([System.UriPartial]::Authority).TrimEnd('/')

$repoRoot = (Resolve-Path "$PSScriptRoot\..").Path
$frontendDir = Join-Path $repoRoot "frontend"
$androidDir = Join-Path $frontendDir "android"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "CartMate Android Test APK Build Pipeline" -ForegroundColor Cyan
Write-Host "Target Backend Origin: $BackendOrigin" -ForegroundColor Yellow
Write-Host "==================================================" -ForegroundColor Cyan

# 2. Setup Toolchain Environment
$env:JAVA_HOME = "C:\Program Files\Android\openjdk\jdk-21.0.8"
$env:ANDROID_HOME = "C:\Program Files (x86)\Android\android-sdk"
$env:ANDROID_SDK_ROOT = $env:ANDROID_HOME
$env:PATH = "$env:JAVA_HOME\bin;$env:ANDROID_HOME\platform-tools;$env:PATH"

if (-not (Test-Path "$env:JAVA_HOME\bin\java.exe")) {
    Write-Error "JDK 21 not found at $env:JAVA_HOME"
    exit 1
}
if (-not (Test-Path "$env:ANDROID_HOME\build-tools\36.0.0")) {
    Write-Error "Android Build Tools not found at $env:ANDROID_HOME\build-tools\36.0.0"
    exit 1
}

# 3. Build Web Bundle
Write-Host "[1/4] Building optimized web bundle with VITE_BACKEND_ORIGIN..." -ForegroundColor Green
Push-Location $frontendDir
try {
    $env:VITE_BACKEND_ORIGIN = $BackendOrigin
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "npm run build failed" }
} finally {
    Pop-Location
}

# 4. Synchronize Assets to Android Project
Write-Host "[2/4] Syncing web assets to native Android project..." -ForegroundColor Green
Push-Location $frontendDir
try {
    npx --no-install cap sync android
    if ($LASTEXITCODE -ne 0) { throw "npx cap sync android failed" }
} finally {
    Pop-Location
}

# 5. Compile Android Debug APK
Write-Host "[3/4] Compiling debug APK via Gradle..." -ForegroundColor Green
Push-Location $androidDir
try {
    .\gradlew.bat assembleDebug
    if ($LASTEXITCODE -ne 0) { throw "gradlew assembleDebug failed" }
} finally {
    Pop-Location
}

# 6. Verify and Output Checksum
$apkPath = Join-Path $androidDir "app\build\outputs\apk\debug\app-debug.apk"
if (-not (Test-Path $apkPath)) {
    Write-Error "APK file not found at expected path: $apkPath"
    exit 1
}

Write-Host "[4/4] Verifying APK signature..." -ForegroundColor Green
$sigOutput = & "$env:ANDROID_HOME\build-tools\36.0.0\apksigner.bat" verify -v $apkPath 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) {
    Write-Error "APK signature verification failed with exit code ${LASTEXITCODE}:`n$sigOutput"
    exit 1
}
if ($sigOutput -notmatch "Verified using v2 scheme.*true") {
    Write-Error "APK is not signed with required APK Signature Scheme v2:`n$sigOutput"
    exit 1
}
Write-Host $sigOutput.Trim()

$fileItem = Get-Item $apkPath
$hash = (Get-FileHash -Algorithm SHA256 $apkPath).Hash

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "APK BUILD SUCCESSFUL!" -ForegroundColor Green
Write-Host "Artifact: $apkPath" -ForegroundColor White
Write-Host "Size:     $([math]::Round($fileItem.Length / 1MB, 2)) MB ($($fileItem.Length) bytes)" -ForegroundColor White
Write-Host "SHA-256:  $hash" -ForegroundColor Yellow
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "`nTo install on a connected Android phone:" -ForegroundColor Cyan
Write-Host "adb install -r `"$apkPath`"" -ForegroundColor Yellow
