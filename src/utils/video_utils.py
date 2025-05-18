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
            - video_codec: 视频编码器 (默认: 'av1_nvenc')
            - audio_codec: 音频编码器 (默认: 'aac')
            - preset: 编码预设 (默认: 'veryslow')
            - crf: 恒定质量因子 (默认: 22)
            - audio_bitrate: 音频比特率 (默认: '320k')
            - scale: 缩放尺寸，如 '1280:720'
            - keep_source_bitrate: 是否保持原视频比特率 (默认: True)
            - use_vbr: 是否使用可变比特率 (默认: True)
            - min_bitrate: 最小比特率，仅在use_vbr=True时有效 (默认: None)
            - max_bitrate: 最大比特率，仅在use_vbr=True时有效 (默认: None)
            - buffer_size: 缓冲区大小，用于VBR (默认: None)
        
    Returns:
        转换后的mp4文件路径，如果转换失败则返回原始文件路径
    """
    if not webm_file_path.endswith('.webm'):
        logging.warning(f"不是webm文件: {webm_file_path}")
        return webm_file_path
        
    mp4_file_path = webm_file_path.replace('.webm', '.mp4')
    
    # 合并默认选项和用户提供的选项
    default_options = {
        'video_codec': 'av1_nvenc',  # 使用NVIDIA GPU加速AV1编码器
        'audio_codec': 'aac',
        'preset': 'p7',            # 使用最高质量预设
        'cq': 20,                  # AV1的VBR模式下的质量值(0-63)
        'audio_bitrate': '320k',
        'scale': None,
        'keep_source_bitrate': True,
        'rc': 'vbr',               # 使用VBR模式
        'multipass': 'qres',       # 两通道编码，四分之一分辨率
        'rc-lookahead': 32,        # 前瞻帧数
        'spatial-aq': True,        # 启用空间自适应量化
        'temporal-aq': True,       # 启用时间自适应量化
        'gpu': 0,                  # 默认使用GPU 0
        'fallback_codecs': ['h264_nvenc', 'hevc_nvenc', 'libx264'],  # 备用编码器列表
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
                timeout=5,  # 设置超时，避免无限等待
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            if ffmpeg_version.returncode != 0:
                logging.error("ffmpeg命令不可用，请确保已安装ffmpeg并添加到PATH中")
                return webm_file_path
        except (subprocess.SubprocessError, FileNotFoundError):
            logging.error("ffmpeg命令不可用，请确保已安装ffmpeg并添加到PATH中")
            return webm_file_path
            
        # 检查是否支持NVIDIA编码器
        if 'nvenc' in options['video_codec']:
            try:
                # 检查NVIDIA编码器是否可用
                nvenc_check = subprocess.run(
                    ['ffmpeg', '-encoders'], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                if options['video_codec'] not in nvenc_check.stdout:
                    logging.warning(f"检测到NVIDIA编码器 {options['video_codec']} 不可用，将尝试使用替代编码器")
                    
                    # 尝试回退到备用编码器列表
                    fallback_used = False
                    if 'fallback_codecs' in options and options['fallback_codecs']:
                        for codec in options['fallback_codecs']:
                            if codec in nvenc_check.stdout:
                                options['video_codec'] = codec
                                logging.info(f"已切换到备用编码器: {codec}")
                                fallback_used = True
                                break
                    
                    # 如果没有在备用列表中找到可用编码器，则尝试其他NVIDIA编码器
                    if not fallback_used:
                        if 'h264_nvenc' in nvenc_check.stdout:
                            options['video_codec'] = 'h264_nvenc'
                            logging.info("已切换到 h264_nvenc 编码器")
                        elif 'hevc_nvenc' in nvenc_check.stdout:
                            options['video_codec'] = 'hevc_nvenc'
                            logging.info("已切换到 hevc_nvenc 编码器")
                        else:
                            # 如果没有可用的NVIDIA编码器，则使用CPU编码器
                            options['video_codec'] = 'libx264'
                            logging.warning("未检测到可用的NVIDIA编码器，将使用CPU编码 (libx264)")
            except Exception as e:
                logging.error(f"检查NVIDIA编码器时出错: {e}")
                options['video_codec'] = 'libx264'
                logging.warning("由于检查错误，将使用CPU编码 (libx264)")
            
        logging.info(f"开始将 {webm_file_path} 转换为 {mp4_file_path}")
        logging.info(f"使用编码器: {options['video_codec']}")
        
        # 使用ffmpeg-python进行转换
        try:
            # 首先获取源视频信息
            if progress_callback:
                progress_callback(0, "正在分析源视频信息...")
                
            probe = ffmpeg.probe(webm_file_path)
            
            # 源视频比特率、分辨率等信息
            video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
            audio_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'audio'), None)
            
            # 如果设置了保持原比特率
            video_bitrate = None
            audio_bitrate = None
            
            if options['keep_source_bitrate']:
                # 尝试获取视频比特率
                if video_stream:
                    # 尝试不同的方式获取比特率
                    if 'bit_rate' in video_stream:
                        video_bitrate = int(video_stream['bit_rate'])
                    elif 'tags' in video_stream and 'BPS' in video_stream['tags']:
                        video_bitrate = int(video_stream['tags']['BPS'])
                    elif 'bit_rate' in probe['format']:
                        # 如果没有视频流比特率，但有总比特率，可以估算
                        video_bitrate = int(float(probe['format']['bit_rate']) * 0.85)  # 假设视频占总比特率的85%
                
                # 尝试获取音频比特率
                if audio_stream:
                    if 'bit_rate' in audio_stream:
                        audio_bitrate = int(audio_stream['bit_rate'])
                    elif 'tags' in audio_stream and 'BPS' in audio_stream['tags']:
                        audio_bitrate = int(audio_stream['tags']['BPS'])
            
            # 记录获取到的比特率信息
            if video_bitrate:
                logging.info(f"源视频比特率: {video_bitrate} bps")
            else:
                logging.warning("无法获取源视频比特率，将使用默认设置")
                
            if audio_bitrate:
                logging.info(f"源音频比特率: {audio_bitrate} bps")
            else:
                logging.warning("无法获取源音频比特率，将使用默认设置")
            
            # 获取视频总时长用于计算进度
            duration = float(probe['format']['duration'])
            
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
                'acodec': options['audio_codec']
            }
            
            # 设置使用的GPU
            if 'gpu' in options and options['gpu'] is not None:
                output_args['gpu'] = str(options['gpu'])
                logging.info(f"使用GPU {options['gpu']} 进行编码")
            
            # 设置码率控制模式
            if 'rc' in options and options['rc']:
                output_args['rc'] = options['rc']
                logging.info(f"使用码率控制: {options['rc']}")
                
                # VBR模式下，设置目标质量
                if options['rc'] == 'vbr' and 'cq' in options:
                    output_args['cq'] = str(options['cq'])
                    logging.info(f"VBR质量值: {options['cq']}")
            
            # 设置多通道编码
            if 'multipass' in options and options['multipass']:
                output_args['multipass'] = options['multipass']
                logging.info(f"多通道编码: {options['multipass']}")
            
            # 设置前瞻帧数
            if 'rc-lookahead' in options and options['rc-lookahead']:
                output_args['rc-lookahead'] = str(options['rc-lookahead'])
                logging.info(f"前瞻帧数: {options['rc-lookahead']}")
            
            # 设置自适应量化
            if 'spatial-aq' in options and options['spatial-aq']:
                output_args['spatial-aq'] = '1'
                logging.info("启用空间自适应量化")
                
            if 'temporal-aq' in options and options['temporal-aq']:
                output_args['temporal-aq'] = '1'
                logging.info("启用时间自适应量化")
            
            # 设置视频比特率限制（如果需要）
            if video_bitrate and options['keep_source_bitrate']:
                # 将bps转换为kbps，ffmpeg接受的格式
                video_bitrate_k = str(int(video_bitrate / 1000)) + 'k'
                
                # 根据编码模式设置比特率参数
                if options.get('rc') == 'vbr':
                    # VBR模式设置最大比特率和缓冲区
                    output_args['maxrate'] = video_bitrate_k
                    output_args['bufsize'] = str(int(video_bitrate / 500)) + 'k'
                elif options.get('rc') == 'cbr':
                    # CBR模式设置固定比特率
                    output_args['b:v'] = video_bitrate_k
                    output_args['minrate'] = video_bitrate_k
                    output_args['maxrate'] = video_bitrate_k
                    output_args['bufsize'] = video_bitrate_k
            
            # 设置音频比特率
            if audio_bitrate and options['keep_source_bitrate']:
                # 将bps转换为kbps
                audio_bitrate_k = str(int(audio_bitrate / 1000)) + 'k'
                output_args['audio_bitrate'] = audio_bitrate_k
            else:
                # 使用默认音频比特率
                output_args['audio_bitrate'] = options['audio_bitrate']
            
            # 创建输出流
            output_stream = ffmpeg.output(
                filtered_stream, 
                mp4_file_path,
                **output_args
            )
            
            # 如果需要进度回调
            if progress_callback:
                # 开始执行转换，使用subprocess而不是ffmpeg.run以便捕获实时输出
                cmd = ffmpeg.compile(output_stream, overwrite_output=True)
                
                # 记录完整命令
                logging.debug(f"FFmpeg命令: {' '.join(cmd)}")
                
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
                    error_logs = []
                    
                    # 读取stderr以获取进度信息
                    for line in process.stderr:
                        # 记录错误信息
                        error_logs.append(line.strip())
                        
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
                    stderr_output = "\n".join([line for line in process.stderr.readlines()])
                    logging.error(f"FFmpeg执行失败: {stderr_output}")
                    
                    # 如果是编码器错误，尝试使用备用编码器
                    if ("No such filter" in stderr_output or 
                        "Error initializing output stream" in stderr_output or 
                        "Encoder not found" in stderr_output or
                        "Invalid encoder type" in stderr_output or
                        "Unrecognized option" in stderr_output):
                        
                        logging.warning(f"{options['video_codec']}编码器不可用或参数无效，尝试使用备用编码器...")
                        
                        # 尝试使用备用编码器列表
                        fallback_found = False
                        if 'fallback_codecs' in options and options['fallback_codecs']:
                            for codec in options['fallback_codecs']:
                                logging.info(f"尝试使用备用编码器: {codec}")
                                
                                # 创建新的输出参数
                                if 'nvenc' in codec:
                                    # NVIDIA编码器参数
                                    output_args = {
                                        'vcodec': codec,
                                        'preset': 'p7',  # 使用最高质量预设
                                        'rc': 'vbr',     # 使用VBR模式
                                        'cq': '20',      # 质量值
                                        'spatial-aq': '1',  # 空间自适应量化
                                        'temporal-aq': '1', # 时间自适应量化
                                        'rc-lookahead': '32', # 前瞻帧数
                                        'acodec': options['audio_codec'],
                                        'gpu': str(options['gpu']) if 'gpu' in options else '0'
                                    }
                                else:
                                    # CPU编码器参数 (如libx264)
                                    output_args = {
                                        'vcodec': codec,
                                        'preset': 'slow',  # CPU编码器的预设
                                        'crf': '20',       # CRF质量值
                                        'acodec': options['audio_codec']
                                    }
                                
                                # 如果保持原比特率，设置相关参数
                                if video_bitrate and options['keep_source_bitrate']:
                                    video_bitrate_k = str(int(video_bitrate / 1000)) + 'k'
                                    
                                    if 'nvenc' in codec:
                                        # NVIDIA编码器设置最大比特率
                                        output_args['maxrate'] = video_bitrate_k
                                        output_args['bufsize'] = str(int(video_bitrate / 500)) + 'k'
                                    else:
                                        # libx264等编码器设置最大比特率
                                        output_args['maxrate'] = video_bitrate_k
                                        output_args['bufsize'] = str(int(video_bitrate / 500)) + 'k'
                                
                                # 设置音频比特率
                                if audio_bitrate and options['keep_source_bitrate']:
                                    audio_bitrate_k = str(int(audio_bitrate / 1000)) + 'k'
                                    output_args['audio_bitrate'] = audio_bitrate_k
                                else:
                                    output_args['audio_bitrate'] = options['audio_bitrate']
                                
                                # 创建新的输出流
                                output_stream = ffmpeg.output(
                                    filtered_stream, 
                                    mp4_file_path,
                                    **output_args
                                )
                                
                                try:
                                    # 直接使用ffmpeg.run运行命令
                                    ffmpeg.run(output_stream, quiet=False, overwrite_output=True)
                                    
                                    # 检查转换是否成功
                                    if os.path.exists(mp4_file_path) and os.path.getsize(mp4_file_path) > 0:
                                        logging.info(f"成功使用备用编码器 {codec} 将 {webm_file_path} 转换为 {mp4_file_path}")
                                        fallback_found = True
                                        return mp4_file_path
                                except ffmpeg.Error as e:
                                    stderr = e.stderr.decode('utf-8', errors='replace') if e.stderr else "未知错误"
                                    logging.error(f"备用编码器 {codec} 处理错误: {stderr}")
                                    continue  # 尝试下一个编码器
                        
                        if not fallback_found:
                            if progress_callback:
                                progress_callback(0, "所有编码器都失败，无法转换视频")
                            logging.error("所有编码器都失败，无法转换视频")
                    
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

# 检查系统中的NVIDIA NVENC编码器支持情况
def check_nvidia_encoder():
    """
    检查系统中是否有可用的NVIDIA编码器
    
    Returns:
        list: 可用的NVIDIA编码器列表
    """
    try:
        # 查询系统中的ffmpeg编码器
        ffmpeg_version = subprocess.run(
            ['ffmpeg', '-encoders'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        # 如果查询成功
        if ffmpeg_version.returncode == 0:
            # 解析输出找出NVIDIA编码器
            output = ffmpeg_version.stdout
            nvidia_encoders = []
            
            # 查找NVIDIA编码器
            for line in output.splitlines():
                if 'nvenc' in line and 'V' in line[:5]:  # 视频编码器以V开头
                    codec_name = line.split()[1]
                    nvidia_encoders.append(codec_name)
            
            # 检查是否有可用的GPU
            if nvidia_encoders:
                logging.info(f"检测到NVIDIA编码器: {', '.join(nvidia_encoders)}")
                
                # 检查系统是否有可用的NVIDIA GPU
                nvenc_check = subprocess.run(
                    ['nvidia-smi', '-L'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                if nvenc_check.returncode == 0:
                    gpu_count = len(nvenc_check.stdout.strip().split('\n'))
                    logging.info(f"检测到{gpu_count}个NVIDIA GPU")
                    return nvidia_encoders
            
            return []
            
    except Exception as e:
        logging.warning(f"检查NVIDIA编码器失败: {str(e)}")
        return [] 