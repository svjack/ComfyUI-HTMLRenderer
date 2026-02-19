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

import torch
import os
import json
import tempfile
import traceback
import asyncio
import threading
import numpy as np
from PIL import Image
import io
import base64
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import uuid
import time
from playwright.async_api import async_playwright

class HTMLVideoRecorderPlaywright:
    """
    ComfyUI节点：使用Playwright进行HTML视频录制
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE", {
                    "tooltip": "输入图像，将进行圆形剪裁并旋转显示"
                }),
                "title": ("STRING", {
                    "default": "动态视频标题",
                    "multiline": False
                }),
                "text": ("STRING", {
                    "default": "这是一个带动态效果的视频示例，文本将进行滚动显示",
                    "multiline": True
                }),
                "template_html": ("STRING", {
                    "default": """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        /* 字体定义 - 开始 */
        @font-face {
            font-family: 'LongCang';
            src: url('https://modelscope.cn/datasets/svjack/temp/resolve/master/Long-Cang-Regular.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
            font-display: swap;
        }
        @font-face {
            font-family: 'SourceHanSansCN';
            src: url('https://modelscope.cn/datasets/svjack/temp/resolve/master/SourceHanSansCN-Regular.ttf') format('truetype');
            font-weight: normal;
            font-style: normal;
            font-display: swap;
        }
        @font-face {
            font-family: 'SourceHanSansCN';
            src: url('https://modelscope.cn/datasets/svjack/temp/resolve/master/SourceHanSansCN-Bold.ttf') format('truetype');
            font-weight: bold;
            font-style: normal;
            font-display: swap;
        }
        /* 字体定义 - 结束 */

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            width: 1080px;
            height: 1920px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            font-family: 'LongCang', 'SourceHanSansCN', sans-serif;
            overflow: hidden;
            position: relative;
        }

        .container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            width: 100%;
            height: 100%;
            padding: 40px;
        }

        /* 图像容器 - 圆形剪裁 */
        .image-container {
            position: relative;
            width: 400px;
            height: 400px;
            margin-bottom: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .circular-image {
            width: 350px;
            height: 350px;
            border-radius: 50%;
            object-fit: cover;
            border: 8px solid rgba(255, 255, 255, 0.3);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            animation: rotate 20s linear infinite;
        }

        @keyframes rotate {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        /* 标题 - 反复缩放动画 */
        .title-container {
            margin-bottom: 40px;
            text-align: center;
        }

        .scaling-title {
            font-size: 48px;
            font-weight: bold;
            color: #ffffff;
            text-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
            animation: scalePulse 3s ease-in-out infinite;
            display: inline-block;
        }

        @keyframes scalePulse {
            0% { transform: scale(1); opacity: 0.8; }
            50% { transform: scale(1.15); opacity: 1; }
            100% { transform: scale(1); opacity: 0.8; }
        }

        /* 文本 - 滚动显示 */
        .text-container {
            width: 80%;
            max-width: 800px;
            height: 200px;
            overflow: hidden;
            position: relative;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 25px;
            margin-top: 30px;
            backdrop-filter: blur(10px);
            border: 2px solid rgba(255, 255, 255, 0.2);
        }

        .scrolling-text {
            font-size: 28px;
            color: #ffffff;
            line-height: 1.5;
            white-space: pre-wrap;
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            padding: 25px;
            animation: scrollText 20s linear infinite;
        }

        @keyframes scrollText {
            0% {
                transform: translateY(200px);
                opacity: 0;
            }
            10% {
                transform: translateY(0);
                opacity: 1;
            }
            90% {
                transform: translateY(0);
                opacity: 1;
            }
            100% {
                transform: translateY(-200px);
                opacity: 0;
            }
        }

        /* 装饰元素 */
        .decoration {
            position: absolute;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: -1;
        }

        .floating-element {
            position: absolute;
            width: 60px;
            height: 60px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 50%;
            animation: float 8s ease-in-out infinite;
        }

        .floating-element:nth-child(1) {
            top: 15%;
            left: 10%;
            animation-delay: 0s;
        }

        .floating-element:nth-child(2) {
            top: 25%;
            right: 15%;
            animation-delay: -2s;
        }

        .floating-element:nth-child(3) {
            bottom: 20%;
            left: 20%;
            animation-delay: -4s;
        }

        .floating-element:nth-child(4) {
            bottom: 30%;
            right: 10%;
            animation-delay: -6s;
        }

        @keyframes float {
            0%, 100% {
                transform: translateY(0) rotate(0deg);
            }
            50% {
                transform: translateY(-30px) rotate(180deg);
            }
        }

        /* 底部信息 */
        .footer {
            position: absolute;
            bottom: 30px;
            left: 0;
            width: 100%;
            text-align: center;
            color: rgba(255, 255, 255, 0.7);
            font-size: 20px;
            padding: 0 20px;
        }
    </style>
</head>
<body>
    <div class="decoration">
        <div class="floating-element"></div>
        <div class="floating-element"></div>
        <div class="floating-element"></div>
        <div class="floating-element"></div>
    </div>
    
    <div class="container">
        <div class="image-container">
            <img id="dynamicImage" class="circular-image" src="{{image_url}}" alt="动态图像">
        </div>
        
        <div class="title-container">
            <h1 class="scaling-title">{{title}}</h1>
        </div>
        
        <div class="text-container">
            <div class="scrolling-text">{{text}}</div>
        </div>
    </div>
    
    <div class="footer">
        <p>视频录制时间: {{current_time}} | 帧率: {{fps}}fps | 时长: {{duration}}秒</p>
    </div>
</body>
</html>""",
                    "multiline": True
                }),
                "duration_seconds": ("FLOAT", {
                    "default": 10.0,
                    "min": 3.0,
                    "max": 120.0,
                    "step": 0.5,
                    "tooltip": "视频总时长（秒）"
                }),
                "fps": ("INT", {
                    "default": 30,
                    "min": 1,
                    "max": 60,
                    "tooltip": "视频帧率"
                }),
                "output_width": ("INT", {
                    "default": 1080,
                    "min": 100,
                    "max": 3840,
                    "tooltip": "输出视频宽度"
                }),
                "output_height": ("INT", {
                    "default": 1920,
                    "min": 100,
                    "max": 2160,
                    "tooltip": "输出视频高度"
                }),
                "image_rotation_speed": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.1,
                    "max": 5.0,
                    "step": 0.1,
                    "tooltip": "图像旋转速度（1.0为正常速度）"
                }),
                "title_scale_speed": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.1,
                    "max": 5.0,
                    "step": 0.1,
                    "tooltip": "标题缩放动画速度"
                }),
                "text_scroll_speed": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.1,
                    "max": 5.0,
                    "step": 0.1,
                    "tooltip": "文本滚动速度"
                })
            },
            "optional": {
                "ext_json": ("STRING", {
                    "default": "{}",
                    "multiline": True,
                    "tooltip": "额外的JSON参数，用于模板替换"
                }),
                "animation_data": ("STRING", {
                    "default": "{}",
                    "multiline": True,
                    "tooltip": "自定义动画数据"
                }),
                "save_to_output": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "是否将视频保存到ComfyUI输出文件夹"
                }),
                "output_filename": ("STRING", {
                    "default": "html_video_output",
                    "multiline": False,
                    "tooltip": "输出文件名（不含扩展名）"
                })
            }
        }
    
    RETURN_TYPES = ("STRING", "INT", "STRING")
    RETURN_NAMES = ("video_path", "frames_count", "video_info_json")
    FUNCTION = "record_video"
    CATEGORY = "视频处理/录制"
    DESCRIPTION = "使用Playwright录制HTML动态效果视频，支持图像圆形剪裁旋转、标题缩放、文本滚动"
    
    def record_video(self, image: torch.Tensor, title: str, text: str, template_html: str,
                    duration_seconds: float, fps: int,
                    output_width: int, output_height: int,
                    image_rotation_speed: float = 1.0,
                    title_scale_speed: float = 1.0,
                    text_scroll_speed: float = 1.0,
                    ext_json: str = "{}", animation_data: str = "{}",
                    save_to_output: bool = True,
                    output_filename: str = "html_video_output") -> Tuple[str, int, str]:
        """
        使用Playwright录制HTML视频
        """
        try:
            # 创建临时目录
            temp_dir = tempfile.mkdtemp(prefix="comfyui_video_recorder_")
            
            # 处理输入图像：转换为圆形剪裁的Base64编码
            print("🖼️ 处理输入图像...")
            image_base64 = self._process_image_to_circle(image)
            
            # 解析扩展参数
            try:
                ext_params = json.loads(ext_json) if ext_json.strip() else {}
            except:
                ext_params = {}
            
            # 解析动画数据
            try:
                anim_data = json.loads(animation_data) if animation_data.strip() else {}
            except:
                anim_data = {}
            
            # 获取当前时间
            from datetime import datetime
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 构建HTML内容
            html_content = self._build_html_content(
                template_html, title, text, duration_seconds, fps,
                image_base64, current_time,
                image_rotation_speed, title_scale_speed, text_scroll_speed,
                ext_params, anim_data
            )
            
            # 保存HTML文件
            html_path = os.path.join(temp_dir, "content.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            # 修复：使用线程运行异步代码
            video_result = [None]  # 用于存储结果视频文件路径
            error_result = [None]  # 用于存储错误
            
            def run_async():
                try:
                    # 创建新的事件循环
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(self._record_with_playwright(
                        html_path=html_path,
                        temp_dir=temp_dir,
                        duration=duration_seconds,
                        width=output_width,
                        height=output_height
                    ))
                    video_result[0] = result
                    loop.close()
                except Exception as e:
                    error_result[0] = e
            
            # 在新线程中运行异步代码
            print("🎬 开始录制视频...")
            thread = threading.Thread(target=run_async)
            thread.start()
            thread.join()  # 等待线程完成
            
            # 检查是否有错误
            if error_result[0]:
                raise error_result[0]
            
            # 获取生成的视频文件路径
            video_path = video_result[0]
            
            if not video_path or not os.path.exists(video_path):
                # 如果没有找到视频文件，尝试在临时目录中查找.webm文件
                webm_files = [f for f in os.listdir(temp_dir) if f.endswith('.webm')]
                if webm_files:
                    video_path = os.path.join(temp_dir, webm_files[0])
                    print(f"✅ 找到视频文件: {video_path}")
                else:
                    raise FileNotFoundError(f"未找到视频文件在目录: {temp_dir}")
            
            # 转换为MP4格式
            mp4_path = os.path.join(temp_dir, "output.mp4")
            self._convert_to_mp4(video_path, mp4_path, fps)
            
            # 如果启用保存到输出文件夹
            final_video_path = mp4_path
            if save_to_output:
                try:
                    import folder_paths
                    # 获取ComfyUI输出目录
                    output_dir = folder_paths.get_output_directory()
                    
                    # 确保文件名唯一
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_filename = f"{output_filename}_{timestamp}.mp4"
                    final_video_path = os.path.join(output_dir, safe_filename)
                    
                    # 复制视频文件到输出目录
                    import shutil
                    shutil.copy2(mp4_path, final_video_path)
                    
                    print(f"💾 视频已保存到输出文件夹: {final_video_path}")
                except Exception as e:
                    print(f"⚠️ 无法保存到输出文件夹: {str(e)}")
                    print(f"📁 视频保存在临时位置: {mp4_path}")
            
            # 计算帧数
            frames_count = int(duration_seconds * fps)
            
            # 创建视频信息JSON
            video_info = {
                "video_path": final_video_path,
                "frames_count": frames_count,
                "fps": fps,
                "duration_seconds": duration_seconds,
                "width": output_width,
                "height": output_height,
                "title": title,
                "text_preview": text[:100] + "..." if len(text) > 100 else text,
                "timestamp": current_time,
                "image_rotation_speed": image_rotation_speed,
                "title_scale_speed": title_scale_speed,
                "text_scroll_speed": text_scroll_speed
            }
            video_info_json = json.dumps(video_info, ensure_ascii=False, indent=2)
            
            print(f"✅ 视频录制完成: {final_video_path}")
            print(f"📊 视频信息: {frames_count}帧, {fps}fps, {duration_seconds}秒")
            
            return (final_video_path, frames_count, video_info_json)
            
        except Exception as e:
            print(f"❌ 视频录制失败: {str(e)}")
            traceback.print_exc()
            return ("", 0, json.dumps({"error": str(e)}))
    
    def _process_image_to_circle(self, image_tensor: torch.Tensor) -> str:
        """将输入的图像张量转换为圆形剪裁的Base64编码"""
        try:
            # 确保图像张量的维度正确
            if len(image_tensor.shape) == 4:  # [B, H, W, C]
                # 取第一张图像
                image_tensor = image_tensor[0]
            
            # 转换为PIL图像
            image_np = image_tensor.cpu().numpy()
            
            # 确保值在0-1范围内
            if image_np.max() > 1.0:
                image_np = image_np / 255.0
            
            # 转换为0-255的uint8
            image_np = (image_np * 255).astype(np.uint8)
            
            # 转换为PIL图像
            if image_np.shape[2] == 4:  # RGBA
                image_pil = Image.fromarray(image_np, 'RGBA')
            elif image_np.shape[2] == 3:  # RGB
                image_pil = Image.fromarray(image_np, 'RGB')
            else:
                # 如果是单通道，转换为RGB
                if len(image_np.shape) == 2:
                    image_np = np.stack([image_np] * 3, axis=-1)
                image_pil = Image.fromarray(image_np, 'RGB')
            
            # 确保图像是正方形，进行中心剪裁
            width, height = image_pil.size
            min_dim = min(width, height)
            left = (width - min_dim) // 2
            top = (height - min_dim) // 2
            right = left + min_dim
            bottom = top + min_dim
            image_pil = image_pil.crop((left, top, right, bottom))
            
            # 调整大小到350x350（与CSS中的尺寸匹配）
            image_pil = image_pil.resize((350, 350), Image.Resampling.LANCZOS)
            
            # 创建圆形遮罩
            mask = Image.new('L', (350, 350), 0)
            mask_draw = Image.new('L', (350, 350), 0)
            draw = Image.new('RGBA', (350, 350), (0, 0, 0, 0))
            
            # 创建圆形遮罩
            from PIL import ImageDraw
            draw_mask = ImageDraw.Draw(mask)
            draw_mask.ellipse([(0, 0), (350, 350)], fill=255)
            
            # 应用圆形遮罩
            if image_pil.mode == 'RGBA':
                # 如果图像有alpha通道，我们需要合并
                image_rgba = image_pil
            else:
                # 转换为RGBA
                image_rgba = image_pil.convert('RGBA')
            
            # 应用圆形剪裁
            circular_image = Image.new('RGBA', (350, 350), (0, 0, 0, 0))
            circular_image.paste(image_rgba, (0, 0), mask)
            
            # 添加白色边框（可选，已在CSS中处理）
            # 转换为Base64
            buffered = io.BytesIO()
            circular_image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}"
            
        except Exception as e:
            print(f"⚠️ 图像处理失败: {str(e)}")
            # 返回一个默认的占位图像
            return "https://via.placeholder.com/350x350/667eea/ffffff?text=Image+Placeholder"
    
    def _build_html_content(self, template: str, title: str, text: str,
                           duration: float, fps: int,
                           image_base64: str, current_time: str,
                           rotation_speed: float, scale_speed: float, scroll_speed: float,
                           ext_params: Dict, anim_data: Dict) -> str:
        """构建HTML内容"""
        # 替换模板变量
        html = template
        html = html.replace("{{title}}", title)
        html = html.replace("{{text}}", text)
        html = html.replace("{{duration}}", str(duration))
        html = html.replace("{{fps}}", str(fps))
        html = html.replace("{{current_time}}", current_time)
        html = html.replace("{{image_url}}", image_base64)
        
        # 添加扩展参数
        for key, value in ext_params.items():
            placeholder = f"{{{{{key}}}}}"
            html = html.replace(placeholder, str(value))
        
        # 添加动画速度控制脚本
        animation_script = f"""
        <script>
            // 动画速度控制
            document.addEventListener('DOMContentLoaded', function() {{
                // 调整图像旋转速度
                const imageElement = document.querySelector('.circular-image');
                if (imageElement) {{
                    const currentAnimation = getComputedStyle(imageElement).animation;
                    const newAnimation = currentAnimation.replace(/\\d+s/, '{20/rotation_speed}s');
                    imageElement.style.animation = newAnimation;
                }}
                
                // 调整标题缩放速度
                const titleElement = document.querySelector('.scaling-title');
                if (titleElement) {{
                    const currentAnimation = getComputedStyle(titleElement).animation;
                    const newAnimation = currentAnimation.replace(/\\d+s/, '{3/scale_speed}s');
                    titleElement.style.animation = newAnimation;
                }}
                
                // 调整文本滚动速度
                const textElement = document.querySelector('.scrolling-text');
                if (textElement) {{
                    const currentAnimation = getComputedStyle(textElement).animation;
                    const newAnimation = currentAnimation.replace(/\\d+s/, '{20/scroll_speed}s');
                    textElement.style.animation = newAnimation;
                }}
                
                // 添加额外的动画数据
                {json.dumps(anim_data) if anim_data else 'window.customAnimationData = {};'}
            }});
        </script>
        """
        html = html.replace("</body>", f"{animation_script}</body>")
        
        return html
    
    async def _record_with_playwright(self, html_path: str, temp_dir: str,
                                     duration: float, width: int, height: int):
        """使用Playwright录制视频，返回生成的视频文件路径"""
        async with async_playwright() as p:
            # 启动浏览器
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--hide-scrollbars',
                    '--disable-web-security',  # 允许跨域资源加载
                ]
            )
            
            # 创建上下文，设置视频录制目录
            context = await browser.new_context(
                viewport={'width': width, 'height': height},
                record_video_dir=temp_dir,
                record_video_size={'width': width, 'height': height},
                ignore_https_errors=True  # 忽略HTTPS错误
            )
            
            # 创建页面
            page = await context.new_page()
            
            # 加载HTML文件
            await page.goto(f"file://{html_path}")
            
            # 等待页面加载完成和字体加载
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(1000)  # 额外等待1秒确保所有资源加载
            
            # 录制指定时长
            await asyncio.sleep(duration)
            
            # 获取视频文件路径
            video_path = None
            if page.video:
                video_path = await page.video.path()
            
            # 关闭上下文（这会触发视频保存）
            await context.close()
            await browser.close()
            
            # 等待一小段时间，确保文件已保存
            await asyncio.sleep(1.0)
            
            # 如果video_path为空，尝试在temp_dir中查找最新的.webm文件
            if not video_path or not os.path.exists(video_path):
                webm_files = []
                for file in os.listdir(temp_dir):
                    if file.endswith('.webm'):
                        file_path = os.path.join(temp_dir, file)
                        webm_files.append((file_path, os.path.getmtime(file_path)))
                
                if webm_files:
                    webm_files.sort(key=lambda x: x[1], reverse=True)
                    video_path = webm_files[0][0]
                    print(f"📹 找到录制的视频文件: {video_path}")
                else:
                    raise Exception(f"在目录中未找到录制的视频文件: {temp_dir}")
            
            return video_path
    
    def _convert_to_mp4(self, input_path: str, output_path: str, fps: int):
        """使用FFmpeg转换视频格式"""
        try:
            import subprocess
            
            if not os.path.exists(input_path):
                raise FileNotFoundError(f"输入视频文件不存在: {input_path}")
            
            print(f"🎬 开始转换视频: {input_path} -> {output_path}")
            
            cmd = [
                'ffmpeg', '-i', input_path,
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-r', str(fps),
                '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart',
                output_path,
                '-y'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"⚠️ FFmpeg错误输出: {result.stderr}")
                if os.path.exists(input_path):
                    import shutil
                    # 如果输入是webm，直接重命名为mp4
                    if input_path.endswith('.webm'):
                        shutil.copy2(input_path, output_path.replace('.mp4', '.webm'))
                        print(f"⚠️ 使用原始WebM文件: {output_path.replace('.mp4', '.webm')}")
                        output_path = output_path.replace('.mp4', '.webm')
                    else:
                        shutil.copy2(input_path, output_path)
                        print(f"⚠️ 直接复制视频文件: {output_path}")
                else:
                    raise Exception(f"FFmpeg转换失败: {result.stderr}")
            else:
                print(f"✅ 视频转换完成: {output_path}")
                
        except FileNotFoundError as e:
            print(f"❌ 文件未找到: {str(e)}")
            raise
        except Exception as e:
            print(f"⚠️ 视频格式转换失败: {str(e)}")
            import shutil
            if os.path.exists(input_path):
                webm_output_path = output_path.replace('.mp4', '.webm')
                shutil.copy2(input_path, webm_output_path)
                print(f"⚠️ 使用原始WebM文件: {webm_output_path}")
                output_path = webm_output_path
            else:
                raise Exception(f"视频转换失败且原始文件不存在: {input_path}")


# 视频保存节点（与comfyui-videohelpersuite兼容）
class VideoSaveNode:
    """
    视频保存节点：将视频文件保存到ComfyUI输出文件夹
    与comfyui-videohelpersuite的video combine节点兼容
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video_path": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "tooltip": "输入视频文件路径"
                }),
                "output_filename": ("STRING", {
                    "default": "video_output",
                    "multiline": False,
                    "tooltip": "输出文件名（不含扩展名）"
                })
            },
            "optional": {
                "video_info_json": ("STRING", {
                    "default": "{}",
                    "multiline": True,
                    "tooltip": "视频信息JSON"
                })
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("saved_video_path", "video_info_json")
    FUNCTION = "save_video"
    CATEGORY = "视频处理/保存"
    DESCRIPTION = "保存视频文件到ComfyUI输出文件夹"
    
    def save_video(self, video_path: str, output_filename: str, 
                  video_info_json: str = "{}") -> Tuple[str, str]:
        """
        保存视频文件到输出文件夹
        """
        try:
            if not video_path or not os.path.exists(video_path):
                print(f"❌ 视频文件不存在: {video_path}")
                return ("", video_info_json)
            
            # 导入ComfyUI的文件夹路径模块
            import folder_paths
            from datetime import datetime
            
            # 获取输出目录
            output_dir = folder_paths.get_output_directory()
            
            # 确保文件名唯一
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 获取文件扩展名
            _, ext = os.path.splitext(video_path)
            if not ext:
                ext = ".mp4"
            
            # 清理文件名
            safe_filename = output_filename.strip()
            if not safe_filename:
                safe_filename = "video_output"
            
            # 构建最终路径
            final_filename = f"{safe_filename}_{timestamp}{ext}"
            final_path = os.path.join(output_dir, final_filename)
            
            # 复制视频文件
            import shutil
            shutil.copy2(video_path, final_path)
            
            print(f"💾 视频已保存到: {final_path}")
            
            # 更新视频信息
            try:
                video_info = json.loads(video_info_json) if video_info_json.strip() else {}
            except:
                video_info = {}
            
            video_info["saved_path"] = final_path
            video_info["saved_timestamp"] = timestamp
            updated_info_json = json.dumps(video_info, ensure_ascii=False, indent=2)
            
            return (final_path, updated_info_json)
            
        except Exception as e:
            print(f"❌ 保存视频失败: {str(e)}")
            traceback.print_exc()
            return ("", video_info_json)


# 节点注册
NODE_CLASS_MAPPINGS = {
    "HTMLVideoRecorderPlaywright": HTMLVideoRecorderPlaywright,
    "VideoSaveNode": VideoSaveNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "HTMLVideoRecorderPlaywright": "HTML视频录制器（增强版）",
    "VideoSaveNode": "视频保存节点"
}

# 如果存在HTMLFrameRenderer，保持兼容性
try:
    from .html_frame_renderer import HTMLFrameRenderer
    NODE_CLASS_MAPPINGS["HTMLFrameRenderer"] = HTMLFrameRenderer
    NODE_DISPLAY_NAME_MAPPINGS["HTMLFrameRenderer"] = "HTML帧渲染器（截图修复版）"
except:
    pass
