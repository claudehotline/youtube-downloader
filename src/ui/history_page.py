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
        history_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        # 操作日志区域
        log_group = QGroupBox("操作日志")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(500)  # 设置最大高度
        self.log_text.setPlaceholderText("此处将显示详细操作信息...")
        
        # 设置日志文本编辑器的样式
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 4px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
                line-height: 1.5;
                padding: 8px;
                color: #333333;
            }
        """)
        
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
        # 根据消息类型设置样式
        if error:
            category = "错误"
            category_style = "color:#ffffff; background-color:#d9534f; font-weight:bold; padding:2px 5px; border-radius:3px;"
            bg_color = "#ffebee"
            border_color = "#d9534f"
        elif debug:
            category = "调试"
            category_style = "color:#ffffff; background-color:#5bc0de; font-weight:bold; padding:2px 5px; border-radius:3px;"
            bg_color = "#e3f2fd"
            border_color = "#5bc0de"
        else:
            category = "信息"
            category_style = "color:#ffffff; background-color:#5cb85c; font-weight:bold; padding:2px 5px; border-radius:3px;"
            bg_color = "#e8f5e9"
            border_color = "#5cb85c"
        
        # 添加时间戳
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        
        # 格式化消息，使用HTML提高可读性
        formatted_message = f"""
        <div style="margin-bottom:8px; background-color:{bg_color}; padding:8px; border:1px solid {border_color}; border-radius:4px;">
            <div style="margin-bottom:5px;">
                <span style="{category_style}">{category}</span>
                <span style="margin-left:10px; color:#666666; font-size:12px;">{timestamp}</span>
            </div>
            <div style="color:#333333; margin-left:5px; font-weight:normal; word-wrap:break-word;">
                {message}
            </div>
        </div>
        """
        
        # 添加消息并滚动到底部
        self.log_text.append(formatted_message)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum()) 