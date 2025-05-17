"""
全局样式表定义模块，为应用程序提供统一的样式设计
"""

def get_application_style():
    """返回亮色主题的全局样式表"""
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

def get_dark_style():
    """返回深色主题的全局样式表"""
    return """
    /* 全局样式 */
    * {
        font-family: "Microsoft YaHei", "SimHei", sans-serif;
        font-size: 13px;
    }
    
    /* 窗口和部件样式 */
    QMainWindow, QDialog {
        background-color: #1e1e1e;
    }
    
    QWidget {
        color: rgba(255, 255, 255, 0.85);
    }
    
    /* 页面标题样式 */
    QLabel#pageTitle {
        font-size: 16px;
        font-weight: bold;
        color: #82b1ff;
        margin: 10px 0;
        padding-bottom: 5px;
        border-bottom: 1px solid #383838;
    }
    
    /* 按钮样式 */
    QPushButton {
        background-color: #3a4d6b;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
        font-weight: 400;
        min-height: 30px;
    }
    
    QPushButton:hover {
        background-color: #4a6285;
    }
    
    QPushButton:pressed {
        background-color: #2d3e59;
    }
    
    QPushButton:disabled {
        background-color: #2a2a2a;
        color: rgba(255, 255, 255, 0.38);
    }
    
    /* 特殊功能按钮样式 */
    QPushButton#downloadButton {
        background-color: #2d6a4f;
        font-weight: bold;
        color: rgba(255, 255, 255, 0.9);
    }
    
    QPushButton#downloadButton:hover {
        background-color: #40916c;
    }
    
    QPushButton#downloadButton:pressed {
        background-color: #1b4332;
    }
    
    QPushButton#cancelButton {
        background-color: #7d3c3c;
        color: rgba(255, 255, 255, 0.9);
    }
    
    QPushButton#cancelButton:hover {
        background-color: #a25050;
    }
    
    QPushButton#cancelButton:pressed {
        background-color: #5c2c2c;
    }
    
    QPushButton#saveButton {
        background-color: #1565c0;
        font-weight: bold;
    }
    
    QPushButton#saveButton:hover {
        background-color: #1976d2;
    }
    
    QPushButton#saveButton:pressed {
        background-color: #0d47a1;
    }
    
    /* 输入框样式 */
    QLineEdit {
        border: 1px solid #383838;
        border-radius: 4px;
        padding: 6px 8px;
        background-color: #2a2a2a;
        selection-background-color: #3a4d6b;
        color: rgba(255, 255, 255, 0.85);
    }
    
    QLineEdit:focus {
        border: 1px solid #4a6285;
    }
    
    /* 下拉框样式 */
    QComboBox {
        border: 1px solid #383838;
        border-radius: 4px;
        padding: 6px 8px;
        background-color: #2a2a2a;
        selection-background-color: #3a4d6b;
        color: rgba(255, 255, 255, 0.85);
        min-height: 25px;
        min-width: 100px;
    }
    
    QComboBox:focus {
        border: 1px solid #4a6285;
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
        background: #4a6285;
        border-radius: 5px;
    }
    
    QComboBox QAbstractItemView {
        border: 1px solid #383838;
        border-radius: 0px;
        background-color: #2a2a2a;
        selection-background-color: #3a4d6b;
        selection-color: white;
        outline: 0px;
    }
    
    QComboBox QAbstractItemView::item {
        min-height: 20px;
        padding: 5px;
        color: rgba(255, 255, 255, 0.85);
    }
    
    /* 列表部件样式 */
    QListWidget {
        border: 1px solid #383838;
        border-radius: 4px;
        background-color: #2a2a2a;
        selection-background-color: #3a4d6b;
        selection-color: white;
    }
    
    QListWidget::item {
        padding: 4px 6px;
        color: rgba(255, 255, 255, 0.85);
    }
    
    QListWidget::item:hover {
        background-color: #333333;
    }
    
    QListWidget::item:selected {
        background-color: #3a4d6b;
        color: white;
    }
    
    /* 分组框样式 */
    QGroupBox {
        font-weight: bold;
        border: 1px solid #383838;
        border-radius: 6px;
        margin-top: 12px;
        padding: 10px;
        background-color: #252525;
    }
    
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 10px;
        padding: 0 5px;
        color: #82b1ff;
    }
    
    /* 标签样式 */
    QLabel {
        color: rgba(255, 255, 255, 0.85);
    }
    
    /* 进度条样式 */
    QProgressBar {
        border: 1px solid #383838;
        border-radius: 4px;
        text-align: center;
        background-color: #2a2a2a;
        height: 20px;
        color: rgba(255, 255, 255, 0.85);
    }
    
    QProgressBar::chunk {
        background-color: #3a4d6b;
        border-radius: 3px;
    }
    
    /* 滚动条样式 */
    QScrollBar:vertical {
        border: none;
        background-color: #252525;
        width: 8px;
        margin: 0px;
    }
    
    QScrollBar::handle:vertical {
        background-color: #454545;
        min-height: 20px;
        border-radius: 4px;
    }
    
    QScrollBar::handle:vertical:hover {
        background-color: #555555;
    }
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    
    QScrollBar:horizontal {
        border: none;
        background-color: #252525;
        height: 8px;
        margin: 0px;
    }
    
    QScrollBar::handle:horizontal {
        background-color: #454545;
        min-width: 20px;
        border-radius: 4px;
    }
    
    QScrollBar::handle:horizontal:hover {
        background-color: #555555;
    }
    
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }
    
    /* 文本编辑区样式 */
    QTextEdit {
        border: 1px solid #383838;
        border-radius: 4px;
        padding: 5px;
        background-color: #2a2a2a;
        selection-background-color: #3a4d6b;
        font-family: 'Consolas', 'Microsoft YaHei', monospace;
        line-height: 1.5;
        color: rgba(255, 255, 255, 0.85);
    }
    
    /* 复选框样式 */
    QCheckBox {
        spacing: 8px;
        color: rgba(255, 255, 255, 0.85);
    }
    
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
    }
    
    QCheckBox::indicator:unchecked {
        border: 1px solid #454545;
        border-radius: 3px;
        background-color: #2a2a2a;
    }
    
    QCheckBox::indicator:checked {
        border: 1px solid #3a4d6b;
        border-radius: 3px;
        background-color: #3a4d6b;
    }
    """

