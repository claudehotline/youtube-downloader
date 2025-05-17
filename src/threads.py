from PySide6.QtCore import QThread, Signal
import os


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
    """处理WebM到MP4格式转换的线程"""
    convert_progress = Signal(str)  # 转换进度信息
    convert_finished = Signal(bool, str, str)  # 成功状态，消息，文件路径
    convert_percent = Signal(int)  # 转换进度百分比
    
    def __init__(self, webm_file_path, options=None):
        super().__init__()
        self.webm_file_path = webm_file_path
        self.is_cancelled = False
        self.options = options or {}
    
    def run(self):
        try:
            from src.utils.video_utils import convert_webm_to_mp4
            
            # 发送开始转换信号
            self.convert_progress.emit("正在准备转换WebM为MP4格式...")
            
            # 设置进度回调函数
            def on_progress(percent, message):
                self.convert_percent.emit(percent)
                self.convert_progress.emit(message)
                
                # 检查是否被取消
                if self.is_cancelled:
                    return False  # 返回False表示需要取消
                return True  # 返回True表示继续
            
            # 执行转换
            mp4_file = convert_webm_to_mp4(
                self.webm_file_path,
                progress_callback=on_progress,
                options=self.options
            )
            
            # 检查是否被取消
            if self.is_cancelled:
                self.convert_finished.emit(False, "转换已取消", self.webm_file_path)
                return
            
            # 检查转换结果
            if mp4_file != self.webm_file_path:  # 转换成功
                self.convert_finished.emit(True, "转换成功", mp4_file)
            else:
                self.convert_finished.emit(False, "转换失败", self.webm_file_path)
                
        except Exception as e:
            self.convert_finished.emit(False, f"转换过程发生错误: {str(e)}", self.webm_file_path)
    
    def cancel(self):
        self.is_cancelled = True
