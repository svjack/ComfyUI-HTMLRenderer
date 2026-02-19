from .html_renderer import *

NODE_CLASS_MAPPINGS = {
    "HTMLFrameRenderer": HTMLFrameRenderer,
    "HTMLVideoRecorderPlaywright": HTMLVideoRecorderPlaywright
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "HTMLFrameRenderer": "HTML Frame Renderer",
    "HTMLVideoRecorderPlaywright": "HTML视频录制器（Playwright版）"
}

WEB_DIRECTORY = "./js"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
