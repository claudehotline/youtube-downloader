# YouTube 视频下载器

基于PySide6和yt-dlp的YouTube视频下载工具。

## 功能特点

* 从YouTube获取视频信息
* 支持不同格式和分辨率的下载选择
* 支持多语言字幕下载
* 支持下载视频缩略图
* 支持自定义下载路径
* 实时显示下载进度

## 安装要求

* Python 3.6+
* PySide6
* requests

安装依赖：
```
pip install -r requirements.txt
```

## 使用说明

1. 确保`yt-dlp.exe`文件和主程序在同一目录下
2. 运行`python main.py`启动程序
3. 在地址栏输入YouTube视频链接，点击"获取信息"
4. 选择需要的视频格式、字幕和选项
5. 设置保存位置，点击"开始下载"

## 注意事项

* 本软件使用yt-dlp作为下载引擎，确保yt-dlp.exe存在并且是最新版本
* 如果下载进度停滞，可能是由于网络问题或YouTube限制，请尝试重新下载
* 下载时请遵守当地法律法规和YouTube的服务条款

## 依赖项

* [PySide6](https://pypi.org/project/PySide6/) - Qt框架的Python绑定
* [yt-dlp](https://github.com/yt-dlp/yt-dlp) - 视频下载引擎
* [requests](https://pypi.org/project/requests/) - HTTP库

## 许可证

此软件使用MIT许可证 