import json
import os
import re
import shutil
import sys
import traceback
from collections import OrderedDict
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets


DEFAULT_SOURCE_PATH = rf"C:\Users\{os.environ.get('USERNAME', 'User')}\AppData\Local\Temp\gmpublisher"
DEFAULT_DESTINATION_PATH = r"D:\Merged"
DEFAULT_MAX_PACK_SIZE_GB = 3.90
BAD_FORMATS = [".dx80.vtx", ".xbox.vtx", ".sw.vtx", ".360.vtx"]
ADDONS_DIR_NAME = "Addons"
LUA_DIR_NAME = "Lua"
SETTINGS_FILE = Path(__file__).with_name("settings.json")
PROJECT_ROOT = Path(__file__).resolve().parent


def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            with SETTINGS_FILE.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            pass
    return {
        "sourcePath": DEFAULT_SOURCE_PATH,
        "destinationPath": DEFAULT_DESTINATION_PATH,
        "maxPackSizeGb": DEFAULT_MAX_PACK_SIZE_GB,
    }


def save_settings(source_path: str, destination_path: str, max_pack_size_gb: str) -> None:
    data = {
        "sourcePath": source_path,
        "destinationPath": destination_path,
        "maxPackSizeGb": max_pack_size_gb,
    }
    with SETTINGS_FILE.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def get_relative_path(base_path: Path, full_path: Path) -> Path:
    return full_path.resolve().relative_to(base_path.resolve())


def test_bad_format(file_name: str, formats: list[str]) -> str | None:
    lower_name = file_name.lower()
    for file_format in formats:
        if lower_name.endswith(file_format.lower()):
            return file_format
    return None


def iter_files(root: Path):
    for path in root.rglob("*"):
        if path.is_file():
            yield path


def normalize_lua_addon_name(addon_name: str) -> str:
    return re.sub(r"_\d+$", "", addon_name)


def remove_empty_directories(root_path: Path) -> int:
    if not root_path.is_dir():
        return 0
    removed = 0
    directories = sorted((path for path in root_path.rglob("*") if path.is_dir()), reverse=True)
    for directory in directories:
        try:
            if not any(directory.iterdir()):
                directory.rmdir()
                removed += 1
        except OSError:
            continue
    return removed


def remove_bad_model_formats(root_path: Path, formats: list[str], log_callback=None) -> dict:
    summary = {
        "RemovedCount": 0,
        "RemovedSize": 0,
        "RemovedPerFormat": {fmt: 0 for fmt in formats},
    }
    if not root_path.is_dir():
        return summary

    for file_path in iter_files(root_path):
        bad_format = test_bad_format(file_path.name, formats)
        if bad_format is None:
            continue
        try:
            file_size = file_path.stat().st_size
            file_path.unlink()
            summary["RemovedCount"] += 1
            summary["RemovedSize"] += file_size
            summary["RemovedPerFormat"][bad_format] += 1
        except OSError:
            if log_callback:
                log_callback(f"Could not remove: {file_path}")
    return summary


def merge_addons(source_path: Path, destination_path: Path, split_lua: bool, formats: list[str], log_callback=None) -> dict:
    summary = OrderedDict(
        AddonsProcessed=0,
        FilesMoved=0,
        LuaFilesMoved=0,
        DuplicatesRemoved=0,
        DuplicateSpaceSaved=0,
        FailedFiles=0,
        BadFormatsRemoved=0,
        BadFormatsSize=0,
        EmptyDirectoriesRemoved=0,
    )

    if not source_path.is_dir():
        raise FileNotFoundError(f"Source path does not exist: {source_path}")

    ensure_directory(destination_path)
    addons = [path for path in source_path.iterdir() if path.is_dir()]
    if not addons:
        return summary

    for addon in addons:
        summary["AddonsProcessed"] += 1
        if log_callback:
            log_callback(f"Processing addon: {addon.name}")

        for file_path in iter_files(addon):
            try:
                relative_path = get_relative_path(addon, file_path)
                is_lua_file = file_path.suffix.lower() == ".lua"
                if split_lua and is_lua_file:
                    target_file = destination_path / LUA_DIR_NAME / normalize_lua_addon_name(addon.name) / relative_path
                else:
                    target_file = destination_path / relative_path

                ensure_directory(target_file.parent)

                if target_file.exists():
                    summary["DuplicatesRemoved"] += 1
                    summary["DuplicateSpaceSaved"] += file_path.stat().st_size
                    file_path.unlink()
                    continue

                shutil.move(str(file_path), str(target_file))
                if split_lua and is_lua_file:
                    summary["LuaFilesMoved"] += 1
                else:
                    summary["FilesMoved"] += 1
            except Exception:
                summary["FailedFiles"] += 1
                if log_callback:
                    log_callback(f"Failed to process file: {file_path}")

        try:
            shutil.rmtree(addon)
        except OSError:
            if log_callback:
                log_callback(f"Could not remove addon folder: {addon}")

    bad_format_summary = remove_bad_model_formats(destination_path, formats, log_callback=log_callback)
    summary["BadFormatsRemoved"] = bad_format_summary["RemovedCount"]
    summary["BadFormatsSize"] = bad_format_summary["RemovedSize"]
    summary["EmptyDirectoriesRemoved"] = remove_empty_directories(destination_path)
    return summary


