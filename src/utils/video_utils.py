import os
import subprocess
import logging
import time
import ffmpeg  # 导入ffmpeg-python库
import re
import threading
import datetime
from typing import Callable, Optional, Dict, Any

def clean_old_files(directory, days=7, extensions=None):
    """
    清理指定目录中超过指定天数的文件
    
    Args:
        directory: 要清理的目录
        days: 文件保留天数，超过此天数的文件会被删除
        extensions: 要清理的文件扩展名列表，如 ['.webm', '.part']，为None时清理所有文件
        
    Returns:
        删除的文件数量
    """
    if not os.path.exists(directory) or not os.path.isdir(directory):
        logging.warning(f"指定目录不存在或不是一个目录: {directory}")
        return 0
    
    # 当前时间
    current_time = time.time()
    # 一天的秒数
    seconds_per_day = 86400  # 24 * 60 * 60
    
    # 要删除的文件计数
    deleted_count = 0
    
    try:
        # 遍历目录中的所有文件
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            
            # 只处理文件，不处理目录
            if not os.path.isfile(file_path):
                continue
            
            # 如果指定了扩展名，则只处理指定扩展名的文件
            if extensions:
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext not in extensions:
                    continue
            
            # 获取文件的修改时间
            file_mod_time = os.path.getmtime(file_path)
            
            # 如果文件修改时间距今超过指定天数，则删除
            if current_time - file_mod_time > days * seconds_per_day:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                    logging.info(f"已删除过期文件: {file_path} (超过{days}天未修改)")
                except Exception as e:
                    logging.error(f"删除文件失败: {file_path}, 错误: {e}")
        
        return deleted_count
    except Exception as e:
        logging.error(f"清理过期文件过程中发生错误: {e}")
        return deleted_count

def convert_webm_to_mp4(webm_file_path, progress_callback=None, options=None):
    """
    使用ffmpeg-python库将webm格式视频转换为mp4格式
    
    Args:
        webm_file_path: webm文件路径
        progress_callback: 进度回调函数，接收百分比和消息参数
        options: 转换选项字典，支持的选项包括：
            - video_codec: 视频编码器 (默认: 'libx264')
            - audio_codec: 音频编码器 (默认: 'aac')
            - preset: 编码预设 (默认: 'medium')
            - crf: 恒定质量因子 (默认: 22)
            - audio_bitrate: 音频比特率 (默认: '128k')
            - scale: 缩放尺寸，如 '1280:720'
        
    Returns:
        转换后的mp4文件路径，如果转换失败则返回原始文件路径
    """
    if not webm_file_path.endswith('.webm'):
        logging.warning(f"不是webm文件: {webm_file_path}")
        return webm_file_path
        
    mp4_file_path = webm_file_path.replace('.webm', '.mp4')
    
    # 合并默认选项和用户提供的选项
    default_options = {
        'video_codec': 'libx264',
        'audio_codec': 'aac',
        'preset': 'medium',
        'crf': 22,
        'audio_bitrate': '128k',
        'scale': None
    }
    
    if options:
        default_options.update(options)
    
    options = default_options
    
    try:
        # 检查ffmpeg是否可用
        try:
            ffmpeg_version = subprocess.run(
                ['ffmpeg', '-version'], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',  # 明确指定编码
                errors='replace',  # 遇到无法解码的字符时替换
                timeout=5  # 设置超时，避免无限等待
            )
            if ffmpeg_version.returncode != 0:
                logging.error("ffmpeg命令不可用，请确保已安装ffmpeg并添加到PATH中")
                return webm_file_path
        except (subprocess.SubprocessError, FileNotFoundError):
            logging.error("ffmpeg命令不可用，请确保已安装ffmpeg并添加到PATH中")
            return webm_file_path
            
        logging.info(f"开始将 {webm_file_path} 转换为 {mp4_file_path}")
        
        # 使用ffmpeg-python进行转换
        try:
            # 创建输入流
            input_stream = ffmpeg.input(webm_file_path)
            
            # 应用过滤器
            filtered_stream = input_stream
            filter_args = {}
            
            # 如果需要缩放
            if options['scale']:
                filtered_stream = filtered_stream.filter('scale', options['scale'])
            
            # 设置输出参数
            output_args = {
                'vcodec': options['video_codec'],
                'preset': options['preset'],
                'crf': options['crf'],
                'acodec': options['audio_codec'],
                'audio_bitrate': options['audio_bitrate']
            }
            
            # 创建输出流
            output_stream = ffmpeg.output(
                filtered_stream, 
                mp4_file_path,
                **output_args
            )
            
            # 如果需要进度回调
            if progress_callback:
                # 首先获取视频总时长
                probe = ffmpeg.probe(webm_file_path)
                duration = float(probe['format']['duration'])
                
                # 开始执行转换，使用subprocess而不是ffmpeg.run以便捕获实时输出
                cmd = ffmpeg.compile(output_stream, overwrite_output=True)
                
                # 创建进程，重定向输出
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                # 创建一个线程来读取stderr并更新进度
                def monitor_progress():
                    progress_pattern = re.compile(r'time=(\d+:\d+:\d+.\d+)')
                    
                    # 读取stderr以获取进度信息
                    for line in process.stderr:
                        # 搜索时间信息
                        match = progress_pattern.search(line)
                        if match:
                            time_str = match.group(1)
                            # 转换时间字符串为秒
                            h, m, s = time_str.split(':')
                            seconds = float(h) * 3600 + float(m) * 60 + float(s)
                            # 计算百分比
                            percent = min(int((seconds / duration) * 100), 100)
                            # 调用回调函数
                            progress_callback(percent, f"正在转换: {percent}%")
                
                # 启动监控线程
                monitor_thread = threading.Thread(target=monitor_progress)
                monitor_thread.daemon = True
                monitor_thread.start()
                
                # 等待进程完成
                process.wait()
                
                # 检查返回码
                if process.returncode != 0:
                    # 读取错误输出
                    progress_callback(0, "转换失败")
                    error_output = process.stderr.read()
                    logging.error(f"FFmpeg执行失败: {error_output}")
                    return webm_file_path
                
                # 完成时通知
                progress_callback(100, "转换完成")
            else:
                # 如果不需要进度回调，则使用ffmpeg.run
                ffmpeg.run(output_stream, quiet=True, overwrite_output=True)
            
            # 检查转换是否成功
            if os.path.exists(mp4_file_path) and os.path.getsize(mp4_file_path) > 0:
                logging.info(f"成功将 {webm_file_path} 转换为 {mp4_file_path}")
                return mp4_file_path
            else:
                logging.error(f"转换后的文件 {mp4_file_path} 不存在或为空")
                return webm_file_path
                
        except ffmpeg.Error as e:
            # ffmpeg-python错误处理
            stderr = e.stderr.decode('utf-8', errors='replace') if e.stderr else "未知错误"
            logging.error(f"FFmpeg处理错误: {stderr}")
            
            if progress_callback:
                progress_callback(0, f"转换失败: {stderr[:100]}...")
                
            return webm_file_path
            
    except Exception as e:
        logging.error(f"转换视频格式失败: {e}")
        
        if progress_callback:
            progress_callback(0, f"转换失败: {str(e)}")
            
        return webm_file_path 