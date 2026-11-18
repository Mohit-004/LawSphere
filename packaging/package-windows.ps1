param(
    [ValidateSet("exe", "msi", "app-image")]
    [string]$PackageType = "exe"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$desktopDirectory = Join-Path $projectRoot "desktop-app"
$pomFile = Join-Path $desktopDirectory "pom.xml"
$targetDirectory = Join-Path $desktopDirectory "target"
$dependencyDirectory = Join-Path $targetDirectory "jpackage-dependencies"

$windowsArchitecture = $env:PROCESSOR_ARCHITEW6432
if ([string]::IsNullOrWhiteSpace($windowsArchitecture)) {
    $windowsArchitecture = $env:PROCESSOR_ARCHITECTURE
}
if ($windowsArchitecture -ne "AMD64") {
    throw "This packaging script currently supports x64 Windows only."
}

$maven = Get-Command mvn -ErrorAction SilentlyContinue
$jpackage = Get-Command jpackage -ErrorAction SilentlyContinue
if ($null -eq $maven) {
    throw "Maven was not found on PATH. Install Maven and try again."
}
if ($null -eq $jpackage) {
    throw "jpackage was not found. Install a Java 21 JDK and make its bin folder available on PATH."
}
$jdkVersion = & $jpackage.Source --version
if ($LASTEXITCODE -ne 0 -or -not $jdkVersion.StartsWith("21.")) {
    throw "Use jpackage from a Java 21 JDK. Found version $jdkVersion."
}

$jdkDirectory = if ([string]::IsNullOrWhiteSpace($env:JAVA_HOME)) {
    Split-Path -Parent (Split-Path -Parent $jpackage.Source)
} else {
    $env:JAVA_HOME
}
$jmodsDirectory = Join-Path $jdkDirectory "jmods"
if (-not (Test-Path -LiteralPath $jmodsDirectory -PathType Container)) {
    throw "Could not find JDK modules at $jmodsDirectory. Set JAVA_HOME to a full JDK 21 installation."
}

if ($PackageType -ne "app-image") {
    foreach ($toolName in @("candle.exe", "light.exe")) {
        if ($null -eq (Get-Command $toolName -ErrorAction SilentlyContinue)) {
            throw "WiX Toolset 3.x was not found on PATH ($toolName is missing). Install WiX Toolset 3.x to build a Windows installer."
        }
    }
}

[xml]$pom = Get-Content -LiteralPath $pomFile -Raw
$artifactId = [string]$pom.project.artifactId
$version = [string]$pom.project.version
$appVersion = [regex]::Match($version, '^\d+(?:\.\d+){1,3}').Value
if ([string]::IsNullOrWhiteSpace($appVersion)) {
    throw "Could not read a numeric application version from $pomFile."
}
$mainJar = Join-Path $targetDirectory "$artifactId-$version.jar"

& $maven.Source -f $pomFile clean package `
    org.apache.maven.plugins:maven-dependency-plugin:3.8.1:copy-dependencies `
    "-DincludeScope=runtime" "-DoutputDirectory=$dependencyDirectory"
if ($LASTEXITCODE -ne 0) {
    throw "Maven packaging failed."
}
if (-not (Test-Path -LiteralPath $mainJar -PathType Leaf)) {
    throw "The desktop JAR was not created at $mainJar."
}

$javafxModules = @(Get-ChildItem -LiteralPath $dependencyDirectory -Filter "javafx-*.jar" |
    Where-Object { $_.Name -match '^javafx-(base|graphics|controls)-.*-win.*\.jar$' })
if ($javafxModules.Count -lt 3) {
    throw "Could not find the Windows JavaFX base, graphics, and controls modules in $dependencyDirectory."
}

$buildStamp = Get-Date -Format "yyyyMMdd-HHmmss"
$buildDirectory = Join-Path $PSScriptRoot "build\$buildStamp"
$inputDirectory = Join-Path $buildDirectory "input"
$outputDirectory = Join-Path $buildDirectory "output"
$backendDirectory = Join-Path $inputDirectory "ai-engine"
New-Item -ItemType Directory -Path $inputDirectory, $outputDirectory, $backendDirectory -Force | Out-Null

Copy-Item -LiteralPath $mainJar -Destination $inputDirectory
Get-ChildItem -LiteralPath $dependencyDirectory -Filter "jackson-*.jar" |
    Copy-Item -Destination $inputDirectory
Copy-Item -LiteralPath (Join-Path $projectRoot "ai-engine\app") `
    -Destination (Join-Path $backendDirectory "app") -Recurse
Copy-Item -LiteralPath (Join-Path $projectRoot "ai-engine\requirements.txt") `
    -Destination $backendDirectory
Copy-Item -LiteralPath (Join-Path $projectRoot "scripts") `
    -Destination (Join-Path $inputDirectory "scripts") -Recurse

$modulePath = @($javafxModules | ForEach-Object { $_.FullName }) + @($jmodsDirectory)
$modulePathArgument = $modulePath -join [IO.Path]::PathSeparator
$jpackageArguments = @(
    "--type", $PackageType,
    "--name", "LawSphere",
    "--app-version", $appVersion,
    "--description", "Offline Indian legal research assistant",
    "--vendor", "LawSphere",
    "--input", $inputDirectory,
    "--main-jar", "$artifactId-$version.jar",
    "--main-class", "in.lawsphere.desktop.LawSphereLauncher",
    "--module-path", $modulePathArgument,
    "--add-modules", "javafx.controls",
    "--java-options", "--add-modules=javafx.controls",
    "--dest", $outputDirectory
)
if ($PackageType -ne "app-image") {
    $jpackageArguments += @("--win-per-user-install", "--win-menu", "--win-shortcut", "--win-dir-chooser")
}

& $jpackage.Source @jpackageArguments
if ($LASTEXITCODE -ne 0) {
    throw "jpackage failed."
}

Write-Host "LawSphere package created under $outputDirectory"
