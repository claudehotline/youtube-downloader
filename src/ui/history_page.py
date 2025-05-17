from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                        QLabel, QPushButton, QGroupBox, QTextEdit)
from PySide6.QtCore import Signal
import time


class HistoryPage(QWidget):
    clear_log_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 添加历史记录和日志区域
        history_title = QLabel("下载历史记录")
        history_title.setObjectName("pageTitle")
        
        # 操作日志区域
        log_group = QGroupBox("操作日志")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(500)  # 设置最大高度
        self.log_text.setPlaceholderText("此处将显示详细操作信息...")
        
        # 添加清除日志按钮
        clear_log_button = QPushButton("清除日志")
        clear_log_button.clicked.connect(self.on_clear_log_clicked)
        
        log_layout.addWidget(self.log_text)
        log_layout.addWidget(clear_log_button)
        
        layout.addWidget(history_title)
        layout.addWidget(log_group)
        layout.addStretch()
    
    def on_clear_log_clicked(self):
        """清除日志"""
        self.log_text.clear()
        self.clear_log_requested.emit()
    
    def add_log_message(self, message, error=False, debug=False):
        """添加消息到日志区域"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        
        # 构建带有样式的HTML消息
        if error:
            html_message = f'<p style="margin:3px 0;"><span style="color:#e74c3c;font-weight:bold;">[{timestamp}] {message}</span></p>'
        elif debug:
            html_message = f'<p style="margin:3px 0;"><span style="color:#7f8c8d;">[{timestamp}] {message}</span></p>'
        else:
            html_message = f'<p style="margin:3px 0;"><span style="color:#2980b9;">[{timestamp}] {message}</span></p>'
        
        # 添加到日志文本编辑器
        self.log_text.append(html_message)
        
        # 将滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum()) 