def get_files_for_split(root_path: Path) -> list[Path]:
    excluded_roots = [
        (root_path / ADDONS_DIR_NAME).resolve(),
        (root_path / LUA_DIR_NAME).resolve(),
    ]
    files = []
    for file_path in iter_files(root_path):
        resolved = file_path.resolve()
        skip_file = False
        for excluded_root in excluded_roots:
            if excluded_root.exists() and resolved.is_relative_to(excluded_root):
                skip_file = True
                break
        if not skip_file:
            files.append(file_path)
    files.sort(key=lambda path: str(path).lower())
    return files


def split_merged_files(destination_path: Path, max_pack_size_bytes: int, delete_original_merged_files: bool) -> dict:
    summary = OrderedDict(
        FilesCopied=0,
        FilesDeleted=0,
        PacksCreated=0,
        TotalBytesCopied=0,
        FailedFiles=0,
        EmptyDirectoriesRemoved=0,
    )

    if not destination_path.is_dir():
        raise FileNotFoundError(f"Destination path does not exist: {destination_path}")

    addons_path = destination_path / ADDONS_DIR_NAME
    ensure_directory(addons_path)

    files = get_files_for_split(destination_path)
    if not files:
        return summary

    current_pack = 1
    current_pack_size = 0
    summary["PacksCreated"] = 1

    for file_path in files:
        try:
            file_size = file_path.stat().st_size
            if current_pack_size > 0 and current_pack_size + file_size > max_pack_size_bytes:
                current_pack += 1
                current_pack_size = 0
                summary["PacksCreated"] = current_pack

            relative_path = get_relative_path(destination_path, file_path)
            target_file = addons_path / str(current_pack) / relative_path
            ensure_directory(target_file.parent)
            shutil.copy2(file_path, target_file)

            summary["FilesCopied"] += 1
            summary["TotalBytesCopied"] += file_size
            current_pack_size += file_size
        except Exception:
            summary["FailedFiles"] += 1

    if delete_original_merged_files:
        for file_path in files:
            try:
                if file_path.exists():
                    file_path.unlink()
                    summary["FilesDeleted"] += 1
            except OSError:
                continue
        summary["EmptyDirectoriesRemoved"] = remove_empty_directories(destination_path)

    return summary


def calculate_folder_size(path: Path) -> int:
    if not path.is_dir():
        return 0
    total = 0
    for file_path in iter_files(path):
        try:
            total += file_path.stat().st_size
        except OSError:
            continue
    return total


def benchmark_merge(source_path: Path) -> dict:
    addons = [path for path in source_path.iterdir() if path.is_dir()]
    total_files = 0
    total_size = 0
    for addon in addons:
        for file_path in iter_files(addon):
            total_files += 1
            try:
                total_size += file_path.stat().st_size
            except OSError:
                continue
    return {
        "AddonFolders": len(addons),
        "TotalFiles": total_files,
        "TotalSize": total_size,
    }


def benchmark_split(destination_path: Path, max_pack_size_bytes: int) -> dict:
    files = get_files_for_split(destination_path)
    total_size = 0
    pack_count = 1 if files else 0
    current_pack_size = 0
    for file_path in files:
        file_size = file_path.stat().st_size
        if current_pack_size > 0 and current_pack_size + file_size > max_pack_size_bytes:
            pack_count += 1
            current_pack_size = 0
        total_size += file_size
        current_pack_size += file_size
    return {
        "TotalFiles": len(files),
        "TotalSize": total_size,
        "PackCount": pack_count,
    }


