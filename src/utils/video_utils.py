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
    
    # 只有当删除了文件时才记录日志
    if deleted_count > 0:
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
    
    # 明确声明一个全局标志来跟踪是否取消转换，避免不同函数间的状态同步问题
    global_cancel_requested = False
    
    # 创建一个共享的进程引用
    ffmpeg_process = {'process': None}
        
    # 自定义回调处理器函数
    def handle_callback(percent, message, proc=None):
        nonlocal global_cancel_requested
        
        # 如果提供了进程，更新共享引用
        if proc:
            ffmpeg_process['process'] = proc
            
        # 调用原始回调并获取结果
        if progress_callback:
            result = progress_callback(percent, message, proc)
            # 如果回调返回False，表示请求取消
            if result is False:
                logger.info("收到来自UI的取消请求")
                global_cancel_requested = True
                # 立即尝试终止进程
                if ffmpeg_process['process'] and ffmpeg_process['process'].poll() is None:
                    try:
                        logger.info(f"正在终止ffmpeg进程 PID:{ffmpeg_process['process'].pid}")
                        terminate_process(ffmpeg_process['process'])
                    except Exception as e:
                        logger.error(f"终止ffmpeg进程失败: {str(e)}")
                return False
        return True

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
            
            # 如果时长为0时，设置一个默认值
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
                handle_callback(0, "开始转换...", None)
                
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
                            last_report_time = time.time()
                            
                            while True:
                                # 检查是否已经请求终止
                                if terminate_requested:
                                    logger.info("检测到终止标志，停止监控进度")
                                    break
                                    
                                # 从共享变量获取进程引用
                                current_process = process_ref['process']
                                
                                # 检查进程是否已经完成
                                if current_process and current_process.poll() is not None:
                                    if current_process.returncode == 0 and last_percent < 100:
                                        # 进程正常完成但进度未到100%，强制发送100%
                                        logger.info("进程已完成，发送100%进度")
                                        handle_callback(100, "转换完成", current_process)
                                    break
                                
                                # 获取文件当前位置
                                where = f.tell()
                                
                                # 读取新行
                                line = f.readline()
                
                                # 如果没有新行，等待一下再试
                                if not line:
                                    # 检查转换是否已完成
                                    if not os.path.exists(log_path):
                                        break
                                    
                                    # 每3秒，即使没有新进度也发送当前进度，保持UI响应
                                    current_time = time.time()
                                    if current_time - last_report_time > 3 and last_percent > 0:
                                        last_report_time = current_time
                                        handle_callback(last_percent, f"转换中: {last_percent}%", current_process)
                                    
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
                                        percent = min(int((seconds / duration) * 100), 99)  # 最多到99%，留给完成信号
                                        
                                        # 仅在进度有变化或经过一定时间后才更新
                                        current_time = time.time()
                                        if percent != last_percent or current_time - last_report_time > 1:
                                            last_percent = percent
                                            last_report_time = current_time
                                            # 立即传递进程引用和进度
                                            handle_callback(percent, f"转换中: {percent}%", current_process)
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
                        if global_cancel_requested or terminate_requested:
                            logger.info("检测到终止请求，正在强制终止ffmpeg进程")
                            try:
                                terminate_process(process)
                                logger.info("ffmpeg进程已被强制终止")
                                break
                            except Exception as e:
                                logger.error(f"终止进程失败: {safe_str(e)}")
                        time.sleep(0.3)
                
                cancel_checker = threading.Thread(target=check_cancellation)
                cancel_checker.daemon = True
                cancel_checker.start()
                
                # 等待进程完成
                return_code = process.wait()
                
                # 如果请求取消，直接返回原始文件
                if global_cancel_requested or terminate_requested:
                    logger.info("转换过程被用户取消")
                    return input_file
                    
                # 检查输出文件
                if return_code == 0 and os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                    logger.info(f"转换成功: {output_file}")
                    if progress_callback:
                        handle_callback(100, "转换完成", process)
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
                        handle_callback(0, "转换失败", process)
                    
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
                    handle_callback(0, "转换失败", process)
                
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

