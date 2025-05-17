# -*- mode: python ; coding: utf-8 -*-

import os

block_cipher = None

# 获取当前工作目录
current_dir = os.getcwd()

a = Analysis(
    ['app.py'],  # 使用app.py作为入口点
    pathex=[],
    binaries=[
        # 直接指定二进制文件
        (os.path.join(current_dir, 'cmd', 'yt-dlp.exe'), 'cmd'),
    ],
    datas=[],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'src',
        'src.ui',
        'src.ui.main_window',
        'src.ui.download_page',
        'src.ui.settings_page',
        'src.ui.history_page',
        'src.downloader',
        'src.config',
        'src.config_manager',
        'src.threads',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='YouTube下载器',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 设置为False以隐藏控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='icon.ico',  # 如果有图标，取消注释并指定路径
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='YouTube下载器',
)