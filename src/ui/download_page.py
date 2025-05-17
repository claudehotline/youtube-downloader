from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                        QLabel, QLineEdit, QPushButton, QComboBox, 
                        QListWidget, QGroupBox, QProgressBar, QMessageBox,
                        QApplication)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QPixmap, QImage
import requests


class DownloadPage(QWidget):
    fetch_info_requested = Signal(str, bool, str)
    download_requested = Signal(str, str, str, list, str, int, bool, str)
    cancel_fetch_requested = Signal()
    cancel_download_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.video_info = None
        self.thumbnail_url = None
        self.thumbnail_data = None
        self.loading_timer = None
        self.loading_dots = 0
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 添加页面标题
        title_label = QLabel("下载YouTube视频")
        title_label.setObjectName("pageTitle")
        layout.addWidget(title_label)
        
        # URL 输入区域
        url_layout = QHBoxLayout()
        url_label = QLabel("YouTube 视频链接:")
        self.url_input = QLineEdit()
        self.fetch_button = QPushButton("获取信息")
        self.fetch_button.clicked.connect(self.on_fetch_button_clicked)
        self.cancel_fetch_button = QPushButton("取消获取")
        self.cancel_fetch_button.clicked.connect(self.on_cancel_fetch_clicked)
        self.cancel_fetch_button.setEnabled(False)
        
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.fetch_button)
        url_layout.addWidget(self.cancel_fetch_button)
        layout.addLayout(url_layout)
        
        # 视频信息区域
        info_group = QGroupBox("视频信息")
        info_layout = QHBoxLayout()
        info_group.setLayout(info_layout)
        
        # 左侧封面区域
        left_layout = QVBoxLayout()
        self.thumbnail_label = QLabel("请输入视频链接并获取信息")
        self.thumbnail_label.setFixedSize(320, 180)
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setStyleSheet("color: #888888;")
        left_layout.addWidget(self.thumbnail_label)
        left_layout.addStretch()
        
        # 右侧信息区域
        right_layout = QVBoxLayout()
        
        self.title_label = QLabel("")
        self.title_label.setWordWrap(True)
        self.duration_label = QLabel("")
        self.uploader_label = QLabel("")
        
        right_layout.addWidget(self.title_label)
        right_layout.addWidget(self.duration_label)
        right_layout.addWidget(self.uploader_label)
        right_layout.addStretch()
        
        # 将左右布局添加到信息区域
        info_layout.addLayout(left_layout, 4)  # 左侧占40%
        info_layout.addLayout(right_layout, 6)  # 右侧占60%
        
        layout.addWidget(info_group)
        
        # 格式选择区域
        options_layout = QHBoxLayout()
        
        # 视频和音频格式选择
        formats_group = QGroupBox("格式选择")
        formats_layout = QVBoxLayout()
        formats_group.setLayout(formats_layout)
        
        # 视频格式选择
        video_format_layout = QVBoxLayout()
        video_format_layout.setSpacing(8)
        video_format_label = QLabel("选择视频格式:")
        self.video_format_combo = QComboBox()
        self.video_format_combo.setEnabled(False)
        video_format_layout.addWidget(video_format_label)
        video_format_layout.addWidget(self.video_format_combo)
        
        # 音频格式选择
        audio_format_layout = QVBoxLayout()
        audio_format_layout.setSpacing(8)
        audio_format_label = QLabel("选择音频格式:")
        self.audio_format_combo = QComboBox()
        self.audio_format_combo.setEnabled(False)
        audio_format_layout.addWidget(audio_format_label)
        audio_format_layout.addWidget(self.audio_format_combo)
        
        formats_layout.addLayout(video_format_layout)
        formats_layout.addSpacing(10)
        formats_layout.addLayout(audio_format_layout)
        formats_layout.addStretch()  # 添加弹性空间，使内容靠上排列
        
        # 字幕选择区域
        subtitle_group = QGroupBox("字幕选择")
        subtitle_layout = QVBoxLayout()
        subtitle_group.setLayout(subtitle_layout)
        
        self.subtitle_list = QListWidget()
        self.subtitle_list.setEnabled(False)
        self.subtitle_list.setSelectionMode(QListWidget.MultiSelection)
        self.subtitle_list.setMinimumWidth(100)
        self.subtitle_list.setMaximumWidth(300)
        # 设置字幕列表的固定高度
        self.subtitle_list.setMaximumHeight(100)
        
        subtitle_layout.addWidget(QLabel("选择字幕语言:"))
        subtitle_layout.addWidget(self.subtitle_list)
        subtitle_layout.addStretch()  # 添加弹性空间，使内容靠上排列
        
        # 设置整个格式选择区域的高度限制
        formats_group.setMaximumHeight(180)
        subtitle_group.setMaximumHeight(180)
        
        options_layout.addWidget(formats_group, 7)  # 占70%的宽度
        options_layout.addWidget(subtitle_group, 3)  # 占30%的宽度
        
        layout.addLayout(options_layout)
        
        # 下载区域
        download_group = QGroupBox("下载选项")
        download_options_layout = QVBoxLayout()
        download_group.setLayout(download_options_layout)
        
        self.download_button = QPushButton("开始下载")
        self.download_button.setObjectName("downloadButton")
        self.download_button.setEnabled(False)
        self.download_button.clicked.connect(self.on_download_button_clicked)
        
        # 添加取消按钮
        self.cancel_button = QPushButton("取消下载")
        self.cancel_button.setObjectName("cancelButton")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.on_cancel_button_clicked)
        
        # 创建按钮布局
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.download_button)
        buttons_layout.addWidget(self.cancel_button)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        
        self.status_label = QLabel("等待中...")
        self.status_label.setWordWrap(True)
        
        self.progress_detail_label = QLabel("")
        self.progress_detail_label.setWordWrap(True)
        
        download_options_layout.addLayout(buttons_layout)
        download_options_layout.addWidget(self.progress_bar)
        download_options_layout.addWidget(self.status_label)
        download_options_layout.addWidget(self.progress_detail_label)
        
        layout.addWidget(download_group)
    
    def on_fetch_button_clicked(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "警告", "请输入有效的YouTube视频URL")
            return
        
        self.status_label.setText("正在获取视频信息...")
        self.video_format_combo.setEnabled(False)
        self.audio_format_combo.setEnabled(False)
        self.subtitle_list.setEnabled(False)
        self.download_button.setEnabled(False)
        self.fetch_button.setEnabled(False)
        self.cancel_fetch_button.setEnabled(True)
        
        self.start_loading_animation()
        QApplication.processEvents()
        
        # 发送获取信息信号，参数分别为URL、是否使用cookie、浏览器类型
        self.fetch_info_requested.emit(url, False, None)
    
    def on_cancel_fetch_clicked(self):
        self.cancel_fetch_requested.emit()
    
    def on_download_button_clicked(self):
        if not self.video_info:
            QMessageBox.warning(self, "警告", "请先获取视频信息")
            return
        
        # 获取选择的视频格式
        video_format = self.video_format_combo.currentData()
        video_format_text = self.video_format_combo.currentText()
        
        # 获取选择的音频格式
        audio_format = self.audio_format_combo.currentData()
        audio_format_text = self.audio_format_combo.currentText()
        
        # 获取选择的字幕
        selected_subtitles = []
        selected_subtitles_text = []
        for i in range(self.subtitle_list.count()):
            item = self.subtitle_list.item(i)
            if item.isSelected():
                selected_subtitles.append(item.data(Qt.UserRole))
                selected_subtitles_text.append(item.text())
        
        # 检查视频和音频格式
        if not video_format:
            QMessageBox.warning(self, "警告", "请选择视频格式")
            return
            
        if not audio_format:
            QMessageBox.warning(self, "警告", "请选择音频格式")
            return
            
        # 检查字幕选择
        if not selected_subtitles:
            QMessageBox.warning(self, "警告", "请至少选择一种字幕")
            return
        
        # 确认选择
        message = "您选择的下载内容:\n\n"
        
        if video_format:
            message += f"视频格式: {video_format_text}\n"
        else:
            message += "视频格式: 不下载视频\n"
            
        if audio_format:
            message += f"音频格式: {audio_format_text}\n"
        else:
            message += "音频格式: 不下载音频\n"
            
        if selected_subtitles:
            message += f"字幕: {', '.join(selected_subtitles_text)}\n"
        else:
            message += "字幕: 不下载字幕\n"
            
        message += "\n确认开始下载吗？"
        
        # 显示确认对话框
        reply = QMessageBox.question(self, "确认下载", message, 
                                      QMessageBox.Yes | QMessageBox.No, 
                                      QMessageBox.Yes)
        if reply == QMessageBox.No:
            return
        
        # 发送下载信号
        self.download_requested.emit(
            self.url_input.text(),
            video_format,
            audio_format,
            selected_subtitles,
            "",  # 输出目录，会在MainWindow中设置
            10,  # 线程数，会在MainWindow中设置
            False,  # 是否使用cookie
            None   # 浏览器类型
        )
        
        self.download_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在准备下载...")
    
    def on_cancel_button_clicked(self):
        self.cancel_button.setEnabled(False)
        self.status_label.setText("正在取消下载...")
        self.cancel_download_requested.emit()
    
    def start_loading_animation(self):
        """启动加载动画"""
        self.loading_dots = 0
        if not self.loading_timer:
            self.loading_timer = QTimer(self)
            self.loading_timer.timeout.connect(self.update_loading_animation)
        self.loading_timer.start(300)
        
        self.thumbnail_label.setText("正在加载视频信息...")
        self.thumbnail_label.setStyleSheet("color: #0066cc;")
    
    def update_loading_animation(self):
        """更新加载动画"""
        self.loading_dots = (self.loading_dots + 1) % 4
        dots = "." * self.loading_dots
        self.thumbnail_label.setText(f"正在加载视频信息{dots}")
    
    def stop_loading_animation(self):
        """停止加载动画"""
        if self.loading_timer and self.loading_timer.isActive():
            self.loading_timer.stop()
        
        if not self.video_info:
            self.thumbnail_label.setText("请输入视频链接并获取信息")
            self.thumbnail_label.setStyleSheet("color: #888888;")
    
    def on_info_fetched(self, video_info):
        """处理获取到的视频信息"""
        self.stop_loading_animation()
        self.video_info = video_info
        self.update_video_info()
        self.status_label.setText("视频信息获取成功")
        self.download_button.setEnabled(True)
        self.fetch_button.setEnabled(True)
        self.cancel_fetch_button.setEnabled(False)
    
    def on_fetch_error(self, error_message):
        """处理获取视频信息失败的情况"""
        self.stop_loading_animation()
        QMessageBox.critical(self, "错误", f"获取视频信息失败: {error_message}")
        self.status_label.setText("获取视频信息失败")
        self.fetch_button.setEnabled(True)
        self.cancel_fetch_button.setEnabled(False)
    
    def update_video_info(self):
        """更新界面上的视频信息"""
        if not self.video_info:
            return
        
        # 更新视频基本信息
        self.title_label.setText(f"标题: {self.video_info['title']}")
        
        # 格式化时长
        duration_secs = self.video_info.get('duration', 0)
        hours, remainder = divmod(duration_secs, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            duration_str = f"{int(hours)}:{int(minutes):02d}:{int(seconds):02d}"
        else:
            duration_str = f"{int(minutes):02d}:{int(seconds):02d}"
        
        self.duration_label.setText(f"时长: {duration_str}")
        self.uploader_label.setText(f"上传者: {self.video_info.get('uploader', '未知')}")
        
        # 加载缩略图
        self.thumbnail_url = self.video_info.get('thumbnail')
        if self.thumbnail_url:
            try:
                response = requests.get(self.thumbnail_url)
                if response.status_code == 200:
                    self.thumbnail_data = response.content
                    image = QImage.fromData(self.thumbnail_data)
                    pixmap = QPixmap.fromImage(image)
                    self.thumbnail_label.setPixmap(pixmap.scaled(
                        self.thumbnail_label.size(), 
                        Qt.KeepAspectRatio, 
                        Qt.SmoothTransformation
                    ))
                    self.thumbnail_label.setStyleSheet("")
            except Exception:
                self.thumbnail_label.setText("无法加载缩略图")
                self.thumbnail_label.setStyleSheet("color: red;")
        
        # 清空并启用格式选择框
        self.video_format_combo.clear()
        self.video_format_combo.setEnabled(True)
        self.audio_format_combo.clear()
        self.audio_format_combo.setEnabled(True)
        
        # 添加"不下载"选项
        self.video_format_combo.addItem("不下载视频", "")
        self.audio_format_combo.addItem("不下载音频", "")
        
        # 分别提取视频和音频格式
        formats = self.video_info.get('formats', [])
        
        # 添加视频格式
        for fmt in formats:
            format_id = fmt.get('format_id', '')
            ext = fmt.get('ext', '')
            resolution = fmt.get('resolution', 'N/A')
            vcodec = fmt.get('vcodec', 'none')
            
            # 只处理有视频的格式
            if vcodec != 'none':
                format_desc = f"[{format_id}] {resolution} ({ext})"
                self.video_format_combo.addItem(format_desc, format_id)
        
        # 添加音频格式
        for fmt in formats:
            format_id = fmt.get('format_id', '')
            ext = fmt.get('ext', '')
            acodec = fmt.get('acodec', 'none')
            abr = fmt.get('abr', 'N/A')
            
            # 只处理有音频的格式
            if acodec != 'none':
                format_desc = f"[{format_id}] {abr}k ({ext})"
                self.audio_format_combo.addItem(format_desc, format_id)
        
        # 更新字幕选择
        self.subtitle_list.clear()
        self.subtitle_list.setEnabled(True)
        
        subtitles = self.video_info.get('subtitles', {})
        for lang_code, subtitle_info in subtitles.items():
            language = subtitle_info[0].get('name', lang_code)
            item_text = f"{language} ({lang_code})"
            self.subtitle_list.addItem(item_text)
            self.subtitle_list.item(self.subtitle_list.count()-1).setData(Qt.UserRole, lang_code)
    
    def update_progress(self, percent, message):
        """更新下载进度"""
        self.progress_bar.setValue(percent)
        
        # 从消息中提取下载状态和详细信息
        if "下载中" in message:
            # 状态标签只显示简单状态
            self.status_label.setText("正在下载中...")
            # 详情标签显示速度和剩余时间
            self.progress_detail_label.setText(message)
        elif "合并" in message:
            self.status_label.setText("正在合并音视频...")
            self.progress_detail_label.setText("")
        elif "准备" in message:
            self.status_label.setText("正在准备下载...")
            self.progress_detail_label.setText("")
        elif "取消" in message:
            self.status_label.setText("下载已取消")
            self.progress_detail_label.setText("")
            self.download_complete(False, "下载已取消")
        elif "完成" in message:
            self.status_label.setText("下载完成")
            self.progress_detail_label.setText("")
        elif "失败" in message:
            self.status_label.setText("下载失败")
            self.progress_detail_label.setText(message)
        else:
            # 其他情况下保持原样
            self.status_label.setText(message)
            self.progress_detail_label.setText("")
    
    def download_complete(self, success, message):
        """下载完成处理"""
        self.status_label.setText(message)
        self.download_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_detail_label.setText("")
        
        if success:
            QMessageBox.information(self, "完成", message)
        elif message != "下载已取消":
            QMessageBox.critical(self, "错误", message) 