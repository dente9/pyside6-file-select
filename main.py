# main_app.py
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMainWindow, QPushButton
from PySide6.QtCore import Qt
from File_open.File_open import FileOpenWidget, DropMode


class MainApplicationWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("最终应用：文件选择器集成演示")
        self.resize(600, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 1. 实例化 FileOpenWidget
        self.file_selector = FileOpenWidget()

        # 2. 外部显示 FileOpenWidget 实时更新的结果
        self.realtime_status_label = QLabel("FileOpenWidget 实时状态: (无选择)")
        self.realtime_status_label.setWordWrap(True)
        self.realtime_status_label.setStyleSheet("font-style: italic; color: #666;")
        self.file_selector.picked.connect(self._update_realtime_status)

        # 3. 外部的“确定”按钮
        bottom_layout = QHBoxLayout()
        self.set_mode_btn = QPushButton("切换到积累模式 (外部设置)")
        self.final_confirm_btn = QPushButton("最终确定选择")
        self.clear_all_btn = QPushButton("清除所有选择 (外部操作)")

        self.set_mode_btn.clicked.connect(self._toggle_external_mode)
        self.final_confirm_btn.clicked.connect(self._confirm_selection)
        self.clear_all_btn.clicked.connect(self._clear_external_selection)

        bottom_layout.addWidget(self.set_mode_btn)
        bottom_layout.addWidget(self.clear_all_btn)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.final_confirm_btn)

        # 4. 外部显示最终确定结果的 QLabel
        self.final_result_display = QLabel("点击 '最终确定选择' 后的结果将显示在这里。")
        self.final_result_display.setWordWrap(True)
        self.final_result_display.setStyleSheet("font-weight: bold; color: #0078d7; background-color: #e6f2fa; padding: 10px; border-radius: 5px;")


        main_layout.addWidget(self.file_selector)
        main_layout.addWidget(self.realtime_status_label)
        main_layout.addLayout(bottom_layout)
        main_layout.addWidget(self.final_result_display)
        main_layout.addStretch()

        self._current_external_mode = DropMode.ONE_SHOT # 跟踪外部设置的模式

    def _update_realtime_status(self, files: list, dirs: list):
        """更新实时状态标签，响应 FileOpenWidget 的 picked 信号"""
        output_text = []
        if files:
            output_text.append(f"文件 ({len(files)}): " + ", ".join([Path(f).name for f in files]))
        if dirs:
            output_text.append(f"目录 ({len(dirs)}): " + ", ".join([Path(d).name for d in dirs]))

        if not output_text:
            self.realtime_status_label.setText("FileOpenWidget 实时状态: (无选择)")
        else:
            self.realtime_status_label.setText("FileOpenWidget 实时状态:<br>" + "<br>".join(output_text))

        print(f"\n[MainApp] 实时更新 - Files: {files}, Dirs: {dirs}")

    def _toggle_external_mode(self):
        """外部切换 FileOpenWidget 的模式"""
        if self._current_external_mode == DropMode.ONE_SHOT:
            self.file_selector.set_drop_mode(DropMode.ACCUMULATE)
            self._current_external_mode = DropMode.ACCUMULATE
            self.set_mode_btn.setText("切换到一次性模式 (外部设置)")
            print("[MainApp] 外部切换模式到: ACCUMULATE")
        else:
            self.file_selector.set_drop_mode(DropMode.ONE_SHOT)
            self._current_external_mode = DropMode.ONE_SHOT
            self.set_mode_btn.setText("切换到积累模式 (外部设置)")
            print("[MainApp] 外部切换模式到: ONE_SHOT")


    def _clear_external_selection(self):
        """外部调用 FileOpenWidget 的清除功能"""
        self.file_selector.clear_all_items()
        self.final_result_display.setText("点击 '最终确定选择' 后的结果将显示在这里。") # 清空最终结果显示
        print("[MainApp] 外部触发清除所有选择。")

    def _confirm_selection(self):
        """处理外部“确定”按钮点击，获取并显示最终结果"""
        final_files, final_dirs = self.file_selector.get_current_selection()

        output_text = []
        if final_files:
            output_text.append(f"<b>文件 ({len(final_files)}):</b><br>" + "<br>".join([f"  - {Path(f).name}" for f in final_files]))
        if final_dirs:
            output_text.append(f"<b>目录 ({len(final_dirs)}):</b><br>" + "<br>".join([f"  - {Path(d).name}" for d in final_dirs]))

        if not output_text:
            self.final_result_display.setText("<b>最终确定结果:</b> 无任何选择。")
        else:
            self.final_result_display.setText("<b>最终确定结果:</b><br>" + "<br>".join(output_text))

        print(f"\n[MainApp] 最终确定选择 - Files: {final_files}, Dirs: {final_dirs}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainApplicationWindow()
    main_window.show()
    sys.exit(app.exec())