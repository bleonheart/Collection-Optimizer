param()

$DefaultSourcePath = "C:\Users\David\AppData\Local\Temp\gmpublisher"
$DefaultDestinationPath = "E:\Merged"
$MaxPackSizeBytes = 3.90 * 1GB

Write-Host "Enter the SOURCE path or press Enter to use [$DefaultSourcePath]:"
$UserSourcePath = Read-Host
if (![string]::IsNullOrWhiteSpace($UserSourcePath)) {
    $DefaultSourcePath = $UserSourcePath
}

Write-Host "Enter the DESTINATION path or press Enter to use [$DefaultDestinationPath]:"
$UserDestinationPath = Read-Host
if (![string]::IsNullOrWhiteSpace($UserDestinationPath)) {
    $DefaultDestinationPath = $UserDestinationPath
}

$SourcePath = $DefaultSourcePath
$DestinationPath = $DefaultDestinationPath

Write-Host ""
Write-Host "Starting Merge Operation..."
Write-Host "Source: $SourcePath"
Write-Host "Destination: $DestinationPath"

if (-not (Test-Path $DestinationPath)) {
    New-Item -ItemType Directory -Path $DestinationPath | Out-Null
}

$topLevelFolders = Get-ChildItem -Path $SourcePath -Directory
if ($topLevelFolders.Count -eq 0) {
    Write-Host "No folders found in '$SourcePath'. Nothing to merge."
    return
}

$filesMoved = 0
$duplicates = 0
$spaceSaved = 0

foreach ($folder in $topLevelFolders) {
    Write-Host "Processing folder: $($folder.FullName)"
    $files = Get-ChildItem -Path $folder.FullName -File -Recurse
    foreach ($file in $files) {
        $relativePath = $file.FullName.Substring($folder.FullName.Length).TrimStart('\')
        $destinationFile = Join-Path $DestinationPath $relativePath
        $destinationFolder = Split-Path $destinationFile
        if (-not (Test-Path $destinationFolder)) {
            New-Item -ItemType Directory -Path $destinationFolder | Out-Null
        }
        if (Test-Path $destinationFile) {
            $duplicates++
            $spaceSaved += $file.Length
            Remove-Item -Path $file.FullName -Force
        } else {
            Move-Item -Path $file.FullName -Destination $destinationFile
            $filesMoved++
        }
    }
    Remove-Item -Path $folder.FullName -Recurse -Force
    Write-Host "Removed folder: $($folder.FullName)"
}

Write-Host ""
Write-Host "Merge Operation Summary:"
Write-Host "Files moved: $filesMoved"
Write-Host "Duplicates found: $duplicates"
Write-Host ("Space saved from duplicates: {0:N2} KB" -f ($spaceSaved / 1KB))

Write-Host ""
Write-Host "Removing unused model formats..."

$badFormats = @(".dx80.vtx",".xbox.vtx",".sw.vtx",".360.vtx")
$removedCount = 0
$removedSize = 0

# Track how many files are removed per format
$removedPerFormat = @{}
foreach ($fmt in $badFormats) {
    $removedPerFormat[$fmt] = 0
}

$allMergedFiles = Get-ChildItem -Path $DestinationPath -Recurse -File
foreach ($f in $allMergedFiles) {
    foreach ($fmt in $badFormats) {
        if ($f.Name.EndsWith($fmt)) {
            $removedSize += $f.Length
            $removedCount++
            $removedPerFormat[$fmt]++
            Remove-Item -Path $f.FullName -Force
            break
        }
    }
}

Write-Host ("Unused files removed: $removedCount, Space freed: {0:N2} KB" -f ($removedSize / 1KB))
Write-Host "Breakdown per format:"
foreach ($fmt in $badFormats) {
    Write-Host "$fmt removed: $($removedPerFormat[$fmt])"
}

Write-Host ""
Write-Host "Starting Split Operation on: $DestinationPath"

$RootFolder = $DestinationPath
$CurrentPack = 1
$CurrentPackSize = 0

if ($RootFolder[-1] -ne '\') {
    $RootFolder += '\'
}

$allFiles = Get-ChildItem -Path $RootFolder -File -Recurse
foreach ($file in $allFiles) {
    $fileSize = $file.Length
    if (($CurrentPackSize + $fileSize) -gt $MaxPackSizeBytes) {
        $CurrentPack++
        $CurrentPackSize = 0
    }
    $relativePath = $file.FullName.Substring($RootFolder.Length).TrimStart('\')
    $packFolderRoot = Join-Path $RootFolder $CurrentPack
    $destination = Join-Path $packFolderRoot $relativePath
    $destDir = Split-Path $destination -Parent
    if (-not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Path $destDir | Out-Null
    }
    Copy-Item -Path $file.FullName -Destination $destination
    $CurrentPackSize += $fileSize
}

Write-Host "Splitting complete. Packs have been created under '$DestinationPath'."
