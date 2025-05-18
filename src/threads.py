from PySide6.QtCore import QThread, Signal
import os
import logging
import time
import threading
import traceback
from src.utils.video_utils import convert_webm_to_mp4


class FetchInfoThread(QThread):
    info_fetched = Signal(dict)
    fetch_error = Signal(str)
    
    def __init__(self, downloader, url, use_cookies=False, browser=None):
        super().__init__()
        self.downloader = downloader
        self.url = url
        self.use_cookies = use_cookies
        self.browser = browser
    
    def run(self):
        try:
            video_info = self.downloader.get_video_info(self.url, self.use_cookies, self.browser)
            self.info_fetched.emit(video_info)
        except Exception as e:
            self.fetch_error.emit(str(e))


class DownloadThread(QThread):
    progress_updated = Signal(int, str)
    download_finished = Signal(bool, str)
    
    def __init__(self, downloader, video_url, video_format, audio_format, subtitles, thumbnail, output_dir, threads=10, use_cookies=False, browser=None):
        super().__init__()
        self.downloader = downloader
        self.video_url = video_url
        self.video_format = video_format
        self.audio_format = audio_format
        self.subtitles = subtitles
        self.thumbnail = thumbnail
        self.output_dir = output_dir
        self.threads = threads
        self.use_cookies = use_cookies
        self.browser = browser
    
    def run(self):
        try:
            format_spec = f"{self.video_format}+{self.audio_format}" if self.video_format and self.audio_format else (self.video_format or self.audio_format)
            
            # 获取下载的文件路径
            downloaded_file = self.downloader.download(
                self.video_url, 
                format_spec, 
                self.subtitles, 
                self.thumbnail, 
                self.output_dir, 
                self.progress_callback,
                self.threads,
                self.use_cookies,
                self.browser
            )
            
            # 只有在未取消的情况下才发送完成信号
            if not self.downloader.is_cancelled:
                if downloaded_file and os.path.exists(downloaded_file):
                    self.download_finished.emit(True, f"下载完成, 路径: {downloaded_file}")
                else:
                    self.download_finished.emit(True, "下载完成！")
        except Exception as e:
            self.download_finished.emit(False, f"下载失败: {str(e)}")
    
    def progress_callback(self, percent, message):
        self.progress_updated.emit(percent, message)
    
    def cancel(self):
        # 调用下载器的取消方法
        if self.downloader:
            self.downloader.cancel_download()


# 添加WebM到MP4的转换线程
class ConvertThread(QThread):
    """视频转换线程"""
    convert_finished = Signal(bool, str, str)
    convert_progress = Signal(str)
    convert_percent = Signal(int)
    
    def __init__(self, file_path, options=None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.options = options
        self.is_canceled = False
        self.record_id = None  # 用于存储历史记录ID
    
    def run(self):
        try:
            # 生成目标文件路径
            target_file = self.file_path.replace('.webm', '.mp4')
            
            # 不再记录转换历史
            
            # 定义进度回调函数
            def progress_callback(percent, message):
                self.convert_percent.emit(percent)
                self.convert_progress.emit(message)
                
                # 不再更新历史记录中的进度
                
                # 检查是否取消
                if self.is_canceled:
                    return False
                return True
            
            # 执行转换
            start_time = time.time()
            output_file = convert_webm_to_mp4(
                self.file_path, 
                progress_callback=progress_callback,
                options=self.options
            )
            
            # 检查转换结果
            if output_file.endswith('.mp4') and os.path.exists(output_file):
                elapsed_time = time.time() - start_time
                success_message = f"转换完成，耗时: {elapsed_time:.2f}秒"
                logging.info(success_message)
                
                # 不再更新历史记录
                
                self.convert_finished.emit(True, success_message, output_file)
            else:
                error_message = "转换失败，请检查源文件和转换设置"
                logging.error(error_message)
                
                # 不再更新历史记录
                
                self.convert_finished.emit(False, error_message, self.file_path)
        except Exception as e:
            error_details = traceback.format_exc()
            error_message = f"转换过程中发生异常: {str(e)}\n{error_details}"
            logging.error(error_message)
            
            # 不再更新历史记录
            
            self.convert_finished.emit(False, str(e), self.file_path)
    
    def cancel(self):
        """取消转换"""
        self.is_canceled = True
        
        # 不再更新历史记录
