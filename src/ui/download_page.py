from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                        QLabel, QLineEdit, QPushButton, QComboBox, 
                        QListWidget, QGroupBox, QProgressBar, QMessageBox,
                        QApplication)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QPixmap, QImage
import requests
import subprocess
import os
import logging
from src.utils.video_utils import convert_webm_to_mp4
from src.threads import ConvertThread  # 导入新的转换线程类


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
        self.preset_video_format = None  # 预设视频格式
        self.preset_audio_format = None  # 预设音频格式
        self.preset_subtitles = []       # 预设字幕
        
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
        self.thumbnail_label.setFixedSize(360, 200)  # 增加封面尺寸
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setStyleSheet("color: #888888;")
        left_layout.addWidget(self.thumbnail_label)
        left_layout.addStretch()
        
        # 右侧信息区域
        right_layout = QVBoxLayout()
        
        self.title_label = QLabel("")
        self.title_label.setWordWrap(True)
        self.title_label.setMinimumHeight(60)  # 设置最小高度，确保能显示多行标题
        self.duration_label = QLabel("")
        self.uploader_label = QLabel("")
        
        right_layout.addWidget(self.title_label)
        right_layout.addWidget(self.duration_label)
        right_layout.addWidget(self.uploader_label)
        right_layout.addStretch()
        
        # 将左右布局添加到信息区域
        info_layout.addLayout(left_layout, 4)  # 左侧占40%
        info_layout.addLayout(right_layout, 6)  # 右侧占60%
        
        # 设置信息区域的最小高度
        info_group.setMinimumHeight(220)
        
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
        self.subtitle_list.setMinimumWidth(150)
        self.subtitle_list.setMaximumWidth(350)
        # 设置字幕列表的固定高度
        self.subtitle_list.setMinimumHeight(120)
        
        subtitle_layout.addWidget(QLabel("选择字幕语言:"))
        subtitle_layout.addWidget(self.subtitle_list)
        subtitle_layout.addStretch()  # 添加弹性空间，使内容靠上排列
        
        # 设置整个格式选择区域的高度限制
        formats_group.setMinimumHeight(200)
        subtitle_group.setMinimumHeight(200)
        
        options_layout.addWidget(formats_group, 6)  # 占60%的宽度
        options_layout.addWidget(subtitle_group, 4)  # 占40%的宽度
        
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
            
        # 字幕选择为可选项，不再进行强制检查
        
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
        self.status_label.setText("正在取消操作...")
        
        # 如果有转换线程正在运行，先终止它
        if hasattr(self, 'convert_thread') and self.convert_thread and self.convert_thread.isRunning():
            self.status_label.setText("正在取消视频转换...")
            self.progress_detail_label.setText("正在终止ffmpeg进程，请稍候...")
            
            # 添加转换取消的直观反馈
            self.progress_bar.setRange(0, 0)  # 设置为未确定状态，显示滚动条
            
            # 日志记录取消请求
            logging.info("用户点击取消按钮，正在强制终止转换")
            
            # 立即发出取消信号
            if self.convert_thread.process and self.convert_thread.process.poll() is None:
                try:
                    # 直接使用os命令终止进程
                    pid = self.convert_thread.process.pid
                    logging.info(f"立即使用OS命令终止进程 PID:{pid}")
                    if os.name == 'nt':
                        os.system(f'TASKKILL /F /PID {pid} /T')
                    else:
                        os.system(f'kill -9 {pid}')
                except Exception as e:
                    logging.error(f"使用OS命令终止进程失败: {str(e)}")
            
            # 调用转换线程的取消方法
            self.convert_thread.cancel()
            
            # 如果在3秒内转换线程仍在运行，强制终止它
            QTimer.singleShot(3000, self.force_stop_convert_thread)
            
            # 设置一个定时器定期检查取消状态
            self.check_cancel_timer = QTimer(self)
            self.check_cancel_timer.timeout.connect(self.check_convert_cancellation)
            self.check_cancel_timer.start(300)  # 每300毫秒检查一次
            
            return  # 提前返回，剩下的由定时器处理
        
        # 取消下载进程
        self.cancel_download_requested.emit()
    
    def force_stop_convert_thread(self):
        """强制终止转换线程"""
        if hasattr(self, 'convert_thread') and self.convert_thread and self.convert_thread.isRunning():
            logging.warning("转换线程3秒后仍在运行，强制终止")
            self.convert_thread.terminate()  # 强制终止线程
            self.convert_thread.wait(1000)   # 等待最多1秒
            
            # 重置UI状态
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.status_label.setText("视频转换已强制终止")
            self.progress_detail_label.setText("")
            self.download_button.setEnabled(True)
            self.cancel_button.setEnabled(True)
    
    def check_convert_cancellation(self):
        """检查转换取消状态"""
        if not hasattr(self, 'convert_thread') or not self.convert_thread or not self.convert_thread.isRunning():
            # 转换线程已经不在运行，取消成功
            self.check_cancel_timer.stop()
            self.progress_bar.setRange(0, 100)  # 恢复正常范围
            self.progress_bar.setValue(0)
            self.status_label.setText("视频转换已取消")
            self.progress_detail_label.setText("")
            self.download_button.setEnabled(True)
            self.cancel_button.setEnabled(True)
        elif hasattr(self, 'convert_thread') and self.convert_thread and self.convert_thread.is_canceled:
            # 转换已标记为取消，但可能仍在处理资源清理
            self.status_label.setText("转换取消中...")
            self.progress_detail_label.setText("正在清理资源，可能需要几秒钟...")
            
            # 如果进程仍在运行，再次尝试终止
            if self.convert_thread.process and self.convert_thread.process.poll() is None:
                try:
                    pid = self.convert_thread.process.pid
                    logging.info(f"再次尝试终止顽固进程 PID:{pid}")
                    if os.name == 'nt':
                        os.system(f'TASKKILL /F /PID {pid} /T')
                    else:
                        os.system(f'kill -9 {pid}')
                except Exception as e:
                    logging.error(f"再次终止进程失败: {str(e)}")
        else:
            # 尝试再次取消
            self.convert_thread.cancel()
            self.status_label.setText("再次尝试终止转换进程...")
            
            # 计数检查次数，如果超过10次(3秒)仍未取消成功，强制终止线程
            if not hasattr(self, 'cancel_check_count'):
                self.cancel_check_count = 0
            self.cancel_check_count += 1
            
            if self.cancel_check_count > 10:
                logging.warning("多次取消尝试失败，强制终止线程")
                self.force_stop_convert_thread()
                self.check_cancel_timer.stop()
                self.cancel_check_count = 0
    
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
        """更新视频信息显示"""
        if not self.video_info:
            return
        
        # 更新标题和其他信息
        title = self.video_info.get('title', '未知标题')
        self.title_label.setText(f"<b>标题:</b> {title}")
        
        duration = self.video_info.get('duration')
        if duration:
            minutes, seconds = divmod(duration, 60)
            hours, minutes = divmod(minutes, 60)
            duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"
            self.duration_label.setText(f"<b>时长:</b> {duration_str}")
        else:
            self.duration_label.setText("<b>时长:</b> 未知")
        
        uploader = self.video_info.get('uploader', '未知')
        self.uploader_label.setText(f"<b>上传者:</b> {uploader}")
        
        # 加载封面
        self.thumbnail_url = self.video_info.get('thumbnail')
        if self.thumbnail_url:
            try:
                response = requests.get(self.thumbnail_url, stream=True)
                if response.status_code == 200:
                    self.thumbnail_data = response.content
                    pixmap = QPixmap()
                    pixmap.loadFromData(self.thumbnail_data)
                    pixmap = pixmap.scaled(360, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.thumbnail_label.setPixmap(pixmap)
                    self.thumbnail_label.setStyleSheet("")
                else:
                    self.thumbnail_label.setText("无法加载封面")
                    self.thumbnail_label.setStyleSheet("color: #888888;")
            except Exception as e:
                self.thumbnail_label.setText(f"加载封面失败: {str(e)}")
                self.thumbnail_label.setStyleSheet("color: #888888;")
        else:
            self.thumbnail_label.setText("无封面")
            self.thumbnail_label.setStyleSheet("color: #888888;")
        
        # 清空和更新格式选择
        self.video_format_combo.clear()
        self.audio_format_combo.clear()
        
        # 添加"不下载视频"选项
        self.video_format_combo.addItem("不下载视频", "")
        
        # 添加"不下载音频"选项
        self.audio_format_combo.addItem("不下载音频", "")
        
        # 获取并排序视频和音频格式
        video_formats = []
        audio_formats = []
        
        # 提取视频和音频格式信息
        for fmt in self.video_info.get('formats', []):
            format_id = fmt.get('format_id', '')
            # 忽略最佳格式
            if format_id == 'best' or format_id == 'worst':
                continue
                
            ext = fmt.get('ext', '')
            format_note = fmt.get('format_note', '')
            
            # 检查是否有视频或音频流
            is_video = fmt.get('vcodec', 'none') != 'none'
            is_audio = fmt.get('acodec', 'none') != 'none'
            
            if is_video and not is_audio:
                # 纯视频流
                resolution = fmt.get('resolution', 'unknown')
                fps = fmt.get('fps', '')
                fps_str = f" {fps}fps" if fps else ""
                vcodec = fmt.get('vcodec', 'unknown')
                bitrate = fmt.get('tbr', 0)
                bitrate_str = f" {int(bitrate)}kbps" if bitrate else ""
                
                format_display = f"{resolution}{fps_str} [{ext}] ({format_note}{bitrate_str} - {vcodec})"
                video_formats.append((format_id, format_display, fmt.get('filesize', 0), resolution))
            
            elif is_audio and not is_video:
                # 纯音频流
                acodec = fmt.get('acodec', 'unknown')
                bitrate = fmt.get('abr', 0) or fmt.get('tbr', 0)
                bitrate_str = f" {int(bitrate)}kbps" if bitrate else ""
                
                format_display = f"{format_note}{bitrate_str} [{ext}] ({acodec})"
                audio_formats.append((format_id, format_display, fmt.get('filesize', 0)))
        
        # 对视频格式按分辨率排序（从高到低）
        video_formats.sort(key=lambda x: (0 if isinstance(x[3], str) else x[3]), reverse=True)
        
        # 对音频格式按文件大小排序（从大到小，假设更大意味着更高质量）
        audio_formats.sort(key=lambda x: x[2] or 0, reverse=True)
        
        # 添加视频格式到下拉框
        preset_video_index = 0
        for i, (format_id, format_display, _, _) in enumerate(video_formats):
            self.video_format_combo.addItem(format_display, format_id)
            # 如果有预设格式且匹配当前格式ID，记录索引
            if self.preset_video_format and format_id == self.preset_video_format:
                preset_video_index = i + 1  # +1 因为我们添加了"不下载视频"选项
        
        # 添加音频格式到下拉框
        preset_audio_index = 0
        for i, (format_id, format_display, _) in enumerate(audio_formats):
            self.audio_format_combo.addItem(format_display, format_id)
            # 如果有预设格式且匹配当前格式ID，记录索引
            if self.preset_audio_format and format_id == self.preset_audio_format:
                preset_audio_index = i + 1  # +1 因为我们添加了"不下载音频"选项
        
        # 清空并更新字幕列表
        self.subtitle_list.clear()
        preset_subtitle_indices = []
        
        # 添加字幕选项
        subtitles = self.video_info.get('subtitles', {})
        for i, (lang_code, _) in enumerate(subtitles.items()):
            display_name = f"{lang_code}"
            item = QListWidgetItem(display_name)
            item.setData(Qt.UserRole, lang_code)
            self.subtitle_list.addItem(item)
            
            # 如果有预设字幕且匹配当前语言，记录索引
            if self.preset_subtitles and lang_code in self.preset_subtitles:
                preset_subtitle_indices.append(i)
        
        # 启用控件
        self.video_format_combo.setEnabled(True)
        self.audio_format_combo.setEnabled(True)
        self.subtitle_list.setEnabled(True)
        self.download_button.setEnabled(True)
        
        # 应用预设格式选择
        if self.preset_video_format and preset_video_index > 0:
            self.video_format_combo.setCurrentIndex(preset_video_index)
            
        if self.preset_audio_format and preset_audio_index > 0:
            self.audio_format_combo.setCurrentIndex(preset_audio_index)
            
        # 选择预设字幕
        for index in preset_subtitle_indices:
            self.subtitle_list.item(index).setSelected(True)
        
        # 重置预设，防止影响下次操作
        self.preset_video_format = None
        self.preset_audio_format = None
        self.preset_subtitles = []
    
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
        self.cancel_button.setEnabled(False)  # 下载完成后停用取消按钮
        self.progress_detail_label.setText("")
        
        if success:
            # 检查是否需要将webm转换为mp4
            if "路径:" in message and ".webm" in message:
                # 提取文件路径
                file_path = message.split("路径:")[1].strip()
                if os.path.exists(file_path) and file_path.endswith('.webm'):
                    # 显示转换中的状态
                    self.status_label.setText("准备转换WebM为MP4格式...")
                    self.progress_bar.setValue(0)  # 重置进度条
                    
                    # 重新启用取消按钮，确保用户可以取消转换
                    self.cancel_button.setEnabled(True)
                    
                    # 创建转换选项
                    convert_options = {
                        'video_codec': 'av1_nvenc',   # 使用NVIDIA GPU加速AV1编码器
                        'preset': 'p7',               # 最高质量预设
                        'tune': 'uhq',                # 超高质量调优
                        'rc': 'vbr',                  # 使用可变比特率模式
                        'cq': 20,                     # AV1的VBR质量值(0-63，值越低质量越高)
                        'audio_bitrate': '320k',      # 音频比特率
                        'keep_source_bitrate': True,  # 保持原视频比特率
                        'multipass': 'qres',          # 两通道编码，第一通道使用四分之一分辨率
                        'rc-lookahead': 32,           # 前瞻帧数，提高编码质量
                        'spatial-aq': True,           # 空间自适应量化，提高视觉质量
                        'temporal-aq': True,          # 时间自适应量化，提高动态场景质量
                        'aq-strength': 8,             # AQ强度(1-15)
                        'tf_level': 0,                # 时间滤波级别
                        'lookahead_level': 3,         # 前瞻级别
                        'fallback_codecs': ['h264_nvenc', 'hevc_nvenc', 'libx264'],  # 备用编码器列表
                        'gpu': 0                      # 固定使用GPU 0
                    }
                    
                    # 创建并启动转换线程
                    self.convert_thread = ConvertThread(file_path, options=convert_options)
                    self.convert_thread.convert_progress.connect(self.on_convert_progress)
                    self.convert_thread.convert_percent.connect(self.on_convert_percent)
                    self.convert_thread.convert_finished.connect(self.on_convert_finished)
                    self.convert_thread.start()
                    
                    # 确保取消按钮在转换期间保持启用状态
                    self.cancel_button.setEnabled(True)
                    
                    # 禁用下载按钮，直到转换完成
                    self.download_button.setEnabled(False)
                    return  # 提前返回，等待转换完成
            
            # 如果没有发生WebM转换，显示原始的成功消息并设置正常颜色
            self.status_label.setText(message)
            self.status_label.setStyleSheet("")
        elif message != "下载已取消":
            # 显示错误消息，并设置红色
            self.status_label.setText(f"错误: {message}")
            self.status_label.setStyleSheet("color: red;")
    
    def on_convert_progress(self, message):
        """处理转换进度更新"""
        self.status_label.setText(message)
        # 确保取消按钮始终可用
        self.cancel_button.setEnabled(True)
        
    def on_convert_percent(self, percent):
        """处理转换百分比更新"""
        # 更新进度条
        self.progress_bar.setRange(0, 100)  # 确保范围正确
        self.progress_bar.setValue(percent)
        # 确保取消按钮始终可用
        self.cancel_button.setEnabled(True)
        
    def on_convert_finished(self, success, message, file_path):
        """处理转换完成"""
        # 恢复进度条的正常范围
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100 if success else 0)
        self.download_button.setEnabled(True)
        self.cancel_button.setEnabled(False)  # 转换完成后禁用取消按钮
        
        # 如果是由取消操作导致的，显示取消信息而不是错误
        if hasattr(self, 'convert_thread') and self.convert_thread and self.convert_thread.is_canceled:
            self.status_label.setText("视频转换已取消")
            self.status_label.setStyleSheet("")
            logging.info("用户取消了视频转换")
            return
        
        if success:
            # 获取原始webm文件路径
            webm_file = file_path.replace('.mp4', '.webm')
            
            # 直接删除原始webm文件，不再询问
            try:
                if os.path.exists(webm_file):
                    os.remove(webm_file)
                    converted_message = "下载并转换完成"
                    logging.info(f"已自动删除原始WebM文件: {webm_file}")
                else:
                    converted_message = "下载并转换完成"
            except Exception as e:
                logging.error(f"删除原始文件失败: {e}")
                converted_message = "下载并转换完成"
            
            # 在状态标签显示消息，不再显示对话框
            self.status_label.setText(converted_message)
        else:
            # 转换失败显示错误信息，但不再弹出对话框
            error_message = "WebM文件转换为MP4失败，但下载已完成"
            self.status_label.setText(error_message)
            self.status_label.setStyleSheet("color: red;")
            logging.error(f"转换失败: {message}，文件路径: {file_path}")

    def set_preset_formats(self, video_format=None, audio_format=None, subtitles=None):
        """设置预设的格式选项，用于重新下载或继续下载"""
        self.preset_video_format = video_format
        self.preset_audio_format = audio_format
        self.preset_subtitles = subtitles or [] 