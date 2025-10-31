# Drop_receiver.py
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QPushButton, QSizePolicy, QMainWindow
from PySide6.QtCore import Qt, Signal, QEvent # Import QEvent for eventFilter
from PySide6.QtGui import QMouseEvent # Import QMouseEvent for eventFilter
from enum import Enum

class DropMode(Enum):
    """定义拖放接收模式"""
    ONE_SHOT = 1    # 一次性模式：每次拖放都清除旧的，只显示新的
    ACCUMULATE = 2  # 积累模式：每次拖放都添加到现有列表中

class DropReceiverWidget(QWidget):
    """
    一个专门接收拖拽文件/目录的UI组件，支持一次性或积累模式。
    界面包含：顶部显示接收列表（通过一个QLabel作为拖拽区和点击触发区），
    底部显示当前模式，底部提供模式切换和清除按钮。
    当有项目被拖入或内部列表被清除时，发射 `dropped` 信号。
    """
    dropped = Signal(list, list) # 信号发出所有积累的文件和目录
    display_area_clicked = Signal() # 新增信号：当显示区域被点击时发出

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True) # 允许QWidget整体接收外部拖放
        self.setMinimumSize(300, 200)

        self._current_files = []
        self._current_dirs = []
        self._mode = DropMode.ONE_SHOT # 默认模式为一次性

        self._build_ui()
        self._connect_internal_signals() # 连接内部按钮信号
        self._update_display() # 首次初始化显示

        # 确保QLabel的背景被填充，以便样式表中的边框可见
        self._display_label.setAutoFillBackground(True)
        # 在 QLabel 上安装事件过滤器，使其能够捕获点击事件
        self._display_label.installEventFilter(self)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 顶部显示区域：现在是 QLabel，作为拖拽区和点击触发区
        self._display_label = QLabel("将文件或目录拖拽到此处") # 默认提示
        self._display_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._display_label.setWordWrap(True)
        self._display_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) # 确保label可以扩张

        # --- 关键修改：将边框样式应用到 _display_label ---
        self._display_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa; /* 永久的灰色虚线 */
                border-radius: 10px;
                background-color: #f8f8f8; /* 默认浅灰色背景，确保边框可见 */
                font-size: 14px;
                color: #777; /* 默认文字颜色 */
                padding: 10px; /* 增加内边距 */
                /* text-align: left; QLabel默认左对齐，不需要这个*/
            }
        """)
        # --- 关键修改结束 ---

        # QLabel 本身没有 clicked 信号，通过 eventFilter 模拟

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self._display_label) # 将 QLabel 放入 QScrollArea
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame) # 无边框

        main_layout.addWidget(scroll_area, 1) # 占据大部分空间

        # 底部模式提示区域
        self._mode_label = QLabel()
        self._mode_label.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
        self._mode_label.setStyleSheet("font-size: 12px; color: gray; padding-top: 5px;")
        main_layout.addWidget(self._mode_label)

        # 底部控制按钮区域 (一行两列：模式切换 | 清除)
        bottom_buttons_layout = QHBoxLayout()
        bottom_buttons_layout.setSpacing(5) # 按钮间距

        self._mode_toggle_btn = QPushButton("切换模式") # 单个模式切换按钮
        self._clear_btn = QPushButton("清除")

        bottom_buttons_layout.addWidget(self._mode_toggle_btn)
        bottom_buttons_layout.addWidget(self._clear_btn)

        main_layout.addLayout(bottom_buttons_layout)

    def _connect_internal_signals(self):
        """连接内部按钮的信号"""
        self._mode_toggle_btn.clicked.connect(self._toggle_mode)
        self._clear_btn.clicked.connect(self.clear_dropped_items)

    def _toggle_mode(self):
        """在一次性模式和积累模式之间切换"""
        if self._mode == DropMode.ONE_SHOT:
            self.set_mode(DropMode.ACCUMULATE)
        else:
            self.set_mode(DropMode.ONE_SHOT)

    def _update_display(self):
        """更新显示文件列表和模式提示"""
        display_text = []
        if self._current_files:
            display_text.append("<b>文件:</b>")
            display_text.extend([f"- {Path(f).name}" for f in self._current_files])
        if self._current_dirs:
            display_text.append("<b>目录:</b>")
            display_text.extend([f"- {Path(d).name}" for d in self._current_dirs])

        if not display_text:
            self._display_label.setText("将文件或目录拖拽到此处 或 点击选择") # 恢复默认提示文本
            self._display_label.setStyleSheet(self._get_default_display_label_stylesheet()) # 恢复默认样式
        else:
            # 使用HTML来格式化列表，并保持左对齐
            self._display_label.setText(
                "<div style='text-align:left;'>" + "<br>".join(display_text) + "</div>"
            )
            # 保持边框样式，只恢复文字颜色
            self._display_label.setStyleSheet(self._get_default_display_label_stylesheet(text_color="#333", bg_color="#f8f8f8"))


        mode_text = f"当前模式: {'一次性返回' if self._mode == DropMode.ONE_SHOT else '积累模式'}"
        self._mode_label.setText(mode_text)

        # 更新模式切换按钮的文本，显示“下次”将切换到的模式
        if self._mode == DropMode.ONE_SHOT:
            self._mode_toggle_btn.setText("切换到积累模式")
        else:
            self._mode_toggle_btn.setText("切换到一次性模式")

    def _get_default_display_label_stylesheet(self, border_color="#aaa", bg_color="#f8f8f8", text_color="#777"):
        """生成 _display_label 的默认样式表，方便在不同状态间切换"""
        return f"""
            QLabel {{
                border: 2px dashed {border_color};
                border-radius: 10px;
                background-color: {bg_color};
                font-size: 14px;
                color: {text_color};
                padding: 10px;
            }}
        """

    # --- 外部调用接口 ---
    def set_mode(self, mode: DropMode):
        """设置拖放接收模式"""
        if not isinstance(mode, DropMode):
            raise ValueError("Mode must be an instance of DropMode enum.")
        self._mode = mode
        if self._mode == DropMode.ONE_SHOT:
            pass
        self._update_display()

    def get_mode(self) -> DropMode:
        """获取当前拖放接收模式"""
        return self._mode

    def set_items(self, files: list, dirs: list):
        """
        外部方法：直接设置显示区域的文件和目录。
        用于从其他选择器同步数据。
        """
        self._current_files = list(files)
        self._current_dirs = list(dirs)
        self._current_files.sort()
        self._current_dirs.sort()
        self._update_display()
        # 注意：这里不应该发出 'dropped' 信号，因为这不是用户拖放操作。

    def clear_dropped_items(self):
        """清除所有已积累的文件和目录"""
        self._current_files = []
        self._current_dirs = []
        self._update_display()
        self.dropped.emit([], []) # 发送空列表表示清除

    def get_dropped_items(self) -> tuple[list, list]:
        """获取当前积累的所有文件和目录"""
        return list(self._current_files), list(self._current_dirs)

    # --- 拖放事件处理 (QWidget整体接收，视觉反馈应用到 _display_label) ---
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            # --- 关键修改：动态修改 _display_label 的样式表 ---
            self._display_label.setStyleSheet(self._get_default_display_label_stylesheet(
                border_color="#0078d7", # 蓝色虚线
                bg_color="#e6f2fa",    # 浅蓝色背景
                text_color="#005a9e"   # 蓝色文字
            ))
            # --- 关键修改结束 ---
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        # --- 关键修改：恢复 _display_label 的默认样式 ---
        self._display_label.setStyleSheet(self._get_default_display_label_stylesheet())
        # --- 关键修改结束 ---

    def dropEvent(self, event):
        self.dragLeaveEvent(event) # 恢复样式

        dropped_files, dropped_dirs = [], []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path:
                if Path(path).exists():
                    if Path(path).is_dir():
                        dropped_dirs.append(path)
                    else:
                        dropped_files.append(path)
                else:
                    print(f"Warning: Dropped item '{path}' does not exist.")


        if self._mode == DropMode.ONE_SHOT:
            self._current_files = dropped_files
            self._current_dirs = dropped_dirs
        elif self._mode == DropMode.ACCUMULATE:
            for f in dropped_files:
                if f not in self._current_files:
                    self._current_files.append(f)
            for d in dropped_dirs:
                if d not in self._current_dirs:
                    self._current_dirs.append(d)

        self._current_files.sort()
        self._current_dirs.sort()

        self._update_display() # 更新UI显示
        self.dropped.emit(self._current_files, self._current_dirs) # 发送当前所有积累的结果

    # --- 事件过滤器，用于捕获 QLabel 的点击事件 ---
    def eventFilter(self, source, event):
        if source == self._display_label and event.type() == QEvent.MouseButtonPress:
            mouse_event: QMouseEvent = event # Type hint for clarity
            if mouse_event.button() == Qt.LeftButton:
                self.display_area_clicked.emit()
                return True # 消耗事件，不让它传播到QLabel的父级或默认处理
        return super().eventFilter(source, event)


# --- 独立运行演示 --- (使用 QMainWindow)
if __name__ == "__main__":
    app = QApplication(sys.argv)

    class DemoMainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("`DropReceiverWidget` 独立演示")
            self.resize(400, 500)

            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            main_layout = QVBoxLayout(central_widget)
            main_layout.setContentsMargins(20, 20, 20, 20)

            self.drop_area = DropReceiverWidget()

            self.result_label_external = QLabel("外部信号接收结果将显示在这里...")
            self.result_label_external.setWordWrap(True)
            self.result_label_external.setStyleSheet("font-style: italic; color: #555;")

            # 模拟外部对 display_area_clicked 信号的连接
            self.drop_area.display_area_clicked.connect(lambda: print("\n--- 收到 DropReceiverWidget 显示区点击信号 ---"))
            self.drop_area.dropped.connect(self._on_dropped_items_external)

            main_layout.addWidget(self.drop_area)
            main_layout.addWidget(self.result_label_external)
            main_layout.addStretch()

        def _on_dropped_items_external(self, files, dirs):
            output_text = []
            if files:
                output_text.append("文件: " + ", ".join([Path(f).name for f in files]))
            if dirs:
                output_text.append("目录: " + ", ".join([Path(d).name for d in dirs]))

            if not output_text:
                self.result_label_external.setText("外部信号接收结果: (列表已清空)")
            else:
                self.result_label_external.setText("外部信号接收结果:<br>" + "<br>".join(output_text))

            current_files, current_dirs = self.drop_area.get_dropped_items()
            print(f"\n--- 外部信号接收 ---")
            print(f"信号 Files: {files}")
            print(f"信号 Dirs: {dirs}")
            print(f"Widget内部状态 Files: {current_files}")
            print(f"Widget内部状态 Dirs: {current_dirs}")
            print(f"当前模式: {self.drop_area.get_mode().name}")
            print(f"--------------------")

    main_win = DemoMainWindow()
    main_win.show()
    sys.exit(app.exec())