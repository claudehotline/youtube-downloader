import os
import json
import subprocess
import re
import glob
from typing import Dict, List, Any, Callable, Optional, Tuple
import tempfile
import shutil
import signal
import time
from src.config import DEFAULT_TIMEOUT, MAX_RETRIES, NETWORK_WAIT
import sys
from pathlib import Path
import logging
from src.utils.subtitle_translator import SubtitleTranslator
from src.config_manager import ConfigManager

# 调整yt-dlp.exe的路径
YTDLP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cmd", "yt-dlp.exe")

class YtDownloader:
    def __init__(self, ytdlp_path: str = None, debug_callback: Callable[[str], None] = None, always_use_cookies: bool = True):
        """
        初始化下载器
        
        Args:
            ytdlp_path: yt-dlp可执行文件的路径，如果为None则使用当前目录下的yt-dlp.exe
            debug_callback: 调试信息回调函数，用于将调试信息传回UI
            always_use_cookies: 是否始终使用cookies（默认为True）
        """
        self.ytdlp_path = ytdlp_path or YTDLP_PATH
        if not os.path.exists(self.ytdlp_path):
            raise FileNotFoundError(f"找不到yt-dlp可执行文件: {self.ytdlp_path}")
        self.processes = []  # 存储所有进程对象
        self.is_cancelled = False  # 取消标志
        self.debug_callback = debug_callback  # 调试信息回调
        self.always_use_cookies = always_use_cookies  # 是否总是使用cookies
        self.config_manager = ConfigManager()  # 配置管理器
    
    def debug(self, message: str):
        """输出调试信息，过滤重复的进度信息"""
        # 跳过常见的重复进度信息
        skip_patterns = [
            "[download]",    # 下载进度百分比
            "ETA",           # 剩余时间信息
            "Destination:",  # 目标文件信息
            "100%"           # 完成信息
        ]
        
        # 始终记录的重要信息模式
        important_patterns = [
            "合并",          # 合并相关信息
            "已下载",        # 下载完成信息
            "错误",          # 错误信息
            "失败",          # 失败信息
            "完成"           # 完成信息
        ]
        
        # 检查是否包含重要信息
        is_important = any(pattern in message for pattern in important_patterns)
        
        # 过滤控制台输出，跳过频繁更新的进度信息
        should_print = True
        if not is_important:  # 如果不是重要信息，则应用过滤
            for pattern in skip_patterns:
                if pattern in message:
                    # 对于下载进度，只在每10%时输出一次
                    if "[download]" in message and "%" in message:
                        try:
                            # 尝试提取百分比
                            percent_part = message.split("%")[0]
                            percent_part = percent_part.split("[download]")[1].strip()
                            percent = float(percent_part)
                            # 只在整10%时输出
                            if percent % 10 != 0 or percent == 0:
                                should_print = False
                        except:
                            pass
                    else:
                        should_print = False
                    break
        
        # 只使用日志系统输出，不再使用print重复输出
        if is_important or should_print:
            formatted_message = f"[YtDownloader] {message}"
            # 如果有回调函数，则调用回调函数
            if self.debug_callback:
                self.debug_callback(message)
            # 只使用logging记录日志，避免重复输出
            logging.info(formatted_message)
    
    def cancel_download(self):
        """
        取消正在进行的下载
        """
        self.debug("尝试取消下载...")
        self.is_cancelled = True
        
        # 终止下载进程
        if self.download_process and self.download_process.poll() is None:
            self.debug(f"终止下载进程 PID={self.download_process.pid}")
            try:
                if os.name == 'nt':  # Windows系统
                    # 使用taskkill强制终止进程及其子进程
                    subprocess.call(
                        ['taskkill', '/F', '/T', '/PID', str(self.download_process.pid)],
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                    )
                else:  # 类Unix系统
                    self.download_process.terminate()
                    # 给进程一点时间来终止
                    time.sleep(0.5)
                    if self.download_process.poll() is None:
                        # 如果进程没有终止，强制杀死它
                        self.download_process.kill()
                
                self.debug("下载已取消")
            except Exception as e:
                self.debug(f"取消下载时发生错误: {str(e)}")
        else:
            self.debug("没有正在进行的下载进程")
    
    def get_video_info(self, url: str, use_cookies=False, browser=None) -> Dict[str, Any]:
        """
        获取视频信息
        
        Args:
            url: YouTube视频URL
            use_cookies: 是否使用浏览器cookie
            browser: 浏览器类型（firefox、chrome等）
            
        Returns:
            视频信息字典
        """
        # 如果设置了总是使用cookies，则强制启用
        if self.always_use_cookies:
            use_cookies = True
            
        # 简化命令，只使用必要的参数
        cmd = [
            self.ytdlp_path,
            "-q",           # 安静模式，减少输出
            "--dump-json",  # 使用JSON格式获取详细信息
            "--no-playlist",
            url
        ]
        
        # 添加浏览器Cookie支持
        if use_cookies and browser:
            cmd.append(f"--cookies-from-browser={browser}")
            self.debug(f"使用{browser}浏览器的cookie")
        elif use_cookies:
            # 如果没有指定浏览器但启用了cookies，使用默认的chrome
            cmd.append("--cookies-from-browser=chrome")
            self.debug("使用默认Chrome浏览器的cookie")
        
        self.debug(f"开始获取视频信息: {url}")
        # 打印完整的命令行到日志
        self.debug(f"执行命令: {' '.join(cmd)}")
        
        retry_count = 0
        max_tries = 2  # 如果完全失败，最多重试2次
        
        while retry_count <= max_tries:
            try:
                start_time = time.time()
                self.debug(f"尝试次数 #{retry_count+1}")
                
                # 对于获取视频信息，不使用CREATE_NO_WINDOW标志，确保正确捕获输出
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',  # 明确指定编码
                    errors='replace'   # 遇到无法解码的字符时替换
                    # 不添加CREATE_NO_WINDOW标志，确保能正确获取输出
                )
                self.processes.append(process)
                
                # 设置超时，但给予充分的时间
                stdout, stderr = "", ""
                timeout_seconds = DEFAULT_TIMEOUT * 2  # 给予2倍超时时间
                
                # 等待进程完成或超时
                try:
                    stdout, stderr = process.communicate(timeout=timeout_seconds)
                except subprocess.TimeoutExpired:
                    process.kill()
                    self.debug(f"进程超时，已终止")
                    stdout, stderr = process.communicate()
                    raise Exception(f"获取视频信息超时 (超过{timeout_seconds}秒)")
                
                if stderr:
                    self.debug(f"进程输出错误: {stderr}")
                
                if process.returncode != 0:
                    error_msg = stderr or "未知错误"
                    if "HTTP Error 429" in error_msg:
                        # 对于429错误，等待一段时间后重试
                        retry_count += 1
                        if retry_count <= max_tries:
                            wait_time = retry_count * 5
                            self.debug(f"请求次数过多(HTTP 429)，等待{wait_time}秒后重试...")
                            time.sleep(wait_time)  # 指数退避
                            continue
                        raise Exception("请求次数过多，YouTube暂时限制了访问，请稍后再试")
                    elif "This video is unavailable" in error_msg:
                        self.debug("视频不可用")
                        raise Exception("视频不可用或已被删除")
                    elif "Sign in to confirm your age" in error_msg:
                        self.debug("需要年龄验证")
                        raise Exception("需要登录验证年龄，请确认已正确配置cookies")
                    elif "Private video" in error_msg:
                        self.debug("私有视频")
                        raise Exception("这是一个私有视频，无法获取信息")
                    elif "is not a valid URL" in error_msg or "URL could be a direct video link" in error_msg:
                        self.debug("无效URL")
                        raise Exception("无效的URL地址，请检查链接是否正确")
                    elif "Unable to download webpage" in error_msg:
                        # 网络问题，尝试重试
                        retry_count += 1
                        if retry_count <= max_tries:
                            wait_time = retry_count * 3
                            self.debug(f"网络连接问题，等待{wait_time}秒后重试...")
                            time.sleep(wait_time)
                            continue
                        raise Exception(f"无法访问YouTube，请检查网络连接: {error_msg}")
                    elif "Unsupported URL" in error_msg:
                        self.debug("不支持的URL")
                        raise Exception("不支持的URL格式，请确保输入的是YouTube视频链接")
                    else:
                        retry_count += 1
                        if retry_count <= max_tries:
                            self.debug(f"获取信息失败，尝试重试 ({retry_count}/{max_tries})...")
                            time.sleep(2)
                            continue
                        raise Exception(f"获取视频信息失败: {error_msg}")
                
                if not stdout:
                    retry_count += 1
                    if retry_count <= max_tries:
                        self.debug("没有返回数据，尝试重试...")
                        time.sleep(2)
                        continue
                    raise Exception("获取视频信息失败: 没有返回数据")
                
                # 解析JSON数据
                try:
                    data = json.loads(stdout)
                    self.debug(f"成功获取视频信息: {data.get('title', '未知')}")
                    return data
                except json.JSONDecodeError:
                    retry_count += 1
                    if retry_count <= max_tries:
                        self.debug("JSON解析失败，尝试重试...")
                        time.sleep(2)
                        continue
                    raise Exception("解析视频信息失败，返回的数据不是有效的JSON格式")
                
            except Exception as e:
                self.debug(f"发生异常: {str(e)}")
                # 网络或进程相关错误，尝试重试
                if isinstance(e, (subprocess.SubprocessError, ConnectionError, TimeoutError)):
                    retry_count += 1
                    if retry_count <= max_tries:
                        self.debug(f"发生错误: {str(e)}，尝试重试 ({retry_count}/{max_tries})...")
                        time.sleep(3)
                        continue
                    raise Exception(f"执行yt-dlp进程失败: {str(e)}")
                # 如果是其他类型的错误，直接抛出
                raise
        
        # 所有重试都失败了
        self.debug("所有尝试均失败")
        raise Exception("多次尝试获取视频信息均失败，请检查网络连接或链接有效性")
    
    def download(self, url, format_spec, subtitles=None, download_thumbnail=False, 
               output_dir=None, progress_callback=None, threads=10,
               use_cookies=False, browser=None, resume=False):
        """
        下载视频
        
        Args:
            url: YouTube视频链接
            format_spec: 格式选择
            subtitles: 字幕语言列表
            download_thumbnail: 是否下载缩略图
            output_dir: 输出目录
            progress_callback: 进度回调函数
            threads: 下载线程数
            use_cookies: 是否使用浏览器cookie
            browser: 浏览器类型
            resume: 是否继续上次的下载（断点续传）
            
        Returns:
            str: 下载文件的路径
        """
        try:
            # 如果设置了总是使用cookies，则强制启用
            if self.always_use_cookies:
                use_cookies = True
                
            # 如果之前有下载任务被取消，重置状态
            self.is_cancelled = False
            self.download_process = None
            downloaded_file_path = None
            subtitle_files = []  # 记录下载的字幕文件路径列表
            
            # 调试信息
            self.debug(f"开始下载：{url}")
            self.debug(f"格式：{format_spec}")
            self.debug(f"输出目录：{output_dir}")
            if resume:
                self.debug("模式：断点续传")
                
            # 1. 如果是续传模式且有指定格式，则跳过字幕和缩略图的下载
            # 如果不是续传模式，则正常下载字幕和缩略图
            should_download_subtitles = subtitles and len(subtitles) > 0 and not resume
            should_download_thumbnail = download_thumbnail and not resume
            
            # 2. 处理字幕下载
            if should_download_subtitles:
                if progress_callback:
                    progress_callback(0, "正在下载字幕...")
                
                subtitle_cmd = [
                    self.ytdlp_path, 
                    "-q",           # 安静模式，减少输出
                    url,
                    "--skip-download",  # 不下载视频
                    "--write-subs",     # 下载字幕
                    "--sub-langs", ",".join(subtitles),
                    "--convert-subs", "srt",  # 转换为srt格式
                    "-o", os.path.join(output_dir, "%(title)s.%(ext)s")  # 输出路径
                ]
                
                # 添加浏览器Cookie支持
                if use_cookies and browser:
                    subtitle_cmd.append(f"--cookies-from-browser={browser}")
                    # 记录使用cookie信息
                    self.debug(f"使用{browser}浏览器的cookie")
                elif use_cookies:
                    # 如果没有指定浏览器但启用了cookies，使用默认的chrome
                    subtitle_cmd.append("--cookies-from-browser=chrome")
                    # 记录使用cookie信息
                    self.debug("使用默认Chrome浏览器的cookie")
                
                # 记录命令
                self.debug(f"执行命令: {' '.join(subtitle_cmd)}")
                
                # 执行字幕下载
                subtitle_process = subprocess.Popen(
                    subtitle_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8',  # 明确指定编码
                    errors='replace',  # 遇到无法解码的字符时替换
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                # 等待字幕下载完成
                while subtitle_process and not self.is_cancelled:
                    line = subtitle_process.stdout.readline()
                    if not line:
                        break
                    
                    # 捕获字幕文件路径
                    if "Writing video subtitles to: " in line:
                        subtitle_path = line.split("Writing video subtitles to: ", 1)[1].strip()
                        self.debug(f"捕获到字幕文件路径: {subtitle_path}")
                        subtitle_files.append(subtitle_path)
                    
                    self.debug(f"字幕: {line.strip()}")
                
                subtitle_process.wait()
                if self.is_cancelled:
                    if progress_callback:
                        progress_callback(0, "下载已取消")
                    return None
                
                # 翻译下载的字幕文件
                if subtitle_files:
                    try:
                        if progress_callback:
                            progress_callback(0, "字幕下载完成")
                            
                        # 记录字幕文件路径但不翻译
                        for subtitle_path in subtitle_files:
                            if os.path.exists(subtitle_path):
                                self.debug(f"下载的字幕文件: {subtitle_path}")
                    except Exception as e:
                        self.debug(f"处理字幕过程中出错: {str(e)}")
            
            # 3. 处理缩略图下载
            if should_download_thumbnail:
                if progress_callback:
                    progress_callback(0, "正在下载封面...")
                
                thumbnail_cmd = [
                    self.ytdlp_path, 
                    "-q",           # 安静模式，减少输出
                    url,
                    "--skip-download",  # 不下载视频
                    "--write-thumbnail",  # 下载缩略图
                    "--convert-thumbnails", "jpg",  # 转换为jpg格式
                    "-o", os.path.join(output_dir, "%(title)s.%(ext)s")  # 输出路径
                ]
                
                # 添加浏览器Cookie支持
                if use_cookies and browser:
                    thumbnail_cmd.append(f"--cookies-from-browser={browser}")
                    # 记录使用cookie信息
                    self.debug(f"使用{browser}浏览器的cookie")
                elif use_cookies:
                    # 如果没有指定浏览器但启用了cookies，使用默认的chrome
                    thumbnail_cmd.append("--cookies-from-browser=chrome")
                    # 记录使用cookie信息
                    self.debug("使用默认Chrome浏览器的cookie")
                
                # 记录命令
                self.debug(f"执行命令: {' '.join(thumbnail_cmd)}")
                
                # 执行缩略图下载
                thumbnail_process = subprocess.Popen(
                    thumbnail_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8',  # 明确指定编码
                    errors='replace',  # 遇到无法解码的字符时替换
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                # 等待缩略图下载完成
                while thumbnail_process and not self.is_cancelled:
                    line = thumbnail_process.stdout.readline()
                    if not line:
                        break
                    self.debug(f"封面: {line.strip()}")
                
                thumbnail_process.wait()
                if self.is_cancelled:
                    if progress_callback:
                        progress_callback(0, "下载已取消")
                    return None
            
            # 4. 如果没有指定格式，则不下载视频
            if not format_spec:
                if progress_callback:
                    progress_callback(100, "下载完成")
                return None
            
            # 设置输出模板，使用UTF-8编码
            output_template = os.path.join(output_dir, "%(title)s.%(ext)s")
            
            # 5. 下载视频
            # 基本参数
            cmd = [self.ytdlp_path, 
                   url, 
                   "--no-mtime",  # 不使用视频上传时间作为文件修改时间
                   "-o", output_template,  # 设置输出路径
                   "-N", str(threads)]  # 设置线程数
            
            # 添加断点续传参数，默认开启
            # 如果明确指定断点续传，则确保参数存在
            if resume:
                if "--continue" not in cmd:
                    cmd.append("--continue")
            
            # 已经单独下载了字幕和缩略图，不需要重复下载
            # 添加格式参数
            if format_spec:
                cmd.extend(["-f", format_spec])
            
            # 添加浏览器Cookie支持
            if use_cookies and browser:
                cmd.append(f"--cookies-from-browser={browser}")
                
                # 记录debug信息
                self.debug(f"使用{browser}浏览器的cookie")
            elif use_cookies:
                # 如果没有指定浏览器但启用了cookies，使用默认的chrome
                cmd.append("--cookies-from-browser=chrome")
                
                # 记录debug信息
                self.debug("使用默认Chrome浏览器的cookie")
            
            # 初始化进度
            if progress_callback:
                progress_callback(0, "正在准备下载视频...")
            
            # 记录完整命令行
            self.debug(f"执行命令: {' '.join(cmd)}")
            
            # 创建进程并启动
            self.download_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',  # 明确指定编码
                errors='replace',  # 遇到无法解码的字符时替换
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                bufsize=1  # 使用行缓冲
            )
            
            # 解析进度的正则表达式
            progress_pattern = re.compile(r'\[download\]\s+(\d+\.\d+)%')
            eta_pattern = re.compile(r'ETA\s+(\d+:\d+)')
            speed_pattern = re.compile(r'(\d+\.\d+\s*\w+/s)')
            merge_pattern = re.compile(r'\[Merger\]|正在合并|Merging')
            
            # 添加文件路径捕获模式
            destination_pattern = re.compile(r'Destination:\s+(.*)')  # 匹配 "Destination: 文件路径"
            download_dest_pattern = re.compile(r'\[download\]\s+Destination:\s+(.*)')  # 匹配 "[download] Destination: 文件路径"
            merged_into_pattern = re.compile(r'\[Merger\].*?into\s+"(.*?)"')  # 匹配 "[Merger] ... into "文件路径""
            
            # 上次进度更新值和时间
            last_percent = 0
            last_update_time = time.time()
            
            # 用于保存下载的文件路径
            downloaded_file_path = None
            
            # 记录视频标题、ID和扩展名，用于后续构建文件路径
            video_title = None
            video_id = None
            file_extension = None
            merge_output_path = None
            
            # 读取输出并更新进度
            while self.download_process and not self.is_cancelled:
                line = self.download_process.stdout.readline()
                if not line:
                    break
                
                line = line.strip()
                
                # 尝试捕获视频标题和ID信息
                if "[info]" in line and "Downloading" in line and "format" not in line:
                    try:
                        # 尝试提取视频ID和标题
                        match = re.search(r'\[info\] (.*): Downloading', line)
                        if match:
                            video_id = match.group(1).strip()
                            self.debug(f"捕获到视频ID: {video_id}")
                    except Exception as e:
                        self.debug(f"解析视频ID时出错: {str(e)}")
                
                # 尝试获取视频标题
                if "[Metadata]" in line and "title:" in line:
                    try:
                        # 尝试提取视频标题
                        match = re.search(r'title:\s+(.*)', line)
                        if match:
                            video_title = match.group(1).strip()
                            self.debug(f"捕获到视频标题: {video_title}")
                            # 如果已知标题和输出目录，尝试构建可能的文件路径
                            if video_title and output_dir:
                                for ext in ['mp4', 'webm', 'mkv', 'avi', 'mov', 'flv']:
                                    potential_path = os.path.join(output_dir, f"{video_title}.{ext}")
                                    if os.path.exists(potential_path):
                                        downloaded_file_path = potential_path
                                        self.debug(f"根据标题找到文件: {downloaded_file_path}")
                                        break
                    except Exception as e:
                        self.debug(f"解析视频标题时出错: {str(e)}")
                
                # 捕获合并输出路径
                if "[Merger] Merging formats into" in line:
                    try:
                        merge_output_path = line.split("[Merger] Merging formats into")[1].strip().strip('"')
                        self.debug(f"捕获到合并输出路径: {merge_output_path}")
                        # 如果路径存在，直接使用它
                        if os.path.exists(merge_output_path):
                            downloaded_file_path = merge_output_path
                    except:
                        pass
                
                # 只记录重要的调试信息
                if not any(pattern in line for pattern in ["[download]", "ETA", "Destination"]):
                    self.debug(line)
                
                # 捕获下载目标路径
                dest_match = destination_pattern.search(line)
                if dest_match:
                    potential_path = dest_match.group(1).strip()
                    # 不再重复输出相同的目标路径
                    if os.path.isabs(potential_path) and (not downloaded_file_path or downloaded_file_path != potential_path):  # 确保是绝对路径且不重复
                        self.debug(f"发现下载目标路径: {potential_path}")
                        downloaded_file_path = potential_path
                
                # 捕获[download] Destination格式的路径
                download_dest_match = download_dest_pattern.search(line)
                if download_dest_match:
                    potential_path = download_dest_match.group(1).strip()
                    # 不再重复输出相同的目标路径
                    if os.path.isabs(potential_path) and (not downloaded_file_path or downloaded_file_path != potential_path):  # 确保是绝对路径且不重复
                        self.debug(f"发现下载目标路径: {potential_path}")
                        downloaded_file_path = potential_path
                
                # 捕获合并输出路径
                merged_match = merged_into_pattern.search(line)
                if merged_match:
                    potential_path = merged_match.group(1).strip()
                    # 不再重复输出相同的目标路径
                    if os.path.isabs(potential_path) and (not downloaded_file_path or downloaded_file_path != potential_path):  # 确保是绝对路径且不重复
                        self.debug(f"发现合并输出路径: {potential_path}")
                        downloaded_file_path = potential_path
                
                # 检查是否是下载进度信息
                progress_match = progress_pattern.search(line)
                
                if progress_match:
                    percent_str = progress_match.group(1)
                    try:
                        percent = int(float(percent_str))
                        
                        # 控制进度更新频率，避免频繁更新UI
                        current_time = time.time()
                        if percent > last_percent or current_time - last_update_time > 0.5:
                            # 直接使用实际进度，不再映射到15%-95%区间
                            ui_percent = percent  # 使用原始百分比
                            
                            # 提取ETA和速度
                            eta = "未知"
                            eta_match = eta_pattern.search(line)
                            if eta_match:
                                eta = eta_match.group(1)
                                
                            speed = "未知"
                            speed_match = speed_pattern.search(line)
                            if speed_match:
                                speed = speed_match.group(1)
                                
                            message = f"下载中: {speed}, 剩余时间: {eta}"
                            
                            if progress_callback:
                                progress_callback(ui_percent, message)
                            
                            # 更新上次进度和时间
                            last_percent = percent
                            last_update_time = current_time
                    except (ValueError, IndexError):
                        pass
                
                # 检查是否在合并
                merge_match = merge_pattern.search(line)
                if merge_match and progress_callback:
                    progress_callback(95, "正在合并音视频...")
                    # 记录合并信息
                    self.debug("正在合并音视频...")
            
            # 等待进程完成
            if self.download_process:
                self.download_process.wait()
            
            # 如果被取消，返回取消消息
            if self.is_cancelled:
                if progress_callback:
                    progress_callback(0, "下载已取消")
                return None
            
            # 下载完成
            if progress_callback:
                if downloaded_file_path:
                    # 确保文件确实存在
                    if os.path.exists(downloaded_file_path):
                        progress_callback(100, f"下载完成, 路径: {downloaded_file_path}")
                        self.debug(f"下载完成，返回文件路径: {downloaded_file_path}")
                    else:
                        # 尝试最后一次通过目录查找最新文件
                        all_files = []
                        for ext in ['mp4', 'webm', 'mkv', 'avi', 'mov', 'flv', 'wmv']:
                            pattern = os.path.join(output_dir, f"*.{ext}")
                            all_files.extend(glob.glob(pattern))
                        
                        if all_files:
                            all_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                            downloaded_file_path = all_files[0]
                            self.debug(f"通过目录查找最新文件: {downloaded_file_path}")
                            progress_callback(100, f"下载完成, 路径: {downloaded_file_path}")
                        else:
                            progress_callback(100, "下载完成，但无法确定文件路径")
                else:
                    # 尝试最后一次查找
                    all_files = []
                    for ext in ['mp4', 'webm', 'mkv', 'avi', 'mov', 'flv', 'wmv']:
                        pattern = os.path.join(output_dir, f"*.{ext}")
                        all_files.extend(glob.glob(pattern))
                    
                    if all_files:
                        all_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                        downloaded_file_path = all_files[0]
                        self.debug(f"最后尝试查找文件: {downloaded_file_path}")
                        progress_callback(100, f"下载完成, 路径: {downloaded_file_path}")
                    else:
                        progress_callback(100, "下载完成，但无法确定文件路径")
            
            # 遍历输出目录查找字幕文件
            if not self.is_cancelled and output_dir:
                try:
                    # 在下载完成后查找可能的字幕文件
                    subtitle_paths = []
                    for ext in ['.srt', '.vtt', '.ass']:
                        subtitle_paths.extend(glob.glob(os.path.join(output_dir, f"*{ext}")))
                    
                    if subtitle_paths:
                        self.debug(f"找到字幕文件: {subtitle_paths}")
                        # 不再自动翻译字幕，用户可以在下载历史中使用右键菜单手动翻译
                except Exception as e:
                    self.debug(f"查找字幕文件时出错: {str(e)}")
            
            return downloaded_file_path  # 返回下载的文件路径
            
        except Exception as e:
            self.debug(f"下载异常: {str(e)}")
            if progress_callback:
                progress_callback(0, f"下载失败: {str(e)}")
            raise
    
    def get_version(self) -> str:
        """获取yt-dlp版本号"""
        cmd = [self.ytdlp_path, "--version"]
        result = subprocess.run(cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        return result.stdout.strip() if result.returncode == 0 else "未知"
    
    def get_video_formats(self, url: str, use_cookies=False, browser=None) -> str:
        """
        获取视频格式列表
        
        Args:
            url: YouTube视频URL
            use_cookies: 是否使用浏览器cookie
            browser: 浏览器类型（firefox、chrome等）
            
        Returns:
            格式列表的文本输出
        """
        # 如果设置了总是使用cookies，则强制启用
        if self.always_use_cookies:
            use_cookies = True
            
        # 使用-F参数获取格式列表
        cmd = [
            self.ytdlp_path,
            "-q",           # 安静模式，减少输出
            "-F",  # 列出所有可用格式
            "--no-playlist",
            url
        ]
        
        # 添加浏览器Cookie支持
        if use_cookies and browser:
            cmd.append(f"--cookies-from-browser={browser}")
            self.debug(f"使用{browser}浏览器的cookie")
        elif use_cookies:
            # 如果没有指定浏览器但启用了cookies，使用默认的chrome
            cmd.append("--cookies-from-browser=chrome")
            self.debug("使用默认Chrome浏览器的cookie")
        
        self.debug(f"获取视频格式列表: {url}")
        self.debug(f"执行命令: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',  # 明确指定编码
                errors='replace',  # 遇到无法解码的字符时替换
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            self.processes.append(process)
            
            # 等待进程完成或超时
            try:
                stdout, stderr = process.communicate(timeout=DEFAULT_TIMEOUT)
            except subprocess.TimeoutExpired:
                process.kill()
                self.debug("获取格式列表超时，已终止")
                stdout, stderr = process.communicate()
                raise Exception(f"获取视频格式列表超时 (超过{DEFAULT_TIMEOUT}秒)")
            
            if stderr:
                self.debug(f"格式列表错误输出: {stderr}")
            
            if process.returncode != 0:
                raise Exception(f"获取视频格式列表失败: {stderr}")
            
            return stdout
        except Exception as e:
            self.debug(f"获取格式列表异常: {str(e)}")
            raise Exception(f"获取视频格式列表失败: {str(e)}") 