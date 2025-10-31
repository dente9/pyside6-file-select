#File_dialog
import sys
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QTreeView, QListWidget, QListWidgetItem, QFileSystemModel,
    QLabel, QAbstractItemView, QCheckBox, QApplication,
    QDialog, QDialogButtonBox, QMainWindow, QMessageBox
)
from PySide6.QtCore import Qt, QStandardPaths, Signal, QDir
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QKeyEvent
class FilePickerWidget(QWidget):
    picked = Signal(list, list)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True) # Enable drop events for this widget (for general window dropping)
        self._build_ui()
        self._connect_signals()
        self.model.setRootPath(str(Path.cwd()))
        self.model.directoryLoaded.connect(self._on_dir_loaded)
    def _build_ui(self):
        main = QVBoxLayout(self)
        nav = QHBoxLayout()
        self.btn_desktop = QPushButton("桌面")
        self.btn_download = QPushButton("下载")
        self.btn_project = QPushButton("项目目录")
        self.cb_hidden = QCheckBox("显示隐藏项")
        self.cb_hidden.setChecked(False) # Default to not showing hidden items
        self.btn_refresh = QPushButton("刷新")
        for w in (self.btn_desktop, self.btn_download, self.btn_project, self.cb_hidden, self.btn_refresh):
            nav.addWidget(w)
        nav.addStretch()
        main.addLayout(nav)
        path = QHBoxLayout()
        path.addWidget(QLabel("路径："))
        self.line_path = QLineEdit()
        path.addWidget(self.line_path)
        main.addLayout(path)
        mid = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(QLabel("显示区（双击添加）"))
        self.model = QFileSystemModel()
        self._apply_filter()
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setSortingEnabled(True)
        for i in range(1, self.model.columnCount()):
            self.tree.setColumnHidden(i, True) # Hide Type, Size, Date Modified columns
        left.addWidget(self.tree)
        mid.addLayout(left, 2)
        right = QVBoxLayout()
        right.addWidget(QLabel("暂存区（双击删除）"))
        self.staging = QListWidget()
        right.addWidget(self.staging)
        mid.addLayout(right, 1)
        main.addLayout(mid, 1)
        self.drag_hint_label = QLabel("可拖动文件/文件夹到此窗口任意位置快速定位")
        self.drag_hint_label.setAlignment(Qt.AlignCenter)
        self.drag_hint_label.setStyleSheet("color: gray;")
        main.addWidget(self.drag_hint_label)
    def _apply_filter(self):
        f = QDir.AllEntries | QDir.NoDotAndDotDot
        if self.cb_hidden.isChecked():
            f |= QDir.Hidden
        self.model.setFilter(f)
    def _connect_signals(self):
        self.btn_desktop.clicked.connect(
            lambda: self.goto_path(QStandardPaths.writableLocation(QStandardPaths.DesktopLocation)))
        self.btn_download.clicked.connect(
            lambda: self.goto_path(QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)))
        self.btn_project.clicked.connect(lambda: self.goto_path(str(Path.cwd())))
        self.btn_refresh.clicked.connect(self.refresh)
        self.cb_hidden.toggled.connect(lambda: (self._apply_filter(), self.refresh()))
        self.tree.doubleClicked.connect(self.add_to_staging)
        self.staging.itemDoubleClicked.connect(self.remove_from_staging)
    def _show_error_message(self, title: str, message: str):
        """Helper method to display a QMessageBox error."""
        dialog_parent = self.window() # Get the top-level QWidget (FilePickerDialog)
        msg_box = QMessageBox(dialog_parent)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setDefaultButton(QMessageBox.Ok)
        msg_box.exec()
    def goto_path(self, path: str):
        path_str = str(path)
        if not os.path.isdir(path_str) and not os.path.isfile(path_str):
            print(f"DEBUG: Path does not exist or is not a file/directory: {path_str}")
            self._show_error_message("路径错误", f"文件/文件夹路径 '{path_str}' 不存在或不是有效的文件/目录，请检查。")
            return
        target_path = Path(path_str)
        if target_path.is_file():
            target_path = target_path.parent
        if not target_path.is_dir():
            print(f"DEBUG: Target path is not a directory after adjustment: {target_path}")
            self._show_error_message("路径错误", f"文件/文件夹路径 '{target_path}' 无效，请检查。")
            return
        idx = self.model.index(str(target_path))
        if not idx.isValid():
            print(f"DEBUG: Model index is not valid for path: {target_path}")
            if sys.platform == "win32":
                drive_root = target_path.anchor # e.g., "C:\"
                if drive_root and self.model.rootPath() != drive_root:
                    self.model.setRootPath(drive_root) # 设置模型根路径为目标驱动器根目录
                    idx = self.model.index(str(target_path)) # 再次尝试获取索引
            else: # Linux/macOS
                 if self.model.rootPath() != "/":
                     self.model.setRootPath("/")
                     idx = self.model.index(str(target_path)) # 再次尝试获取索引
            if not idx.isValid(): # 修复后如果仍然无效
                print(f"DEBUG: Model index still not valid after root adjustment for path: {target_path}")
                self._show_error_message("路径错误", f"无法访问路径 '{target_path}'，可能权限不足或路径无效。请检查。")
                return
        self.line_path.setText(str(target_path)) # 路径栏更新为实际导航的有效路径
        self.tree.expand(idx)
        self.tree.setCurrentIndex(idx)
        self.tree.scrollTo(idx, QAbstractItemView.PositionAtCenter)
    def refresh(self):
        cur = self.line_path.text()
        self.model.setRootPath("") # Clear cache and force re-scan
        if os.path.isdir(cur):
            self.goto_path(cur)
    def add_to_staging(self, idx_or_path):
        """Adds a path to the staging area. Can accept a QModelIndex or a string path."""
        if isinstance(idx_or_path, str):
            path = idx_or_path
        else: # Assume QModelIndex
            path = self.model.filePath(idx_or_path)
        if not os.path.exists(path):
            print(f"Warning: Attempted to add non-existent path to staging: {path}")
            return
        if self.staging.findItems(path, Qt.MatchExactly):
            return # Prevent duplicates
        self.staging.addItem(path)
    def remove_from_staging(self, item: QListWidgetItem):
        self.staging.takeItem(self.staging.row(item))
    def _on_dir_loaded(self, path: str):
        if Path(path) == Path.cwd():
            self.model.directoryLoaded.disconnect(self._on_dir_loaded) # Disconnect after first use
            self.goto_path(str(Path.cwd()))
        else:
            pass # Keep relying on goto_path's robustness
    def get_result(self):
        files, dirs = [], []
        for i in range(self.staging.count()):
            p = self.staging.item(i).text()
            if os.path.exists(p):
                (dirs if os.path.isdir(p) else files).append(p)
            else:
                print(f"Warning: Path '{p}' in staging area no longer exists, skipping.")
        return files, dirs
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if os.path.exists(file_path):
                    self.goto_path(file_path)
                    event.acceptProposedAction()
                    return
        event.ignore()
