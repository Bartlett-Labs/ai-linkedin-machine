"""
Image Optimizer - Core optimization module.

Provides intelligent image resizing with aspect ratio preservation,
quality optimization, and support for multiple output formats.
"""

import os
from pathlib import Path
from typing import Optional, Tuple, List, Union, Dict, Any
from dataclasses import dataclass
from enum import Enum

try:
    from PIL import Image, ImageOps, ImageFilter, ImageEnhance
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

from .strategies import (
    ResizeStrategy,
    calculate_fit_dimensions,
    calculate_fill_dimensions,
    calculate_crop_box,
    calculate_padding,
    get_anchor_from_strategy,
)
from .presets import get_preset, SIZE_PRESETS


class OutputFormat(Enum):
    """Supported output formats."""
    PNG = "png"
    JPEG = "jpeg"
    WEBP = "webp"
    ICO = "ico"
    BMP = "bmp"
    TIFF = "tiff"


@dataclass
class OptimizationResult:
    """Result of an image optimization operation."""
    success: bool
    output_path: Optional[str]
    original_size: Tuple[int, int]
    new_size: Tuple[int, int]
    original_file_size: int
    new_file_size: int
    format: str
    strategy_used: str
    message: str = ""

    @property
    def size_reduction_percent(self) -> float:
        """Calculate file size reduction percentage."""
        if self.original_file_size == 0:
            return 0.0
        return ((self.original_file_size - self.new_file_size) /
                self.original_file_size) * 100


