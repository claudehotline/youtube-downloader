"""
全局样式表定义模块，为应用程序提供统一的样式设计
"""

def get_application_style():
    """返回应用程序全局样式表"""
    return """
    /* 全局样式 */
    * {
        font-family: "Microsoft YaHei", "SimHei", sans-serif;
        font-size: 13px;
    }
    
    /* 窗口和部件样式 */
    QMainWindow, QDialog {
        background-color: #f8f9fa;
    }
    
    QWidget {
        color: #333333;
    }
    
    /* 页面标题样式 */
    QLabel#pageTitle {
        font-size: 16px;
        font-weight: bold;
        color: #2c3e50;
        margin: 10px 0;
        padding-bottom: 5px;
        border-bottom: 1px solid #ecf0f1;
    }
    
    /* 按钮样式 */
    QPushButton {
        background-color: #3498db;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
        font-weight: 500;
        min-height: 30px;
    }
    
    QPushButton:hover {
        background-color: #2980b9;
    }
    
    QPushButton:pressed {
        background-color: #1c6ca1;
    }
    
    QPushButton:disabled {
        background-color: #bdc3c7;
        color: #7f8c8d;
    }
    
    /* 特殊功能按钮样式 */
    QPushButton#downloadButton {
        background-color: #27ae60;
        font-weight: bold;
    }
    
    QPushButton#downloadButton:hover {
        background-color: #2ecc71;
    }
    
    QPushButton#downloadButton:pressed {
        background-color: #219653;
    }
    
    QPushButton#cancelButton {
        background-color: #e74c3c;
    }
    
    QPushButton#cancelButton:hover {
        background-color: #c0392b;
    }
    
    QPushButton#cancelButton:pressed {
        background-color: #a93226;
    }
    
    QPushButton#saveButton {
        background-color: #2980b9;
        font-weight: bold;
    }
    
    QPushButton#saveButton:hover {
        background-color: #3498db;
    }
    
    QPushButton#saveButton:pressed {
        background-color: #1c6ca1;
    }
    
    /* 输入框样式 */
    QLineEdit {
        border: 1px solid #bdc3c7;
        border-radius: 4px;
        padding: 6px 8px;
        background-color: white;
        selection-background-color: #3498db;
    }
    
    QLineEdit:focus {
        border: 1px solid #3498db;
    }
    
    /* 下拉框样式 */
    QComboBox {
        border: 1px solid #bdc3c7;
        border-radius: 4px;
        padding: 6px 8px;
        background-color: white;
        selection-background-color: #3498db;
        min-height: 25px;
        min-width: 100px;
    }
    
    QComboBox:focus {
        border: 1px solid #3498db;
    }
    
    QComboBox::drop-down {
        border: none;
        width: 20px;
        subcontrol-origin: padding;
        subcontrol-position: center right;
        padding-right: 5px;
    }
    
    QComboBox::down-arrow {
        image: none;
        width: 10px;
        height: 10px;
        background: #3498db;
        border-radius: 5px;
    }
    
    QComboBox QAbstractItemView {
        border: 1px solid #bdc3c7;
        border-radius: 0px;
        background-color: white;
        selection-background-color: #3498db;
        selection-color: white;
        outline: 0px;
    }
    
    QComboBox QAbstractItemView::item {
        min-height: 20px;
        padding: 5px;
    }
    
    /* 列表部件样式 */
    QListWidget {
        border: 1px solid #bdc3c7;
        border-radius: 4px;
        background-color: white;
        selection-background-color: #3498db;
        selection-color: white;
    }
    
    QListWidget::item {
        padding: 4px 6px;
    }
    
    QListWidget::item:hover {
        background-color: #e8f5fe;
    }
    
    QListWidget::item:selected {
        background-color: #3498db;
        color: white;
    }
    
    /* 分组框样式 */
    QGroupBox {
        font-weight: bold;
        border: 1px solid #d0d0d0;
        border-radius: 6px;
        margin-top: 12px;
        padding: 10px;
        background-color: white;
    }
    
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 10px;
        padding: 0 5px;
        color: #2c3e50;
    }
    
    /* 标签样式 */
    QLabel {
        color: #2c3e50;
    }
    
    /* 进度条样式 */
    QProgressBar {
        border: 1px solid #bdc3c7;
        border-radius: 4px;
        text-align: center;
        background-color: #ecf0f1;
        height: 20px;
    }
    
    QProgressBar::chunk {
        background-color: #3498db;
        border-radius: 3px;
    }
    
    /* 滚动条样式 */
    QScrollBar:vertical {
        border: none;
        background-color: #f0f0f0;
        width: 8px;
        margin: 0px;
    }
    
    QScrollBar::handle:vertical {
        background-color: #c0c0c0;
        min-height: 20px;
        border-radius: 4px;
    }
    
    QScrollBar::handle:vertical:hover {
        background-color: #a0a0a0;
    }
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    
    QScrollBar:horizontal {
        border: none;
        background-color: #f0f0f0;
        height: 8px;
        margin: 0px;
    }
    
    QScrollBar::handle:horizontal {
        background-color: #c0c0c0;
        min-width: 20px;
        border-radius: 4px;
    }
    
    QScrollBar::handle:horizontal:hover {
        background-color: #a0a0a0;
    }
    
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }
    
    /* 文本编辑区样式 */
    QTextEdit {
        border: 1px solid #bdc3c7;
        border-radius: 4px;
        padding: 5px;
        background-color: white;
        selection-background-color: #3498db;
        font-family: 'Consolas', 'Microsoft YaHei', monospace;
        line-height: 1.5;
    }
    
    /* 复选框样式 */
    QCheckBox {
        spacing: 8px;
    }
    
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
    }
    
    QCheckBox::indicator:unchecked {
        border: 1px solid #bdc3c7;
        border-radius: 3px;
        background-color: white;
    }
    
    QCheckBox::indicator:checked {
        border: 1px solid #3498db;
        border-radius: 3px;
        background-color: #3498db;
    }
    """

def get_navigation_button_style():
    """返回导航按钮基础样式"""
    return """
        QPushButton {
            text-align: left;
            padding: 12px;
            padding-left: 15px;
            border: none;
            border-radius: 5px;
            font-size: 14px;
            color: #2c3e50;
            font-weight: 500;
            background-color: transparent;
        }
        QPushButton:hover {
            background-color: #ecf0f1;
        }
    """

def get_active_navigation_button_style():
    """返回激活状态的导航按钮样式"""
    return get_navigation_button_style() + """
        QPushButton {
            background-color: #3498db;
            color: white;
            font-weight: 600;
        }
        QPushButton:hover {
            background-color: #2980b9;
        }
    """ 