def parse_max_pack_size_gb(value: str) -> float:
    try:
        parsed = float(value.strip())
        if parsed > 0:
            return parsed
    except Exception:
        pass
    return DEFAULT_MAX_PACK_SIZE_GB


def format_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{num_bytes} B"


class TaskWorker(QtCore.QObject):
    finished = QtCore.Signal(object)
    failed = QtCore.Signal(str)
    log = QtCore.Signal(str)

    def __init__(self, task):
        super().__init__()
        self._task = task

    @QtCore.Slot()
    def run(self):
        try:
            result = self._task(self.log.emit)
            self.finished.emit(result)
        except Exception:
            self.failed.emit(traceback.format_exc())


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GM Collection Optimizer")
        self.resize(980, 720)

        self.thread: QtCore.QThread | None = None
        self.worker: TaskWorker | None = None
        self._task_active = False

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QVBoxLayout(central)

        folders_group = QtWidgets.QGroupBox("Work Folders")
        folders_form = QtWidgets.QFormLayout()
        folders_form.setHorizontalSpacing(8)
        folders_form.setVerticalSpacing(6)

        self.source_edit, source_row = self.make_folder_row("Source folder path...", "Select source folder", self.on_source_browse)
        self.dest_edit, dest_row = self.make_folder_row("Destination folder path...", "Select destination folder", self.on_dest_browse)

        max_pack_row = QtWidgets.QHBoxLayout()
        self.max_pack_edit = QtWidgets.QLineEdit()
        self.max_pack_edit.setFixedWidth(70)
        max_pack_row.addWidget(self.max_pack_edit)
        max_pack_row.addWidget(QtWidgets.QLabel("GB"))
        max_pack_row.addStretch()

        self.inline_folder_size_label = QtWidgets.QLabel("Not calculated yet")

        folders_form.addRow("Source:", source_row)
        folders_form.addRow("Destination:", dest_row)
        folders_form.addRow("Max Pack Size:", max_pack_row)
        folders_form.addRow("Folder Size:", self.inline_folder_size_label)
        folders_group.setLayout(folders_form)
        main_layout.addWidget(folders_group)

        size_row = QtWidgets.QHBoxLayout()
        self.size_label = QtWidgets.QLabel("Folder size: Not calculated yet")
        self.size_label.setStyleSheet("QLabel { padding: 5px; }")
        size_row.addWidget(self.size_label)
        size_row.addStretch()
        main_layout.addLayout(size_row)

        legend_label = QtWidgets.QLabel("💡 <span style='color: #4CAF50;'>Green buttons</span> generally have no downsides and can always be used.")
        legend_label.setTextFormat(QtCore.Qt.RichText)
        main_layout.addWidget(legend_label)

        tip_label = QtWidgets.QLabel("💡 Hover over buttons to see more information about what they do.")
        main_layout.addWidget(tip_label)

        actions_container = QtWidgets.QWidget()
        actions_layout = QtWidgets.QVBoxLayout(actions_container)
        actions_layout.setSpacing(12)

        file_merging_group = QtWidgets.QGroupBox("File Merging")
        file_merging_grid = QtWidgets.QGridLayout()
        file_merging_grid.setHorizontalSpacing(12)
        file_merging_grid.setVerticalSpacing(8)
        self.run_merge_btn = self.add_button(file_merging_grid, 0, "Run Merge", self.on_run_merge, recommended=True, tooltip="Merge all addon folders into the destination folder.")
        self.run_split_btn = self.add_button(file_merging_grid, 1, "Run Split", self.on_run_split, recommended=True, tooltip=rf"Split merged files into numbered addon packs under Destination\{ADDONS_DIR_NAME}.")
        self.run_merge_split_btn = self.add_button(file_merging_grid, 2, "Run Merge + Split", self.on_run_merge_split, recommended=True, tooltip="Merge addons first, then split the result into numbered addon packs.")
        file_merging_group.setLayout(file_merging_grid)
        actions_layout.addWidget(file_merging_group)

        cleanup_group = QtWidgets.QGroupBox("Cleanup Utilities")
        cleanup_grid = QtWidgets.QGridLayout()
        cleanup_grid.setHorizontalSpacing(12)
        cleanup_grid.setVerticalSpacing(8)
        self.remove_bad_formats_btn = self.add_button(cleanup_grid, 0, "Remove unused model formats", self.on_remove_bad_formats, recommended=True, tooltip="Remove .dx80.vtx, .xbox.vtx, .sw.vtx, and .360.vtx files.")
        self.remove_empty_folders_btn = self.add_button(cleanup_grid, 1, "Remove empty folders", self.on_remove_empty_folders, recommended=True, tooltip="Remove empty directories from the destination folder.")
        cleanup_group.setLayout(cleanup_grid)
        actions_layout.addWidget(cleanup_group)

        benchmark_group = QtWidgets.QGroupBox("Benchmark")
        benchmark_grid = QtWidgets.QGridLayout()
        benchmark_grid.setHorizontalSpacing(12)
        benchmark_grid.setVerticalSpacing(8)
        self.benchmark_merge_btn = self.add_button(benchmark_grid, 0, "Benchmark Merge", self.on_benchmark_merge, tooltip="Preview the merge source folder size and file count.")
        self.benchmark_split_btn = self.add_button(benchmark_grid, 1, "Benchmark Split", self.on_benchmark_split, tooltip="Preview the split pack count and size.")
        self.calculate_size_btn = self.add_button(benchmark_grid, 2, "Calculate Folder Size", self.on_calculate_size, tooltip="Calculate and display the destination folder size.")
        benchmark_group.setLayout(benchmark_grid)
        actions_layout.addWidget(benchmark_group)

        actions_layout.addStretch()

        actions_scroll = QtWidgets.QScrollArea()
        actions_scroll.setWidgetResizable(True)
        actions_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        actions_scroll.setWidget(actions_container)
        main_layout.addWidget(actions_scroll, 1)

        progress_row = QtWidgets.QHBoxLayout()
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        progress_row.addWidget(self.progress)
        main_layout.addLayout(progress_row)

        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Status and output will appear here...")
        self.log.setMaximumHeight(140)
        main_layout.addWidget(self.log)

        self.source_edit.editingFinished.connect(self.on_settings_changed)
        self.dest_edit.editingFinished.connect(self.on_settings_changed)
        self.max_pack_edit.editingFinished.connect(self.on_settings_changed)

        self.load_settings_into_ui()

        QtWidgets.QApplication.setStyle("Fusion")
        self.apply_dark_palette()
        self.update_folder_size_display()
        self.write_log("GM Collection Optimizer", "#FFC107")
        self.write_log("Ready. Configure your paths and choose an operation.", "#AAAAAA")
        self.write_log("")

    def make_folder_row(self, placeholder: str, browse_title: str, browse_handler):
        row = QtWidgets.QHBoxLayout()
        edit = QtWidgets.QLineEdit()
        edit.setPlaceholderText(placeholder)
        button = QtWidgets.QPushButton("Browse...")
        button.setFixedWidth(80)
        button.clicked.connect(browse_handler)
        row.addWidget(edit)
        row.addWidget(button)
        return edit, row

    def add_button(self, grid, index: int, text: str, handler, recommended: bool = False, tooltip: str | None = None):
        button = QtWidgets.QPushButton(text)
        button.clicked.connect(handler)
        if recommended:
            button.setStyleSheet("QPushButton { color: #4CAF50; font-weight: bold; }")
        if tooltip:
            button.setToolTip(tooltip)
        grid.addWidget(button, index // 2, index % 2)
        return button

    def load_settings_into_ui(self):
        data = load_settings()
        self.source_edit.setText(str(data.get("sourcePath", DEFAULT_SOURCE_PATH)))
        self.dest_edit.setText(str(data.get("destinationPath", DEFAULT_DESTINATION_PATH)))
        self.max_pack_edit.setText(str(data.get("maxPackSizeGb", DEFAULT_MAX_PACK_SIZE_GB)))

    def on_settings_changed(self):
        try:
            save_settings(self.source_edit.text().strip(), self.dest_edit.text().strip(), self.max_pack_edit.text().strip())
        except Exception as exc:
            print(f"Warning: Could not save settings: {exc}")
        self.update_folder_size_display()

    def apply_dark_palette(self):
        palette = QtGui.QPalette()
        base = QtGui.QColor(45, 45, 45)
        alt = QtGui.QColor(53, 53, 53)
        text = QtGui.QColor(220, 220, 220)
        highlight = QtGui.QColor(42, 130, 218)
        palette.setColor(QtGui.QPalette.Window, alt)
        palette.setColor(QtGui.QPalette.WindowText, text)
        palette.setColor(QtGui.QPalette.Base, base)
        palette.setColor(QtGui.QPalette.AlternateBase, alt)
        palette.setColor(QtGui.QPalette.ToolTipBase, text)
        palette.setColor(QtGui.QPalette.ToolTipText, text)
        palette.setColor(QtGui.QPalette.Text, text)
        palette.setColor(QtGui.QPalette.Button, alt)
        palette.setColor(QtGui.QPalette.ButtonText, text)
        palette.setColor(QtGui.QPalette.BrightText, QtCore.Qt.red)
        palette.setColor(QtGui.QPalette.Highlight, highlight)
        palette.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.black)
        self.setPalette(palette)

    def write_log(self, message: str, color: str = "#DCDCDC"):
        cursor = self.log.textCursor()
        fmt = QtGui.QTextCharFormat()
        fmt.setForeground(QtGui.QColor(color))
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertText(f"{message}\n", fmt)
        self.log.setTextCursor(cursor)
        self.log.ensureCursorVisible()

    def write_log_success(self, message: str):
        self.write_log(f"[OK] {message}", "#4CAF50")

    def write_log_info(self, message: str):
        self.write_log(f"[INFO] {message}", "#64B5F6")

    def write_log_error(self, message: str):
        self.write_log(f"[ERROR] {message}", "#FF5252")

    def clear_log(self):
        self.log.clear()

    def set_busy(self, busy: bool):
        self.progress.setVisible(busy)
        if busy:
            self.progress.setRange(0, 0)
        else:
            self.progress.setRange(0, 1)

    def update_folder_size_display(self):
        dest_path_text = self.dest_edit.text().strip()
        if dest_path_text and Path(dest_path_text).exists():
            size_text = format_size(calculate_folder_size(Path(dest_path_text)))
            self.inline_folder_size_label.setText(size_text)
            self.size_label.setText(f"Folder size: {size_text}")
        else:
            self.inline_folder_size_label.setText("Not calculated yet")
            self.size_label.setText("Folder size: Not calculated yet")

    def choose_folder(self, title: str, initial: str) -> str:
        return QtWidgets.QFileDialog.getExistingDirectory(self, title, initial or "")

    def on_source_browse(self):
        path = self.choose_folder("Select source folder", self.source_edit.text())
        if path:
            self.source_edit.setText(path)
            self.on_settings_changed()

    def on_dest_browse(self):
        path = self.choose_folder("Select destination folder", self.dest_edit.text())
        if path:
            self.dest_edit.setText(path)
            self.on_settings_changed()

    def ensure_split_output_ready(self, dest_path: Path) -> bool:
        addons_path = dest_path / ADDONS_DIR_NAME
        if addons_path.is_dir() and any(addons_path.iterdir()):
            answer = QtWidgets.QMessageBox.question(
                self,
                "Existing addon packs",
                f"Existing addon packs were found at:\n\n{addons_path}\n\nDelete them before splitting?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if answer != QtWidgets.QMessageBox.Yes:
                self.write_log_error("Split cancelled because existing addon packs would conflict with the new output.")
                return False
            shutil.rmtree(addons_path)
        return True

    def ask_yes_no(self, title: str, message: str, default_no: bool = False) -> bool:
        default_button = QtWidgets.QMessageBox.No if default_no else QtWidgets.QMessageBox.Yes
        answer = QtWidgets.QMessageBox.question(
            self,
            title,
            message,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            default_button,
        )
        return answer == QtWidgets.QMessageBox.Yes

    def source_path(self) -> Path | None:
        text = self.source_edit.text().strip()
        return Path(text) if text else None

    def dest_path(self) -> Path | None:
        text = self.dest_edit.text().strip()
        return Path(text) if text else None

    def require_paths(self, need_source: bool, need_dest: bool, dest_must_exist: bool = False):
        source = self.source_path()
        dest = self.dest_path()

        if need_source and not source:
            self.write_log_error("Please fill in the Source path.")
            return None, None
        if need_dest and not dest:
            self.write_log_error("Please fill in the Destination path.")
            return None, None
        if need_source and source and not source.exists():
            self.write_log_error(f"Source path does not exist: {source}")
            return None, None
        if need_dest and dest_must_exist and dest and not dest.exists():
            self.write_log_error(f"Destination path does not exist: {dest}")
            return None, None
        return source, dest

    def start_task(self, description: str, task, on_success):
        if self.thread and self.thread.isRunning():
            QtWidgets.QMessageBox.information(self, "Busy", "Another operation is already running.")
            return

        self._task_active = True
        self.set_busy(True)
        self.write_log_info(f"Starting: {description}")

        self.thread = QtCore.QThread()
        self.worker = TaskWorker(task)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.log.connect(self.write_log_info)
        self.worker.finished.connect(lambda result: self.finish_task(description, result, on_success))
        self.worker.failed.connect(self.fail_task)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.failed.connect(self.worker.deleteLater)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.cleanup_task_refs)
        self.thread.start()

    def finish_task(self, description: str, result, on_success):
        if not self._task_active:
            return
        self._task_active = False
        self.set_busy(False)
        self.write_log_success(f"{description} completed.")
        self.update_folder_size_display()
        on_success(result)

    def fail_task(self, traceback_text: str):
        if not self._task_active:
            return
        self._task_active = False
        self.set_busy(False)
        lines = [line for line in traceback_text.strip().splitlines() if line.strip()]
        if lines:
            self.write_log_error(lines[-1])
        self.write_log_error(traceback_text.strip())

    def cleanup_task_refs(self):
        self.worker = None
        self.thread = None

    def show_merge_summary(self, summary: dict):
        self.write_log("")
        self.write_log("=== Merge Summary ===", "#FFC107")
        self.write_log(f"Addons processed: {summary['AddonsProcessed']}")
        self.write_log(f"Content files moved: {summary['FilesMoved']}")
        if summary.get("LuaFilesMoved"):
            self.write_log(f"Lua files moved separately: {summary['LuaFilesMoved']}")
        self.write_log(f"Duplicates removed: {summary['DuplicatesRemoved']}")
        self.write_log(f"Duplicate space saved: {format_size(summary['DuplicateSpaceSaved'])}")
        self.write_log(f"Unused model files removed: {summary['BadFormatsRemoved']}")
        self.write_log(f"Unused model space freed: {format_size(summary['BadFormatsSize'])}")
        self.write_log(f"Empty directories removed: {summary['EmptyDirectoriesRemoved']}")
        self.write_log(f"Failed files: {summary['FailedFiles']}")

    def show_split_summary(self, summary: dict):
        self.write_log("")
        self.write_log("=== Split Summary ===", "#FFC107")
        self.write_log(f"Packs created: {summary['PacksCreated']}")
        self.write_log(f"Files copied: {summary['FilesCopied']}")
        self.write_log(f"Total copied size: {format_size(summary['TotalBytesCopied'])}")
        self.write_log(f"Original merged files deleted: {summary['FilesDeleted']}")
        self.write_log(f"Empty directories removed: {summary['EmptyDirectoriesRemoved']}")
        self.write_log(f"Failed files: {summary['FailedFiles']}")

    def show_bad_format_summary(self, summary: dict):
        self.write_log("")
        self.write_log("=== Unused Model Format Removal Summary ===", "#FFC107")
        self.write_log(f"Removed files: {summary['RemovedCount']}")
        self.write_log(f"Freed space: {format_size(summary['RemovedSize'])}")
        for file_format in BAD_FORMATS:
            self.write_log(f"{file_format} : {summary['RemovedPerFormat'][file_format]}")

    def on_run_merge(self):
        self.clear_log()
        source, dest = self.require_paths(True, True, False)
        if not source or not dest:
            return

        def task(log_callback):
            return merge_addons(source, dest, True, BAD_FORMATS, log_callback=log_callback)

        self.start_task("Merge Only", task, self.show_merge_summary)

    def on_run_split(self):
        self.clear_log()
        _, dest = self.require_paths(False, True, True)
        if not dest:
            return
        if not self.ensure_split_output_ready(dest):
            return

        max_pack_size_bytes = int(parse_max_pack_size_gb(self.max_pack_edit.text()) * (1024 ** 3))
        delete_original = self.ask_yes_no(
            "Split Option",
            "Delete original merged files after split?\n\nChoose Yes to remove the source merged files after pack creation.",
            default_no=True,
        )

        def task(_log_callback):
            return split_merged_files(dest, max_pack_size_bytes, delete_original)

        self.start_task("Split Only", task, self.show_split_summary)

    def on_run_merge_split(self):
        self.clear_log()
        source, dest = self.require_paths(True, True, False)
        if not source or not dest:
            return
        if dest.exists() and not self.ensure_split_output_ready(dest):
            return

        split_lua = self.ask_yes_no(
            "Merge Option",
            rf"Split Lua files into Destination\{LUA_DIR_NAME}\AddonName during merge?",
            default_no=False,
        )
        delete_original_after_split = self.ask_yes_no(
            "Split Option",
            "Delete original merged files after split?\n\nChoose Yes to remove the source merged files after pack creation.",
            default_no=True,
        )
        max_pack_size_bytes = int(parse_max_pack_size_gb(self.max_pack_edit.text()) * (1024 ** 3))

        def task(log_callback):
            merge_summary = merge_addons(source, dest, split_lua, BAD_FORMATS, log_callback=log_callback)
            split_summary = split_merged_files(dest, max_pack_size_bytes, delete_original_after_split)
            return merge_summary, split_summary

        def on_success(result):
            merge_summary, split_summary = result
            self.show_merge_summary(merge_summary)
            self.show_split_summary(split_summary)

        self.start_task("Merge + Split", task, on_success)

    def on_remove_bad_formats(self):
        self.clear_log()
        _, dest = self.require_paths(False, True, True)
        if not dest:
            return

        def task(log_callback):
            return remove_bad_model_formats(dest, BAD_FORMATS, log_callback=log_callback)

        self.start_task("Remove Unused Model Formats", task, self.show_bad_format_summary)

    def on_remove_empty_folders(self):
        self.clear_log()
        _, dest = self.require_paths(False, True, True)
        if not dest:
            return

        def task(_log_callback):
            return remove_empty_directories(dest)

        def on_success(result):
            self.write_log("")
            self.write_log("=== Empty Folder Removal Summary ===", "#FFC107")
            self.write_log(f"Empty directories removed: {result}")

        self.start_task("Remove Empty Folders", task, on_success)

    def on_benchmark_merge(self):
        self.clear_log()
        source, _ = self.require_paths(True, False)
        if not source:
            return

        self.write_log_info("Benchmark: Analyzing source folder...")
        summary = benchmark_merge(source)
        self.write_log("")
        self.write_log("=== Benchmark: Merge Preview ===", "#FFC107")
        self.write_log(f"Addon folders found: {summary['AddonFolders']}")
        self.write_log(f"Total files: {summary['TotalFiles']}")
        self.write_log(f"Total size: {format_size(summary['TotalSize'])}")
        self.write_log("")
        self.write_log_info("This is a preview only. No files were modified.")

    def on_benchmark_split(self):
        self.clear_log()
        _, dest = self.require_paths(False, True, True)
        if not dest:
            return

        max_gb = parse_max_pack_size_gb(self.max_pack_edit.text())
        max_pack_size_bytes = int(max_gb * (1024 ** 3))
        self.write_log_info("Benchmark: Analyzing destination folder for split preview...")
        summary = benchmark_split(dest, max_pack_size_bytes)
        self.write_log("")
        self.write_log("=== Benchmark: Split Preview ===", "#FFC107")
        self.write_log(f"Total files to split: {summary['TotalFiles']}")
        self.write_log(f"Total size: {format_size(summary['TotalSize'])}")
        self.write_log(f"Estimated packs needed: {summary['PackCount']}")
        self.write_log(f"Max pack size: {max_gb:.2f} GB")
        self.write_log("")
        self.write_log_info("This is a preview only. No files were modified.")

    def on_calculate_size(self):
        self.clear_log()
        _, dest = self.require_paths(False, True, True)
        if not dest:
            return

        def task(_log_callback):
            return calculate_folder_size(dest)

        def on_success(result):
            self.write_log("")
            self.write_log("=== Folder Size ===", "#FFC107")
            self.write_log(f"Destination: {dest}")
            self.write_log(f"Total size: {format_size(result)}")

        self.start_task("Calculate Size", task, on_success)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
