# 📦 Collection Optimizer

A PowerShell utility that **merges**, **cleans**, and **splits** large folder collections — perfect for consolidating and packaging Garry’s Mod addons (or any large file tree).

---

## 🚀 Features

1. **Merge**  
   - Recursively move every file from each top‑level subfolder in a source directory into a single destination folder  
   - Automatically delete duplicates and report total space saved  

2. **Clean**  
   - Remove unwanted model‑format files (`.dx80.vtx`, `.xbox.vtx`, `.sw.vtx`, `.360.vtx`)  
   - Report count of removed files and space reclaimed  

3. **Split**  
   - Copy the merged folder into sequentially numbered subfolders (`1`, `2`, `3`, …)  
   - Each subfolder capped at ~1.95 GB for easy distribution  

4. **Cleanup**  
   - Delete original source folders after successful merge  
   - Leaves only the split packs in the destination  

---

## 📂 Installation

1. Download or clone this repository.  
2. Ensure `collectionoptimizer.ps1` and `run.bat` reside in the **same folder**.

---

## ▶️ Usage

Double‑click **run.bat** (or execute it in Command Prompt). It will:

1. Temporarily set PowerShell’s execution policy  
2. Run `collectionoptimizer.ps1`

You’ll be prompted to enter the **Source** and **Destination** paths (defaults shown in brackets). Press Enter to accept defaults.

---

## 📋 Example Output

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

## 🔗 Related

For uploading Garry’s Mod addons to Steam Workshop, check out **gmpublisher** 👉 https://github.com/WilliamVenner/gmpublisher  
