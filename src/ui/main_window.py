from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, 
                              QStackedWidget, QPushButton, QVBoxLayout,
                              QStyle, QMessageBox, QApplication)
from PySide6.QtCore import Qt, Slot, QTimer
import logging
import os
import traceback

from src.ui.download_page import DownloadPage
from src.ui.settings_page import SettingsPage
from src.ui.history_page import HistoryPage
from src.ui.download_history_page import DownloadHistoryPage
from src.ui.styles import (get_application_style, get_navigation_button_style, 
                          get_active_navigation_button_style, get_dark_style,
                          get_dark_navigation_button_style, get_dark_active_navigation_button_style,
                          get_light_theme_style, get_light_theme_navigation_button_style,
                          get_light_theme_active_navigation_button_style,
                          get_chrome_dark_style, get_chrome_dark_navigation_button_style,
                          get_chrome_dark_active_navigation_button_style)
from src.threads import FetchInfoThread, DownloadThread, ConvertThread
from src.downloader import YtDownloader
from src.config import UI_MIN_WIDTH, UI_MIN_HEIGHT, APP_NAME, TEMP_DIR, DOWNLOADS_DIR
from src.config_manager import ConfigManager
from src.utils.video_utils import clean_old_files
from src.db.download_history import DownloadHistoryDB


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 自动清理过期临时文件
        self.clean_temp_files()
        
        # 初始化配置管理器
        self.config_manager = ConfigManager()
        
        # 初始化下载器
        self.downloader = YtDownloader(debug_callback=self.on_debug_message, always_use_cookies=True)
        
        # 初始化进度记录变量
        self.last_logged_percent = 0
        
        # 验证数据库并初始化
        self.initialize_database()
        
        self.setWindowTitle(APP_NAME)
        
        # 从配置读取主题设置
        self.theme = self.config_manager.get("UI", "Theme", fallback="Fusion")
        
        # 应用全局样式表
        self.apply_theme(self.theme)
        
        # 从配置读取窗口大小
        min_width = self.config_manager.getint("UI", "MinWidth", fallback=UI_MIN_WIDTH)
        min_height = self.config_manager.getint("UI", "MinHeight", fallback=UI_MIN_HEIGHT)
        self.setMinimumSize(min_width, min_height)
        
        self.setup_ui()
        
        # 程序启动时，加载上次保存的设置
        self.load_settings_from_config()
    
    def setup_ui(self):
        # 创建主部件
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)  # 水平布局
        main_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        
        # 创建左侧导航区域
        nav_widget = QWidget()
        nav_widget.setFixedWidth(150)  # 固定宽度
        nav_widget.setStyleSheet("border-right: 1px solid #e0e0e0;")  # 添加边框
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setSpacing(10)  # 按钮之间的间距
        nav_layout.setContentsMargins(10, 20, 10, 10)  # 边距
        
        # 创建QStackedWidget
        self.stacked_widget = QStackedWidget()
        
        # 创建四个页面
        self.download_page = DownloadPage()
        self.settings_page = SettingsPage(self.config_manager)
        self.history_page = HistoryPage()
        self.download_history_page = DownloadHistoryPage()
        
        # 连接下载页面的信号
        self.download_page.fetch_info_requested.connect(self.fetch_video_info)
        self.download_page.download_requested.connect(self.start_download)
        self.download_page.cancel_fetch_requested.connect(self.cancel_fetch_info)
        self.download_page.cancel_download_requested.connect(self.cancel_download)
        
        # 连接设置页面的信号
        self.settings_page.settings_saved.connect(self.on_settings_saved)
        
        # 连接历史页面的信号
        self.history_page.clear_log_requested.connect(self.clear_log)
        
        # 连接下载历史页面的信号
        self.download_history_page.delete_history_requested.connect(self.on_delete_history)
        self.download_history_page.clear_all_requested.connect(self.on_clear_all_history)
        self.download_history_page.redownload_requested.connect(self.on_redownload_requested)
        self.download_history_page.continue_download_requested.connect(self.on_continue_download_requested)
        
        # 将页面添加到堆叠部件
        self.stacked_widget.addWidget(self.download_page)  # 索引0 - 下载页面
        self.stacked_widget.addWidget(self.settings_page)  # 索引1 - 设置页面
        self.stacked_widget.addWidget(self.history_page)   # 索引2 - 日志页面
        self.stacked_widget.addWidget(self.download_history_page)  # 索引3 - 下载历史页面
        
        # 创建导航按钮
        self.download_nav_btn = QPushButton("下载视频")
        # 使用QStyle的标准图标
        self.download_nav_btn.setIcon(self.style().standardIcon(QStyle.SP_ArrowDown))
        
        self.settings_nav_btn = QPushButton("设置")
        # 使用QStyle的标准图标
        self.settings_nav_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        
        self.history_nav_btn = QPushButton("操作日志")
        # 使用QStyle的标准图标
        self.history_nav_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogInfoView))
        
        self.download_history_nav_btn = QPushButton("下载历史")
        # 使用QStyle的标准图标
        self.download_history_nav_btn.setIcon(self.style().standardIcon(QStyle.SP_DriveHDIcon))
        
        # 设置按钮样式
        nav_button_style = get_navigation_button_style()
        
        self.download_nav_btn.setStyleSheet(nav_button_style)
        self.settings_nav_btn.setStyleSheet(nav_button_style)
        self.history_nav_btn.setStyleSheet(nav_button_style)
        self.download_history_nav_btn.setStyleSheet(nav_button_style)
        
        # 连接导航按钮信号
        self.download_nav_btn.clicked.connect(lambda: self.switch_page(0))
        self.settings_nav_btn.clicked.connect(lambda: self.switch_page(1))
        self.history_nav_btn.clicked.connect(lambda: self.switch_page(2))
        self.download_history_nav_btn.clicked.connect(lambda: self.switch_page(3))
        
        # 添加按钮到导航布局
        nav_layout.addWidget(self.download_nav_btn)
        nav_layout.addWidget(self.settings_nav_btn)
        nav_layout.addWidget(self.history_nav_btn)
        nav_layout.addWidget(self.download_history_nav_btn)
        nav_layout.addStretch()  # 添加弹性空间，使按钮靠上排列
        
        # 将导航和堆叠部件添加到主布局
        main_layout.addWidget(nav_widget)
        main_layout.addWidget(self.stacked_widget)
        
        # 连接堆叠部件的currentChanged信号
        self.stacked_widget.currentChanged.connect(self.on_page_changed)
        
        # 设置主部件
        self.setCentralWidget(central_widget)
        
        # 总是从下载视频界面开始
        self.stacked_widget.setCurrentIndex(0)
        self.update_nav_button_style(0)
    
    def log_message(self, message, error=False, debug=False):
        """添加日志消息"""
        # 跳过包含特定模式的消息以避免重复记录
        skip_patterns = [
            "下载进度: 0%", 
            "尝试次数 #",
            "执行命令:"
        ]
        
        # 如果消息匹配跳过模式，则不记录
        if any(pattern in message for pattern in skip_patterns):
            return
        
        # 向历史页面添加消息
        self.history_page.add_log_message(message, error, debug)
    
    def clear_log(self):
        """清除日志内容"""
        # 历史页面会自己清理UI
        pass
    
    def fetch_video_info(self, url, use_cookies, browser):
        """获取视频信息"""
        if not url:
            QMessageBox.warning(self, "警告", "请输入有效的YouTube视频URL")
            return
        
        # 从配置中获取cookie设置
        use_cookies = self.config_manager.getboolean("Cookies", "UseCookies", fallback=False)
        browser = self.config_manager.get("Cookies", "Browser", fallback="chrome") if use_cookies else None
        
        # 记录日志
        self.log_message(f"开始获取视频信息: {url}")
        if use_cookies:
            self.log_message(f"使用{browser}浏览器的cookies")
        
        # 使用线程异步获取视频信息
        self.fetch_thread = FetchInfoThread(self.downloader, url, use_cookies, browser)
        self.fetch_thread.info_fetched.connect(self.on_info_fetched)
        self.fetch_thread.fetch_error.connect(self.on_fetch_error)
        self.fetch_thread.start()
    
    @Slot(dict)
    def on_info_fetched(self, video_info):
        """处理获取到的视频信息"""
        self.download_page.on_info_fetched(video_info)
        
        # 存储视频信息供下载使用
        self.current_video_info = video_info
        
        # 记录日志
        title = video_info.get('title', '未知标题')
        self.log_message(f"成功获取视频信息: {title}")
    
    @Slot(str)
    def on_fetch_error(self, error_message):
        """处理获取视频信息失败的情况"""
        self.download_page.on_fetch_error(error_message)
        
        # 记录日志
        self.log_message(f"获取视频信息失败: {error_message}", error=True)
        
        # 刷新下载历史列表
        self.refresh_download_history()
    
    def start_download(self, url, video_format, audio_format, subtitles, output_dir, threads, use_cookies, browser, resume=False):
        """开始下载视频"""
        if not url:
            QMessageBox.warning(self, "警告", "请输入有效的YouTube视频URL")
            return
        
        # 使用配置中的设置
        if not output_dir:
            output_dir = self.config_manager.get("General", "DownloadPath")
        
        if not output_dir:
            QMessageBox.warning(self, "警告", "请先在设置中设置下载路径")
            self.switch_page(1)  # 切换到设置页面
            return
        
        if threads <= 0:
            threads = self.config_manager.getint("General", "Threads", fallback=10)
        
        # 忽略传入的cookies参数，只使用配置中的设置
        use_cookies = self.config_manager.getboolean("Cookies", "UseCookies", fallback=False)
        browser = self.config_manager.get("Cookies", "Browser", fallback="chrome") if use_cookies else None
        
        download_thumbnail = self.config_manager.getboolean("General", "DownloadThumbnail", fallback=True)
        
        # 重置进度记录
        self.last_logged_percent = 0
        
        # 日志记录
        format_text = f"视频格式: {video_format if video_format else '无'}, 音频格式: {audio_format if audio_format else '无'}"
        subtitle_text = f"字幕: {','.join(subtitles) if subtitles else '无'}"
        if resume:
            self.log_message(f"继续下载 - {format_text}, {subtitle_text}")
        else:
            self.log_message(f"开始下载 - {format_text}, {subtitle_text}")
        if use_cookies:
            self.log_message(f"使用{browser}浏览器的cookies")
        
        # 获取视频信息
        video_info = getattr(self, 'current_video_info', None)
        
        # 创建下载线程
        self.download_thread = DownloadThread(
            self.downloader,
            url,
            video_format,
            audio_format,
            subtitles,
            download_thumbnail,
            output_dir,
            threads,
            use_cookies,
            browser,
            video_info,  # 传递视频信息
            resume  # 传递断点续传参数
        )
        
        self.download_thread.progress_updated.connect(self.update_download_progress)
        self.download_thread.download_finished.connect(self.download_complete)
        self.download_thread.start()
    
    @Slot()
    def cancel_download(self):
        """取消当前下载任务"""
        if hasattr(self, 'download_thread') and self.download_thread.isRunning():
            # 调用下载线程的取消方法
            self.download_thread.cancel()
            self.log_message("用户取消下载")
            # 重置进度记录
            self.last_logged_percent = 0
            
            # 延迟刷新下载历史列表，确保取消操作已完成
            QTimer.singleShot(500, self.refresh_download_history)
    
    def update_download_progress(self, percent, message):
        # 更新进度条
        self.download_page.update_progress(percent, message)
        
        # 记录关键进度信息，避免产生过多日志
        if percent % 10 == 0 or "下载完成" in message or "下载失败" in message or "合并" in message:
            self.log_message(f"下载进度: {percent}% - {message}")
    
    @Slot(bool, str)
    def download_complete(self, success, message):
        """下载完成处理"""
        # 连接下载线程的转换信号
        if hasattr(self, 'download_thread') and self.download_thread:
            # 断开旧的连接
            try:
                self.download_thread.convert_progress.disconnect()
            except:
                pass
            
            try:
                self.download_thread.convert_finished.disconnect()
            except:
                pass
            
            # 连接转换信号
            self.download_thread.convert_progress.connect(self.on_convert_progress_new)
            self.download_thread.convert_finished.connect(self.on_convert_finished)
        
        # 调用下载页面的下载完成处理
        self.download_page.download_complete(success, message)
        
        # 记录日志
        if success:
            self.log_message(f"下载完成: {message}")
        else:
            self.log_message(f"下载失败: {message}", error=True)
        
        # 重置进度记录
        self.last_logged_percent = 0
        
        # 刷新下载历史列表
        if hasattr(self, 'download_history_page'):
            self.download_history_page.load_download_history()
    
    @Slot(int, str)
    def on_convert_progress_new(self, percent, message):
        """处理转换进度更新（新版本，接收百分比和消息）"""
        try:
            # 确保百分比是有效的整数
            if not isinstance(percent, (int, float)):
                # 尝试从消息中提取百分比
                if "%" in message:
                    try:
                        percent_str = message.split("%")[0].strip().split(" ")[-1]
                        percent = int(float(percent_str))
                    except:
                        percent = 0
                else:
                    percent = 0
            
            # 确保百分比在有效范围内
            percent = max(0, min(100, int(percent)))
            
            # 将进度传递给下载页面
            if hasattr(self, 'download_page'):
                try:
                    self.download_page.on_convert_progress(percent, message)
                except Exception as e:
                    logging.error(f"向下载页面传递转换进度时出错: {str(e)}")
            
            # 记录重要进度到日志
            if percent % 10 == 0 and percent > self.last_logged_percent:
                self.log_message(f"转换进度: {percent}%")
                self.last_logged_percent = percent
            elif "初始化" in message or "开始" in message or "完成" in message or "错误" in message or "失败" in message:
                self.log_message(f"转换状态: {message}")
        except Exception as e:
            logging.error(f"处理转换进度时出错: {str(e)}")
            # 尝试传递原始消息
            if hasattr(self, 'download_page'):
                self.download_page.on_convert_progress(0, f"处理进度时出错: {message}")
    
    def on_convert_progress(self, message):
        """处理转换进度消息（旧版本，兼容性保留）"""
        # 将转换进度消息记录到历史记录界面
        if not message.startswith("正在转换"):  # 避免记录太多重复的百分比消息
            self.log_message(f"转换进度: {message}")
    
    def on_convert_percent(self, percent):
        """处理转换百分比更新（旧版本，兼容性保留）"""
        # 每10%记录一次进度到历史记录
        if percent > 0 and percent % 10 == 0 and percent > self.last_logged_percent:
            self.log_message(f"转换进度: {percent}%")
            self.last_logged_percent = percent
    
    def on_convert_finished(self, success, message, file_path):
        """处理转换完成"""
        if success:
            # 成功完成转换，记录MP4文件路径
            self.log_message(f"转换完成: {os.path.basename(file_path)}")
            self.log_message(f"MP4文件已保存: {file_path}")
        else:
            # 转换失败，标记为转换中断
            self.log_message(f"转换失败: {message}", error=True)
        
        # 确保信号断开操作在完全完成后执行
        try:
            # 使用QTimer延迟断开信号连接，避免线程间的冲突
            QTimer.singleShot(100, self.disconnect_convert_signals)
        except Exception as e:
            logging.error(f"断开信号时出错: {str(e)}")
        
        # 重置进度记录
        self.last_logged_percent = 0
        
        # 刷新下载历史列表
        if hasattr(self, 'download_history_page'):
            self.download_history_page.load_download_history()
    
    def disconnect_convert_signals(self):
        """安全断开转换相关的信号连接"""
        try:
            # 尝试断开下载线程的转换信号连接
            if hasattr(self, 'download_thread') and self.download_thread:
                try:
                    # 先检查是否有连接，然后再尝试断开特定的连接
                    if hasattr(self, 'on_convert_progress_new') and hasattr(self.download_thread, 'convert_progress'):
                        try:
                            # 先检查是否有连接信号
                            if self.download_thread.convert_progress.receivers(self.on_convert_progress_new) > 0:
                                self.download_thread.convert_progress.disconnect(self.on_convert_progress_new)
                        except Exception:
                            pass
                except Exception:
                    pass
                
                try:
                    if hasattr(self, 'on_convert_finished') and hasattr(self.download_thread, 'convert_finished'):
                        try:
                            if self.download_thread.convert_finished.receivers(self.on_convert_finished) > 0:
                                self.download_thread.convert_finished.disconnect(self.on_convert_finished)
                        except Exception:
                            pass
                except Exception:
                    pass
            
            # 兼容性代码：尝试断开下载页面中可能存在的转换线程的信号连接
            if hasattr(self, 'download_page') and hasattr(self.download_page, 'convert_thread'):
                convert_thread = self.download_page.convert_thread
                
                if convert_thread:
                    try:
                        if hasattr(self, 'on_convert_progress') and hasattr(convert_thread, 'convert_progress'):
                            if convert_thread.convert_progress.receivers(self.on_convert_progress) > 0:
                                convert_thread.convert_progress.disconnect(self.on_convert_progress)
                    except Exception:
                        pass
                    
                    try:
                        if hasattr(self, 'on_convert_percent') and hasattr(convert_thread, 'convert_percent'):
                            if convert_thread.convert_percent.receivers(self.on_convert_percent) > 0:
                                convert_thread.convert_percent.disconnect(self.on_convert_percent)
                    except Exception:
                        pass
                    
                    try:
                        if hasattr(self, 'on_convert_finished') and hasattr(convert_thread, 'convert_finished'):
                            if convert_thread.convert_finished.receivers(self.on_convert_finished) > 0:
                                convert_thread.convert_finished.disconnect(self.on_convert_finished)
                    except Exception:
                        pass
        except Exception as e:
            logging.error(f"断开转换相关信号时发生错误: {str(e)}")
    
    @Slot()
    def cancel_fetch_info(self):
        """取消获取视频信息"""
        if hasattr(self, 'fetch_thread') and self.fetch_thread.isRunning():
            # 记录日志
            self.log_message("用户取消获取视频信息")
            
            # 尝试终止下载器中的进程
            self.downloader.cancel_download()
            # 终止线程
            self.fetch_thread.terminate()
            self.fetch_thread.wait()
    
    def on_debug_message(self, message):
        """接收来自下载器的调试消息"""
        # 过滤掉一些不需要记录的日志信息
        # 常见的进度更新信息已经通过其他方式记录，这里不再重复
        skip_patterns = [
            "尝试次数",
            "使用浏览器的cookie",  # 已经在其他地方记录
            "开始获取视频信息",    # 已经在其他地方记录
            "开始下载",           # 已经在其他地方记录
            "格式：",             # 已经在其他地方记录
            "输出目录",           # 已经在其他地方记录
            "[download]",        # 下载进度信息已经通过progress_callback处理
            "ETA",               # 剩余时间信息已经通过progress_callback处理
            "Destination",       # 目标文件信息不需要记录
            "发现下载目标路径",    # 不再重复记录路径信息
            "捕获到视频ID",       # 内部处理消息，不需要记录
            "捕获到视频标题",      # 内部处理消息，不需要记录
            "捕获到合并输出路径",   # 内部处理消息，不需要记录
            "执行命令"            # 不再重复记录命令信息
        ]
        
        # 如果消息为空，不记录
        if not message.strip():
            return
        
        # 如果消息包含任何需要跳过的模式，则不记录
        for pattern in skip_patterns:
            if pattern in message:
                return
                
        # 记录其他调试信息
        self.log_message(f"调试: {message}", debug=True)
    
    def switch_page(self, index):
        """切换页面并更新导航按钮样式"""
        self.stacked_widget.setCurrentIndex(index)
    
    def on_page_changed(self, index):
        """响应页面变化，更新导航按钮样式"""
        self.update_nav_button_style(index)
    
    def update_nav_button_style(self, index):
        """更新导航按钮样式"""
        # 根据主题选择样式
        if self.theme == "Dark":
            nav_button_style = get_dark_navigation_button_style()
            active_nav_button_style = get_dark_active_navigation_button_style()
        elif self.theme == "ChromeDark":
            nav_button_style = get_chrome_dark_navigation_button_style()
            active_nav_button_style = get_chrome_dark_active_navigation_button_style()
        elif self.theme == "LightBlue":
            nav_button_style = get_light_theme_navigation_button_style()
            active_nav_button_style = get_light_theme_active_navigation_button_style()
        else:
            nav_button_style = get_navigation_button_style()
            active_nav_button_style = get_active_navigation_button_style()
        
        # 重置所有按钮样式
        self.download_nav_btn.setStyleSheet(nav_button_style)
        self.settings_nav_btn.setStyleSheet(nav_button_style)
        self.history_nav_btn.setStyleSheet(nav_button_style)
        self.download_history_nav_btn.setStyleSheet(nav_button_style)
        
        # 设置当前活跃页对应的按钮样式
        if index == 0:
            self.download_nav_btn.setStyleSheet(active_nav_button_style)
        elif index == 1:
            self.settings_nav_btn.setStyleSheet(active_nav_button_style)
        elif index == 2:
            self.history_nav_btn.setStyleSheet(active_nav_button_style)
        elif index == 3:
            self.download_history_nav_btn.setStyleSheet(active_nav_button_style)
    
    @Slot(dict)
    def on_settings_saved(self, settings):
        """处理设置保存事件"""
        # 如果主题已更改，则应用新主题
        if 'theme' in settings and settings['theme'] != self.theme:
            self.apply_theme(settings['theme'])
        
        # 记录日志
        self.log_message("设置已保存")
        
        # 切换回下载页面
        self.switch_page(0)
    
    def load_settings_from_config(self):
        """从配置文件加载设置"""
        # 应用界面主题
        theme = self.config_manager.get("UI", "Theme", fallback="Fusion")
        if theme != self.theme:
            self.apply_theme(theme)
            
        # 如果设置页面已初始化，则加载设置
        if hasattr(self, 'settings_page') and self.settings_page:
            self.settings_page.load_settings_from_config()
    
    def apply_theme(self, theme):
        """应用主题样式"""
        self.theme = theme
        
        if theme == "Dark":
            self.setStyleSheet(get_dark_style())
        elif theme == "ChromeDark":
            self.setStyleSheet(get_chrome_dark_style())
        elif theme == "LightBlue":
            self.setStyleSheet(get_light_theme_style())
        else:  # 默认为Fusion主题
            self.setStyleSheet(get_application_style())
        
        # 如果界面已经初始化，更新导航按钮样式
        if hasattr(self, 'stacked_widget'):
            self.update_nav_button_style(self.stacked_widget.currentIndex()) 
    
    def clean_temp_files(self):
        """清理过期的临时文件"""
        try:
            # 清理临时目录中超过3天的webm和part文件
            temp_deleted = clean_old_files(TEMP_DIR, days=3, extensions=['.webm', '.part', '.temp'])
            
            # 清理下载目录中超过30天的webm文件
            downloads_deleted = clean_old_files(DOWNLOADS_DIR, days=30, extensions=['.webm'])
            
            # 只记录一次总结日志
            total_deleted = temp_deleted + downloads_deleted
            if total_deleted > 0:
                logging.info(f"自动清理完成: 临时目录删除了{temp_deleted}个文件，下载目录删除了{downloads_deleted}个过期WebM文件")
        except Exception as e:
            logging.error(f"自动清理临时文件失败: {e}")
    
    # 下载历史记录页面相关方法
    def on_delete_history(self, record_id):
        """处理删除历史记录请求"""
        # 这个方法只是接收信号，实际删除工作在下载历史页面内完成
        pass
    
    def on_clear_all_history(self):
        """处理清空所有历史记录请求"""
        # 这个方法只是接收信号，实际清空工作在下载历史页面内完成
        pass

    @Slot(dict)
    def on_redownload_requested(self, record):
        """处理重新下载请求"""
        # 记录日志
        self.log_message(f"从历史记录重新下载: {record['title']}")
        
        # 切换到下载页面
        self.switch_page(0)
        
        # 设置URL并获取视频信息
        self.download_page.url_input.setText(record['url'])
        
        # 设置预设格式
        self.download_page.set_preset_formats(
            video_format=record['video_format'],
            audio_format=record['audio_format'],
            subtitles=record['subtitles'].split(',') if record['subtitles'] else []
        )
        
        # 如果有视频ID，直接填充已有信息
        if record['video_id'] and record['title']:
            # 触发获取视频信息
            self.fetch_video_info(record['url'], False, None)
        else:
            # 没有足够信息，重新获取
            self.fetch_video_info(record['url'], False, None)
    
    @Slot(dict)
    def on_continue_download_requested(self, record):
        """处理继续下载请求"""
        # 记录日志
        self.log_message(f"继续下载: {record['title']}")
        
        # 切换到下载页面
        self.switch_page(0)
        
        # 设置URL并获取视频信息
        self.download_page.url_input.setText(record['url'])
        
        # 提取记录中的输出路径
        output_path = record.get('output_path')
        if output_path:
            self.log_message(f"将继续下载到: {output_path}")
        
        # 设置预设格式
        self.download_page.set_preset_formats(
            video_format=record['video_format'],
            audio_format=record['audio_format'],
            subtitles=record['subtitles'].split(',') if record['subtitles'] else []
        )
        
        # 触发获取视频信息的流程
        self.fetch_video_info(record['url'], False, None)

    def refresh_download_history(self):
        """刷新下载历史列表"""
        try:
            logging.debug("开始刷新下载历史列表")
            
            if hasattr(self, 'download_history_page'):
                # 使用QTimer延迟执行，确保UI事件循环有机会处理其他事件
                QTimer.singleShot(100, self._refresh_history_table)
            else:
                logging.warning("下载历史页面未初始化，无法刷新列表")
        except Exception as e:
            logging.error(f"刷新下载历史列表时出错: {str(e)}")
            
    def _refresh_history_table(self):
        """实际执行历史记录刷新的方法"""
        try:
            # 调用下载历史页面的加载方法
            self.download_history_page.load_download_history()
            logging.debug("下载历史列表刷新完成")
        except Exception as e:
            logging.error(f"刷新下载历史表时出错: {str(e)}")
            logging.error(traceback.format_exc())

    def initialize_database(self):
        """初始化并验证下载历史数据库"""
        try:
            # 初始化数据库
            from src.db.download_history import DownloadHistoryDB
            db = DownloadHistoryDB()
            
            # 验证数据库状态
            result = db.validate_database()
            logging.info(f"数据库验证结果: {result}")
            
            # 如果数据库存在但没有记录，可以添加一些测试数据
            if result["exists"] and result["tables_exist"] and result["record_count"] == 0:
                logging.info("数据库表存在但无记录，尝试添加测试数据")
                db.add_test_data(count=3)
            
        except Exception as e:
            logging.error(f"初始化数据库时出错: {str(e)}")
            logging.error(traceback.format_exc())