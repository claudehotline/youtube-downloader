import os
import subprocess
import logging
import time
import json
import re
import threading
import traceback
from typing import Union, Optional, Callable, Dict, Any
import ffmpeg
import tempfile


# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def custom_ffprobe(filename: str) -> Dict:
    """
    自定义的ffprobe函数，避免str对象的decode问题
    """
    try:
        cmd = [
            'ffprobe', 
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            filename
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        if result.returncode != 0:
            logger.error(f"ffprobe失败: {result.stderr}")
            return {}
        
        return json.loads(result.stdout)
    except Exception as e:
        logger.error(f"ffprobe错误: {e}")
        return {}

def clean_old_files(directory: str, days: int = 7, extensions: Optional[list] = None) -> int:
    """
    清理指定目录中超过指定天数的文件
    """
    if not os.path.exists(directory) or not os.path.isdir(directory):
        logger.warning(f"目录不存在或不是有效目录: {directory}")
        return 0
    
    cutoff_time = time.time() - (days * 24 * 60 * 60)
    deleted_count = 0
    
    try:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            
            if os.path.isdir(file_path):
                continue
            
            if extensions is not None:
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext not in extensions:
                    continue
            
            file_mtime = os.path.getmtime(file_path)
            if file_mtime < cutoff_time:
                try:
                    os.remove(file_path)
                    logger.info(f"已删除过期文件: {file_path}")
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"删除文件时出错: {file_path}, 错误: {e}")
        
    except Exception as e:
        logger.error(f"清理目录时出错: {directory}, 错误: {e}")
    
    logger.info(f"共删除 {deleted_count} 个过期文件")
    return deleted_count

def safe_str(obj: Any) -> str:
    """将任何对象安全地转换为字符串"""
    if isinstance(obj, bytes):
        try:
            return obj.decode('utf-8', errors='replace')
        except Exception:
            return str(obj)
    return str(obj)