def get_dark_navigation_button_style():
    """返回深色主题的导航按钮基础样式"""
    return """
        QPushButton {
            text-align: left;
            padding: 12px;
            padding-left: 15px;
            border: none;
            border-radius: 5px;
            font-size: 14px;
            color: #ecf0f1;
            font-weight: 500;
            background-color: transparent;
        }
        QPushButton:hover {
            background-color: #34495e;
        }
    """

def get_dark_active_navigation_button_style():
    """返回深色主题激活状态的导航按钮样式"""
    return get_dark_navigation_button_style() + """
        QPushButton {
            background-color: #3498db;
            color: white;
            font-weight: 600;
        }
        QPushButton:hover {
            background-color: #2980b9;
        }
    """

def get_light_theme_style():
    """返回全新的浅色主题样式表"""
    return """
    /* 全局样式 */
    * {
        font-family: "Microsoft YaHei", "SimHei", sans-serif;
        font-size: 13px;
    }
    
    /* 窗口和部件样式 */
    QMainWindow, QDialog {
        background-color: #f5f7fa;
    }
    
    QWidget {
        color: #2c3e50;
    }
    
    /* 页面标题样式 */
    QLabel#pageTitle {
        font-size: 16px;
        font-weight: bold;
        color: #1565c0;
        margin: 10px 0;
        padding-bottom: 5px;
        border-bottom: 1px solid #e1e5ea;
    }
    
    /* 按钮样式 */
    QPushButton {
        background-color: #64b5f6;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
        font-weight: 500;
        min-height: 30px;
    }
    
    QPushButton:hover {
        background-color: #42a5f5;
    }
    
    QPushButton:pressed {
        background-color: #1e88e5;
    }
    
    QPushButton:disabled {
        background-color: #e1e5ea;
        color: #a0aec0;
    }
    
    /* 特殊功能按钮样式 */
    QPushButton#downloadButton {
        background-color: #4caf50;
        font-weight: bold;
        color: white;
    }
    
    QPushButton#downloadButton:hover {
        background-color: #43a047;
    }
    
    QPushButton#downloadButton:pressed {
        background-color: #388e3c;
    }
    
    QPushButton#cancelButton {
        background-color: #ef5350;
        color: white;
    }
    
    QPushButton#cancelButton:hover {
        background-color: #e53935;
    }
    
    QPushButton#cancelButton:pressed {
        background-color: #d32f2f;
    }
    
    QPushButton#saveButton {
        background-color: #1976d2;
        font-weight: bold;
        color: white;
    }
    
    QPushButton#saveButton:hover {
        background-color: #1565c0;
    }
    
    QPushButton#saveButton:pressed {
        background-color: #0d47a1;
    }
    
    /* 输入框样式 */
    QLineEdit {
        border: 1px solid #cbd5e0;
        border-radius: 4px;
        padding: 6px 8px;
        background-color: white;
        selection-background-color: #64b5f6;
        color: #2c3e50;
    }
    
    QLineEdit:focus {
        border: 1px solid #64b5f6;
    }
    
    /* 下拉框样式 */
    QComboBox {
        border: 1px solid #cbd5e0;
        border-radius: 4px;
        padding: 6px 8px;
        background-color: white;
        selection-background-color: #64b5f6;
        color: #2c3e50;
        min-height: 25px;
        min-width: 100px;
    }
    
    QComboBox:focus {
        border: 1px solid #64b5f6;
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
        background: #64b5f6;
        border-radius: 5px;
    }
    
    QComboBox QAbstractItemView {
        border: 1px solid #cbd5e0;
        border-radius: 0px;
        background-color: white;
        selection-background-color: #64b5f6;
        selection-color: white;
        outline: 0px;
    }
    
    QComboBox QAbstractItemView::item {
        min-height: 20px;
        padding: 5px;
        color: #2c3e50;
    }
    
    /* 列表部件样式 */
    QListWidget {
        border: 1px solid #cbd5e0;
        border-radius: 4px;
        background-color: white;
        selection-background-color: #64b5f6;
        selection-color: white;
    }
    
    QListWidget::item {
        padding: 4px 6px;
        color: #2c3e50;
    }
    
    QListWidget::item:hover {
        background-color: #e6f2ff;
    }
    
    QListWidget::item:selected {
        background-color: #64b5f6;
        color: white;
    }
    
    /* 分组框样式 */
    QGroupBox {
        font-weight: bold;
        border: 1px solid #e1e5ea;
        border-radius: 6px;
        margin-top: 12px;
        padding: 10px;
        background-color: #ffffff;
    }
    
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 10px;
        padding: 0 5px;
        color: #1565c0;
    }
    
    /* 标签样式 */
    QLabel {
        color: #2c3e50;
    }
    
    /* 进度条样式 */
    QProgressBar {
        border: 1px solid #cbd5e0;
        border-radius: 4px;
        text-align: center;
        background-color: #f7fafc;
        height: 20px;
        color: #2c3e50;
    }
    
    QProgressBar::chunk {
        background-color: #64b5f6;
        border-radius: 3px;
    }
    
    /* 滚动条样式 */
    QScrollBar:vertical {
        border: none;
        background-color: #f7fafc;
        width: 8px;
        margin: 0px;
    }
    
    QScrollBar::handle:vertical {
        background-color: #cbd5e0;
        min-height: 20px;
        border-radius: 4px;
    }
    
    QScrollBar::handle:vertical:hover {
        background-color: #a0aec0;
    }
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    
    QScrollBar:horizontal {
        border: none;
        background-color: #f7fafc;
        height: 8px;
        margin: 0px;
    }
    
    QScrollBar::handle:horizontal {
        background-color: #cbd5e0;
        min-width: 20px;
        border-radius: 4px;
    }
    
    QScrollBar::handle:horizontal:hover {
        background-color: #a0aec0;
    }
    
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }
    
    /* 文本编辑区样式 */
    QTextEdit {
        border: 1px solid #cbd5e0;
        border-radius: 4px;
        padding: 5px;
        background-color: white;
        selection-background-color: #64b5f6;
        font-family: 'Consolas', 'Microsoft YaHei', monospace;
        line-height: 1.5;
        color: #2c3e50;
    }
    
    /* 复选框样式 */
    QCheckBox {
        spacing: 8px;
        color: #2c3e50;
    }
    
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
    }
    
    QCheckBox::indicator:unchecked {
        border: 1px solid #cbd5e0;
        border-radius: 3px;
        background-color: white;
    }
    
    QCheckBox::indicator:checked {
        border: 1px solid #64b5f6;
        border-radius: 3px;
        background-color: #64b5f6;
    }
    """

def get_light_theme_navigation_button_style():
    """返回新浅色主题的导航按钮基础样式"""
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
            background-color: #e6f2ff;
        }
    """

def get_light_theme_active_navigation_button_style():
    """返回新浅色主题激活状态的导航按钮样式"""
    return get_light_theme_navigation_button_style() + """
        QPushButton {
            background-color: #64b5f6;
            color: white;
            font-weight: 600;
        }
        QPushButton:hover {
            background-color: #42a5f5;
        }
    """ 