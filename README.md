<p align="center">
 <strong>Collection Optimizer</strong><br/>
 A desktop utility for merging, cleaning, and splitting Garry's Mod addon collections into cleaner deployable packs.<br/>
 Built to help server owners and content maintainers remove dead weight, collapse duplicate files, and prepare content for upload or distribution.<br/>
</p>

<p align="center">
 <a href="./license">
  <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License MIT" />
 </a>
</p>

<h1 align="center">Collection Optimizer</h1>

---

## Quick Start

<p align="center">
 Clone the repository, run <code>run.bat</code>, and launch the desktop application on Windows.
</p>

```bash
git clone https://github.com/your-org/Collection-Optimizer.git
cd Collection-Optimizer
run.bat
```

The batch launcher will:

1. Start the Python desktop UI by default
2. Use the saved `settings.json` values if they exist
3. Run the PySide6 application directly from this repository

## Usage

Run the launcher without arguments:

```bash
run.bat
```

This mode will:

1. Launch the PySide6 desktop app with the saved Source, Destination, and Max Pack Size settings
2. Let you browse folders, run merge and split operations, and review logs in one window
3. Persist settings back to `settings.json` whenever you finish editing the path or size fields

## Features

### File Merging

- `Run Merge`  
  Merge all top-level addon folders from the source folder into one destination folder while removing duplicate collisions.

- `Run Split`  
  Split merged content into sequential numbered addon packs under `Destination\Addons` using the chosen maximum pack size.

- `Run Merge + Split`  
  Run the full workflow in one pass: merge addon folders first, then split the result into numbered packs.

### Cleanup Utilities

- `Remove unused model formats`  
  Remove `.dx80.vtx`, `.xbox.vtx`, `.sw.vtx`, and `.360.vtx` files that are not needed for Garry's Mod.

- `Remove empty folders`  
  Clean up empty directories left behind after merge, deletion, or split operations.

### Merge Options

- `Split Lua files into Destination\Lua\AddonName`  
  Store Lua files separately under `Destination\Lua\<AddonName>` during merge instead of mixing them into the main merged content tree. Trailing suffixes like `_1` or `_27` are stripped from Lua addon folder names.

- `Delete original merged files after split`  
  Remove the pre-split merged files from the destination root after numbered packs have been created.

### Benchmark

- `Benchmark Merge`  
  Preview how many addon folders, files, and total bytes exist in the source collection without modifying anything.

- `Benchmark Split`  
  Preview how many files will be split, the total size involved, and the estimated number of packs required.

- `Calculate Folder Size`  
  Calculate and display the current destination folder size in the UI and log panel.

## Settings

The desktop app stores its UI settings in `settings.json` beside the scripts.

Saved values include:

- Source path
- Destination path
- Max pack size in GB

These settings are loaded automatically on startup and saved again whenever you finish editing the related fields or use the browse buttons.

## Requirements

- Windows is the primary supported platform for the desktop workflow
- Python 3.10 or newer
- `PySide6`

## Contributing

We welcome improvements to both the UI and the collection-processing workflow. To contribute:

1. Fork the repository
2. Create a feature branch
3. Make your changes and test them
4. Open a pull request with a clear explanation of what changed
