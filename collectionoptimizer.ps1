param()

$DefaultSourcePath = "C:\Users\Admin\AppData\Local\Temp\gmpublisher"
$DefaultDestinationPath = "D:\Merged"
$MaxPackSizeBytes = 1.95 * 1GB

Write-Host "Enter the SOURCE path or press Enter to use [$DefaultSourcePath]:"
$UserSourcePath = Read-Host
if (![string]::IsNullOrWhiteSpace($UserSourcePath)) { $DefaultSourcePath = $UserSourcePath }

Write-Host "Enter the DESTINATION path or press Enter to use [$DefaultDestinationPath]:"
$UserDestinationPath = Read-Host
if (![string]::IsNullOrWhiteSpace($UserDestinationPath)) { $DefaultDestinationPath = $UserDestinationPath }

$SourcePath = $DefaultSourcePath
$DestinationPath = $DefaultDestinationPath

Write-Host "`nStarting Merge Operation..."
Write-Host "Source: $SourcePath"
Write-Host "Destination: $DestinationPath"

if (-not (Test-Path $DestinationPath)) { New-Item -ItemType Directory -Path $DestinationPath | Out-Null }

$topLevelFolders = Get-ChildItem -Path $SourcePath -Directory
if ($topLevelFolders.Count -eq 0) {
    Write-Host "No folders found in '$SourcePath'. Nothing to merge."
    return
}

$filesMoved = 0; $duplicates = 0; $spaceSaved = 0

foreach ($folder in $topLevelFolders) {
    Write-Host "Processing folder: $($folder.FullName)"
    Get-ChildItem -Path $folder.FullName -File -Recurse | ForEach-Object {
        $relativePath = $_.FullName.Substring($folder.FullName.Length).TrimStart('\')
        $destFile = Join-Path $DestinationPath $relativePath
        $destFolder = Split-Path $destFile
        if (-not (Test-Path $destFolder)) { New-Item -ItemType Directory -Path $destFolder | Out-Null }

        if (Test-Path $destFile) {
            $duplicates++; $spaceSaved += $_.Length
            Remove-Item $_.FullName -Force
        } else {
            Move-Item $_.FullName -Destination $destFile
            $filesMoved++
        }
    }
    Remove-Item $folder.FullName -Recurse -Force
    Write-Host "Removed folder: $($folder.FullName)"
}

Write-Host "`nMerge Operation Summary:"
Write-Host "Files moved: $filesMoved"
Write-Host "Duplicates found: $duplicates"
Write-Host ("Space saved from duplicates: {0:N2} KB" -f ($spaceSaved / 1KB))

Write-Host "`nRemoving unused model formats..."
$badFormats = @(".dx80.vtx",".xbox.vtx",".sw.vtx",".360.vtx")
$removedCount = 0; $removedSize = 0
$removedPerFormat = @{}
foreach ($fmt in $badFormats) { $removedPerFormat[$fmt] = 0 }

Get-ChildItem -Path $DestinationPath -Recurse -File | ForEach-Object {
    foreach ($fmt in $badFormats) {
        if ($_.Name.EndsWith($fmt)) {
            $removedSize += $_.Length; $removedCount++; $removedPerFormat[$fmt]++
            Remove-Item $_.FullName -Force
            break
        }
    }
}

Write-Host ("Unused files removed: $removedCount, Space freed: {0:N2} KB" -f ($removedSize / 1KB))
Write-Host "Breakdown per format:"
$removedPerFormat.GetEnumerator() | ForEach-Object { Write-Host "$($_.Key) removed: $($_.Value)" }

Write-Host "`nStarting Split Operation on: $DestinationPath"
$RootFolder = if ($DestinationPath[-1] -eq '\') { $DestinationPath } else { "$DestinationPath\" }
$CurrentPack = 1; $CurrentPackSize = 0

Get-ChildItem -Path $RootFolder -File -Recurse | ForEach-Object {
    if (($CurrentPackSize + $_.Length) -gt $MaxPackSizeBytes) {
        $CurrentPack++; $CurrentPackSize = 0
    }
    $relativePath = $_.FullName.Substring($RootFolder.Length).TrimStart('\')
    $packFolder = Join-Path $RootFolder $CurrentPack
    $dest = Join-Path $packFolder $relativePath
    if (-not (Test-Path (Split-Path $dest))) { New-Item -ItemType Directory -Path (Split-Path $dest) | Out-Null }
    Copy-Item $_.FullName -Destination $dest
    $CurrentPackSize += $_.Length
}

Write-Host "Removing original source files..."
if (Test-Path $SourcePath) {
    Remove-Item -Path (Join-Path $SourcePath '*') -Recurse -Force
}
Write-Host "Original source files removed."