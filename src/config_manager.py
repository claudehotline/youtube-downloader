import os
import configparser
from pathlib import Path

class ConfigManager:
    def __init__(self, config_file="config.ini"):
        # 配置文件路径
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), config_file)
        self.config = configparser.ConfigParser()
        
        # 默认配置
        self.default_config = {
            "General": {
                "DownloadPath": os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "downloads"),
                "Threads": "10",
                "DefaultVideoFormat": "",
                "DefaultAudioFormat": "",
                "DownloadThumbnail": "True"  # 默认下载封面图片
            },
            "Cookies": {
                "UseCookies": "False",
                "Browser": "chrome"
            },
            "UI": {
                "Theme": "Fusion",
                "MinWidth": "800",
                "MinHeight": "600"
            }
        }
        
        # 加载配置，如果不存在则创建默认配置
        self.load_config()
    
    def load_config(self):
        """加载配置文件，如果不存在则创建默认配置"""
        if os.path.exists(self.config_path):
            try:
                self.config.read(self.config_path, encoding='utf-8')
                return True
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                self.create_default_config()
                return False
        else:
            self.create_default_config()
            return True
    
    def create_default_config(self):
        """创建默认配置文件"""
        for section, options in self.default_config.items():
            if not self.config.has_section(section):
                self.config.add_section(section)
            
            for option, value in options.items():
                self.config.set(section, option, value)
        
        self.save_config()
    
    def save_config(self):
        """保存配置到文件"""
        try:
            # 确保下载目录存在
            download_dir = self.get("General", "DownloadPath")
            if download_dir:
                Path(download_dir).mkdir(parents=True, exist_ok=True)
            
            # 保存配置
            with open(self.config_path, 'w', encoding='utf-8') as configfile:
                self.config.write(configfile)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def get(self, section, option, fallback=None):
        """获取配置项"""
        return self.config.get(section, option, fallback=fallback)
    
    def getint(self, section, option, fallback=0):
        """获取整数配置项"""
        return self.config.getint(section, option, fallback=fallback)
    
    def getboolean(self, section, option, fallback=False):
        """获取布尔配置项"""
        return self.config.getboolean(section, option, fallback=fallback)
    
    def set(self, section, option, value):
        """设置配置项"""
        if not self.config.has_section(section):
            self.config.add_section(section)
        
        self.config.set(section, option, str(value))
        return self.save_config() 