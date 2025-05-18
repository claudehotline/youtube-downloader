"""
YouTube 视频下载器主入口
运行此文件启动应用程序
"""
import sys
import os

# 添加src目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 导入主模块
from src.main import main

# 验证yt-dlp.exe是否可用并支持--cookies-from-browser参数
def validate_ytdlp():
    cmd_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cmd")
    ytdlp_path = os.path.join(cmd_dir, "yt-dlp.exe")
    
    if not os.path.exists(ytdlp_path):
        print(f"警告: yt-dlp.exe文件未找到。请确保{ytdlp_path}存在。")
        # 不中断程序，因为打包后路径可能会变
    
    # 验证是否支持cookies参数也可以在这里添加
    # 但我们已经在代码中添加了always_use_cookies=True参数

# 运行验证
validate_ytdlp()

# 启动主程序
if __name__ == "__main__":
    main() 