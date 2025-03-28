---

# Collection Optimizer

A PowerShell utility designed to **merge**, **clean**, and **split** large file collections. It’s ideal for consolidating and packaging Garry’s Mod addons or any extensive file tree.

---

## Features

### 1. Merge
- **Recursively combine files:**  
  Moves every file from each top‑level subfolder in your source directory into a single destination folder.
- **Duplicate management:**  
  Automatically detects and deletes duplicate files while reporting the total space saved.

### 2. Clean
- **Remove unnecessary files:**  
  Deletes unwanted model‑format files:  
  - `.dx80.vtx` – DirectX 8.0 fallback (deprecated)
  - `.xbox.vtx` – Original Xbox compiled (not used in GMOD)
  - `.sw.vtx` – Software rendering path (not used in GMOD)
  - `.360.vtx` – Xbox 360 compiled (not used in GMOD)
- **Reporting:**  
  Displays the count of removed files and the space reclaimed, including a breakdown by file type.

### 3. Split
- **Organized packaging:**  
  Copies the merged files into sequentially numbered subfolders (e.g., `1`, `2`, `3`, …).
- **Size limit:**  
  Each subfolder is capped at approximately 1.95 GB for easier distribution.

### 4. Cleanup
- **Post-merge cleanup:**  
  Deletes the original source folders after a successful merge, leaving only the split packages in the destination folder.

---

## Installation

1. **Download or clone the repository.**
2. **Place files together:**  
   Ensure that both `collectionoptimizer.ps1` and `run.bat` are located in the same folder.

---

## Usage

1. **Run the utility:**  
   Double‑click **run.bat** or execute it from the Command Prompt. This will:
   - Temporarily adjust PowerShell’s execution policy.
   - Execute `collectionoptimizer.ps1`.

2. **Input paths:**  
   You will be prompted to enter the **Source** and **Destination** paths. Default values are provided, and you can press Enter to accept them.

---

## Example Output

```
Starting Merge Operation...
Source: C:\MyAddons
Destination: D:\Merged

Processing folder: C:\MyAddons\AddonA
Removed folder: C:\MyAddons\AddonA
...

Merge Operation Summary:
Files moved: 1234
Duplicates found: 12 (50.00 KB saved)

Removing unused model formats...
Unused files removed: 150 (100.00 KB freed)
Breakdown per format:
  .dx80.vtx removed: 50
  .xbox.vtx removed: 50
  .sw.vtx removed: 25
  .360.vtx removed: 25

Starting Split Operation on: D:\Merged
Splitting complete. Packs have been created under 'D:\Merged'.
```

---

## Related

For uploading Garry’s Mod addons to the Steam Workshop, check out [gmpublisher](https://github.com/WilliamVenner/gmpublisher).

---
