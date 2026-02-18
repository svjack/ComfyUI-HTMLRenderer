from .html_renderer import HTMLFrameRenderer

NODE_CLASS_MAPPINGS = {
    "HTMLFrameRenderer": HTMLFrameRenderer
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "HTMLFrameRenderer": "HTML Frame Renderer"
}

WEB_DIRECTORY = "./js"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
