from PySide6.QtCore import QThread, Signal
import os
import logging
import time
import threading
import traceback
from src.utils.video_utils import convert_webm_to_mp4
import subprocess
import json
import re
import glob


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
    convert_progress = Signal(int, str)  # 添加转换进度信号
    convert_finished = Signal(bool, str, str)  # 添加转换完成信号
    
    def __init__(self, downloader, video_url, video_format, audio_format, subtitles, thumbnail, output_dir, threads=10, use_cookies=False, browser=None, video_info=None, resume=False, output_path=None):
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
        self.resume = resume  # 是否断点续传
        self.output_path = output_path  # 指定的输出路径（用于断点续传）
        self.db = None  # 数据库连接
        self.download_record_id = None  # 下载记录ID
    
    def run(self):
        try:
            # 导入数据库模块
            from src.db.download_history import DownloadHistoryDB
            self.db = DownloadHistoryDB()
            
            # 构建格式规格
            format_spec = f"{self.video_format}+{self.audio_format}" if self.video_format and self.audio_format else (self.video_format or self.audio_format)
            
            # 添加或更新下载记录（根据是否为断点续传）
            if self.resume and self.download_record_id:
                # 断点续传，更新已有记录状态
                self.db.update_download_status(
                    self.download_record_id,
                    status='进行中',
                    error_message=None  # 清除之前的错误信息
                )
            else:
                # 新下载，添加新记录
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
                        output_path=self.output_path  # 可能为None
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
                        output_path=self.output_path  # 可能为None
                    )
            
            # 记录当前下载的记录ID
            if self.download_record_id:
                logging.info(f"下载线程已创建记录ID: {self.download_record_id}")
            else:
                logging.error("下载线程创建记录ID失败")
                
            # 初始化下载文件路径
            self.downloaded_file = None
            
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
                self.browser,
                self.resume  # 传递断点续传参数
            )
            
            # 保存下载文件路径到类属性
            self.downloaded_file = downloaded_file
            
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
                    
                    # 确保路径是.webm文件路径（如果存在的话）
                    webm_path = downloaded_file
                    if not webm_path.endswith('.webm') and '.webm' in downloaded_file:
                        webm_path = re.sub(r'\.[^.]+$', '.webm', downloaded_file)
                        if os.path.exists(webm_path):
                            downloaded_file = webm_path
                            self.downloaded_file = downloaded_file  # 更新类属性
                    
                    self.db.update_download_status(
                        self.download_record_id, 
                        status='下载完成',
                        output_path=downloaded_file,
                        file_size=file_size
                    )
                else:
                    # 下载完成但找不到文件
                    self.db.update_download_status(
                        self.download_record_id, 
                        status='下载完成',
                        error_message='找不到下载的文件'
                    )
            
            # 只有在未取消的情况下才发送完成信号并尝试转换
            if not self.downloader.is_cancelled:
                if downloaded_file and os.path.exists(downloaded_file):
                    self.download_finished.emit(True, f"下载完成, 路径: {downloaded_file}")
                    
                    # 检查文件扩展名
                    _, ext = os.path.splitext(downloaded_file)
                    
                    # 如果不是MP4格式，进行转换
                    if ext.lower() != '.mp4':
                        logging.info(f"下载完成，开始自动转换: {downloaded_file}")
                        
                        # 导入视频工具模块
                        from src.utils.video_utils import convert_video
                        
                        # 定义进度回调函数
                        def convert_progress_callback(percent, message):
                            # 发送进度信号
                            self.convert_progress.emit(percent, message)
                            # 检查是否下载线程已被取消
                            return not self.downloader.is_cancelled
                        
                        # 定义完成回调函数
                        def convert_finished_callback(success, message, file_path):
                            # 发送完成信号
                            self.convert_finished.emit(success, message, file_path)
                        
                        # 直接调用转换函数，传递记录ID
                        convert_video(
                            file_path=downloaded_file,
                            record_id=self.download_record_id,
                            progress_callback=convert_progress_callback,
                            finished_callback=convert_finished_callback
                        )
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
    
    def __init__(self, file_path, options=None, record_id=None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.options = options
        self.record_id = record_id  # 记录ID
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
                
                # 确保发送100%进度
                self.convert_percent.emit(100)
                self.convert_progress.emit("转换完成")
                
                # 更新数据库中的文件路径为MP4
                try:
                    from src.db.download_history import DownloadHistoryDB
                    db = DownloadHistoryDB()
                    db.update_conversion_status(
                        output_file,  # MP4文件路径
                        status="转换完成",
                        record_id=self.record_id  # 使用指定的记录ID
                    )
                    logging.info(f"已更新MP4文件路径到数据库，记录ID: {self.record_id}, 文件: {output_file}")
                except Exception as e:
                    logging.error(f"更新MP4文件路径到数据库失败: {str(e)}")
                
                self.convert_finished.emit(True, success_message, output_file)
            else:
                error_message = f"转换失败，请检查源文件和转换设置，文件路径: {self.file_path}"
                logging.error(error_message)
                
                # 更新数据库状态为转换中断
                try:
                    from src.db.download_history import DownloadHistoryDB
                    db = DownloadHistoryDB()
                    
                    # 确保文件路径是webm格式，而不是mp4
                    file_path = self.file_path
                    if file_path.endswith('.mp4'):
                        file_path = file_path.replace('.mp4', '.webm')
                        logging.info(f"转换文件路径从MP4到WebM: {self.file_path} -> {file_path}")
                    
                    # 验证文件是否存在
                    if not os.path.exists(file_path) and os.path.exists(self.file_path):
                        file_path = self.file_path
                        logging.info(f"WebM文件不存在，使用原始路径: {file_path}")
                    
                    # 更新状态，使用指定的记录ID
                    result = db.update_conversion_status(
                        file_path,  # 原始文件路径(webm)
                        status="转换中断",
                        error_message=error_message,
                        record_id=self.record_id
                    )
                    if result:
                        logging.info(f"已成功将状态更新为转换中断，记录ID: {self.record_id}")
                    else:
                        logging.warning(f"更新转换中断状态失败，可能找不到记录ID: {self.record_id}")
                except Exception as ex:
                    logging.error(f"更新转换中断状态到数据库失败: {str(ex)}")
                    logging.error(traceback.format_exc())
                
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
            
            # 更新数据库状态为转换中断
            try:
                from src.db.download_history import DownloadHistoryDB
                db = DownloadHistoryDB()
                
                # 确保文件路径是webm格式，而不是mp4
                file_path = self.file_path
                if file_path.endswith('.mp4'):
                    file_path = file_path.replace('.mp4', '.webm')
                    logging.info(f"转换文件路径从MP4到WebM: {self.file_path} -> {file_path}")
                
                # 验证文件是否存在
                if not os.path.exists(file_path) and os.path.exists(self.file_path):
                    file_path = self.file_path
                    logging.info(f"WebM文件不存在，使用原始路径: {file_path}")
                
                # 更新状态，使用指定的记录ID
                result = db.update_conversion_status(
                    file_path,  # 原始文件路径(webm)
                    status="转换中断",
                    error_message=error_message,
                    record_id=self.record_id
                )
                if result:
                    logging.info(f"已成功将状态更新为转换中断，记录ID: {self.record_id}")
                else:
                    logging.warning(f"更新转换中断状态失败，可能找不到记录ID: {self.record_id}")
            except Exception as ex:
                logging.error(f"更新转换中断状态到数据库失败: {str(ex)}")
                logging.error(traceback.format_exc())
            
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
