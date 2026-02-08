# Image Optimizer Tool
# Properly resizes images for various app uses with minimal quality loss

from .optimizer import ImageOptimizer, OutputFormat, OptimizationResult
from .presets import SIZE_PRESETS, get_preset, list_presets
from .strategies import ResizeStrategy

__all__ = [
    'ImageOptimizer',
    'OutputFormat',
    'OptimizationResult',
    'SIZE_PRESETS',
    'get_preset',
    'list_presets',
    'ResizeStrategy',
]
__version__ = '1.0.0'


def launch_gui():
    """Launch the graphical user interface."""
    from .gui import main
    return main()
