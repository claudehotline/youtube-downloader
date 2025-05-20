import os
import re
import logging
import chardet
import requests
from pathlib import Path


class SubtitleTranslator:
    """字幕翻译工具，将非中文字幕或繁体中文字幕自动翻译为简体中文"""
    
    def __init__(self, translation_api_url="http://localhost:5678/webhook/translate", force_translate_traditional=True, use_n8n=True):
        """初始化翻译工具
        
        Args:
            translation_api_url: 翻译服务API地址
            force_translate_traditional: 是否强制翻译繁体中文字幕
            use_n8n: 是否使用n8n工作流进行翻译
        """
        self.translation_api_url = translation_api_url
        self.force_translate_traditional = force_translate_traditional
        self.use_n8n = use_n8n
        self.logger = logging.getLogger(__name__)
    
    def is_chinese_subtitle(self, subtitle_path):
        """检测字幕文件是否为简体中文
        
        Args:
            subtitle_path: 字幕文件路径
            
        Returns:
            tuple: (是否为中文字幕, 是否为繁体中文字幕)
        """
        if not os.path.exists(subtitle_path):
            self.logger.warning(f"字幕文件不存在: {subtitle_path}")
            return False, False
            
        try:
            # 检测文件编码
            with open(subtitle_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                encoding = result['encoding']
            
            # 读取文件内容
            with open(subtitle_path, 'r', encoding=encoding, errors='replace') as f:
                content = f.read()
            
            # 提取字幕文本（跳过时间轴和序号）
            text_only = ""
            lines = content.split('\n')
            for i, line in enumerate(lines):
                # 跳过时间轴行和空行
                if '-->' in line or re.match(r'^\d+$', line.strip()) or line.strip() == '':
                    continue
                text_only += line + " "
            
            # 所有中文字符（简体+繁体）
            all_chinese_chars = re.findall(r'[\u4e00-\u9fff]', text_only)
            chinese_char_ratio = len(all_chinese_chars) / max(1, len(text_only.strip()))
            
            # 如果中文字符比例低于50%，则不是中文字幕
            if chinese_char_ratio < 0.5:
                self.logger.info(f"检测到非中文字幕: {subtitle_path}")
                return False, False
            
            # 检测是否为繁体中文
            # 繁简体差异明显的常用字
            simplified_chars = "国东车边出发见后还龙飞风"
            traditional_chars = "國東車邊出發見後還龍飛風"
            
            # 计算繁体字符数量
            traditional_count = 0
            simplified_count = 0
            
            for char in all_chinese_chars:
                if char in traditional_chars:
                    traditional_count += 1
                elif char in simplified_chars:
                    simplified_count += 1
            
            # 如果存在明显的繁体字符且比例较高，判定为繁体中文
            is_traditional = False
            if traditional_count > 0:
                traditional_ratio = traditional_count / max(1, traditional_count + simplified_count)
                if traditional_ratio > 0.3:  # 如果超过30%的区分字符是繁体的，判定为繁体中文
                    is_traditional = True
                    self.logger.info(f"检测到繁体中文字幕: {subtitle_path}")
                else:
                    self.logger.info(f"检测到简体中文字幕: {subtitle_path}")
            else:
                self.logger.info(f"检测到简体中文字幕: {subtitle_path}")
            
            return True, is_traditional
            
        except Exception as e:
            self.logger.error(f"检测字幕语言时出错: {str(e)}")
            return False, False
    
    def translate(self, subtitle_path):
        """将字幕翻译为简体中文
        
        Args:
            subtitle_path: 字幕文件路径
            
        Returns:
            str: 翻译后的字幕文件路径，如果翻译失败则返回None
        """
        if not os.path.exists(subtitle_path):
            self.logger.error(f"字幕文件不存在: {subtitle_path}")
            return None
        
        # 检测字幕语言
        is_chinese, is_traditional = self.is_chinese_subtitle(subtitle_path)
        
        # 如果是简体中文，则不需要翻译
        if is_chinese and not is_traditional:
            self.logger.info(f"字幕已经是简体中文，无需翻译: {subtitle_path}")
            return subtitle_path
        
        # 如果是繁体中文但未设置强制翻译，则不翻译
        if is_chinese and is_traditional and not self.force_translate_traditional:
            self.logger.info(f"字幕是繁体中文，但未设置强制翻译: {subtitle_path}")
            return subtitle_path
        
        try:
            # 使用n8n工作流进行翻译
            if self.use_n8n:
                self.logger.info(f"使用n8n工作流进行字幕翻译: {subtitle_path}")
                return self.translate_with_n8n(subtitle_path)
            
            # 使用默认翻译方法
            self.logger.info(f"使用默认翻译方法: {subtitle_path}")
            
            # 准备请求
            files = {'file': (os.path.basename(subtitle_path), open(subtitle_path, 'rb'))}
            
            # 发送翻译请求
            if is_traditional:
                self.logger.info(f"发送繁体中文翻译请求: {subtitle_path} -> {self.translation_api_url}")
            else:
                self.logger.info(f"发送翻译请求: {subtitle_path} -> {self.translation_api_url}")
                
            self.logger.info(f"开始字幕翻译，这可能需要较长时间，请耐心等待...")
                
            response = requests.post(
                self.translation_api_url, 
                files=files,
                timeout=300  # 设置超时时间为300秒
            )
            
            # 检查响应
            if response.status_code != 200:
                self.logger.error(f"翻译请求失败，状态码: {response.status_code}, 响应: {response.text}")
                return None
                
            self.logger.info(f"已收到翻译服务响应，正在处理翻译结果...")
            
            # 解析响应
            try:
                # 记录完整响应内容以便调试
                self.logger.debug(f"完整响应内容: {response.text}")
                
                # 如果响应内容为空，直接返回错误
                if not response.text.strip():
                    self.logger.error("翻译响应为空")
                    return None
                
                # 尝试解析JSON，但也处理非JSON响应
                try:
                    result = response.json()
                    self.logger.info(f"成功解析JSON响应，结果类型: {type(result)}")
                    if isinstance(result, list):
                        self.logger.info(f"列表长度: {len(result)}")
                        if len(result) > 0:
                            self.logger.info(f"第一个元素类型: {type(result[0])}")
                            if isinstance(result[0], dict):
                                self.logger.info(f"第一个元素键: {list(result[0].keys())}")
                except requests.exceptions.JSONDecodeError as json_err:
                    self.logger.warning(f"响应不是有效的JSON格式: {str(json_err)}")
                    # 如果不是JSON，直接使用文本内容
                    translated_content = response.text
                    self.logger.info("使用纯文本响应作为翻译结果")
                    
                    # 生成翻译后的文件路径并保存
                    original_path = Path(subtitle_path)
                    original_stem = original_path.stem
                    translated_path = original_path.with_stem(f"{original_stem}.zh-CN")
                    
                    # 保存翻译后的字幕
                    with open(translated_path, 'w', encoding='utf-8') as f:
                        # 清理翻译内容中的<think>标记及其内容
                        cleaned_content = self.clean_translation_content(translated_content)
                        f.write(cleaned_content)
                    
                    self.logger.info(f"字幕翻译完成(非JSON响应): {subtitle_path} -> {translated_path}")
                    return str(translated_path)
                
                # 处理特殊情况：result为数字0
                if result == 0:
                    self.logger.warning("翻译响应为数字0，尝试使用原始响应文本")
                    # 直接使用响应文本作为翻译结果
                    translated_content = response.text
                    
                    # 生成翻译后的文件路径并保存
                    original_path = Path(subtitle_path)
                    original_stem = original_path.stem
                    translated_path = original_path.with_stem(f"{original_stem}.zh-CN")
                    
                    # 保存翻译后的字幕
                    with open(translated_path, 'w', encoding='utf-8') as f:
                        # 清理翻译内容中的<think>标记及其内容
                        cleaned_content = self.clean_translation_content(translated_content)
                        f.write(cleaned_content)
                    
                    self.logger.info(f"字幕翻译完成(数字0响应): {subtitle_path} -> {translated_path}")
                    return str(translated_path)
                elif not result:
                    self.logger.error(f"翻译响应解析后为空: {response.text}")
                    return None
                else:
                    # 尝试获取不同格式的输出
                    translated_content = None
                    
                    # 处理n8n格式 [{ "output": "xxxxx" }]
                    if isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict) and "output" in result[0]:
                        translated_content = result[0]["output"]
                        self.logger.info("成功解析响应格式: [{ \"output\": \"xxxxx\" }]")
                    # 输出格式1: {"output": "翻译内容"}
                    elif isinstance(result, dict) and "output" in result:
                        translated_content = result["output"]
                        self.logger.info("使用响应格式1解析翻译结果")
                    
                    # 输出格式2: [{"output": "翻译内容"}]
                    elif isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict) and "output" in result[0]:
                        translated_content = result[0]["output"]
                        self.logger.info("使用响应格式2解析翻译结果")
                    
                    # 输出格式3: {"result": "翻译内容"}
                    elif isinstance(result, dict) and "result" in result:
                        translated_content = result["result"]
                        self.logger.info("使用响应格式3解析翻译结果")
                    
                    # 输出格式4: 直接是文本
                    elif isinstance(result, str):
                        translated_content = result
                        self.logger.info("使用响应格式4解析翻译结果")
                
                # 如果无法识别输出格式，尝试直接使用响应文本
                if not translated_content:
                    self.logger.warning(f"无法识别响应格式: {result}，尝试直接使用响应文本")
                    translated_content = response.text
                
                # 检查翻译内容是否为空
                if not translated_content.strip():
                    self.logger.error("翻译内容为空")
                    return None
                
                # 生成翻译后的文件路径
                original_path = Path(subtitle_path)
                original_stem = original_path.stem
                translated_path = original_path.with_stem(f"{original_stem}.zh-CN")
                
                # 保存翻译后的字幕
                with open(translated_path, 'w', encoding='utf-8') as f:
                    # 清理翻译内容中的<think>标记及其内容
                    cleaned_content = self.clean_translation_content(translated_content)
                    f.write(cleaned_content)
                
                self.logger.info(f"字幕翻译完成: {subtitle_path} -> {translated_path}")
                return str(translated_path)
                
            except Exception as e:
                self.logger.error(f"解析翻译响应时出错: {str(e)}")
                # 添加更详细的错误日志
                self.logger.error(f"错误详情: 响应状态码={response.status_code}, 响应内容={response.text[:200]}")
                import traceback
                self.logger.error(f"错误堆栈: {traceback.format_exc()}")
                return None
                
        except Exception as e:
            self.logger.error(f"翻译字幕时出错: {str(e)}")
            return None
    
    def translate_with_n8n(self, subtitle_path):
        """使用n8n工作流翻译字幕
        
        Args:
            subtitle_path: 字幕文件路径
            
        Returns:
            str: 翻译后的字幕文件路径，如果翻译失败则返回None
        """
        if not os.path.exists(subtitle_path):
            self.logger.error(f"字幕文件不存在: {subtitle_path}")
            return None
        
        try:
            self.logger.info(f"开始通过n8n工作流翻译字幕: {subtitle_path}")
            
            # 准备请求
            files = {'file': (os.path.basename(subtitle_path), open(subtitle_path, 'rb'))}
            
            # 发送翻译请求到n8n工作流
            response = requests.post(
                self.translation_api_url, 
                files=files,
                timeout=300  # 设置超时时间为300秒
            )
            
            # 检查响应
            if response.status_code != 200:
                self.logger.error(f"n8n翻译请求失败，状态码: {response.status_code}, 响应: {response.text}")
                return None
                
            self.logger.info(f"已收到n8n工作流响应，正在处理翻译结果...")
            
            # 解析响应
            try:
                # 记录完整响应内容以便调试
                self.logger.debug(f"完整响应内容: {response.text}")
                
                # 如果响应内容为空，直接返回错误
                if not response.text.strip():
                    self.logger.error("n8n工作流响应为空")
                    return None
                
                # 尝试解析JSON，但也处理非JSON响应
                try:
                    result = response.json()
                    self.logger.info(f"成功解析JSON响应，结果类型: {type(result)}")
                    if isinstance(result, list):
                        self.logger.info(f"列表长度: {len(result)}")
                        if len(result) > 0:
                            self.logger.info(f"第一个元素类型: {type(result[0])}")
                            if isinstance(result[0], dict):
                                self.logger.info(f"第一个元素键: {list(result[0].keys())}")
                except requests.exceptions.JSONDecodeError as json_err:
                    self.logger.warning(f"n8n响应不是有效的JSON格式: {str(json_err)}")
                    # 如果不是JSON，直接使用文本内容
                    translated_content = response.text
                    self.logger.info("使用纯文本响应作为翻译结果")
                    
                    # 生成翻译后的文件路径并保存
                    original_path = Path(subtitle_path)
                    original_stem = original_path.stem
                    translated_path = original_path.with_stem(f"{original_stem}.zh-CN")
                    
                    # 保存翻译后的字幕
                    with open(translated_path, 'w', encoding='utf-8') as f:
                        # 清理翻译内容中的<think>标记及其内容
                        cleaned_content = self.clean_translation_content(translated_content)
                        f.write(cleaned_content)
                    
                    self.logger.info(f"字幕翻译完成(非JSON响应): {subtitle_path} -> {translated_path}")
                    return str(translated_path)
                
                # 处理n8n工作流的各种可能的响应格式
                translated_content = None
                
                # 处理n8n工作流的响应格式 [{ "output": "xxxxx" }]
                if isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict) and "output" in result[0]:
                    translated_content = result[0]["output"]
                    self.logger.info("成功解析n8n响应格式: [{ \"output\": \"xxxxx\" }]")
                # 兼容其他可能的格式
                elif isinstance(result, dict):
                    # 尝试常见的n8n响应格式
                    if "translatedContent" in result:
                        translated_content = result["translatedContent"]
                    elif "output" in result:
                        translated_content = result["output"]
                    elif "result" in result:
                        translated_content = result["result"]
                    elif "data" in result:
                        if isinstance(result["data"], str):
                            translated_content = result["data"]
                        elif isinstance(result["data"], dict) and "content" in result["data"]:
                            translated_content = result["data"]["content"]
                elif isinstance(result, str):
                    translated_content = result
                
                # 如果无法识别输出格式，记录警告并尝试直接使用响应文本
                if not translated_content:
                    self.logger.warning(f"无法识别n8n响应格式: {result}，尝试直接使用响应文本")
                    self.logger.warning(f"尝试将整个响应作为字幕内容保存")
                    translated_content = response.text
                
                # 检查翻译内容是否为空
                if not translated_content or not translated_content.strip():
                    self.logger.error("n8n翻译内容为空")
                    return None
                
                # 生成翻译后的文件路径
                original_path = Path(subtitle_path)
                original_stem = original_path.stem
                translated_path = original_path.with_stem(f"{original_stem}.zh-CN")
                
                # 保存翻译后的字幕
                with open(translated_path, 'w', encoding='utf-8') as f:
                    # 清理翻译内容中的<think>标记及其内容
                    cleaned_content = self.clean_translation_content(translated_content)
                    f.write(cleaned_content)
                
                self.logger.info(f"n8n字幕翻译完成: {subtitle_path} -> {translated_path}")
                return str(translated_path)
                
            except Exception as e:
                self.logger.error(f"解析n8n翻译响应时出错: {str(e)}")
                # 添加更详细的错误日志
                self.logger.error(f"错误详情: 响应状态码={response.status_code}, 响应内容={response.text[:200]}")
                import traceback
                self.logger.error(f"错误堆栈: {traceback.format_exc()}")
                return None
                
        except Exception as e:
            self.logger.error(f"使用n8n翻译字幕时出错: {str(e)}")
            import traceback
            self.logger.error(f"错误堆栈: {traceback.format_exc()}")
            return None
    
    def auto_translate_subtitle(self, subtitle_path, force_translate_traditional=None, use_n8n=None):
        """自动检测并翻译字幕文件
        
        Args:
            subtitle_path: 字幕文件路径
            force_translate_traditional: 是否强制翻译繁体中文字幕，如果为None则使用默认设置
            use_n8n: 是否使用n8n工作流进行翻译，如果为None则使用默认设置
            
        Returns:
            str: 最终使用的字幕文件路径（原路径或翻译后的路径）
        """
        if not subtitle_path or not os.path.exists(subtitle_path):
            self.logger.warning(f"无效的字幕文件路径: {subtitle_path}")
            return subtitle_path
        
        # 临时覆盖设置
        original_force_setting = self.force_translate_traditional
        original_n8n_setting = self.use_n8n
        
        if force_translate_traditional is not None:
            self.force_translate_traditional = force_translate_traditional
            
        if use_n8n is not None:
            self.use_n8n = use_n8n
            
        try:
            # 检测是否为中文字幕以及是否为繁体中文
            is_chinese, is_traditional = self.is_chinese_subtitle(subtitle_path)
            
            # 如果是简体中文，直接返回原路径
            if is_chinese and not is_traditional:
                return subtitle_path
                
            # 如果是繁体中文但未设置强制翻译，则不翻译
            if is_chinese and is_traditional and not self.force_translate_traditional:
                self.logger.info(f"字幕是繁体中文，但未设置强制翻译: {subtitle_path}")
                return subtitle_path
                
            # 进行翻译
            translated_path = self.translate(subtitle_path)
            if translated_path:
                return translated_path
            else:
                # 翻译失败时返回原路径
                self.logger.warning(f"翻译失败，将使用原始字幕: {subtitle_path}")
                return subtitle_path
        finally:
            # 恢复原始设置
            if force_translate_traditional is not None:
                self.force_translate_traditional = original_force_setting
            if use_n8n is not None:
                self.use_n8n = original_n8n_setting 
    
    def clean_translation_content(self, content):
        """清理翻译内容中的<think>标记及其内容
        
        Args:
            content: 原始翻译内容
            
        Returns:
            str: 清理后的翻译内容
        """
        # 如果内容为空，直接返回
        if not content or not isinstance(content, str):
            return content
            
        # 使用正则表达式移除<think>到</think>之间的内容（包括标记本身）
        import re
        cleaned_content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
        
        # 移除</think>标记后的空行
        cleaned_content = re.sub(r'</think>\s*\n', '', cleaned_content)
        
        # 处理文件开头的空行，使用分行处理的方式
        lines = cleaned_content.split('\n')
        # 去掉开头的空行
        while lines and not lines[0].strip():
            lines.pop(0)
        
        # 重新组合成文本
        cleaned_content = '\n'.join(lines)
        
        # 如果整个文件被清空了，返回原始内容
        if not cleaned_content.strip() and content.strip():
            self.logger.warning("清理<think>标记后内容为空，使用原始内容")
            return content
            
        self.logger.info("已清理翻译内容中的<think>标记及其内容")
        
        # 确保文本末尾有一个空行
        if not cleaned_content.endswith('\n\n'):
            if cleaned_content.endswith('\n'):
                cleaned_content += '\n'
            else:
                cleaned_content += '\n\n'
                
        return cleaned_content 