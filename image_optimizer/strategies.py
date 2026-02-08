"""
Resize strategies for image optimization.

These strategies determine how images are resized to fit target dimensions
while handling aspect ratio differences intelligently.
"""

from enum import Enum
from typing import Tuple


class ResizeStrategy(Enum):
    """
    Available strategies for resizing images to target dimensions.

    Each strategy handles aspect ratio differences differently:

    FIT: Resize to fit entirely within target, may have letterboxing/pillarboxing
    FILL: Resize to fill target completely, may crop edges
    CROP_CENTER: Crop from center to match aspect ratio, then resize
    CROP_TOP: Crop from top (keep top), useful for portraits
    CROP_BOTTOM: Crop from bottom (keep bottom)
    CROP_LEFT: Crop from left (keep left side)
    CROP_RIGHT: Crop from right (keep right side)
    CROP_SMART: Use face/content detection to find best crop (requires additional deps)
    STRETCH: Stretch to exact dimensions (may distort - NOT RECOMMENDED)
    PAD: Fit within target and pad with background color
    THUMBNAIL: Create a thumbnail that fits within dimensions
    """

    FIT = "fit"
    FILL = "fill"
    CROP_CENTER = "crop_center"
    CROP_TOP = "crop_top"
    CROP_BOTTOM = "crop_bottom"
    CROP_LEFT = "crop_left"
    CROP_RIGHT = "crop_right"
    CROP_SMART = "crop_smart"
    STRETCH = "stretch"
    PAD = "pad"
    THUMBNAIL = "thumbnail"


def calculate_fit_dimensions(
    source_width: int,
    source_height: int,
    target_width: int,
    target_height: int
) -> Tuple[int, int]:
    """
    Calculate dimensions to fit image within target while preserving aspect ratio.

    The image will be scaled down (or up) to fit entirely within the target
    dimensions. The resulting image will have the same aspect ratio as the source.

    Args:
        source_width: Original image width
        source_height: Original image height
        target_width: Target container width
        target_height: Target container height

    Returns:
        Tuple of (new_width, new_height)
    """
    source_ratio = source_width / source_height
    target_ratio = target_width / target_height

    if source_ratio > target_ratio:
        # Source is wider than target - constrain by width
        new_width = target_width
        new_height = int(target_width / source_ratio)
    else:
        # Source is taller than target - constrain by height
        new_height = target_height
        new_width = int(target_height * source_ratio)

    return (new_width, new_height)


def calculate_fill_dimensions(
    source_width: int,
    source_height: int,
    target_width: int,
    target_height: int
) -> Tuple[int, int]:
    """
    Calculate dimensions to fill target completely while preserving aspect ratio.

    The image will be scaled to completely fill the target dimensions.
    Some parts of the image will be cropped.

    Args:
        source_width: Original image width
        source_height: Original image height
        target_width: Target container width
        target_height: Target container height

    Returns:
        Tuple of (new_width, new_height)
    """
    source_ratio = source_width / source_height
    target_ratio = target_width / target_height

    if source_ratio > target_ratio:
        # Source is wider - constrain by height, crop width
        new_height = target_height
        new_width = int(target_height * source_ratio)
    else:
        # Source is taller - constrain by width, crop height
        new_width = target_width
        new_height = int(target_width / source_ratio)

    return (new_width, new_height)


def calculate_crop_box(
    source_width: int,
    source_height: int,
    target_width: int,
    target_height: int,
    anchor: str = "center"
) -> Tuple[int, int, int, int]:
    """
    Calculate the crop box to achieve target aspect ratio.

    Args:
        source_width: Original image width
        source_height: Original image height
        target_width: Target width (for aspect ratio calculation)
        target_height: Target height (for aspect ratio calculation)
        anchor: Where to anchor the crop ('center', 'top', 'bottom', 'left', 'right')

    Returns:
        Tuple of (left, top, right, bottom) defining the crop box
    """
    source_ratio = source_width / source_height
    target_ratio = target_width / target_height

    if abs(source_ratio - target_ratio) < 0.01:
        # Aspect ratios are close enough - no cropping needed
        return (0, 0, source_width, source_height)

    if source_ratio > target_ratio:
        # Source is wider - crop width
        new_width = int(source_height * target_ratio)
        new_height = source_height

        if anchor == "left":
            left = 0
        elif anchor == "right":
            left = source_width - new_width
        else:  # center
            left = (source_width - new_width) // 2

        return (left, 0, left + new_width, source_height)
    else:
        # Source is taller - crop height
        new_width = source_width
        new_height = int(source_width / target_ratio)

        if anchor == "top":
            top = 0
        elif anchor == "bottom":
            top = source_height - new_height
        else:  # center
            top = (source_height - new_height) // 2

        return (0, top, source_width, top + new_height)


def calculate_padding(
    image_width: int,
    image_height: int,
    target_width: int,
    target_height: int,
    position: str = "center"
) -> Tuple[int, int, int, int]:
    """
    Calculate padding needed to center image in target dimensions.

    Args:
        image_width: Fitted image width
        image_height: Fitted image height
        target_width: Target canvas width
        target_height: Target canvas height
        position: Position of image ('center', 'top-left', 'top-right', etc.)

    Returns:
        Tuple of (left_pad, top_pad, right_pad, bottom_pad)
    """
    total_h_pad = target_width - image_width
    total_v_pad = target_height - image_height

    if position == "center":
        left = total_h_pad // 2
        top = total_v_pad // 2
    elif position == "top-left":
        left = 0
        top = 0
    elif position == "top-right":
        left = total_h_pad
        top = 0
    elif position == "bottom-left":
        left = 0
        top = total_v_pad
    elif position == "bottom-right":
        left = total_h_pad
        top = total_v_pad
    elif position == "top":
        left = total_h_pad // 2
        top = 0
    elif position == "bottom":
        left = total_h_pad // 2
        top = total_v_pad
    elif position == "left":
        left = 0
        top = total_v_pad // 2
    elif position == "right":
        left = total_h_pad
        top = total_v_pad // 2
    else:
        left = total_h_pad // 2
        top = total_v_pad // 2

    right = total_h_pad - left
    bottom = total_v_pad - top

    return (left, top, right, bottom)


def get_anchor_from_strategy(strategy: ResizeStrategy) -> str:
    """
    Get the anchor point string from a strategy enum.

    Args:
        strategy: The resize strategy

    Returns:
        Anchor string for crop calculations
    """
    mapping = {
        ResizeStrategy.CROP_CENTER: "center",
        ResizeStrategy.CROP_TOP: "top",
        ResizeStrategy.CROP_BOTTOM: "bottom",
        ResizeStrategy.CROP_LEFT: "left",
        ResizeStrategy.CROP_RIGHT: "right",
    }
    return mapping.get(strategy, "center")
