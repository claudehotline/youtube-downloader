import sqlite3
import os
import time
import logging
from pathlib import Path


class DownloadHistoryDB:
    """下载历史记录数据库管理类"""
    
    def __init__(self, db_path=None):
        """初始化数据库连接
        
        Args:
            db_path: 数据库文件路径，如果为None则使用默认路径
        """
        if db_path is None:
            # 获取项目根目录
            project_root = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            
            # 使用项目根目录下的data目录
            data_dir = project_root / "data"
            os.makedirs(data_dir, exist_ok=True)
            db_path = data_dir / "download_history.db"
        
        self.db_path = str(db_path)
        self._create_tables()
    
    def _create_tables(self):
        """创建必要的表结构"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建下载历史记录表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS download_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                thumbnail_url TEXT,
                video_format TEXT,
                audio_format TEXT,
                subtitles TEXT,
                output_path TEXT,
                file_size INTEGER DEFAULT 0,
                status TEXT NOT NULL,
                start_time INTEGER NOT NULL,
                end_time INTEGER,
                duration INTEGER,
                error_message TEXT
            )
            ''')
            
            conn.commit()
    
    def add_download(self, video_id, title, url, thumbnail_url=None, 
                    video_format=None, audio_format=None, subtitles=None,
                    output_path=None):
        """添加新的下载记录
        
        Args:
            video_id: 视频ID
            title: 视频标题
            url: 视频URL
            thumbnail_url: 缩略图URL
            video_format: 视频格式
            audio_format: 音频格式
            subtitles: 字幕列表
            output_path: 输出路径
            
        Returns:
            int: 新记录的ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 将字幕列表转换为字符串
            if subtitles:
                subtitles_str = ','.join(subtitles)
            else:
                subtitles_str = None
            
            # 获取当前时间戳
            current_time = int(time.time())
            
            cursor.execute('''
            INSERT INTO download_history 
            (video_id, title, url, thumbnail_url, video_format, audio_format, 
             subtitles, output_path, status, start_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (video_id, title, url, thumbnail_url, video_format, audio_format, 
                  subtitles_str, output_path, '进行中', current_time))
            
            conn.commit()
            return cursor.lastrowid
    
    def update_download_status(self, record_id, status, output_path=None, 
                              file_size=None, error_message=None):
        """更新下载状态
        
        Args:
            record_id: 记录ID
            status: 新状态（进行中、完成、失败、已取消、转换中断）
            output_path: 输出文件路径
            file_size: 文件大小（字节）
            error_message: 错误信息（如果有）
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 获取当前时间戳
            current_time = int(time.time())
            
            # 构建更新查询
            query = "UPDATE download_history SET status = ?, end_time = ?"
            params = [status, current_time]
            
            # 计算持续时间
            query += ", duration = end_time - start_time"
            
            # 可选参数
            if output_path:
                query += ", output_path = ?"
                params.append(output_path)
            
            if file_size is not None:
                query += ", file_size = ?"
                params.append(file_size)
                
            if error_message:
                query += ", error_message = ?"
                params.append(error_message)
                
            query += " WHERE id = ?"
            params.append(record_id)
            
            cursor.execute(query, params)
            conn.commit()
    
    def update_conversion_status(self, file_path, status, error_message=None, record_id=None):
        """根据记录ID更新转换状态
        
        Args:
            file_path: 文件路径（webm或mp4）
            status: 新状态（完成 或 转换中断）
            error_message: 错误信息（如果有）
            record_id: 记录ID，必须提供
            
        Returns:
            bool: 是否找到并更新了记录
        """
        # 文件路径可能是.webm或.mp4格式，需要处理两种情况
        webm_path = file_path
        mp4_path = file_path.replace('.webm', '.mp4')
        
        if webm_path.endswith('.mp4'):
            webm_path = file_path.replace('.mp4', '.webm')
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 必须提供record_id
            if not record_id:
                logging.error("更新转换状态失败：未提供记录ID")
                return False
                
            # 使用record_id查询记录
            cursor.execute('SELECT id, output_path FROM download_history WHERE id = ?', (record_id,))
            record = cursor.fetchone()
            if not record:
                logging.error(f"找不到指定ID的记录: {record_id}")
                return False
            
            # 获取当前时间戳
            current_time = int(time.time())
            
            # 构建更新查询
            query = "UPDATE download_history SET status = ?, end_time = ?"
            params = [status, current_time]
            
            # 计算持续时间
            query += ", duration = end_time - start_time"
            
            # 根据状态更新文件路径和大小
            if status == "完成" and file_path.endswith('.mp4'):
                # 成功完成转换，更新文件路径为MP4
                query += ", output_path = ?"
                params.append(mp4_path)
                
                # 更新文件大小
                if os.path.exists(mp4_path):
                    file_size = os.path.getsize(mp4_path)
                    query += ", file_size = ?"
                    params.append(file_size)
            elif status == "转换中断" and webm_path:
                # 转换中断，确保保留webm文件路径
                query += ", output_path = ?"
                params.append(webm_path)
                
                # 如果webm文件存在，更新其大小
                if os.path.exists(webm_path):
                    file_size = os.path.getsize(webm_path)
                    query += ", file_size = ?"
                    params.append(file_size)
                    logging.info(f"更新转换中断记录的webm文件路径: {webm_path}, 大小: {file_size}")
            
            # 添加错误信息（如果有）
            if error_message:
                query += ", error_message = ?"
                params.append(error_message)
                
            query += " WHERE id = ?"
            params.append(record_id)
            
            cursor.execute(query, params)
            conn.commit()
            return True
    
    def get_all_downloads(self, limit=100, offset=0):
        """获取所有下载记录
        
        Args:
            limit: 结果数量限制
            offset: 结果偏移量
            
        Returns:
            list: 下载记录列表
        """
        with sqlite3.connect(self.db_path) as conn:
            # 配置连接以返回字典
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT * FROM download_history
            ORDER BY start_time DESC
            LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_download_by_id(self, record_id):
        """根据ID获取下载记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            dict: 下载记录或None
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT * FROM download_history
            WHERE id = ?
            ''', (record_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def delete_download(self, record_id):
        """删除下载记录
        
        Args:
            record_id: 要删除的记录ID
            
        Returns:
            bool: 是否成功删除
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
            DELETE FROM download_history
            WHERE id = ?
            ''', (record_id,))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_all_downloads(self):
        """清空所有下载记录
        
        Returns:
            int: 删除的记录数量
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM download_history")
            
            conn.commit()
            return cursor.rowcount
    
    def search_downloads(self, keyword, limit=100, offset=0):
        """搜索下载记录
        
        Args:
            keyword: 搜索关键词
            limit: 结果数量限制
            offset: 结果偏移量
            
        Returns:
            list: 下载记录列表
        """
        search_term = f"%{keyword}%"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT * FROM download_history
            WHERE title LIKE ? OR url LIKE ?
            ORDER BY start_time DESC
            LIMIT ? OFFSET ?
            ''', (search_term, search_term, limit, offset))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_download_stats(self):
        """获取下载统计数据
        
        Returns:
            dict: 包含总下载数、成功数、失败数等统计信息
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 总下载数
            cursor.execute("SELECT COUNT(*) FROM download_history")
            total = cursor.fetchone()[0]
            
            # 成功下载数
            cursor.execute("SELECT COUNT(*) FROM download_history WHERE status = '完成'")
            completed = cursor.fetchone()[0]
            
            # 失败下载数
            cursor.execute("SELECT COUNT(*) FROM download_history WHERE status = '失败'")
            failed = cursor.fetchone()[0]
            
            # 取消下载数
            cursor.execute("SELECT COUNT(*) FROM download_history WHERE status = '已取消'")
            cancelled = cursor.fetchone()[0]
            
            # 转换中断数
            cursor.execute("SELECT COUNT(*) FROM download_history WHERE status = '转换中断'")
            conversion_interrupted = cursor.fetchone()[0]
            
            # 总下载大小
            cursor.execute("SELECT SUM(file_size) FROM download_history WHERE file_size > 0")
            total_size = cursor.fetchone()[0] or 0
            
            return {
                'total': total,
                'completed': completed,
                'failed': failed,
                'cancelled': cancelled,
                'conversion_interrupted': conversion_interrupted,
                'total_size': total_size
            } 