import sys
import os
import requests
import logging
from src.utils.subtitle_translator import SubtitleTranslator
from src.config_manager import ConfigManager

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python test_subtitle_translate.py <字幕文件路径>")
        sys.exit(1)
    
    subtitle_path = sys.argv[1]
    if not os.path.exists(subtitle_path):
        print(f"文件不存在: {subtitle_path}")
        sys.exit(1)
    
    # 从配置文件获取设置
    config = ConfigManager()
    use_n8n = config.getboolean("Subtitle", "use_n8n", fallback=True)
    n8n_workflow_url = config.get("Subtitle", "n8n_workflow_url", 
                                fallback="http://localhost:5678/webhook/translate")
    force_translate = config.getboolean("Subtitle", "force_translate_traditional", fallback=True)
    
    print(f"字幕翻译配置:")
    print(f"- 使用n8n工作流: {use_n8n}")
    print(f"- n8n工作流URL: {n8n_workflow_url}")
    print(f"- 强制翻译繁体中文: {force_translate}")
    
    # 创建翻译器
    translator = SubtitleTranslator(
        translation_api_url=n8n_workflow_url,
        force_translate_traditional=force_translate,
        use_n8n=use_n8n
    )
    
    # 检测字幕语言
    is_chinese, is_traditional = translator.is_chinese_subtitle(subtitle_path)
    print(f"字幕检测结果:")
    print(f"- 是中文字幕: {is_chinese}")
    print(f"- 是繁体中文: {is_traditional}")
    
    # 翻译字幕
    print(f"正在翻译字幕文件: {subtitle_path}")
    translated_path = translator.auto_translate_subtitle(subtitle_path)
    
    if translated_path and translated_path != subtitle_path:
        print(f"字幕已成功翻译: {subtitle_path} -> {translated_path}")
    elif translated_path and translated_path == subtitle_path:
        print(f"无需翻译，字幕已经是简体中文: {subtitle_path}")
    else:
        print(f"字幕翻译失败")
