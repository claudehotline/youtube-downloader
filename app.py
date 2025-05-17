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

if __name__ == "__main__":
    main() 