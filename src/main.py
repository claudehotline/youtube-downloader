import os
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

# 添加src目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# 导入其他模块
from src.ui.main_window import MainWindow
from src.config import APP_NAME, UI_THEME, YTDLP_PATH
from src.config_manager import ConfigManager

def main():
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