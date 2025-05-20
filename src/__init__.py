import logging
import sys
import os
import subprocess
import logging.handlers

# 处理无控制台模式下sys.stdout和sys.stderr可能为None的情况
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding='utf-8')
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding='utf-8')

# 设置日志格式 - 移除basicConfig，让main.py中的配置生效
# 由于Python日志系统的设计，第一个basicConfig会生效，后续的会被忽略
# 所以我们在这里只设置一些基本变量，不调用basicConfig

# 检查ffmpeg是否已安装
def check_ffmpeg():
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True, 
                               encoding='utf-8',
                               errors='replace',
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        if result.returncode == 0:
            logging.info(f"FFmpeg已安装: {result.stdout.splitlines()[0]}")
            return True
        else:
            logging.warning("FFmpeg未正确安装或不在PATH中")
            return False
    except Exception as e:
        logging.warning(f"检查FFmpeg安装失败: {e}")
        return False

# 检查ffmpeg-python库是否已安装
def check_ffmpeg_python():
    try:
        import ffmpeg
        logging.info(f"ffmpeg-python已安装")
        return True
    except ImportError:
        logging.warning("ffmpeg-python未安装，尝试安装...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'ffmpeg-python'],
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            logging.info("ffmpeg-python安装成功")
            return True
        except Exception as e:
            logging.error(f"ffmpeg-python安装失败: {e}")
            return False

# 应用启动时进行检查
check_ffmpeg()
check_ffmpeg_python() 