def terminate_process(process):
    """
    强制终止进程的通用方法
    """
    if not process or process.poll() is not None:
        return

    try:
        pid = process.pid
        logger.info(f"终止进程 PID:{pid}")
        
        if os.name == 'nt':
            # Windows系统使用taskkill命令，强制终止进程及其子进程
            subprocess.call(
                ['taskkill', '/F', '/T', '/PID', str(pid)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # 如果进程仍在运行，使用更强的方法
            if process.poll() is None:
                time.sleep(0.5)
                os.system(f'TASKKILL /F /PID {pid} /T')
        else:
            # Unix系统先尝试正常终止
            process.terminate()
            time.sleep(0.3)
            
            # 如果进程仍在运行，使用SIGKILL信号强制终止
            if process.poll() is None:
                process.kill()
                time.sleep(0.2)
                
                # 如果仍然没有终止，尝试使用系统kill命令
                if process.poll() is None:
                    os.system(f'kill -9 {pid}')
                    
        # 确认进程已终止
        time.sleep(0.2)
        if process.poll() is None:
            logger.warning(f"进程 {pid} 可能仍在运行")
        else:
            logger.info(f"进程 {pid} 已成功终止")
            
    except Exception as e:
        logger.error(f"终止进程 {process.pid} 时出错: {str(e)}")
        logger.error(traceback.format_exc())

def convert_video(
    file_path: str,
    record_id: Optional[int] = None,
    progress_callback: Optional[Callable[[int, str], bool]] = None,
    finished_callback: Optional[Callable[[bool, str, str], None]] = None
) -> None:
    """
    执行视频格式转换的完整流程，包括转换、数据库更新和原始文件删除
    
    Args:
        file_path: 要转换的文件路径
        record_id: 数据库记录ID，用于更新状态
        progress_callback: 进度更新回调函数
        finished_callback: 转换完成后的回调函数
    """
    logger.info(f"开始视频转换流程，文件: {file_path}, 记录ID: {record_id}")
    
    # 确保文件存在
    if not os.path.exists(file_path):
        error_msg = f"要转换的文件不存在: {file_path}"
        logger.error(error_msg)
        if finished_callback:
            finished_callback(False, error_msg, file_path)
        return
    
    # 获取文件扩展名，确定是否需要转换
    _, ext = os.path.splitext(file_path)
    if ext.lower() == '.mp4':
        logger.info(f"文件已经是MP4格式，无需转换: {file_path}")
        if finished_callback:
            finished_callback(True, "文件已经是MP4格式，无需转换", file_path)
        return
    
    # 设置默认转换选项
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
    
    # 生成目标文件路径
    target_file = file_path.replace(ext, '.mp4')
    
    # 初始化转换并首先发送开始信息
    if progress_callback:
        progress_callback(0, "准备开始转换...")
    
    # 转发进度更新到回调函数并添加进程引用参数
    conversion_cancelled = [False]  # 使用列表作为可变对象来跟踪取消状态
    last_percent = [0]  # 跟踪上次发送的百分比
    
    def internal_progress_callback(percent, message, process_ref=None):
        if progress_callback:
            # 更新进度信息，使其更具体
            updated_message = message
            if "转换中" in message:
                updated_message = f"正在转换: {percent}%"
            elif "开始转换" in message:
                updated_message = "正在初始化转换..."
            
            # 只有当百分比发生实质性变化或消息发生变化时才调用外部回调
            if percent != last_percent[0] or "转换中" not in message:
                last_percent[0] = percent
                # 调用外部进度回调
                result = progress_callback(percent, updated_message)
                # 如果返回False，表示请求取消
                if result is False:
                    conversion_cancelled[0] = True
                    return False
        return True
    
    try:
        # 执行转换
        start_time = time.time()
        
        # 调用外部回调通知转换开始
        if progress_callback:
            progress_callback(0, "开始转换视频...")
        
        output_file = convert_webm_to_mp4(
            file_path, 
            output_file=target_file,
            progress_callback=internal_progress_callback,
            options=convert_options
        )
        
        # 如果转换被取消
        if conversion_cancelled[0]:
            logger.info("视频转换被取消")
            # 更新数据库状态
            if record_id:
                try:
                    from src.db.download_history import DownloadHistoryDB
                    db = DownloadHistoryDB()
                    db.update_conversion_status(
                        file_path=file_path,
                        status="转换中断",
                        error_message="用户取消了视频转换",
                        record_id=record_id
                    )
                except Exception as e:
                    logger.error(f"更新数据库状态失败: {str(e)}")
            
            # 调用完成回调
            if finished_callback:
                finished_callback(False, "用户取消了转换", file_path)
            return
        
        # 检查转换结果
        if output_file.endswith('.mp4') and os.path.exists(output_file):
            elapsed_time = time.time() - start_time
            success_message = f"转换完成，耗时: {elapsed_time:.2f}秒"
            logger.info(success_message)
            
            # 确保最后发送100%进度
            if progress_callback:
                progress_callback(100, "转换完成")
            
            # 更新数据库
            if record_id:
                try:
                    from src.db.download_history import DownloadHistoryDB
                    db = DownloadHistoryDB()
                    db.update_conversion_status(
                        file_path=output_file,
                        status="完成",
                        record_id=record_id
                    )
                    logger.info(f"已更新MP4文件路径到数据库，记录ID: {record_id}, 文件: {output_file}")
                except Exception as e:
                    logger.error(f"更新MP4文件路径到数据库失败: {str(e)}")
            
            # 删除原始文件
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"已自动删除原始文件: {file_path}")
            except Exception as e:
                logger.error(f"删除原始文件失败: {str(e)}")
            
            # 调用完成回调
            if finished_callback:
                finished_callback(True, success_message, output_file)
        else:
            error_message = f"转换失败，请检查源文件和转换设置，文件路径: {file_path}"
            logger.error(error_message)
            
            # 更新数据库状态
            if record_id:
                try:
                    from src.db.download_history import DownloadHistoryDB
                    db = DownloadHistoryDB()
                    db.update_conversion_status(
                        file_path=file_path,
                        status="转换中断",
                        error_message=error_message,
                        record_id=record_id
                    )
                except Exception as e:
                    logger.error(f"更新数据库状态失败: {str(e)}")
            
            # 调用完成回调
            if finished_callback:
                finished_callback(False, error_message, file_path)
    except Exception as e:
        # 捕获转换过程中的任何异常
        error_details = traceback.format_exc()
        error_message = f"转换过程中出错: {str(e)}"
        logger.error(error_message)
        logger.error(error_details)
        
        # 更新数据库状态
        if record_id:
            try:
                from src.db.download_history import DownloadHistoryDB
                db = DownloadHistoryDB()
                db.update_conversion_status(
                    file_path=file_path,
                    status="转换中断",
                    error_message=error_message,
                    record_id=record_id
                )
            except Exception as ex:
                logger.error(f"更新数据库状态失败: {str(ex)}")
        
        # 调用完成回调
        if finished_callback:
            finished_callback(False, error_message, file_path)
