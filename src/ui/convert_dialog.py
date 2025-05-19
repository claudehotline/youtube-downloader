from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QProgressBar, QDialogButtonBox)
from PySide6.QtCore import Qt, Slot, Signal
import logging
import os
from src.threads import ConvertThread
from src.db.download_history import DownloadHistoryDB
import sqlite3

class ConvertDialog(QDialog):
    """视频格式转换对话框，用于显示转换进度"""
    
    # 添加一个信号用于发送日志消息
    log_message = Signal(str, bool, bool)  # 消息, 是否错误, 是否调试信息
    
    def __init__(self, file_path, parent=None, record_id=None):
        super().__init__(parent)
        self.file_path = file_path
        # 直接使用传入的record_id，不再尝试查询
        self.record_id = record_id
        if self.record_id is None:
            logging.warning(f"转换对话框初始化时未提供记录ID，将无法更新数据库记录。文件: {file_path}")
        
        self.convert_thread = None
        self.is_finished = False
        
        # 设置日志
        self.parent_window = parent
        while self.parent_window and not hasattr(self.parent_window, 'log_message'):
            self.parent_window = self.parent_window.parent()
            
        self.setWindowTitle("视频格式转换")
        self.setMinimumWidth(400)
        self.setup_ui()
        
        # 自动开始转换
        self.start_conversion()
    
    def add_log(self, message, error=False, debug=False):
        """添加日志，会同时记录到日志文件和发送到主窗口"""
        # 记录到日志文件
        if error:
            logging.error(message)
        elif debug:
            logging.debug(message)
        else:
            logging.info(message)
        
        # 发送到主窗口的日志
        if hasattr(self.parent_window, 'log_message'):
            self.parent_window.log_message(message, error, debug)
        
        # 发送信号
        self.log_message.emit(message, error, debug)
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题和文件名
        self.title_label = QLabel("<b>正在将WebM文件转换为MP4格式</b>")
        self.title_label.setAlignment(Qt.AlignCenter)
        
        # 显示文件名
        file_name = os.path.basename(self.file_path)
        self.file_label = QLabel(f"文件: {file_name}")
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        # 状态标签
        self.status_label = QLabel("准备转换...")
        self.status_label.setWordWrap(True)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.cancel_conversion)
        
        self.close_button = QPushButton("关闭")
        self.close_button.clicked.connect(self.close)
        self.close_button.setEnabled(False)  # 转换完成前禁用
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.close_button)
        
        # 添加所有元素到布局
        layout.addWidget(self.title_label)
        layout.addWidget(self.file_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        layout.addLayout(button_layout)
        
        # 设置对话框模式和大小
        self.setModal(True)
        self.resize(450, 200)
    
    def start_conversion(self):
        """开始转换过程"""
        self.status_label.setText("正在初始化转换...")
        
        # 添加日志
        file_name = os.path.basename(self.file_path)
        self.add_log(f"开始将WebM转换为MP4: {file_name}")
        
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
        self.convert_thread = ConvertThread(self.file_path, options=convert_options, record_id=self.record_id)
        self.convert_thread.convert_progress.connect(self.on_convert_progress)
        self.convert_thread.convert_percent.connect(self.on_convert_percent)
        self.convert_thread.convert_finished.connect(self.on_convert_finished)
        self.convert_thread.start()
    
    def on_convert_progress(self, message):
        """处理转换进度更新"""
        self.status_label.setText(message)
        
        # 添加重要进度消息到日志
        if "初始化" in message or "开始转换" in message or "编码器" in message:
            self.add_log(f"转换进度: {message}")
    
    def on_convert_percent(self, percent):
        """处理转换百分比更新"""
        self.progress_bar.setValue(percent)
        
        # 添加每25%的进度到日志
        if percent > 0 and percent % 25 == 0:
            self.add_log(f"转换进度: {percent}%")
    
    def on_convert_finished(self, success, message, file_path):
        """处理转换完成"""
        self.is_finished = True
        self.progress_bar.setValue(100 if success else 0)
        self.cancel_button.setEnabled(False)
        self.close_button.setEnabled(True)
        
        if success:
            # 获取原始webm文件路径
            webm_file = file_path.replace('.mp4', '.webm')
            
            # 更新数据库中的状态为"完成"，并更新为mp4文件路径
            db = DownloadHistoryDB()
            db.update_conversion_status(
                file_path=file_path,
                status="完成",
                record_id=self.record_id
            )
            
            # 记录转换成功的日志
            file_name = os.path.basename(file_path)
            self.add_log(f"视频转换成功: {file_name}")
            
            # 直接删除原始webm文件
            try:
                if os.path.exists(webm_file):
                    os.remove(webm_file)
                    self.status_label.setText("转换完成！已自动删除WebM文件。")
                    self.add_log(f"已自动删除原始WebM文件: {os.path.basename(webm_file)}")
                else:
                    self.status_label.setText("转换完成！")
            except Exception as e:
                logging.error(f"删除原始文件失败: {e}")
                self.add_log(f"删除原始文件失败: {str(e)}", error=True)
                self.status_label.setText("转换完成！但无法删除原始WebM文件。")
        else:
            # 转换失败，更新数据库
            db = DownloadHistoryDB()
            db.update_conversion_status(
                file_path=file_path,
                status="转换中断",
                error_message=f"转换失败: {message}",
                record_id=self.record_id
            )
            
            # 记录转换失败的日志
            self.add_log(f"视频转换失败: {message}", error=True)
            
            self.title_label.setText("<b>转换失败</b>")
            self.status_label.setText(f"错误: {message}")
    
    def cancel_conversion(self):
        """取消转换"""
        if self.convert_thread and self.convert_thread.isRunning():
            self.status_label.setText("正在取消转换...")
            self.cancel_button.setEnabled(False)
            self.progress_bar.setRange(0, 0)  # 设置进度条为未确定状态
            
            # 记录取消操作到日志
            self.add_log("用户取消了视频转换")
            
            # 发送取消信号到线程
            self.convert_thread.cancel()
            
            # 如果线程有进程，尝试直接终止
            if self.convert_thread.process and self.convert_thread.process.poll() is None:
                try:
                    pid = self.convert_thread.process.pid
                    self.add_log(f"尝试终止进程 PID:{pid}")
                    if os.name == 'nt':
                        os.system(f'TASKKILL /F /PID {pid} /T')
                    else:
                        os.system(f'kill -9 {pid}')
                except Exception as e:
                    self.add_log(f"终止进程失败: {str(e)}", error=True)
    
    def closeEvent(self, event):
        """处理对话框关闭事件"""
        if not self.is_finished and self.convert_thread and self.convert_thread.isRunning():
            # 如果转换仍在进行中，询问是否取消
            self.cancel_conversion()
            event.ignore()  # 阻止关闭
        else:
            event.accept()  # 允许关闭 