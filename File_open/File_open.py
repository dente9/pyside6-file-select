# File_open.py
import sys
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, QMainWindow,)
from PySide6.QtCore import Signal
from .File_dialog import FilePickerDialog
from .Drop_receiver import DropReceiverWidget, DropMode

class FileOpenWidget(QWidget):
    picked = Signal(list, list) # 最终选中的文件和目录列表

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._connect_signals()

        # 用于存储 DropReceiverWidget 和 FilePickerDialog 整合后的最终结果
        self._final_selected_files = []
        self._final_selected_dirs = []

        # 初始化 DropReceiverWidget 显示
        self._update_drop_receiver_display()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0) # 紧凑布局
        main_layout.setSpacing(0)

        # 顶部是 DropReceiverWidget
        self.drop_receiver = DropReceiverWidget()
        main_layout.addWidget(self.drop_receiver)

    def _connect_signals(self):
        # 连接 DropReceiverWidget 的点击信号，以激活 FilePickerDialog
        self.drop_receiver.display_area_clicked.connect(self._open_file_dialog)

        # 连接 DropReceiverWidget 的 dropped 信号，以同步内部状态和转发
        self.drop_receiver.dropped.connect(self._on_drop_receiver_dropped)

    def _open_file_dialog(self):
        """打开文件选择对话框，并处理其返回结果"""
        dialog = FilePickerDialog(self) # 以此widget为父级

        # 预加载当前 FileOpenWidget 维护的最终文件列表到 FilePickerDialog 的暂存区
        # 注意：这里需要访问 dialog.picker (FilePickerWidget实例) 来调用其 add_to_staging 方法
        for f_path in self._final_selected_files:
            dialog.picker.add_to_staging(f_path)
        for d_path in self._final_selected_dirs:
            dialog.picker.add_to_staging(d_path)

        # 连接对话框的picked信号，处理其返回结果
        dialog.picked.connect(self._on_file_dialog_picked_result)

        dialog.exec() # 以模态方式运行对话框

    def _on_file_dialog_picked_result(self, files: list, dirs: list):
        """处理 FilePickerDialog 返回的结果，并同步到 _final_selected_files/_dirs"""
        current_mode = self.drop_receiver.get_mode()

        if current_mode == DropMode.ONE_SHOT:
            self._final_selected_files = files
            self._final_selected_dirs = dirs
        elif current_mode == DropMode.ACCUMULATE:
            # 避免重复添加
            for f in files:
                if f not in self._final_selected_files:
                    self._final_selected_files.append(f)
            for d in dirs:
                if d not in self._final_selected_dirs:
                    self._final_selected_dirs.append(d)

        # 始终排序以保持显示一致性
        self._final_selected_files.sort()
        self._final_selected_dirs.sort()

        # 更新 DropReceiverWidget 的显示，使其反映最终结果
        self._update_drop_receiver_display()
        # 发出 FileOpenWidget 自己的 picked 信号
        self.picked.emit(self._final_selected_files, self._final_selected_dirs)


    def _on_drop_receiver_dropped(self, files: list, dirs: list):
        """当 DropReceiverWidget 内部状态改变时（例如外部拖放或清除），同步到 _final_selected_files/_dirs 并发出信号"""
        # DropReceiverWidget 的 dropped 信号已经包含了根据其模式处理后的完整列表
        # 所以直接用它的结果更新 _final_selected_files/_dirs
        self._final_selected_files = files
        self._final_selected_dirs = dirs
        # 更新 DropReceiverWidget 的显示（尽管它自己已经更新，这里是确保一致性）
        self._update_drop_receiver_display()
        # 转发 FileOpenWidget 自己的 picked 信号
        self.picked.emit(self._final_selected_files, self._final_selected_dirs)

    def _update_drop_receiver_display(self):
        """更新 DropReceiverWidget 的显示内容，使其与 _final_selected_files/_dirs 同步"""
        self.drop_receiver.set_items(self._final_selected_files, self._final_selected_dirs)


    # --- 外部集成接口 ---
    def set_drop_mode(self, mode: DropMode):
        """设置拖放接收模式"""
        self.drop_receiver.set_mode(mode)

    def get_drop_mode(self) -> DropMode:
        """获取当前拖放接收模式"""
        return self.drop_receiver.get_mode()

    def clear_all_items(self):
        """清除所有已选择/拖放的文件和目录"""
        # 调用 drop_receiver 的清除方法，它会更新其内部状态并发出 dropped 信号，
        # 进而触发 _on_drop_receiver_dropped 来更新 _final_selected_files/_dirs 并发出 picked 信号。
        self.drop_receiver.clear_dropped_items()

    def get_current_selection(self) -> tuple[list, list]:
        """获取当前最终选择的文件和目录"""
        return list(self._final_selected_files), list(self._final_selected_dirs)


# --- 独立运行演示 ---
if __name__ == "__main__":
    app = QApplication(sys.argv)

    class MainDemoApp(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("终极文件选择器演示")
            self.resize(500, 600)

            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            main_layout = QVBoxLayout(central_widget)
            main_layout.setContentsMargins(20, 20, 20, 20)

            # 实例化终极文件选择器部件
            self.file_open_widget = FileOpenWidget()

            # 外部显示最终结果的 QLabel
            self.final_result_label = QLabel("外部监听到的最终选择结果将显示在这里...")
            self.final_result_label.setWordWrap(True)
            self.final_result_label.setStyleSheet("font-style: italic; color: #555;")

            # 连接 FileOpenWidget 的 picked 信号
            self.file_open_widget.picked.connect(self._on_final_picked)

            main_layout.addWidget(self.file_open_widget)
            main_layout.addWidget(self.final_result_label)
            main_layout.addStretch()

        def _on_final_picked(self, files: list, dirs: list):
            output_text = []
            if files:
                output_text.append("文件: " + ", ".join([Path(f).name for f in files]))
            if dirs:
                output_text.append("目录: " + ", ".join([Path(d).name for d in dirs]))

            if not output_text:
                self.final_result_label.setText("外部监听到的最终结果: (列表已清空)")
            else:
                self.final_result_label.setText("外部监听到的最终结果:<br>" + "<br>".join(output_text))

            print(f"\n--- 外部监听到的最终结果 ---")
            print(f"Files: {files}")
            print(f"Dirs: {dirs}")
            print(f"--------------------------")
            print(f"通过 get_current_selection(): {self.file_open_widget.get_current_selection()}")


    main_win = MainDemoApp()
    main_win.show()
    sys.exit(app.exec())