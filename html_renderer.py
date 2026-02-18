import torch
import os
import json
import tempfile
import traceback
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from PIL import Image
import numpy as np
import re
import uuid
from html2image import Html2Image

class HTMLFrameRenderer:
    """
    ComfyUI节点：HTML模板渲染器（包含Chromium截图截断修复）
    
    输入:
        - image: 输入图像 (IMAGE类型)
        - title: 标题文本 (STRING类型)
        - text: 正文文本 (STRING类型)
        - template_html: HTML模板内容 (STRING类型)
        - ext_json: 扩展参数的JSON字符串 (STRING类型，可选)
        - output_width: 输出宽度 (INT类型，默认1080)
        - output_height: 输出高度 (INT类型，默认1920)
    
    输出:
        - image: 渲染后的图像 (IMAGE类型)
        - image_path: 图像保存路径 (STRING类型)
    """
    
    # Chromium截图高度偏移补偿（修复截断问题）
    CHROMIUM_HEIGHT_OFFSET = 87
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "title": ("STRING", {
                    "default": "默认标题",
                    "multiline": False
                }),
                "text": ("STRING", {
                    "default": "默认正文内容",
                    "multiline": True
                }),
                "template_html": ("STRING", {
                    "default": """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="template:media-width" content="1024">
    <meta name="template:media-height" content="1024">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{title}}</title>
    <style>
        /* 使用固定绝对路径的字体定义 */
        @font-face {
            font-family: 'SourceHanSansCN';
            src: url('https://modelscope.cn/datasets/svjack/temp/resolve/master/SourceHanSansCN-Bold.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
            font-display: swap;
        }

        @font-face {
            font-family: 'SourceHanSansCN';
            src: url('https://modelscope.cn/datasets/svjack/temp/resolve/master/SourceHanSansCN-Regular.ttf') format('truetype');
            font-weight: bold;
            font-style: normal;
            font-display: swap;
        }

        @font-face {
            font-family: 'LongCang';
            src: url('https://modelscope.cn/datasets/svjack/temp/resolve/master/Long-Cang-Regular.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
            font-display: swap;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'SourceHanSansCN', 'Comic Sans MS', 'Marker Felt', 'Arial Rounded MT Bold', sans-serif;
        }
        
        body {
            width: 1080px;
            height: 1920px;
            background-image: url('https://lmg.jj20.com/up/allimg/sj02/210122142U11054-0-lp.jpg');
            background-size: cover;
            background-position: center;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: flex-start;
            padding: 40px 20px 0 20px;
            gap: 30px;
            position: relative;
            overflow: hidden;
        }
        
        /* 卡通装饰元素 */
        .cloud {
            position: absolute;
            background: rgba(255, 255, 255, 0.8);
            border-radius: 50%;
            z-index: -1;
        }
        
        .cloud:before, .cloud:after {
            content: '';
            position: absolute;
            background: rgba(255, 255, 255, 0.8);
            border-radius: 50%;
        }
        
        .cloud-1 {
            width: 120px;
            height: 60px;
            top: 10%;
            left: 5%;
        }
        
        .cloud-1:before {
            width: 70px;
            height: 70px;
            top: -30px;
            left: 10px;
        }
        
        .cloud-1:after {
            width: 50px;
            height: 50px;
            top: -20px;
            right: 10px;
        }
        
        .cloud-2 {
            width: 150px;
            height: 70px;
            bottom: 15%;
            right: 5%;
        }
        
        .cloud-2:before {
            width: 80px;
            height: 80px;
            top: -35px;
            left: 15px;
        }
        
        .cloud-2:after {
            width: 60px;
            height: 60px;
            top: -25px;
            right: 20px;
        }
        
        /* 标题样式 */
        .title-container {
            background-color: rgba(255, 255, 255, 0.85);
            padding: 20px 40px;
            border-radius: 25px;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
            text-align: center;
            border: 5px solid #FF9ED8;
            max-width: 90%;
            position: relative;
            z-index: 10;
        }
        
        .title-container h1 {
            font-size: 48px;
            color: #FF5BAE;
            text-shadow: 3px 3px 0 #FFC2E9;
            margin: 0;
            font-family: 'SourceHanSansCN', 'Comic Sans MS', sans-serif;
            font-weight: bold;
        }
        
        /* 图片容器 */
        .image-container {
            width: 1024px;
            height: 1024px;
            background-color: rgba(255, 255, 255, 0.9);
            border-radius: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            border: 8px solid #A6E3FF;
            overflow: hidden;
            position: relative;
            z-index: 10;
        }
        
        .image-container img {
            max-width: 95%;
            max-height: 95%;
            border-radius: 15px;
            object-fit: contain;
        }
        
        /* 字幕样式 */
        .caption-container {
            background-color: rgba(255, 255, 255, 0.9);
            padding: 25px 40px;
            border-radius: 25px;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
            text-align: center;
            border: 5px solid #B5FFA6;
            max-width: 90%;
            position: relative;
            z-index: 10;
        }
        
        .caption-container p {
            font-size: 36px;
            color: #5BAE5B;
            line-height: 1.4;
            text-shadow: 2px 2px 0 #C2FFC2;
            margin: 0;
            font-family: 'SourceHanSansCN', sans-serif;
        }
        
        /* 装饰元素 */
        .decoration {
            position: absolute;
            z-index: 5;
        }
        
        .star {
            width: 30px;
            height: 30px;
            background-color: #FFF9A6;
            clip-path: polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%);
        }
        
        .star-1 {
            top: 15%;
            right: 10%;
            transform: rotate(15deg);
        }
        
        .star-2 {
            bottom: 20%;
            left: 8%;
            transform: rotate(-10deg);
            width: 40px;
            height: 40px;
        }
        
        .heart {
            width: 40px;
            height: 40px;
            background-color: #FF9ED8;
            transform: rotate(-45deg);
            position: absolute;
        }
        
        .heart:before, .heart:after {
            content: '';
            width: 40px;
            height: 40px;
            background-color: #FF9ED8;
            border-radius: 50%;
            position: absolute;
        }
        
        .heart:before {
            top: -20px;
            left: 0;
        }
        
        .heart:after {
            top: 0;
            left: 20px;
        }
        
        .heart-1 {
            top: 12%;
            left: 12%;
        }
        
        .heart-2 {
            bottom: 25%;
            right: 12%;
            width: 30px;
            height: 30px;
        }
        
        .heart-2:before, .heart-2:after {
            width: 30px;
            height: 30px;
        }
        
        .heart-2:before {
            top: -15px;
        }
        
        .heart-2:after {
            left: 15px;
        }

        /* 特殊字体样式类 */
        .font-longcang {
            font-family: 'LongCang', cursive;
        }
    </style>
</head>
<body>
    <!-- 装饰元素 -->
    <div class="cloud cloud-1"></div>
    <div class="cloud cloud-2"></div>
    
    <div class="decoration star star-1"></div>
    <div class="decoration star star-2"></div>
    
    <div class="decoration heart heart-1"></div>
    <div class="decoration heart heart-2"></div>
    
    <!-- 标题区域 -->
    <div class="title-container">
        <h1>{{title}}</h1>
    </div>
    
    <!-- 图片区域 -->
    <div class="image-container">
        <img src="{{image}}" alt="卡通图片">
    </div>
    
    <!-- 字幕区域 -->
    <div class="caption-container">
        <p>{{text}}</p>
    </div>
</body>
</html>""",
                    "multiline": True
                })
            },
            "optional": {
                "ext_json": ("STRING", {
                    "default": "{}",
                    "multiline": True
                }),
                "output_width": ("INT", {
                    "default": 1080,
                    "min": 100,
                    "max": 4096
                }),
                "output_height": ("INT", {
                    "default": 1920,
                    "min": 100,
                    "max": 4096
                })
            }
        }
    
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "image_path")
    FUNCTION = "render_frame"
    CATEGORY = "图像处理/渲染"
    DESCRIPTION = "使用HTML模板渲染图像帧（包含Chromium截图截断修复）"
    
    def render_frame(self, image: torch.Tensor, title: str, text: str, 
                    template_html: str, ext_json: str = "{}", 
                    output_width: int = 1080, output_height: int = 1920) -> Tuple[torch.Tensor, str]:
        """
        渲染HTML模板到图像（包含Chromium截图截断修复）
        """
        try:
            # 处理输入图像
            if len(image.shape) == 4:  # 如果有批次维度
                image = image[0]  # 取第一张
            
            # 转换图像为RGB
            image_np = image.numpy() if isinstance(image, torch.Tensor) else image
            if image_np.shape[-1] == 1:  # 灰度图转RGB
                image_np = np.repeat(image_np, 3, axis=-1)
            elif image_np.shape[-1] == 4:  # RGBA转RGB
                image_np = image_np[..., :3]
            
            # 创建临时目录
            temp_dir = tempfile.mkdtemp(prefix="comfyui_html_render_")
            
            # 保存输入图像为临时文件
            input_image_path = os.path.join(temp_dir, "input_image.png")
            pil_image = Image.fromarray((image_np * 255).astype(np.uint8))
            pil_image.save(input_image_path)
            
            # 保存HTML模板为临时文件
            template_path = os.path.join(temp_dir, "template.html")
            with open(template_path, "w", encoding="utf-8") as f:
                f.write(template_html)
            
            # 解析扩展参数
            try:
                ext_params = json.loads(ext_json) if ext_json.strip() else {}
            except json.JSONDecodeError:
                print(f"警告: ext_json解析失败，使用空字典")
                ext_params = {}
            
            # 添加尺寸参数到扩展参数中
            ext_params["width"] = output_width
            ext_params["height"] = output_height
            
            # 创建HTMLFrameGenerator实例
            generator = self._create_html_frame_generator(
                template_path, 
                output_width, 
                output_height
            )
            
            # 生成帧
            output_image_path = generator.generate_frame(
                title=title,
                text=text,
                image=input_image_path,
                ext=ext_params,
                output_path=os.path.join(temp_dir, "output_frame.png")
            )
            
            # 加载渲染后的图像
            rendered_image = Image.open(output_image_path)
            
            # 转换回ComfyUI的IMAGE格式 (转换为RGB)
            if rendered_image.mode != "RGB":
                rendered_image = rendered_image.convert("RGB")
            
            # 转换为numpy数组
            image_array = np.array(rendered_image).astype(np.float32) / 255.0
            
            # 转换为torch张量并添加批次维度
            image_tensor = torch.from_numpy(image_array)[None, ...]
            
            # 保存最终输出文件
            output_saved_path = os.path.join(os.path.dirname(temp_dir), f"rendered_frame_{uuid.uuid4().hex[:8]}.png")
            rendered_image.save(output_saved_path)
            
            # 清理临时目录
            import shutil
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
                
            print(f"✅ 渲染完成，图像已保存到: {output_saved_path}")
            return (image_tensor, output_saved_path)
                
        except Exception as e:
            print(f"❌ 渲染失败: {str(e)}")
            traceback.print_exc()
            # 返回原始图像作为降级处理
            return (image[None, ...] if len(image.shape) == 3 else image, "")
    
    def _create_html_frame_generator(self, template_path: str, width: int, height: int):
        """创建包含Chromium截图截断修复的HTMLFrameGenerator"""
        
        class FixedHTMLFrameGenerator:
            def __init__(self, template_path: str, width: int, height: int):
                self.template_path = template_path
                self.width = width
                self.height = height
                self.template = self._load_template(template_path)
                self.hti = None
                
            def _load_template(self, template_path: str) -> str:
                with open(template_path, 'r', encoding='utf-8') as f:
                    return f.read()
            
            def _replace_parameters(self, html: str, values: Dict[str, Any]) -> str:
                # 替换所有{{variable}}格式的变量
                for key, value in values.items():
                    placeholder = f"{{{{{key}}}}}"
                    html = html.replace(placeholder, str(value))
                return html
            
            def _ensure_hti(self, render_width: int, render_height: int):
                if self.hti is None:
                    # 配置Chrome flags
                    custom_flags = [
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--hide-scrollbars',
                        '--mute-audio',
                        '--disable-background-networking',
                        '--disable-features=TranslateUI',
                    ]
                    
                    self.hti = Html2Image(
                        size=(render_width, render_height),
                        custom_flags=custom_flags
                    )
            
            def generate_frame(self, title: str, text: str, image: str, 
                             ext: Optional[Dict[str, Any]] = None, 
                             output_path: Optional[str] = None) -> str:
                
                # 构建变量上下文
                context = {
                    "title": title,
                    "text": text,
                    "image": f"file://{image}" if image and not image.startswith(('http://', 'https://', 'file://')) else image,
                }
                
                # 添加扩展参数
                if ext:
                    context.update(ext)
                
                # 替换HTML中的变量
                html = self._replace_parameters(self.template, context)
                
                # 设置输出路径
                import os
                if output_path is None:
                    output_dir = os.path.join(os.path.expanduser("~"), "comfyui_output")
                    os.makedirs(output_dir, exist_ok=True)
                    output_filename = f"frame_{uuid.uuid4().hex[:8]}.png"
                    output_path = os.path.join(output_dir, output_filename)
                else:
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # 关键修复：渲染时增加高度以补偿Chromium截图截断问题
                render_height = self.height + HTMLFrameRenderer.CHROMIUM_HEIGHT_OFFSET
                
                # 确保Html2Image初始化（使用增加后的高度）
                self._ensure_hti(self.width, render_height)
                
                # 渲染HTML到图像
                try:
                    # 先渲染到临时文件
                    temp_filename = f"temp_{uuid.uuid4().hex[:8]}.png"
                    self.hti.screenshot(
                        html_str=html,
                        save_as=temp_filename
                    )
                    
                    # 获取临时文件路径
                    temp_output = os.path.join(os.getcwd(), temp_filename)
                    
                    if os.path.exists(temp_output):
                        # 关键修复：裁剪图像以移除额外的高度补偿
                        with Image.open(temp_output) as img:
                            # 裁剪到原始尺寸 (0, 0, width, height)
                            cropped_img = img.crop((0, 0, self.width, self.height))
                            cropped_img.save(output_path)
                        
                        # 清理临时文件
                        os.remove(temp_output)
                        
                        print(f"✅ 图像已渲染并裁剪，保存到: {output_path}")
                        return output_path
                    else:
                        raise Exception("临时渲染文件未生成")
                    
                except Exception as e:
                    print(f"❌ HTML渲染错误: {str(e)}")
                    raise
        
        return FixedHTMLFrameGenerator(template_path, width, height)


# 节点注册
NODE_CLASS_MAPPINGS = {
    "HTMLFrameRenderer": HTMLFrameRenderer
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "HTMLFrameRenderer": "HTML帧渲染器（截图修复版）"
}