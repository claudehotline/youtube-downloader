from PySide6.QtCore import QThread, Signal
import os
import logging
import time
import threading
import traceback
from src.utils.video_utils import convert_webm_to_mp4
import subprocess


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
    
    def __init__(self, downloader, video_url, video_format, audio_format, subtitles, thumbnail, output_dir, threads=10, use_cookies=False, browser=None, video_info=None):
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
        self.video_info = video_info  # 存储视频信息
        self.db = None  # 数据库连接
        self.download_record_id = None  # 下载记录ID
    
    def run(self):
        try:
            # 导入数据库模块
            from src.db.download_history import DownloadHistoryDB
            self.db = DownloadHistoryDB()
            
            # 构建格式规格
            format_spec = f"{self.video_format}+{self.audio_format}" if self.video_format and self.audio_format else (self.video_format or self.audio_format)
            
            # 添加下载记录到数据库
            if self.video_info:
                # 如果有完整信息，则添加更多详情
                self.download_record_id = self.db.add_download(
                    video_id=self.video_info.get('id'),
                    title=self.video_info.get('title', '未知标题'),
                    url=self.video_url,
                    thumbnail_url=self.video_info.get('thumbnail'),
                    video_format=self.video_format,
                    audio_format=self.audio_format,
                    subtitles=self.subtitles,
                    output_path=None  # 下载完成后更新
                )
            else:
                # 简单记录，没有详细信息
                self.download_record_id = self.db.add_download(
                    video_id=None,
                    title=f"从 {self.video_url} 下载的视频",
                    url=self.video_url,
                    video_format=self.video_format,
                    audio_format=self.audio_format,
                    subtitles=self.subtitles,
                    output_path=None  # 下载完成后更新
                )
            
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
            
            # 更新下载记录
            if self.download_record_id:
                if self.downloader.is_cancelled:
                    # 如果下载被取消
                    self.db.update_download_status(
                        self.download_record_id, 
                        status='已取消'
                    )
                elif downloaded_file and os.path.exists(downloaded_file):
                    # 如果下载成功，获取文件大小并更新记录
                    file_size = os.path.getsize(downloaded_file)
                    self.db.update_download_status(
                        self.download_record_id, 
                        status='完成',
                        output_path=downloaded_file,
                        file_size=file_size
                    )
                else:
                    # 下载完成但找不到文件
                    self.db.update_download_status(
                        self.download_record_id, 
                        status='完成',
                        error_message='找不到下载的文件'
                    )
            
            # 只有在未取消的情况下才发送完成信号
            if not self.downloader.is_cancelled:
                if downloaded_file and os.path.exists(downloaded_file):
                    self.download_finished.emit(True, f"下载完成, 路径: {downloaded_file}")
                else:
                    self.download_finished.emit(True, "下载完成！")
        except Exception as e:
            # 更新下载记录为失败状态
            if self.download_record_id:
                self.db.update_download_status(
                    self.download_record_id, 
                    status='失败',
                    error_message=str(e)
                )
            
            self.download_finished.emit(False, f"下载失败: {str(e)}")
    
    def progress_callback(self, percent, message):
        # 更新进度
        self.progress_updated.emit(percent, message)
        
        # 对于取消消息，更新数据库记录
        if "取消" in message and self.download_record_id:
            self.db.update_download_status(
                self.download_record_id, 
                status='已取消'
            )
    
    def cancel(self):
        # 调用下载器的取消方法
        if self.downloader:
            self.downloader.cancel_download()
            
            # 更新下载记录为已取消状态
            if self.download_record_id:
                self.db.update_download_status(
                    self.download_record_id, 
                    status='已取消'
                )


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
        self.process = None  # 存储ffmpeg进程引用
        self.cancel_lock = threading.Lock()  # 添加锁以避免竞态条件
    
    def run(self):
        try:
            # 生成目标文件路径
            target_file = self.file_path.replace('.webm', '.mp4')
            
            # 定义进度回调函数
            def progress_callback(percent, message, process_ref=None):
                # 先检查是否已经取消
                with self.cancel_lock:
                    if self.is_canceled:
                        logging.info("已检测到取消标志，停止转换过程")
                        return False
                
                # 存储进程引用
                if process_ref and not self.process:
                    self.process = process_ref
                
                self.convert_percent.emit(percent)
                self.convert_progress.emit(message)
                
                # 再次检查取消状态
                with self.cancel_lock:
                    if self.is_canceled:
                        logging.info("检测到取消请求，正在终止视频转换")
                        return False
                return True
            
            # 执行转换
            start_time = time.time()
            output_file = convert_webm_to_mp4(
                self.file_path, 
                progress_callback=progress_callback,
                options=self.options
            )
            
            # 如果已取消，直接返回取消信息
            with self.cancel_lock:
                if self.is_canceled:
                    self.convert_finished.emit(False, "用户取消了转换", self.file_path)
                    return
            
            # 检查转换结果
            if output_file.endswith('.mp4') and os.path.exists(output_file):
                elapsed_time = time.time() - start_time
                success_message = f"转换完成，耗时: {elapsed_time:.2f}秒"
                logging.info(success_message)
                
                self.convert_finished.emit(True, success_message, output_file)
            else:
                error_message = f"转换失败，请检查源文件和转换设置，文件路径: {self.file_path}"
                logging.error(error_message)
                
                self.convert_finished.emit(False, error_message, self.file_path)
        except Exception as e:
            # 如果已取消，直接返回取消信息而不是错误
            with self.cancel_lock:
                if self.is_canceled:
                    self.convert_finished.emit(False, "用户取消了转换", self.file_path)
                    return
                
            error_details = traceback.format_exc()
            error_message = f"转换失败: {str(e)}，文件路径: {self.file_path}"
            logging.error(error_message)
            logging.error(error_details)
            
            self.convert_finished.emit(False, error_message, self.file_path)
    
    def cancel(self):
        """取消转换"""
        logging.info(f"请求取消视频转换: {self.file_path}")
        
        # 使用锁保护取消操作
        with self.cancel_lock:
            self.is_canceled = True
            
            # 立即向UI发送取消通知
            self.convert_progress.emit("正在取消转换...")
        
        # 直接终止任何运行中的ffmpeg进程
        if self.process and self.process.poll() is None:
            try:
                logging.info(f"终止ffmpeg进程 PID:{self.process.pid}")
                if os.name == 'nt':
                    # 先尝试使用taskkill命令终止进程
                    try:
                        subprocess.call(['taskkill', '/F', '/T', '/PID', str(self.process.pid)],
                                      creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                        logging.info("成功使用taskkill终止进程")
                    except Exception as e:
                        logging.error(f"使用taskkill终止进程失败: {str(e)}")
                        
                        # 如果taskkill失败，尝试使用process对象的方法
                        self.process.terminate()
                        time.sleep(0.5)
                        if self.process.poll() is None:
                            self.process.kill()
                            logging.info("成功使用process.kill()终止进程")
                else:
                    # 类Unix系统
                    self.process.terminate()
                    time.sleep(0.5)
                    if self.process.poll() is None:
                        self.process.kill()
                logging.info("ffmpeg进程已终止")
                
                # 如果进程仍在运行，尝试更极端的方式
                if self.process.poll() is None:
                    logging.warning("进程仍在运行，尝试更极端的终止方式")
                    try:
                        # 使用Windows特有的方法强制终止进程
                        if os.name == 'nt':
                            os.system(f'TASKKILL /F /PID {self.process.pid} /T')
                            logging.info(f"尝试使用系统命令终止进程: TASKKILL /F /PID {self.process.pid} /T")
                        else:
                            # 类Unix系统
                            os.system(f'kill -9 {self.process.pid}')
                            logging.info(f"尝试使用系统命令终止进程: kill -9 {self.process.pid}")
                    except Exception as ex:
                        logging.error(f"使用系统命令终止进程失败: {str(ex)}")
            except Exception as e:
                logging.error(f"终止进程时出错: {str(e)}")
        
        # 发送取消结果通知
        self.convert_finished.emit(False, "转换已取消", self.file_path)
