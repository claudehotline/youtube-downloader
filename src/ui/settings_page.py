from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                        QLabel, QLineEdit, QPushButton, QComboBox, 
                        QCheckBox, QGroupBox, QMessageBox, QFileDialog)
from PySide6.QtCore import Signal


class SettingsPage(QWidget):
    settings_saved = Signal(dict)
    
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 添加页面标题
        title_label = QLabel("设置")
        title_label.setObjectName("pageTitle")
        layout.addWidget(title_label)
        
        # 下载设置组
        download_settings_group = QGroupBox("下载设置")
        download_settings_layout = QVBoxLayout(download_settings_group)
        
        # 保存位置设置
        output_layout = QHBoxLayout()
        output_label = QLabel("默认保存位置:")
        self.output_path = QLineEdit()
        self.output_path.setText(self.config_manager.get("General", "DownloadPath", fallback=""))
        browse_button = QPushButton("浏览...")
        browse_button.clicked.connect(self.browse_output_dir)
        
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(browse_button)
        
        # 线程数设置
        threads_layout = QHBoxLayout()
        threads_layout.setSpacing(10)
        threads_label = QLabel("下载线程数:")
        self.threads_spinner = QComboBox()
        for i in [1, 2, 4, 8, 10, 16]:
            self.threads_spinner.addItem(str(i), i)
        # 从配置中读取线程数
        threads = self.config_manager.getint("General", "Threads", fallback=10)
        self.threads_spinner.setCurrentText(str(threads))
        threads_layout.setContentsMargins(0, 5, 0, 5)
        
        threads_layout.addWidget(threads_label)
        threads_layout.addWidget(self.threads_spinner)
        threads_layout.addStretch()
        
        # 封面图片下载选项
        thumbnail_layout = QHBoxLayout()
        self.download_thumbnail_checkbox = QCheckBox("下载视频封面图片")
        download_thumbnail = self.config_manager.getboolean("General", "DownloadThumbnail", fallback=True)
        self.download_thumbnail_checkbox.setChecked(download_thumbnail)
        
        thumbnail_layout.addWidget(self.download_thumbnail_checkbox)
        thumbnail_layout.addStretch()
        
        download_settings_layout.addLayout(output_layout)
        download_settings_layout.addLayout(threads_layout)
        download_settings_layout.addLayout(thumbnail_layout)
        
        # 浏览器Cookie设置组
        cookie_group = QGroupBox("浏览器Cookie设置")
        cookie_layout = QVBoxLayout(cookie_group)
        
        # 是否使用Cookie
        self.use_cookie_checkbox = QCheckBox("使用浏览器Cookie（可解决一些视频的访问限制）")
        # 从配置中读取是否使用cookie
        use_cookies = self.config_manager.getboolean("Cookies", "UseCookies", fallback=False)
        self.use_cookie_checkbox.setChecked(use_cookies)
        
        # 浏览器选择
        browser_layout = QHBoxLayout()
        browser_layout.setSpacing(10)
        browser_label = QLabel("选择浏览器:")
        self.browser_combo = QComboBox()
        self.browser_combo.addItem("Chrome", "chrome")
        self.browser_combo.addItem("Firefox", "firefox")
        self.browser_combo.addItem("Edge", "edge")
        self.browser_combo.addItem("Safari", "safari")
        self.browser_combo.addItem("Opera", "opera")
        self.browser_combo.addItem("Brave", "brave")
        # 从配置中读取浏览器
        browser = self.config_manager.get("Cookies", "Browser", fallback="chrome")
        index = self.browser_combo.findData(browser)
        if index >= 0:
            self.browser_combo.setCurrentIndex(index)
        self.browser_combo.setEnabled(use_cookies)  # 根据配置启用或禁用
        browser_layout.setContentsMargins(0, 5, 0, 5)
        
        browser_layout.addWidget(browser_label)
        browser_layout.addWidget(self.browser_combo)
        browser_layout.addStretch()
        
        # 连接复选框信号
        self.use_cookie_checkbox.toggled.connect(self.browser_combo.setEnabled)
        
        cookie_layout.addWidget(self.use_cookie_checkbox)
        cookie_layout.addLayout(browser_layout)
        
        # UI设置组
        ui_settings_group = QGroupBox("界面设置")
        ui_settings_layout = QVBoxLayout(ui_settings_group)
        
        # 主题选择
        theme_layout = QHBoxLayout()
        theme_layout.setSpacing(10)
        theme_label = QLabel("界面主题:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("默认 (Fusion)", "Fusion")
        self.theme_combo.addItem("深色 (Dark)", "Dark")
        self.theme_combo.addItem("Chrome深色 (ChromeDark)", "ChromeDark")
        self.theme_combo.addItem("浅蓝 (LightBlue)", "LightBlue")
        # 从配置中读取主题
        theme = self.config_manager.get("UI", "Theme", fallback="Fusion")
        index = self.theme_combo.findData(theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
        theme_layout.setContentsMargins(0, 5, 0, 5)
        
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        
        ui_settings_layout.addLayout(theme_layout)
        
        # 保存设置按钮
        save_settings_button = QPushButton("保存设置")
        save_settings_button.setObjectName("saveButton")
        save_settings_button.clicked.connect(self.save_settings)
        
        # 添加所有设置组到页面
        layout.addWidget(download_settings_group)
        layout.addWidget(cookie_group)
        layout.addWidget(ui_settings_group)
        layout.addWidget(save_settings_button)
        layout.addStretch()
    
    def browse_output_dir(self):
        """浏览并选择输出目录"""
        directory = QFileDialog.getExistingDirectory(
            self, "选择保存目录", self.output_path.text()
        )
        if directory:
            self.output_path.setText(directory)
    
    def save_settings(self):
        """保存设置"""
        # 保存下载路径
        download_path = self.output_path.text()
        self.config_manager.set("General", "DownloadPath", download_path)
        
        # 保存线程数
        threads = self.threads_spinner.currentText()
        self.config_manager.set("General", "Threads", threads)
        
        # 保存封面下载设置
        download_thumbnail = str(self.download_thumbnail_checkbox.isChecked())
        self.config_manager.set("General", "DownloadThumbnail", download_thumbnail)
        
        # 保存Cookie设置
        use_cookies = str(self.use_cookie_checkbox.isChecked())
        self.config_manager.set("Cookies", "UseCookies", use_cookies)
        
        browser = self.browser_combo.currentData()
        self.config_manager.set("Cookies", "Browser", browser)
        
        # 保存主题设置
        theme = self.theme_combo.currentData()
        self.config_manager.set("UI", "Theme", theme)
        
        # 显示保存成功消息
        QMessageBox.information(self, "设置保存", "设置已保存")
        
        # 发送设置已保存信号，携带当前设置
        settings = {
            'download_path': download_path,
            'threads': int(threads),
            'download_thumbnail': self.download_thumbnail_checkbox.isChecked(),
            'use_cookies': self.use_cookie_checkbox.isChecked(),
            'browser': browser,
            'theme': theme
        }
        self.settings_saved.emit(settings)
    
    def load_settings_from_config(self):
        """从配置文件重新加载设置"""
        # 加载下载路径
        download_path = self.config_manager.get("General", "DownloadPath", fallback="")
        self.output_path.setText(download_path)
        
        # 加载线程数
        threads = self.config_manager.getint("General", "Threads", fallback=10)
        index = self.threads_spinner.findData(threads)
        if index >= 0:
            self.threads_spinner.setCurrentIndex(index)
        else:
            self.threads_spinner.setCurrentText(str(threads))
        
        # 加载封面下载设置
        download_thumbnail = self.config_manager.getboolean("General", "DownloadThumbnail", fallback=True)
        self.download_thumbnail_checkbox.setChecked(download_thumbnail)
        
        # 加载Cookie设置
        use_cookies = self.config_manager.getboolean("Cookies", "UseCookies", fallback=False)
        self.use_cookie_checkbox.setChecked(use_cookies)
        
        browser = self.config_manager.get("Cookies", "Browser", fallback="chrome")
        index = self.browser_combo.findData(browser)
        if index >= 0:
            self.browser_combo.setCurrentIndex(index)
        self.browser_combo.setEnabled(use_cookies)
        
        # 加载主题设置
        theme = self.config_manager.get("UI", "Theme", fallback="Fusion")
        index = self.theme_combo.findData(theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
        else:
            self.theme_combo.setCurrentText(theme) 