class ImageOptimizer:
    """
    Main image optimizer class.

    Provides methods to resize images intelligently while preserving
    quality and aspect ratio.
    """

    # Resampling filter for high-quality resizing
    RESAMPLE_FILTER = Image.Resampling.LANCZOS if PILLOW_AVAILABLE else None

    def __init__(
        self,
        default_quality: int = 95,
        default_format: OutputFormat = OutputFormat.PNG,
        default_strategy: ResizeStrategy = ResizeStrategy.CROP_CENTER,
        optimize: bool = True,
        preserve_exif: bool = False,
    ):
        """
        Initialize the optimizer.

        Args:
            default_quality: Default JPEG/WebP quality (1-100)
            default_format: Default output format
            default_strategy: Default resize strategy
            optimize: Whether to optimize output file size
            preserve_exif: Whether to preserve EXIF metadata
        """
        if not PILLOW_AVAILABLE:
            raise ImportError(
                "Pillow is required. Install with: pip install Pillow"
            )

        self.default_quality = default_quality
        self.default_format = default_format
        self.default_strategy = default_strategy
        self.optimize = optimize
        self.preserve_exif = preserve_exif

    def load_image(self, image_path: Union[str, Path]) -> Image.Image:
        """
        Load an image from disk.

        Args:
            image_path: Path to the image file

        Returns:
            PIL Image object

        Raises:
            FileNotFoundError: If image doesn't exist
            ValueError: If file is not a valid image
        """
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")

        try:
            img = Image.open(path)
            # Load the image data into memory
            img.load()
            return img
        except Exception as e:
            raise ValueError(f"Failed to load image: {e}")

    def resize(
        self,
        image: Image.Image,
        target_width: int,
        target_height: int,
        strategy: Optional[ResizeStrategy] = None,
        background_color: Tuple[int, int, int, int] = (255, 255, 255, 0),
    ) -> Image.Image:
        """
        Resize an image using the specified strategy.

        Args:
            image: PIL Image to resize
            target_width: Target width in pixels
            target_height: Target height in pixels
            strategy: Resize strategy to use
            background_color: RGBA color for padding (if applicable)

        Returns:
            Resized PIL Image
        """
        strategy = strategy or self.default_strategy
        source_width, source_height = image.size

        # Handle different color modes
        if image.mode not in ('RGB', 'RGBA'):
            if image.mode == 'P' and 'transparency' in image.info:
                image = image.convert('RGBA')
            elif image.mode in ('L', 'LA', 'P'):
                image = image.convert('RGBA' if image.mode == 'LA' else 'RGB')
            else:
                image = image.convert('RGB')

        if strategy == ResizeStrategy.STRETCH:
            # Direct resize - may distort
            return image.resize(
                (target_width, target_height),
                resample=self.RESAMPLE_FILTER
            )

        elif strategy == ResizeStrategy.FIT:
            # Fit within dimensions, no cropping
            new_width, new_height = calculate_fit_dimensions(
                source_width, source_height, target_width, target_height
            )
            return image.resize(
                (new_width, new_height),
                resample=self.RESAMPLE_FILTER
            )

        elif strategy == ResizeStrategy.THUMBNAIL:
            # Create thumbnail (modifies in place, so copy first)
            img_copy = image.copy()
            img_copy.thumbnail(
                (target_width, target_height),
                resample=self.RESAMPLE_FILTER
            )
            return img_copy

        elif strategy == ResizeStrategy.PAD:
            # Fit and pad to exact dimensions
            fit_width, fit_height = calculate_fit_dimensions(
                source_width, source_height, target_width, target_height
            )
            resized = image.resize(
                (fit_width, fit_height),
                resample=self.RESAMPLE_FILTER
            )

            # Create padded canvas
            if image.mode == 'RGBA':
                canvas = Image.new('RGBA', (target_width, target_height), background_color)
            else:
                canvas = Image.new('RGB', (target_width, target_height), background_color[:3])

            # Calculate position to paste
            left = (target_width - fit_width) // 2
            top = (target_height - fit_height) // 2

            if image.mode == 'RGBA':
                canvas.paste(resized, (left, top), resized)
            else:
                canvas.paste(resized, (left, top))

            return canvas

        elif strategy == ResizeStrategy.FILL:
            # Fill dimensions completely, crop excess
            fill_width, fill_height = calculate_fill_dimensions(
                source_width, source_height, target_width, target_height
            )
            resized = image.resize(
                (fill_width, fill_height),
                resample=self.RESAMPLE_FILTER
            )

            # Center crop to target
            left = (fill_width - target_width) // 2
            top = (fill_height - target_height) // 2
            return resized.crop((left, top, left + target_width, top + target_height))

        elif strategy in (
            ResizeStrategy.CROP_CENTER,
            ResizeStrategy.CROP_TOP,
            ResizeStrategy.CROP_BOTTOM,
            ResizeStrategy.CROP_LEFT,
            ResizeStrategy.CROP_RIGHT,
        ):
            # Crop to aspect ratio first, then resize
            anchor = get_anchor_from_strategy(strategy)
            crop_box = calculate_crop_box(
                source_width, source_height,
                target_width, target_height,
                anchor
            )
            cropped = image.crop(crop_box)
            return cropped.resize(
                (target_width, target_height),
                resample=self.RESAMPLE_FILTER
            )

        elif strategy == ResizeStrategy.CROP_SMART:
            # Smart crop - fall back to center crop
            # Could integrate face detection here in future
            return self.resize(
                image, target_width, target_height,
                ResizeStrategy.CROP_CENTER, background_color
            )

        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def optimize_for_preset(
        self,
        image_path: Union[str, Path],
        platform: str,
        preset_name: str,
        output_path: Optional[Union[str, Path]] = None,
        strategy: Optional[ResizeStrategy] = None,
        output_format: Optional[OutputFormat] = None,
        quality: Optional[int] = None,
    ) -> OptimizationResult:
        """
        Optimize an image for a specific platform preset.

        Args:
            image_path: Path to source image
            platform: Platform name (e.g., 'ios', 'linkedin')
            preset_name: Preset name (e.g., 'app_logo', 'icon_1024')
            output_path: Optional output path (auto-generated if not provided)
            strategy: Resize strategy
            output_format: Output format
            quality: Output quality (1-100)

        Returns:
            OptimizationResult with details of the operation
        """
        size = get_preset(platform, preset_name)
        if not size:
            return OptimizationResult(
                success=False,
                output_path=None,
                original_size=(0, 0),
                new_size=(0, 0),
                original_file_size=0,
                new_file_size=0,
                format="",
                strategy_used="",
                message=f"Unknown preset: {platform}/{preset_name}"
            )

        target_width, target_height = size

        # Generate output path if not provided
        if output_path is None:
            input_path = Path(image_path)
            fmt = output_format or self.default_format
            suffix = f".{fmt.value}"
            output_path = input_path.parent / f"{input_path.stem}_{platform}_{preset_name}{suffix}"

        return self.optimize_image(
            image_path=image_path,
            target_width=target_width,
            target_height=target_height,
            output_path=output_path,
            strategy=strategy,
            output_format=output_format,
            quality=quality,
        )

    def optimize_image(
        self,
        image_path: Union[str, Path],
        target_width: int,
        target_height: int,
        output_path: Optional[Union[str, Path]] = None,
        strategy: Optional[ResizeStrategy] = None,
        output_format: Optional[OutputFormat] = None,
        quality: Optional[int] = None,
        background_color: Tuple[int, int, int, int] = (255, 255, 255, 0),
    ) -> OptimizationResult:
        """
        Optimize an image to target dimensions.

        Args:
            image_path: Path to source image
            target_width: Target width in pixels
            target_height: Target height in pixels
            output_path: Output file path
            strategy: Resize strategy to use
            output_format: Output format
            quality: Output quality (1-100)
            background_color: Background color for padding

        Returns:
            OptimizationResult with details of the operation
        """
        image_path = Path(image_path)
        original_size_bytes = image_path.stat().st_size if image_path.exists() else 0

        try:
            image = self.load_image(image_path)
            original_dimensions = image.size

            # Resize using strategy
            strategy = strategy or self.default_strategy
            resized = self.resize(
                image, target_width, target_height, strategy, background_color
            )

            # Determine output format
            fmt = output_format or self.default_format
            quality = quality or self.default_quality

            # Generate output path if not provided
            if output_path is None:
                suffix = f".{fmt.value}"
                output_path = image_path.parent / f"{image_path.stem}_optimized{suffix}"
            else:
                output_path = Path(output_path)

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Save with appropriate options
            save_kwargs = self._get_save_options(fmt, quality, resized, image)

            resized.save(str(output_path), **save_kwargs)

            new_size_bytes = output_path.stat().st_size

            return OptimizationResult(
                success=True,
                output_path=str(output_path),
                original_size=original_dimensions,
                new_size=resized.size,
                original_file_size=original_size_bytes,
                new_file_size=new_size_bytes,
                format=fmt.value,
                strategy_used=strategy.value,
                message="Image optimized successfully"
            )

        except Exception as e:
            return OptimizationResult(
                success=False,
                output_path=None,
                original_size=(0, 0),
                new_size=(0, 0),
                original_file_size=original_size_bytes,
                new_file_size=0,
                format="",
                strategy_used="",
                message=f"Optimization failed: {str(e)}"
            )

    def _get_save_options(
        self,
        fmt: OutputFormat,
        quality: int,
        resized_image: Image.Image,
        original_image: Image.Image,
    ) -> Dict[str, Any]:
        """Get save options based on format."""
        options: Dict[str, Any] = {}

        if fmt == OutputFormat.JPEG:
            options['format'] = 'JPEG'
            options['quality'] = quality
            options['optimize'] = self.optimize
            # Convert RGBA to RGB for JPEG
            if resized_image.mode == 'RGBA':
                background = Image.new('RGB', resized_image.size, (255, 255, 255))
                background.paste(resized_image, mask=resized_image.split()[3])
                resized_image = background

        elif fmt == OutputFormat.PNG:
            options['format'] = 'PNG'
            options['optimize'] = self.optimize

        elif fmt == OutputFormat.WEBP:
            options['format'] = 'WEBP'
            options['quality'] = quality
            options['method'] = 6  # Best compression

        elif fmt == OutputFormat.ICO:
            options['format'] = 'ICO'

        elif fmt == OutputFormat.BMP:
            options['format'] = 'BMP'

        elif fmt == OutputFormat.TIFF:
            options['format'] = 'TIFF'
            options['compression'] = 'tiff_lzw'

        # Preserve EXIF if requested
        if self.preserve_exif and hasattr(original_image, 'info'):
            if 'exif' in original_image.info:
                options['exif'] = original_image.info['exif']

        return options

    def batch_optimize(
        self,
        image_path: Union[str, Path],
        presets: List[Tuple[str, str]],
        output_dir: Optional[Union[str, Path]] = None,
        strategy: Optional[ResizeStrategy] = None,
        output_format: Optional[OutputFormat] = None,
        quality: Optional[int] = None,
    ) -> List[OptimizationResult]:
        """
        Optimize an image for multiple presets at once.

        Args:
            image_path: Path to source image
            presets: List of (platform, preset_name) tuples
            output_dir: Directory for output files
            strategy: Resize strategy
            output_format: Output format
            quality: Output quality

        Returns:
            List of OptimizationResult for each preset
        """
        results = []
        image_path = Path(image_path)

        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        for platform, preset_name in presets:
            if output_dir:
                fmt = output_format or self.default_format
                output_path = output_dir / f"{platform}_{preset_name}.{fmt.value}"
            else:
                output_path = None

            result = self.optimize_for_preset(
                image_path=image_path,
                platform=platform,
                preset_name=preset_name,
                output_path=output_path,
                strategy=strategy,
                output_format=output_format,
                quality=quality,
            )
            results.append(result)

        return results

    def generate_all_ios_icons(
        self,
        image_path: Union[str, Path],
        output_dir: Union[str, Path],
        strategy: Optional[ResizeStrategy] = None,
    ) -> List[OptimizationResult]:
        """
        Generate all iOS app icon sizes from a source image.

        Args:
            image_path: Path to source image (should be at least 1024x1024)
            output_dir: Directory for output icons
            strategy: Resize strategy

        Returns:
            List of OptimizationResult for each icon size
        """
        presets = [("ios", name) for name in SIZE_PRESETS["ios"].keys()]
        return self.batch_optimize(
            image_path=image_path,
            presets=presets,
            output_dir=output_dir,
            strategy=strategy or ResizeStrategy.CROP_CENTER,
            output_format=OutputFormat.PNG,
        )

    def generate_all_android_icons(
        self,
        image_path: Union[str, Path],
        output_dir: Union[str, Path],
        strategy: Optional[ResizeStrategy] = None,
    ) -> List[OptimizationResult]:
        """
        Generate all Android app icon sizes from a source image.

        Args:
            image_path: Path to source image (should be at least 512x512)
            output_dir: Directory for output icons
            strategy: Resize strategy

        Returns:
            List of OptimizationResult for each icon size
        """
        presets = [("android", name) for name in SIZE_PRESETS["android"].keys()]
        return self.batch_optimize(
            image_path=image_path,
            presets=presets,
            output_dir=output_dir,
            strategy=strategy or ResizeStrategy.CROP_CENTER,
            output_format=OutputFormat.PNG,
        )

    def generate_social_profile_images(
        self,
        image_path: Union[str, Path],
        output_dir: Union[str, Path],
        platforms: Optional[List[str]] = None,
        strategy: Optional[ResizeStrategy] = None,
    ) -> List[OptimizationResult]:
        """
        Generate profile images for social media platforms.

        Args:
            image_path: Path to source image
            output_dir: Directory for output images
            platforms: List of platforms (default: all)
            strategy: Resize strategy

        Returns:
            List of OptimizationResult
        """
        if platforms is None:
            platforms = ["linkedin", "twitter", "facebook", "instagram"]

        presets = []
        for platform in platforms:
            if platform in SIZE_PRESETS and "profile_photo" in SIZE_PRESETS[platform]:
                presets.append((platform, "profile_photo"))

        return self.batch_optimize(
            image_path=image_path,
            presets=presets,
            output_dir=output_dir,
            strategy=strategy or ResizeStrategy.CROP_CENTER,
            output_format=OutputFormat.PNG,
        )

    def apply_sharpening(
        self,
        image: Image.Image,
        amount: float = 1.0
    ) -> Image.Image:
        """
        Apply sharpening to counteract blur from resizing.

        Args:
            image: PIL Image
            amount: Sharpening amount (0.0 to 2.0, 1.0 = normal)

        Returns:
            Sharpened image
        """
        enhancer = ImageEnhance.Sharpness(image)
        return enhancer.enhance(1.0 + amount * 0.5)

    def get_image_info(self, image_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Get information about an image.

        Args:
            image_path: Path to image

        Returns:
            Dictionary with image information
        """
        path = Path(image_path)
        image = self.load_image(path)

        return {
            "path": str(path),
            "filename": path.name,
            "format": image.format,
            "mode": image.mode,
            "size": image.size,
            "width": image.size[0],
            "height": image.size[1],
            "aspect_ratio": round(image.size[0] / image.size[1], 3),
            "file_size_bytes": path.stat().st_size,
            "file_size_kb": round(path.stat().st_size / 1024, 2),
            "has_alpha": image.mode in ('RGBA', 'LA', 'PA'),
        }
