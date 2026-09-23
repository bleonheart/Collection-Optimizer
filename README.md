<p align="center">
 <strong>Collection Optimizer</strong><br/>
 A desktop utility for merging, cleaning, benchmarking, and splitting Garry's Mod addon collections into deployable content packs.<br/>
 Built for server owners and content maintainers who need to reduce duplicate content, remove unused model formats, organize Lua separately, and prepare large collections for deployment.<br/>
</p>

<p align="center">
 <a href="./license">
  <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License MIT" />
 </a>
 <img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white" alt="Python 3.10+" />
 <a href="https://github.com/bleonheart/Collection-Optimizer/stargazers">
  <img src="https://img.shields.io/github/stars/bleonheart/Collection-Optimizer?style=social" alt="GitHub Stars" />
 </a>
</p>

<h1 align="center">Collection Optimizer</h1>

---

## Quick Start

Clone the repository:

```bash
git clone https://github.com/bleonheart/Collection-Optimizer.git
cd Collection-Optimizer
```

Install the GUI dependency:

```bash
python -m pip install PySide6
```

Launch the application:

```bat
run.bat
```

You can also start it directly:

```bash
python collectionoptimizer.py
```

## Overview

Collection Optimizer is designed around the common Garry's Mod content workflow where a large set of downloaded or exported addons needs to be consolidated into cleaner deployment packs.

The application provides a PySide6 desktop interface for selecting source and destination directories, configuring pack sizes, running merge/split operations, and reviewing operation summaries.

## Features

### Merge Addons

Merge top-level addon directories into one destination tree.

During the merge process the application can:

- Move addon files into a shared destination
- Detect duplicate destination paths
- Remove duplicate source files
- Remove unused Source model sidecar formats
- Remove empty directories
- Track processed addons, moved files, duplicates, failures, and saved space

### Split Content

Split merged content into numbered packs under:

```text
Destination/Addons/
```

Pack boundaries are controlled by the configured maximum pack size.

The default maximum pack size is:

```text
3.90 GB
```

### Lua Separation

When enabled, Lua files can be separated into:

```text
Destination/Lua/<AddonName>/
```

Numeric suffixes such as `_1` or `_27` are stripped from addon names when creating Lua output directories.

### Cleanup

The optimizer removes model formats that Garry's Mod normally does not need:

- `.dx80.vtx`
- `.xbox.vtx`
- `.sw.vtx`
- `.360.vtx`

It can also remove empty directories left behind by merge and cleanup operations.

### Benchmarks

Benchmark operations let you inspect a workload before performing the main operation.

Available workflow information includes:

- Addon counts
- File counts
- Total content size
- Estimated pack counts
- Destination folder size

### Persistent Settings

Application settings are stored in `settings.json`.

Saved values include:

- Source path
- Destination path
- Maximum pack size

The application restores these settings between launches.

## Data Safety

**Use a backup or disposable source directory when merging.**

The merge workflow is intentionally destructive to its source:

- Files are moved from source addon directories into the destination
- Duplicate source files may be deleted
- Processed addon directories are removed after their files are handled

The split workflow copies merged files into numbered packs. If the delete-original option is enabled, the original merged files are then removed.

Use the benchmark tools first when you want to inspect the workload before changing files.

## Typical Workflow

1. Export or download addons into a source directory
2. Select that directory as the source
3. Choose a clean destination directory
4. Set the desired maximum pack size
5. Run a benchmark
6. Run **Merge** or **Merge + Split**
7. Review the operation log and summary
8. Use the generated packs for deployment or upload

## Repository Structure

```text
Collection-Optimizer/
├── collectionoptimizer.py
├── run.bat
├── settings.json
├── README.md
└── license
```

## Requirements

- Windows for the provided batch launcher and default path conventions
- Python 3.10 or newer
- PySide6

Install PySide6 with:

```bash
python -m pip install PySide6
```

## Contributing

Contributions to the UI, cleanup logic, performance, reporting, and deployment workflow are welcome.

1. Fork the repository
2. Create a feature branch
3. Make and test your changes
4. Open a pull request with a clear description of the change

## License

Collection Optimizer is distributed under the MIT License. See [license](./license) for details.