def convert_webm_to_mp4(input_file: str, output_file: Optional[str] = None, 
                        progress_callback: Optional[Callable[[int, str, Optional[subprocess.Popen]], bool]] = None,
                        options: Optional[Dict[str, Any]] = None) -> str:
    """
    将WebM视频转换为MP4格式，利用NVIDIA GPU进行硬件加速编码
    
    Args:
        input_file: 输入WebM文件路径
        output_file: 输出MP4文件路径 (如果为None，则使用输入文件名替换扩展名)
        progress_callback: 进度回调函数，接收进度百分比、状态消息和进程引用
        options: 额外的编码选项
        
    Returns:
        输出文件路径
    """
    logger.info(f"开始转换WebM到MP4: {input_file}")
    
    # 如果没有提供输出路径，则使用输入文件名但更改扩展名
    if output_file is None:
        output_file = os.path.splitext(input_file)[0] + '.mp4'
    
    # 如果输入文件不存在，直接返回
    if not os.path.exists(input_file):
        logger.error(f"输入文件不存在: {input_file}")
        if progress_callback:
            progress_callback(0, "输入文件不存在", None)
        return input_file
    
    try:
        # 使用ffmpeg-python获取视频信息
        try:
            # 修复ffmpeg-python的probe调用
            try:
                cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', input_file]
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                if result.returncode == 0:
                    probe = json.loads(result.stdout)
                else:
                    logger.warning(f"内置ffprobe失败，尝试使用自定义探测：{safe_str(result.stderr)}")
                    probe = custom_ffprobe(input_file)
            except Exception as e:
                logger.warning(f"使用subprocess进行probe失败，尝试ffmpeg-python的probe: {safe_str(e)}")
                try:
                    probe = ffmpeg.probe(input_file)
                except Exception as inner_e:
                    logger.error(f"ffmpeg-python探测失败，尝试自定义探测: {safe_str(inner_e)}")
                    probe = custom_ffprobe(input_file)
                
        except Exception as e:
            logger.error(f"无法获取视频信息: {safe_str(e)}")
            if progress_callback:
                progress_callback(0, "无法获取视频信息", None)
            return input_file
        
        # 检查视频流
        video_stream = None
        for stream in probe.get('streams', []):
            if stream.get('codec_type') == 'video':
                video_stream = stream
                break
                    
        if not video_stream:
            logger.error("未找到视频流")
            if progress_callback:
                progress_callback(0, "无法获取视频信息", None)
            return input_file
        
        # 从视频流获取时长和码率
        try:
            # 获取视频时长
            try:
                duration = float(video_stream.get('duration', 0))
            except (ValueError, TypeError):
                duration = float(probe.get('format', {}).get('duration', 0))
        
            # 如果时长仍然为0，尝试从format中获取
            if duration <= 0:
                try:
                    duration = float(probe.get('format', {}).get('duration', 0))
                except (ValueError, TypeError):
                    duration = 0
            
            # 时长为0时，设置一个默认值
            if duration <= 0:
                duration = 300.0  # 默认假设视频有5分钟
                logger.warning(f"无法获取视频时长，使用默认值 {duration}秒")
            
            # 获取视频比特率，用于保持质量
            try:
                bit_rate = int(video_stream.get('bit_rate', 0))
            except (ValueError, TypeError):
                bit_rate = 0
            
            # 如果比特率无效，尝试从格式信息中获取
            if bit_rate <= 0:
                try:
                    bit_rate = int(probe.get('format', {}).get('bit_rate', 0))
                except (ValueError, TypeError):
                    bit_rate = 0
            
            # 比特率过低或无法获取时，设置默认值
            if bit_rate <= 100000:  # 低于100kbps认为是无效值
                bit_rate = 5000000  # 默认5Mbps
                logger.warning(f"无法获取有效的视频比特率，使用默认值 {bit_rate/1000:.0f}kbps")
            
            # 通知开始转换
            if progress_callback:
                progress_callback(0, "开始转换...", None)
                
        except Exception as e:
            logger.error(f"分析视频信息时出错: {safe_str(e)}")
            # 设置默认值
            duration = 300.0
            bit_rate = 5000000
        
        # 检测可用的编码器
        encoders = detect_encoders()
        video_codec = select_best_encoder(encoders)
        logger.info(f"使用编码器: {video_codec}")
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 提取音频流信息
        audio_stream = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)
        
        if not video_stream:
            logger.error("无法找到视频流")
            return input_file
        
        # 获取视频长度，用于计算进度
            duration = float(probe['format']['duration'])
            
        # 提取原始视频比特率
        video_bitrate = None
        if 'bit_rate' in video_stream:
            video_bitrate = int(video_stream['bit_rate'])
        elif 'bit_rate' in probe['format']:
            # 如果没有视频流比特率，但有总比特率，可以估算
            total_bitrate = int(probe['format']['bit_rate'])
            video_bitrate = int(total_bitrate * 0.85)  # 假设视频占总比特率的85%
        
        if video_bitrate:
            logger.info(f"源视频比特率: {video_bitrate / 1000:.2f} kbps")
        
        # 提取原始音频比特率
        audio_bitrate = None
        if audio_stream and 'bit_rate' in audio_stream:
            audio_bitrate = int(audio_stream['bit_rate'])
            logger.info(f"源音频比特率: {audio_bitrate / 1000:.2f} kbps")
        
        # 准备ffmpeg参数
        global_args = ['-v', 'info', '-stats']
        
        # 创建ffmpeg输入
        input_stream = ffmpeg.input(input_file)
            
        # 准备输出参数
        output_kwargs = {
            'f': 'mp4',  # 强制输出为MP4格式
            'movflags': '+faststart',  # 优化MP4结构以便快速开始播放
        }
        
        # 设置视频编码器和参数
        if video_codec == 'av1_nvenc':
            # AV1 NVENC参数
            output_kwargs.update({
                'c:v': video_codec,
                'preset': 'p7',
                'rc': 'vbr',
                'cq': 20,
                'gpu': 0,
                'spatial-aq': 1,
                'tune': 'hq',
            })
        elif 'nvenc' in video_codec:
            # 其他NVENC编码器参数
            output_kwargs.update({
                'c:v': video_codec,
                'preset': 'p7',
                'rc': 'vbr',
                'cq': 20,
                'spatial-aq': 1,
                'temporal-aq': 1,
                'gpu': 0,
            })
        else:
            # 软件编码器参数
            output_kwargs.update({
                'c:v': video_codec,
                'preset': 'medium' if video_codec == 'libx264' else 'slow',
                'crf': 23,
            })
        
        # 设置视频比特率
        if video_bitrate:
            output_kwargs['b:v'] = f"{int(video_bitrate)}"
            output_kwargs['maxrate'] = f"{int(video_bitrate * 1.5)}"
            output_kwargs['bufsize'] = f"{int(video_bitrate * 2)}"
        
        # 设置音频编码器和比特率
        output_kwargs['c:a'] = 'aac'
        
        if audio_bitrate:
            output_kwargs['b:a'] = f"{int(audio_bitrate)}"
        else:
            output_kwargs['b:a'] = '192k'
        
        # 应用用户自定义选项
        if options and isinstance(options, dict):
            # 过滤掉不被ffmpeg直接支持的选项
            supported_keys = {
                'c:v', 'c:a', 'b:v', 'b:a', 'preset', 'crf', 'maxrate', 
                'bufsize', 'f', 'movflags', 'rc', 'cq', 'gpu', 'spatial-aq', 
                'temporal-aq', 'tune', 'profile:v', 'level', 'g', 'bf', 
                'refs', 'rc-lookahead', 'me', 'subq', 'trellis'
            }
            # 只添加支持的选项
            filtered_options = {k: v for k, v in options.items() if k in supported_keys}
            output_kwargs.update(filtered_options)
                    
        # 移除不支持的参数
        for key in list(output_kwargs.keys()):
            if key in ['fallback_codecs', 'video_codec', 'aq-strength', 'lookahead_level', 
                      'keep_source_bitrate', 'tf_level', 'multipass', 'rc-lookahead']:
                output_kwargs.pop(key, None)
        
        # 创建输出流
        output_stream = ffmpeg.output(input_stream, output_file, **output_kwargs)
                    
        # 创建临时文件来存储进度输出
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.log', delete=False) as log_file:
            log_path = log_file.name
            logger.info(f"创建临时日志文件: {log_path}")
                    
            # 启动进度监控线程
            if progress_callback:
                # 创建一个进程终止标志
                terminate_requested = False
                # 创建一个共享的进程引用变量
                process_ref = {'process': None}
                
                def monitor_progress():
                    # 获取外部作用域的变量
                    nonlocal terminate_requested
                    
                    # 等待一小段时间，确保日志文件已经创建
                    time.sleep(0.5)
                    
                    # 打开日志文件
                    try:
                        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                            progress_pattern = re.compile(r'time=(\d+:\d+:\d+.\d+)')
                            last_percent = 0
                            
                            while True:
                                # 检查是否已经请求终止
                                if terminate_requested:
                                    logger.info("检测到终止标志，停止监控进度")
                                    break
                                    
                                # 从共享变量获取进程引用
                                current_process = process_ref['process']
                                
                                # 获取文件当前位置
                                where = f.tell()
                                
                                # 读取新行
                                line = f.readline()
                
                                # 如果没有新行，等待一下再试
                                if not line:
                                    # 检查转换是否已完成
                                    if not os.path.exists(log_path):
                                        break
                                    
                                    time.sleep(0.1)
                                    f.seek(where)
                                    continue
                                
                                # 检查是否是进度信息
                                match = progress_pattern.search(line)
                                if match:
                                    time_str = match.group(1)
                                    parts = time_str.split(':')
                                    if len(parts) == 3:
                                        h, m, s = parts
                                        seconds = float(h) * 3600 + float(m) * 60 + float(s)
                                        
                                        # 计算进度百分比
                                        percent = min(int((seconds / duration) * 100), 100)
                                        
                                        # 仅在进度有变化时才更新
                                        if percent != last_percent:
                                            last_percent = percent
                                            # 立即传递进程引用
                                            if current_process and progress_callback:
                                                should_continue = progress_callback(percent, f"转换中: {percent}%", current_process)
                                                if should_continue is False:
                                                    logger.info("收到取消请求，设置终止标志")
                                                    terminate_requested = True
                                                    # 终止进程
                                                    if current_process and current_process.poll() is None:
                                                        try:
                                                            logger.info(f"终止ffmpeg进程 PID:{current_process.pid}")
                                                            if os.name == 'nt':
                                                                # 使用taskkill强制终止进程树
                                                                subprocess.call(['taskkill', '/F', '/T', '/PID', str(current_process.pid)],
                                                                              creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                                                            else:
                                                                current_process.terminate()
                                                                time.sleep(0.5)
                                                                if current_process.poll() is None:
                                                                    current_process.kill()
                                                            logger.info("ffmpeg进程已终止")
                                                            return
                                                        except Exception as e:
                                                            logger.error(f"终止进程时出错: {safe_str(e)}")
                                                        return
                    except Exception as e:
                        logger.error(f"监控进度时出错: {safe_str(e)}")
                        logger.error(traceback.format_exc())
                
                # 启动监控线程
                monitor_thread = threading.Thread(target=monitor_progress)
                monitor_thread.daemon = True
                monitor_thread.start()
            
            try:
                # 执行转换，将日志输出到文件
                cmd = ffmpeg.compile(output_stream, overwrite_output=True)
                
                # 确保添加-v info和-stats参数以输出进度信息
                if '-v' not in cmd:
                    cmd.insert(1, '-v')
                    cmd.insert(2, 'info')
                
                if '-stats' not in cmd:
                    cmd.insert(3, '-stats')
                
                logger.info(f"执行命令: {' '.join(cmd)}")
                
                # 使用Popen直接运行，并将输出重定向到日志文件
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    encoding='utf-8',
                    errors='replace',
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                # 更新进程引用
                if progress_callback:
                    process_ref['process'] = process
                
                # 读取stderr进行日志捕获
                log_handler = threading.Thread(
                    target=lambda: handle_ffmpeg_output(process, log_path)
                )
                log_handler.daemon = True
                log_handler.start()
                
                # 添加一个检查取消的线程
                def check_cancellation():
                    while process and process.poll() is None:
                        if terminate_requested:
                            logger.info("检测到终止请求，正在强制终止ffmpeg进程")
                            try:
                                if os.name == 'nt':
                                    subprocess.call(['taskkill', '/F', '/T', '/PID', str(process.pid)],
                                                  creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                                else:
                                    process.terminate()
                                    time.sleep(0.5)
                                    if process.poll() is None:
                                        process.kill()
                                logger.info("ffmpeg进程已被强制终止")
                                break
                            except Exception as e:
                                logger.error(f"终止进程失败: {safe_str(e)}")
                        time.sleep(0.5)
                
                cancel_checker = threading.Thread(target=check_cancellation)
                cancel_checker.daemon = True
                cancel_checker.start()
                
                # 等待进程完成
                return_code = process.wait()
                
                # 给线程一点时间完成写入
                time.sleep(0.5)
                    
                # 检查输出文件
                if return_code == 0 and os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                    logger.info(f"转换成功: {output_file}")
                    if progress_callback:
                        progress_callback(100, "转换完成", process)
                    return output_file
                else:
                    logger.error(f"转换失败，返回代码: {return_code}")
                    
                    # 尝试读取错误信息
                    stderr_text = ""
                    try:
                        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                            stderr_text = f.read()
                    except:
                        pass
                        
                    logger.error(f"ffmpeg错误: {stderr_text}")
                    
                    if progress_callback:
                        progress_callback(0, "转换失败", process)
                    
                    # 如果主要编码器失败，尝试备用编码器
                    if video_codec != 'libx264':
                        logger.info(f"尝试使用备用编码器 libx264")
                        
                        # 创建新的options字典，只更改编码器
                        fallback_options = options.copy() if options else {}
                        fallback_options['c:v'] = 'libx264'
                        
                        return convert_webm_to_mp4(
                            input_file,
                            output_file,
                            progress_callback,
                            fallback_options
                        )
                    
                    return input_file
                    
            except Exception as e:
                stderr = safe_str(e)
                logger.error(f"ffmpeg错误: {stderr}")
                
                if progress_callback:
                    progress_callback(0, "转换失败", process)
                
                # 如果主要编码器失败，尝试备用编码器
                if video_codec != 'libx264':
                    logger.info(f"尝试使用备用编码器 libx264")
                    
                    # 创建新的options字典，只更改编码器
                    fallback_options = options.copy() if options else {}
                    fallback_options['c:v'] = 'libx264'
                    
                    return convert_webm_to_mp4(
                        input_file,
                        output_file,
                        progress_callback,
                        fallback_options
                    )
                
                return input_file
            
            finally:
                # 清理临时日志文件
                try:
                    if os.path.exists(log_path):
                        os.unlink(log_path)
                except:
                    pass
            
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"转换过程中发生错误: {safe_str(e)}")
        logger.error(f"错误详情: {error_traceback}")
        if progress_callback:
            progress_callback(0, f"转换失败: {safe_str(e)}", None)
        return input_file

# 处理ffmpeg输出的辅助函数
def handle_ffmpeg_output(process, log_path):
    try:
        # 读取进程的stderr
        with open(log_path, 'w', encoding='utf-8', errors='replace') as log:
            for line in process.stderr:
                log.write(line)
                log.flush()
    except Exception as e:
        logger.error(f"处理ffmpeg输出时发生错误: {safe_str(e)}")
        logger.error(traceback.format_exc())

def detect_encoders() -> Dict[str, bool]:
    """检测系统中可用的编码器"""
    encoders = {
        'av1_nvenc': False,
        'hevc_nvenc': False,
        'h264_nvenc': False,
        'libx264': False,
        'libaom-av1': False
    }
    
    try:
        # 检查ffmpeg可用性
        result = subprocess.run(
            ['ffmpeg', '-encoders'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        if result.returncode == 0:
            # 解析可用编码器
            for line in result.stdout.splitlines():
                for encoder in encoders.keys():
                    if encoder in line:
                        encoders[encoder] = True
        
        # 额外检查NVIDIA硬件
        if any(encoder for encoder, available in encoders.items() if 'nvenc' in encoder and available):
            try:
                nvidia_check = subprocess.run(
                    ['nvidia-smi'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                if nvidia_check.returncode != 0:
                    # nvidia-smi失败，禁用所有NVENC编码器
                    for encoder in encoders.keys():
                        if 'nvenc' in encoder:
                            encoders[encoder] = False
            except Exception:
                # 如果无法运行nvidia-smi，禁用所有NVENC编码器
                for encoder in encoders.keys():
                    if 'nvenc' in encoder:
                        encoders[encoder] = False
            
    except Exception as e:
        logger.error(f"检测编码器时出错: {safe_str(e)}")
    
    # 记录可用编码器
    available = [encoder for encoder, available in encoders.items() if available]
    logger.info(f"可用编码器: {', '.join(available) if available else '无'}")
    
    return encoders

def select_best_encoder(encoders: Dict[str, bool]) -> str:
    """选择最佳可用编码器"""
    # 按优先级尝试编码器，优先使用AV1
    preferred_order = ['av1_nvenc', 'libaom-av1', 'hevc_nvenc', 'h264_nvenc', 'libx264']
    
    for encoder in preferred_order:
        if encoders.get(encoder, False):
            return encoder
    
    # 如果没有可用的编码器，默认返回libx264
    return 'libx264'
