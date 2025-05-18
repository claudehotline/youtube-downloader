from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                         QLabel, QPushButton, QTableWidget, QTableWidgetItem,
                         QHeaderView, QAbstractItemView, QMenu, QMessageBox,
                         QLineEdit, QToolBar, QComboBox, QSizePolicy, QSpacerItem,
                         QDialog, QDialogButtonBox, QTextEdit, QStyle)
from PySide6.QtCore import Qt, Signal, QSize, QDateTime, QEvent, QTimer
from PySide6.QtGui import QIcon, QAction
import os
import datetime
import locale
from src.db.download_history import DownloadHistoryDB


class DownloadHistoryPage(QWidget):
    delete_history_requested = Signal(int)  # 单个记录ID
    clear_all_requested = Signal()
    redownload_requested = Signal(dict)  # 发送下载记录信息
    continue_download_requested = Signal(dict)  # 发送下载记录信息
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DownloadHistoryDB()
        self.setup_ui()
        self.load_download_history()
        
        # 监听窗口大小变化事件
        self.installEventFilter(self)
    
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
        
        # 设置每列的宽度比例
        self.history_table.setColumnWidth(0, int(total_width * 0.25))  # 标题列
        self.history_table.setColumnWidth(1, int(total_width * 0.12))  # 格式列
        self.history_table.setColumnWidth(2, int(total_width * 0.25))  # 路径列
        self.history_table.setColumnWidth(3, int(total_width * 0.08))  # 大小列
        self.history_table.setColumnWidth(4, int(total_width * 0.12))  # 时间列
        self.history_table.setColumnWidth(5, int(total_width * 0.08))  # 耗时列
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
        
        # 设置列
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels([
            "视频标题", "格式", "输出路径", "大小", "下载时间", "耗时", "状态"
        ])
        
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
        
        for i, record in enumerate(records):
            # 视频标题
            title_item = QTableWidgetItem(record['title'])
            title_item.setData(Qt.ItemDataRole.UserRole, record['id'])  # 存储记录ID
            self.history_table.setItem(i, 0, title_item)
            
            # 格式
            format_str = ""
            if record['video_format']:
                format_str += f"视频:{record['video_format']}"
            if record['audio_format']:
                if format_str:
                    format_str += " + "
                format_str += f"音频:{record['audio_format']}"
            self.history_table.setItem(i, 1, QTableWidgetItem(format_str))
            
            # 输出路径
            output_path = record['output_path'] or "未知"
            self.history_table.setItem(i, 2, QTableWidgetItem(output_path))
            
            # 文件大小
            file_size = record['file_size'] or 0
            size_str = self.format_size(file_size) if file_size > 0 else "未知"
            self.history_table.setItem(i, 3, QTableWidgetItem(size_str))
            
            # 下载时间
            start_time = record['start_time']
            if start_time:
                dt = datetime.datetime.fromtimestamp(start_time)
                time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                time_str = "未知"
            self.history_table.setItem(i, 4, QTableWidgetItem(time_str))
            
            # 耗时
            duration = record['duration']
            if duration and duration > 0:
                duration_str = self.format_duration(duration)
            else:
                if record['status'] == '进行中':
                    duration_str = "进行中..."
                elif record['status'] == '已取消':
                    duration_str = "--"
                else:
                    duration_str = "未知"
            self.history_table.setItem(i, 5, QTableWidgetItem(duration_str))
            
            # 状态
            status = record['status']
            status_item = QTableWidgetItem(status)
            if status == '完成':
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            elif status == '失败':
                status_item.setForeground(Qt.GlobalColor.red)
            elif status == '已取消':
                status_item.setForeground(Qt.GlobalColor.darkGray)
            else:
                status_item.setForeground(Qt.GlobalColor.blue)
            self.history_table.setItem(i, 6, status_item)
        
        # 更新统计信息
        self.update_status_bar()
    
    def update_status_bar(self):
        """更新状态栏信息"""
        stats = self.db.get_download_stats()
        
        status_text = (f"总计: {stats['total']} | "
                      f"成功: {stats['completed']} | "
                      f"失败: {stats['failed']} | "
                      f"已取消: {stats['cancelled']} | "
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
        reply = QMessageBox.question(
            self, "确认清空", "确定要清空所有下载历史记录吗？此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            count = self.db.delete_all_downloads()
            QMessageBox.information(self, "清空完成", f"已成功清空 {count} 条下载记录。")
            self.load_download_history()
            self.clear_all_requested.emit()
    
    def on_row_double_clicked(self, index):
        """表格行双击事件"""
        row = index.row()
        record_id = self.history_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
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
        record_id = self.history_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
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
        elif record['status'] in ['失败', '已取消']:
            continue_action = QAction("继续下载", self)
            continue_action.triggered.connect(lambda: self.on_continue_download_triggered(record))
            menu.addAction(continue_action)
        
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
        record_id = self.history_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
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
        record_id = self.history_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
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
                record_id = self.history_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
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