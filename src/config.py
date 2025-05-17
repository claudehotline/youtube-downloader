import os

# 应用程序信息
APP_NAME = "YouTube 视频下载器"
APP_VERSION = "1.0.0"

# UI 设置
UI_THEME = "Fusion"  # fusion, windowsvista, windows
UI_MIN_WIDTH = 1000
UI_MIN_HEIGHT = 720

# 网络设置
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
NETWORK_WAIT = 2

# 路径设置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CMD_DIR = os.path.join(BASE_DIR, "cmd")
YTDLP_PATH = os.path.join(CMD_DIR, "yt-dlp.exe")

# 添加临时目录和下载目录路径
TEMP_DIR = os.path.join(BASE_DIR, "temp")
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")

# 确保目录存在
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# 其他设置
DEFAULT_TIMEOUT = 60  # 请求超时时间（秒）
MAX_RETRIES = 5       # 最大重试次数
NETWORK_WAIT = 10     # 网络等待时间（秒） 