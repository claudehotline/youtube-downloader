import os
import sys
import logging
from datetime import datetime
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

# 设置默认编码为UTF-8，解决中文Windows系统的编码问题
if hasattr(sys, 'setdefaultencoding'):
    sys.setdefaultencoding('utf-8')

# 设置环境变量，确保子进程使用UTF-8编码
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 添加全局STARTUPINFO配置，用于隐藏Windows上的子进程窗口
if os.name == 'nt':
    import subprocess
    # 设置全局STARTUPINFO对象，所有子进程都会隐藏窗口
    STARTUPINFO = subprocess.STARTUPINFO()
    STARTUPINFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    STARTUPINFO.wShowWindow = 0  # SW_HIDE
    
    # 替换subprocess.Popen原始方法
    original_popen = subprocess.Popen
    def _custom_popen(*args, **kwargs):
        # 如果在Windows上，自动添加startupinfo
        if os.name == 'nt' and 'startupinfo' not in kwargs:
            kwargs['startupinfo'] = STARTUPINFO
        # 强制设置UTF-8编码，避免GBK编码错误
        if 'encoding' not in kwargs:
            kwargs['encoding'] = 'utf-8'
        if 'errors' not in kwargs:
            kwargs['errors'] = 'replace'  # 无法编码的字符将被替换而不是抛出错误
        return original_popen(*args, **kwargs)
    # 替换默认的Popen方法
    subprocess.Popen = _custom_popen
    
    # 替换subprocess.run方法
    original_run = subprocess.run
    def _custom_run(*args, **kwargs):
        # 如果在Windows上，自动添加startupinfo
        if os.name == 'nt' and 'startupinfo' not in kwargs:
            kwargs['startupinfo'] = STARTUPINFO
        # 强制设置UTF-8编码，避免GBK编码错误
        if 'encoding' not in kwargs:
            kwargs['encoding'] = 'utf-8'
        if 'errors' not in kwargs:
            kwargs['errors'] = 'replace'  # 无法编码的字符将被替换而不是抛出错误
        return original_run(*args, **kwargs)
    # 替换默认的run方法
    subprocess.run = _custom_run
    
    # 替换subprocess.call方法
    original_call = subprocess.call
    def _custom_call(*args, **kwargs):
        # 如果在Windows上，自动添加startupinfo
        if os.name == 'nt' and 'startupinfo' not in kwargs:
            kwargs['startupinfo'] = STARTUPINFO
        # 强制设置UTF-8编码，避免GBK编码错误
        if 'encoding' not in kwargs:
            kwargs['encoding'] = 'utf-8'
        if 'errors' not in kwargs:
            kwargs['errors'] = 'replace'  # 无法编码的字符将被替换而不是抛出错误
        return original_call(*args, **kwargs)
    # 替换默认的call方法
    subprocess.call = _custom_call

# 添加src目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# 导入其他模块
from src.ui.main_window import MainWindow
from src.config import APP_NAME, UI_THEME, YTDLP_PATH
from src.config_manager import ConfigManager

def configure_logging():
    """配置日志系统"""
    # 创建logs目录
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except Exception:
            log_dir = os.path.dirname(os.path.dirname(__file__))
    
    # 生成日志文件名，包含日期
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"yt-dlp-{today}.log")
    
    # 配置根日志记录器
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logging.info("日志系统初始化完成")

def main():
    # 配置日志
    configure_logging()
    
    # 检查ffmpeg是否已安装
    try:
        import ffmpeg
        logging.info("ffmpeg-python已安装")
    except ImportError:
        logging.error("ffmpeg-python未安装，某些功能可能不可用")
    
    # 初始化配置管理器
    config_manager = ConfigManager()
    
    # 检查是否存在yt-dlp.exe
    if not os.path.exists(YTDLP_PATH):
        print(f"错误: 找不到yt-dlp.exe文件，请确保它在程序同一目录下。")
        sys.exit(1)
    
    # 创建下载目录如果不存在
    download_path = config_manager.get("General", "DownloadPath")
    if download_path and not os.path.exists(download_path):
        os.makedirs(download_path)
    
    # 创建QApplication实例
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    
    # 从配置中读取主题
    theme = config_manager.get("UI", "Theme", fallback=UI_THEME)
    app.setStyle(theme)  # 使用配置中的风格
    
    # 设置应用图标（如果有的话）
    # app.setWindowIcon(QIcon("icon.png"))
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    # 运行应用程序事件循环
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 