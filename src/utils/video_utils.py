import os
import subprocess
import logging
import time

def convert_webm_to_mp4(webm_file_path):
    """
    将webm格式视频转换为mp4格式
    
    Args:
        webm_file_path: webm文件路径
        
    Returns:
        转换后的mp4文件路径，如果转换失败则返回原始文件路径
    """
    if not webm_file_path.endswith('.webm'):
        logging.warning(f"不是webm文件: {webm_file_path}")
        return webm_file_path
        
    mp4_file_path = webm_file_path.replace('.webm', '.mp4')
    try:
        # 检查ffmpeg是否可用
        try:
            ffmpeg_version = subprocess.run(
                ['ffmpeg', '-version'], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=5  # 设置超时，避免无限等待
            )
            if ffmpeg_version.returncode != 0:
                logging.error("ffmpeg命令不可用，请确保已安装ffmpeg并添加到PATH中")
                return webm_file_path
        except (subprocess.SubprocessError, FileNotFoundError):
            logging.error("ffmpeg命令不可用，请确保已安装ffmpeg并添加到PATH中")
            return webm_file_path
            
        logging.info(f"开始将 {webm_file_path} 转换为 {mp4_file_path}")
        
        # 使用ffmpeg进行转换，设置较高质量的参数
        command = [
            'ffmpeg', 
            '-i', webm_file_path,  # 输入文件
            '-c:v', 'libx264',     # 视频编码器
            '-preset', 'medium',   # 编码预设，medium提供较好的速度/质量平衡
            '-crf', '22',          # 恒定质量因子，值越小质量越高（18-28之间是较好的范围）
            '-c:a', 'aac',         # 音频编码器
            '-b:a', '128k',        # 音频比特率
            '-y',                  # 如果输出文件已存在，则覆盖
            mp4_file_path          # 输出文件
        ]
        
        # 使用CREATE_NO_WINDOW标志，避免命令窗口闪现
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',  # 明确指定编码
            errors='replace',  # 遇到无法解码的字符时替换
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        # 等待进程完成
        stdout, stderr = process.communicate()
        
        # 检查进程退出码
        if process.returncode != 0:
            logging.error(f"FFmpeg执行失败: {stderr}")
            return webm_file_path
        
        # 检查转换是否成功
        if os.path.exists(mp4_file_path) and os.path.getsize(mp4_file_path) > 0:
            logging.info(f"成功将 {webm_file_path} 转换为 {mp4_file_path}")
            return mp4_file_path
        else:
            logging.error(f"转换后的文件 {mp4_file_path} 不存在或为空")
            return webm_file_path
            
    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg执行失败: {e}")
        return webm_file_path
    except Exception as e:
        logging.error(f"转换视频格式失败: {e}")
        return webm_file_path 