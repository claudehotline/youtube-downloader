from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                         QLabel, QPushButton, QTableWidget, QTableWidgetItem,
                         QHeaderView, QAbstractItemView, QMenu, QMessageBox,
                         QLineEdit, QToolBar, QComboBox, QSizePolicy, QSpacerItem,
                         QDialog, QDialogButtonBox, QTextEdit, QStyle, QProgressBar)
from PySide6.QtCore import Qt, Signal, QSize, QDateTime, QEvent, QTimer, QItemSelectionModel
from PySide6.QtGui import QIcon, QAction
import os
import datetime
import locale
from src.db.download_history import DownloadHistoryDB
from src.ui.convert_dialog import ConvertDialog
from src.utils.video_utils import convert_video
import glob


class DownloadHistoryPage(QWidget):
    delete_history_requested = Signal(int)  # 单个记录ID
    clear_all_requested = Signal()
    redownload_requested = Signal(dict)  # 发送下载记录信息
    continue_download_requested = Signal(dict)  # 发送下载记录信息
    continue_conversion_requested = Signal(dict)  # 保留此信号定义，以防未来需要
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DownloadHistoryDB()
        self.setup_ui()
        self.load_download_history()
        
        # 监听窗口大小变化事件
        self.installEventFilter(self)
        
        # 添加自动刷新定时器
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.load_download_history)
        self.refresh_timer.start(10000)  # 每10秒刷新一次
    
    def eventFilter(self, obj, event):
        """事件过滤器，处理窗口大小变化"""
        if obj == self and event.type() == QEvent.Type.Resize:
            # 确保表格已初始化
            if hasattr(self, 'history_table') and self.history_table.width() > 0:
                self.adjust_column_widths()
        return super().eventFilter(obj, event)
    
    def adjust_column_widths(self):
        """根据窗口大小调整列宽比例"""
        total_width = self.history_table.width() - 20  # 减去滚动条宽度
        
        # 设置每列的宽度比例 (跳过ID列 - 索引0，因为它是隐藏的)
        self.history_table.setColumnWidth(1, int(total_width * 0.25))  # 标题列
        self.history_table.setColumnWidth(2, int(total_width * 0.12))  # 格式列
        self.history_table.setColumnWidth(3, int(total_width * 0.25))  # 路径列
        self.history_table.setColumnWidth(4, int(total_width * 0.08))  # 大小列
        self.history_table.setColumnWidth(5, int(total_width * 0.12))  # 时间列
        self.history_table.setColumnWidth(6, int(total_width * 0.08))  # 耗时列
        # 最后一列(状态)不需要设置，会自动伸展
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 页面标题
        title_label = QLabel("下载历史记录")
        title_label.setObjectName("pageTitle")
        layout.addWidget(title_label)
        
        # 工具栏 - 包含搜索和过滤器
        toolbar = QHBoxLayout()
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索视频标题或URL...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.on_search_changed)
        
        # 状态过滤下拉框
        status_filter_label = QLabel("状态:")
        self.status_filter = QComboBox()
        self.status_filter.addItem("全部", "all")
        self.status_filter.addItem("完成", "完成")
        self.status_filter.addItem("进行中", "进行中")
        self.status_filter.addItem("失败", "失败")
        self.status_filter.addItem("已取消", "已取消")
        self.status_filter.addItem("转换中断", "转换中断")
        self.status_filter.currentIndexChanged.connect(self.on_filter_changed)
        
        # 刷新按钮
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.refresh_btn.clicked.connect(self.load_download_history)
        
        # 清空历史按钮
        self.clear_btn = QPushButton("清空历史")
        self.clear_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogDiscardButton))
        self.clear_btn.clicked.connect(self.on_clear_all_clicked)
        
        # 添加到工具栏
        toolbar.addWidget(self.search_input, 3)
        toolbar.addWidget(status_filter_label)
        toolbar.addWidget(self.status_filter, 1)
        toolbar.addWidget(self.refresh_btn)
        toolbar.addWidget(self.clear_btn)
        
        layout.addLayout(toolbar)
        
        # 下载历史表格
        self.history_table = QTableWidget()
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.history_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.history_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.history_table.customContextMenuRequested.connect(self.show_context_menu)
        
        # 设置列（包含隐藏的ID列）
        self.history_table.setColumnCount(8)
        self.history_table.setHorizontalHeaderLabels([
            "ID", "视频标题", "格式", "输出路径", "大小", "下载时间", "耗时", "状态"
        ])
        
        # 隐藏ID列
        self.history_table.hideColumn(0)
        
        # 设置列宽
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)  # 默认所有列都可拖拽调整宽度
        header.setStretchLastSection(True)  # 最后一列拉伸填充
        
        # 连接双击事件
        self.history_table.doubleClicked.connect(self.on_row_double_clicked)
        
        layout.addWidget(self.history_table)
        
        # 状态栏 - 显示统计信息
        status_bar = QHBoxLayout()
        self.status_label = QLabel("无下载记录")
        status_bar.addWidget(self.status_label)
        
        layout.addLayout(status_bar)
        
        # 窗口显示后设置初始列宽
        QTimer.singleShot(100, self.adjust_column_widths)
    
    def load_download_history(self):
        """从数据库加载下载历史记录"""
        # 保存当前滚动位置
        current_scroll_position = self.history_table.verticalScrollBar().value() if self.history_table.rowCount() > 0 else 0
        
        # 保存当前选中的行ID
        selected_ids = []
        for index in self.history_table.selectionModel().selectedRows():
            row = index.row()
            item = self.history_table.item(row, 1)  # 现在标题是第2列 (索引1)
            if item:
                selected_ids.append(item.data(Qt.ItemDataRole.UserRole))
        
        # 清空表格
        self.history_table.setRowCount(0)
        
        # 获取当前过滤器
        status_filter = self.status_filter.currentData()
        search_text = self.search_input.text().strip()
        
        # 根据过滤条件获取数据
        if search_text:
            # 搜索模式
            records = self.db.search_downloads(search_text)
        else:
            # 普通列表模式
            records = self.db.get_all_downloads()
        
        # 应用状态过滤
        if status_filter != "all":
            records = [r for r in records if r['status'] == status_filter]
        
        # 填充表格
        self.history_table.setRowCount(len(records))
        
        # 记录新行与ID的映射
        row_id_map = {}
        
        for i, record in enumerate(records):
            # 数据库记录ID（隐藏列）
            id_item = QTableWidgetItem(str(record['id']))
            self.history_table.setItem(i, 0, id_item)
            
            # 视频标题
            title_item = QTableWidgetItem(record['title'])
            title_item.setData(Qt.ItemDataRole.UserRole, record['id'])  # 存储记录ID
            self.history_table.setItem(i, 1, title_item)
            
            # 记录行号与ID的映射
            row_id_map[record['id']] = i
            
            # 格式
            format_str = ""
            if record['video_format']:
                format_str += f"视频:{record['video_format']}"
            if record['audio_format']:
                if format_str:
                    format_str += " + "
                format_str += f"音频:{record['audio_format']}"
            self.history_table.setItem(i, 2, QTableWidgetItem(format_str))
            
            # 输出路径
            path_item = QTableWidgetItem(record['output_path'] if record['output_path'] else "")
            self.history_table.setItem(i, 3, path_item)
            
            # 检查是否有翻译后的字幕
            if record.get('subtitle_path') and os.path.exists(record.get('subtitle_path')):
                path_item.setToolTip(f"字幕文件: {record.get('subtitle_path')}")
            
            # 文件大小
            file_size = record['file_size'] or 0
            size_str = self.format_size(file_size) if file_size > 0 else "未知"
            self.history_table.setItem(i, 4, QTableWidgetItem(size_str))
            
            # 下载时间
            start_time = record['start_time']
            if start_time:
                dt = datetime.datetime.fromtimestamp(start_time)
                time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                time_str = "未知"
            self.history_table.setItem(i, 5, QTableWidgetItem(time_str))
            
            # 耗时
            duration = record['duration']
            if duration and duration > 0:
                duration_str = self.format_duration(duration)
            else:
                if record['status'] == '进行中':
                    duration_str = "进行中..."
                elif record['status'] == '已取消':
                    duration_str = "--"
                elif record['status'] == '转换中断':
                    duration_str = "中断"
                else:
                    duration_str = "未知"
            self.history_table.setItem(i, 6, QTableWidgetItem(duration_str))
            
            # 状态
            status = record['status']
            status_item = QTableWidgetItem(status)
            if status == '完成':
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            elif status == '失败':
                status_item.setForeground(Qt.GlobalColor.red)
            elif status == '已取消':
                status_item.setForeground(Qt.GlobalColor.darkGray)
            elif status == '转换中断':
                status_item.setForeground(Qt.GlobalColor.darkYellow)
            else:
                status_item.setForeground(Qt.GlobalColor.blue)
            self.history_table.setItem(i, 7, QTableWidgetItem(status_item))
        
        # 恢复选中项
        if selected_ids:
            selection_model = self.history_table.selectionModel()
            for record_id in selected_ids:
                if record_id in row_id_map:
                    row = row_id_map[record_id]
                    index = self.history_table.model().index(row, 1)  # 现在标题是第2列 (索引1)
                    selection_model.select(index, QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
        
        # 恢复滚动位置
        self.history_table.verticalScrollBar().setValue(current_scroll_position)
        
        # 更新统计信息
        self.update_status_bar()
    
    def update_status_bar(self):
        """更新状态栏信息"""
        stats = self.db.get_download_stats()
        
        status_text = (f"总计: {stats['total']} | "
                      f"成功: {stats['completed']} | "
                      f"失败: {stats['failed']} | "
                      f"已取消: {stats['cancelled']} | "
                      f"转换中断: {stats['conversion_interrupted']} | "
                      f"总大小: {self.format_size(stats['total_size'])}")
        
        self.status_label.setText(status_text)
    
    def on_search_changed(self):
        """搜索框文本变化事件"""
        self.load_download_history()
    
    def on_filter_changed(self):        
        """状态过滤器变化事件"""        
        self.load_download_history()        
        
    def on_clear_all_clicked(self):        
        """清空全部历史点击事件"""        
        reply = QMessageBox.question(self, "确认清空", "确定要清空所有下载历史记录吗？此操作不可恢复。", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)                
        if reply == QMessageBox.StandardButton.Yes:            
            count = self.db.delete_all_downloads()            
            QMessageBox.information(self, "清空完成", f"已成功清空 {count} 条下载记录。")            
            self.load_download_history()            
            self.clear_all_requested.emit()        
            
    def on_row_double_clicked(self, index):        
        """表格行双击事件"""        
        row = index.row()        
        # 直接从ID列获取记录ID (索引0)        
        record_id = int(self.history_table.item(row, 0).text())        
        record = self.db.get_download_by_id(record_id)                
        if record:            
            self.show_record_details(record)
    
    def show_context_menu(self, position):
        """显示右键菜单"""
        menu = QMenu(self)
        
        # 获取选中的行
        selected_rows = self.history_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        # 获取选中行的记录        
        row = selected_rows[0].row()        
        # 直接从ID列获取记录ID       
        record_id = int(self.history_table.item(row, 0).text())        
        record = self.db.get_download_by_id(record_id)
        if not record:
            return
        
        # 创建菜单动作
        view_action = QAction("查看详情", self)
        open_folder_action = QAction("打开所在文件夹", self)
        delete_action = QAction("删除记录", self)
        
        # 根据状态添加重新下载或继续下载选项
        if record['status'] == '完成':
            redownload_action = QAction("重新下载", self)
            redownload_action.triggered.connect(lambda: self.on_redownload_triggered(record))
            menu.addAction(redownload_action)
            
            # 如果是已完成状态且输出路径是.webm文件，添加"转换为MP4"选项
            if record['output_path'] and record['output_path'].endswith('.webm') and os.path.exists(record['output_path']):
                convert_action = QAction("转换为MP4", self)
                convert_action.triggered.connect(lambda: self.on_continue_conversion_triggered(record))
                menu.addAction(convert_action)
                
            # 添加字幕翻译选项
            if record['subtitles']:  # 如果有下载字幕
                translate_action = QAction("翻译字幕", self)
                translate_action.triggered.connect(lambda: self.on_translate_subtitle_triggered(record))
                menu.addAction(translate_action)
            else:
                # 即使没有记录字幕，也尝试在视频目录查找字幕文件
                if record['output_path'] and os.path.exists(record['output_path']):
                    video_dir = os.path.dirname(record['output_path'])
                    video_name = os.path.splitext(os.path.basename(record['output_path']))[0]
                    subtitle_files = []
                    for ext in ['.srt', '.vtt', '.ass']:
                        pattern = os.path.join(video_dir, f"{video_name}*{ext}")
                        subtitle_files.extend(glob.glob(pattern))
                    
                    if subtitle_files:
                        translate_action = QAction("翻译字幕", self)
                        translate_action.triggered.connect(lambda: self.on_translate_subtitle_triggered(record))
                        menu.addAction(translate_action)
        elif record['status'] in ['失败', '已取消']:
            continue_action = QAction("继续下载", self)
            continue_action.triggered.connect(lambda: self.on_continue_download_triggered(record))
            menu.addAction(continue_action)
        elif record['status'] == '转换中断':
            # 对于转换中断的记录，添加"重新下载"和"转换为MP4"选项
            redownload_action = QAction("重新下载", self)
            redownload_action.triggered.connect(lambda: self.on_redownload_triggered(record))
            menu.addAction(redownload_action)
            
            # 添加"转换为MP4"选项，不再检查文件路径是否存在
            convert_action = QAction("转换为MP4", self)
            convert_action.triggered.connect(lambda: self.on_continue_conversion_triggered(record))
            menu.addAction(convert_action)
        
        # 添加动作到菜单
        menu.addAction(view_action)
        menu.addAction(open_folder_action)
        menu.addSeparator()
        menu.addAction(delete_action)
        
        # 连接信号
        view_action.triggered.connect(self.on_view_action_triggered)
        open_folder_action.triggered.connect(self.on_open_folder_triggered)
        delete_action.triggered.connect(self.on_delete_action_triggered)
        
        # 显示菜单
        menu.exec(self.history_table.viewport().mapToGlobal(position))
    
    def on_view_action_triggered(self):
        """查看详情动作"""
        selected_rows = self.history_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        # 获取第一个选中行的记录ID        
        row = selected_rows[0].row()        
        # 直接从ID列获取记录ID        
        record_id = int(self.history_table.item(row, 0).text())        
        record = self.db.get_download_by_id(record_id)
        
        if record:
            self.show_record_details(record)
    
    def on_open_folder_triggered(self):
        """打开所在文件夹动作"""
        selected_rows = self.history_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        # 获取第一个选中行的输出路径        
        row = selected_rows[0].row()        
        # 直接从ID列获取记录ID        
        record_id = int(self.history_table.item(row, 0).text())        
        record = self.db.get_download_by_id(record_id)
        
        if record and record['output_path'] and os.path.exists(os.path.dirname(record['output_path'])):
            folder_path = os.path.dirname(record['output_path'])
            os.startfile(folder_path)
        else:
            QMessageBox.warning(self, "无法打开文件夹", "文件夹不存在或路径无效")
    
    def on_delete_action_triggered(self):
        """删除记录动作"""
        selected_rows = self.history_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        # 确认删除
        count = len(selected_rows)
        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除选定的 {count} 条记录吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 执行删除            
            for index in selected_rows:                
                row = index.row()                
                # 直接从ID列获取记录ID                
                record_id = int(self.history_table.item(row, 0).text())                
                self.db.delete_download(record_id)                
                self.delete_history_requested.emit(record_id)
            
            # 重新加载列表
            self.load_download_history()
    
    def show_record_details(self, record):
        """显示记录详情对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("下载记录详情")
        dialog.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(dialog)
        
        # 创建详情文本
        details = QTextEdit()
        details.setReadOnly(True)
        
        # 格式化详情文本
        html = f"""
        <h2>{record['title']}</h2>
        <p><b>视频ID:</b> {record['video_id'] or '未知'}</p>
        <p><b>URL:</b> <a href="{record['url']}">{record['url']}</a></p>
        <p><b>状态:</b> {record['status']}</p>
        """
        
        if record['video_format'] or record['audio_format']:
            html += "<p><b>下载格式:</b> "
            if record['video_format']:
                html += f"视频: {record['video_format']} "
            if record['audio_format']:
                html += f"音频: {record['audio_format']}"
            html += "</p>"
        
        if record['subtitles']:
            html += f"<p><b>字幕:</b> {record['subtitles']}</p>"
            
        if record.get('subtitle_path') and os.path.exists(record.get('subtitle_path')):
            html += f"<p><b>字幕文件:</b> {record.get('subtitle_path')}</p>"
        
        if record['output_path']:
            html += f"<p><b>输出路径:</b> {record['output_path']}</p>"
        
        if record['file_size']:
            html += f"<p><b>文件大小:</b> {self.format_size(record['file_size'])}</p>"
        
        # 时间信息
        if record['start_time']:
            start_time_str = datetime.datetime.fromtimestamp(record['start_time']).strftime("%Y-%m-%d %H:%M:%S")
            html += f"<p><b>开始时间:</b> {start_time_str}</p>"
        
        if record['end_time']:
            end_time_str = datetime.datetime.fromtimestamp(record['end_time']).strftime("%Y-%m-%d %H:%M:%S")
            html += f"<p><b>结束时间:</b> {end_time_str}</p>"
        
        if record['duration']:
            html += f"<p><b>耗时:</b> {self.format_duration(record['duration'])}</p>"
        
        if record['error_message']:
            html += f"""<p><b>错误信息:</b> <span style="color: red;">{record['error_message']}</span></p>"""
        
        details.setHtml(html)
        layout.addWidget(details)
        
        # 添加按钮
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.exec()
    
    def format_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes/1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes/(1024*1024):.2f} MB"
        else:
            return f"{size_bytes/(1024*1024*1024):.2f} GB"
    
    def format_duration(self, seconds):
        """格式化持续时间"""
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}分{secs}秒"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            return f"{hours}时{minutes}分{secs}秒"
    
    def on_redownload_triggered(self, record):
        """处理重新下载请求"""
        reply = QMessageBox.question(
            self, "确认重新下载", 
            f"确定要重新下载【{record['title']}】吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 发送信号，传递记录信息
            self.redownload_requested.emit(record)
            # 主窗口会处理信号并切换页面
    
    def on_continue_download_triggered(self, record):
        """处理继续下载请求"""
        reply = QMessageBox.question(
            self, "确认继续下载", 
            f"确定要继续下载【{record['title']}】吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 发送信号，传递记录信息
            self.continue_download_requested.emit(record)
            # 主窗口会处理信号并切换页面
    
    def on_continue_conversion_triggered(self, record):
        """处理继续转换请求"""
        # 获取文件路径
        file_path = record['output_path']
        
        if not file_path:
            QMessageBox.warning(
                self, "无法转换", 
                "找不到文件路径信息。"
            )
            return
        
        # 确保路径是.webm文件路径
        webm_path = file_path
        if file_path.endswith('.mp4'):
            # 如果是.mp4文件路径，转换为.webm文件路径
            webm_path = file_path.replace('.mp4', '.webm')
        
        # 检查.webm文件是否存在
        if not webm_path.endswith('.webm') or not os.path.exists(webm_path):
            reply = QMessageBox.question(
                self, "文件不存在", 
                f"WebM文件不存在: {webm_path}\n您可能需要先重新下载视频。是否继续尝试转换？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        # 使用新的转换函数代替创建转换对话框
        from src.utils.video_utils import convert_video
        
        # 创建转换对话框，显示进度
        dialog = QDialog(self)
        dialog.setWindowTitle("视频格式转换")
        dialog.setMinimumWidth(400)
        
        # 设置对话框UI
        layout = QVBoxLayout(dialog)
        
        # 标题和文件名
        title_label = QLabel("<b>正在将WebM文件转换为MP4格式</b>")
        title_label.setAlignment(Qt.AlignCenter)
        
        # 显示文件名
        file_name = os.path.basename(webm_path)
        file_label = QLabel(f"文件: {file_name}")
        
        # 进度条
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        
        # 状态标签
        status_label = QLabel("准备转换...")
        status_label.setWordWrap(True)
        
        # 按钮
        button_layout = QHBoxLayout()
        cancel_button = QPushButton("取消")
        close_button = QPushButton("关闭")
        close_button.setEnabled(False)  # 转换完成前禁用
        
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(close_button)
        
        # 添加所有元素到布局
        layout.addWidget(title_label)
        layout.addWidget(file_label)
        layout.addWidget(progress_bar)
        layout.addWidget(status_label)
        layout.addLayout(button_layout)
        
        # 设置对话框模式和大小
        dialog.setModal(True)
        dialog.resize(450, 200)
        
        # 调用转换需要的回调函数
        conversion_cancelled = [False]  # 用于跟踪取消状态
        
        def progress_callback(percent, message):
            # 更新进度条
            progress_bar.setValue(percent)
            
            # 更新状态标签，格式化显示信息
            if "转换中" in message or "%" in message:
                status_label.setText(f"转换进度: {percent}%")
            else:
                status_label.setText(message)
                
            # 确保UI及时更新
            QApplication.processEvents()
            
            # 如果取消标志被设置，返回False
            return not conversion_cancelled[0]
        
        def finished_callback(success, message, file_path):
            # 更新进度条
            progress_bar.setValue(100 if success else 0)
            
            # 更新状态标签
            if success:
                status_label.setText("转换完成！")
                title_label.setText("<b>转换完成</b>")
            else:
                status_label.setText(f"转换失败: {message}")
                title_label.setText("<b>转换失败</b>")
            
            # 更新按钮状态
            cancel_button.setEnabled(False)
            close_button.setEnabled(True)
            
            # 转换后刷新列表
            self.load_download_history()
        
        # 连接取消和关闭按钮信号
        def on_cancel_clicked():
            conversion_cancelled[0] = True
            cancel_button.setEnabled(False)
            status_label.setText("正在取消转换...")
            progress_bar.setRange(0, 0)  # 设置为未确定状态
            
        def on_close_clicked():
            dialog.close()
            
        cancel_button.clicked.connect(on_cancel_clicked)
        close_button.clicked.connect(on_close_clicked)
        
        # 显示对话框
        dialog.show()
        
        # 启动转换（在对话框显示后）
        convert_video(
            file_path=webm_path,
            record_id=record['id'],
            progress_callback=progress_callback,
            finished_callback=finished_callback
        )
        
        # 执行对话框
        dialog.exec()
    
    def on_translate_subtitle_triggered(self, record):
        """翻译字幕"""
        if not record:
            return
            
        # 检查输出路径是否存在
        if not record['output_path'] or not os.path.exists(record['output_path']):
            QMessageBox.warning(self, "无法翻译", "视频文件不存在，无法找到对应的字幕文件")
            return
        
        # 查找可能的字幕文件
        video_dir = os.path.dirname(record['output_path'])
        video_name = os.path.splitext(os.path.basename(record['output_path']))[0]
        subtitle_files = []
        
        # 查找可能的字幕文件
        for ext in ['.srt', '.vtt', '.ass']:
            pattern = os.path.join(video_dir, f"{video_name}*{ext}")
            subtitle_files.extend(glob.glob(pattern))
        
        if not subtitle_files:
            QMessageBox.warning(self, "无法翻译", "未找到字幕文件")
            return
            
        # 如果找到多个字幕文件，让用户选择
        selected_subtitle = None
        if len(subtitle_files) == 1:
            selected_subtitle = subtitle_files[0]
        else:
            # 创建选择对话框
            from PySide6.QtWidgets import QInputDialog
            selected_subtitle, ok = QInputDialog.getItem(
                self, "选择字幕文件", "请选择要翻译的字幕文件:", 
                subtitle_files, 0, False
            )
            if not ok or not selected_subtitle:
                return
        
        # 创建进度对话框
        progress_dialog = QDialog(self)
        progress_dialog.setWindowTitle("翻译字幕")
        progress_dialog.setModal(True)
        progress_dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(progress_dialog)
        
        # 添加标签
        status_label = QLabel("正在翻译字幕...")
        layout.addWidget(status_label)
        
        # 添加进度条
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        layout.addWidget(progress_bar)
        
        # 添加详细信息
        detail_label = QLabel("准备中...")
        layout.addWidget(detail_label)
        
        # 添加按钮
        button_layout = QHBoxLayout()
        cancel_button = QPushButton("取消")
        close_button = QPushButton("关闭")
        close_button.setEnabled(False)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
        
        # 设置状态变量
        is_translating = [True]
        is_cancelled = [False]
        translated_path = [None]
        
        # 导入配置和翻译器
        from src.config_manager import ConfigManager
        from src.utils.subtitle_translator import SubtitleTranslator
        import threading
        
        # 获取翻译配置
        config = ConfigManager()
        use_n8n = config.getboolean("Subtitle", "use_n8n", fallback=True)
        n8n_workflow_url = config.get("Subtitle", "n8n_workflow_url", fallback="http://localhost:5678/webhook/translate")
        force_translate_traditional = config.getboolean("Subtitle", "force_translate_traditional", fallback=True)
        
        # 更新进度信息的回调函数
        def update_progress(percent, message):
            if not is_cancelled[0]:
                progress_bar.setValue(percent)
                detail_label.setText(message)
        
        # 翻译完成的回调函数
        def translation_finished(success, message, path=None):
            is_translating[0] = False
            if not is_cancelled[0]:
                if success:
                    translated_path[0] = path
                    status_label.setText("翻译完成")
                    detail_label.setText(f"翻译结果保存在: {path}")
                    progress_bar.setValue(100)
                    
                    # 更新数据库中的字幕路径
                    self.db.update_subtitle_path(record.get('id'), path)
                    
                    # 移除成功弹窗，只在对话框中显示状态
                else:
                    status_label.setText("翻译失败")
                    detail_label.setText(message)
                    # 失败时也不显示额外弹窗
            
            # 启用关闭按钮，禁用取消按钮
            cancel_button.setEnabled(False)
            close_button.setEnabled(True)
        
        # 进行翻译的函数
        def do_translate():
            try:
                # 初始化翻译器
                translator = SubtitleTranslator(
                    translation_api_url=n8n_workflow_url,
                    force_translate_traditional=force_translate_traditional,
                    use_n8n=use_n8n
                )
                
                # 更新进度
                update_progress(10, "检测字幕语言...")
                
                # 检测字幕语言
                is_chinese, is_traditional = translator.is_chinese_subtitle(selected_subtitle)
                
                # 根据检测结果更新进度
                if is_chinese and not is_traditional:
                    update_progress(100, "字幕已经是简体中文，无需翻译")
                    translation_finished(True, "字幕已经是简体中文，无需翻译", selected_subtitle)
                    return
                
                # 更新进度
                if is_chinese and is_traditional:
                    update_progress(20, "检测到繁体中文字幕，开始翻译...")
                else:
                    update_progress(20, "检测到外语字幕，开始翻译...")
                
                # 进行翻译
                if is_cancelled[0]:
                    return
                    
                update_progress(30, "正在翻译字幕，这可能需要一些时间...")
                translated_path = translator.translate(selected_subtitle)
                
                if translated_path and translated_path != selected_subtitle:
                    update_progress(90, "翻译完成，正在保存...")
                    translation_finished(True, "翻译完成", translated_path)
                else:
                    translation_finished(False, "翻译失败，请检查网络连接或服务配置")
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                translation_finished(False, f"翻译过程中出错: {str(e)}\n\n{error_details}")
        
        # 取消按钮点击事件
        def on_cancel_clicked():
            is_cancelled[0] = True
            status_label.setText("正在取消...")
            cancel_button.setEnabled(False)
            # 不能真正取消正在进行的HTTP请求，但可以停止后续处理
        
        # 关闭按钮点击事件
        def on_close_clicked():
            progress_dialog.accept()
        
        # 连接按钮信号
        cancel_button.clicked.connect(on_cancel_clicked)
        close_button.clicked.connect(on_close_clicked)
        
        # 在新线程中执行翻译
        threading.Thread(target=do_translate, daemon=True).start()
        
        # 显示对话框
        progress_dialog.exec()
        
        # 如果翻译成功，重新加载历史记录
        if translated_path[0]:
            self.load_download_history()
    
    def showEvent(self, event):
        """页面显示时触发"""
        super().showEvent(event)
        # 当页面显示时立即刷新一次
        self.load_download_history()
        # 启动定时器
        if hasattr(self, 'refresh_timer') and not self.refresh_timer.isActive():
            self.refresh_timer.start()
    
    def hideEvent(self, event):
        """页面隐藏时触发"""
        super().hideEvent(event)
        # 当页面隐藏时停止定时器，节省资源
        if hasattr(self, 'refresh_timer') and self.refresh_timer.isActive():
            self.refresh_timer.stop()
    
    def get_selected_record_id(self):
        """获取当前选中行的记录ID"""
        selected_rows = self.history_table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        
        row = selected_rows[0].row()
        # 直接从ID列获取记录ID (索引0)
        id_item = self.history_table.item(row, 0)
        if id_item:
            return int(id_item.text()) 