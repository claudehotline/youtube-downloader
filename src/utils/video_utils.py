import os
import subprocess
import logging

def convert_webm_to_mp4(webm_file_path):
    """
    将webm格式视频转换为mp4格式
    
    Args:
        webm_file_path: webm文件路径
        
    Returns:
        转换后的mp4文件路径，如果转换失败则返回原始文件路径
    """
    if not webm_file_path.endswith('.webm'):
        return webm_file_path
        
    mp4_file_path = webm_file_path.replace('.webm', '.mp4')
    try:
        # 使用ffmpeg进行转换，设置较高质量的参数
        subprocess.run([
            'ffmpeg', 
            '-i', webm_file_path,  # 输入文件
            '-c:v', 'libx264',     # 视频编码器
            '-preset', 'slow',     # 编码预设，较慢但质量更好
            '-crf', '22',          # 恒定质量因子，值越小质量越高（18-28之间是较好的范围）
            '-c:a', 'aac',         # 音频编码器
            '-b:a', '128k',        # 音频比特率
            '-y',                  # 如果输出文件已存在，则覆盖
            mp4_file_path          # 输出文件
        ], check=True)
        
        # 检查转换是否成功
        if os.path.exists(mp4_file_path) and os.path.getsize(mp4_file_path) > 0:
            logging.info(f"成功将 {webm_file_path} 转换为 {mp4_file_path}")
            
            # 询问是否删除原始webm文件的功能将在UI层实现
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