class FilePickerDialog(QDialog):
    """独立窗口壳，解决‘确定/取消’无法关闭问题"""
    picked = Signal(list, list)  # 转发
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("文件选择器")
        self.resize(900, 700)
        self.picker = FilePickerWidget(self) # Pass self as parent to the picker
        self.btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel) # Store btn_box as instance variable
        self.btn_box.accepted.connect(self._forward_and_accept)
        self.btn_box.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addWidget(self.picker)
        lay.addWidget(self.btn_box)
    def _forward_and_accept(self):
        """Gathers results from the picker, emits the dialog's signal, and accepts the dialog."""
        files, dirs = self.picker.get_result()
        self.picked.emit(files, dirs)
        print("[FilePickerDialog]: Dialog accepted (explicitly by button).") # Debug print
        super().accept() # Call the QDialog's accept method directly
    def reject(self):
        print("[FilePickerDialog]: Dialog rejected (explicitly).") # Debug print
        super().reject()
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self.picker.line_path.hasFocus():
                print("[FilePickerDialog]: Enter key pressed in path line edit, calling goto_path.")
                self.picker.goto_path(self.picker.line_path.text())
                event.accept() # Crucially, accept the event to prevent it from propagating further
                return # Stop processing this event
        super().keyPressEvent(event)
if __name__ == "__main__":
    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("文件选择器测试应用")
            self.resize(400, 200)
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            layout = QVBoxLayout(central_widget)
            self.open_picker_button = QPushButton("打开文件选择器")
            self.result_label = QLabel("暂无选择结果")
            self.result_label.setTextInteractionFlags(Qt.TextSelectableByMouse) # Allow selecting text
            self.result_label.setWordWrap(True) # Ensure long paths wrap
            layout.addWidget(self.open_picker_button)
            layout.addWidget(self.result_label)
            layout.addStretch()
            self.open_picker_button.clicked.connect(self._open_file_picker)
        def _open_file_picker(self):
            dialog = FilePickerDialog(self) # Pass self as parent for proper dialog modality
            dialog.picked.connect(self._handle_picked_result)
            result = dialog.exec()
            if result == QDialog.Accepted:
                print("\n[MainWindow]: 文件选择器对话框已接受。")
            else:
                print("\n[MainWindow]: 文件选择器对话框已取消。")
        def _handle_picked_result(self, files: list, dirs: list):
            result_text = "选择结果:\n"
            if files:
                result_text += f"  文件 ({len(files)}):\n" + "\n".join([f"    - {Path(f).name}" for f in files]) + "\n"
            if dirs:
                result_text += f"  目录 ({len(dirs)}):\n" + "\n".join([f"    - {Path(d).name}" for d in dirs]) + "\n"
            if not files and not dirs:
                result_text = "未选择任何文件或目录"
            self.result_label.setText(result_text)
            print(f"[MainWindow]: 完整文件路径: {files}")
            print(f"[MainWindow]: 完整目录路径: {dirs}")
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())