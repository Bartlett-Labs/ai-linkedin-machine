#!/usr/bin/env python3
"""
Image Optimizer CLI - Command-line interface for the image optimizer tool.

Usage:
    python -m image_optimizer <image_path> --size <width>x<height> [options]
    python -m image_optimizer <image_path> --preset <platform>/<preset_name> [options]
    python -m image_optimizer <image_path> --ios-icons --output-dir ./icons
    python -m image_optimizer --list-presets

Examples:
    # Resize to specific dimensions
    python -m image_optimizer logo.png --size 180x180 -o logo_resized.png

    # Use a platform preset
    python -m image_optimizer logo.png --preset linkedin/app_logo

    # Generate all iOS icons
    python -m image_optimizer app_icon.png --ios-icons --output-dir ./ios_icons

    # Generate LinkedIn profile + post images
    python -m image_optimizer photo.jpg --preset linkedin/profile_photo --preset linkedin/post_image
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from .optimizer import ImageOptimizer, OutputFormat, OptimizationResult
from .strategies import ResizeStrategy
from .presets import SIZE_PRESETS, list_presets


def parse_size(size_str: str) -> tuple:
    """Parse size string like '180x180' into (width, height) tuple."""
    try:
        parts = size_str.lower().replace('x', ',').split(',')
        if len(parts) != 2:
            raise ValueError()
        return (int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        raise argparse.ArgumentTypeError(
            f"Invalid size format: '{size_str}'. Use format: WIDTHxHEIGHT (e.g., 180x180)"
        )


def parse_preset(preset_str: str) -> tuple:
    """Parse preset string like 'linkedin/app_logo' into (platform, preset_name) tuple."""
    try:
        parts = preset_str.split('/')
        if len(parts) != 2:
            raise ValueError()
        platform, preset_name = parts
        if platform not in SIZE_PRESETS:
            raise ValueError(f"Unknown platform: {platform}")
        if preset_name not in SIZE_PRESETS[platform]:
            raise ValueError(f"Unknown preset: {preset_name} for platform {platform}")
        return (platform, preset_name)
    except ValueError as e:
        if str(e):
            raise argparse.ArgumentTypeError(str(e))
        raise argparse.ArgumentTypeError(
            f"Invalid preset format: '{preset_str}'. Use format: platform/preset_name (e.g., linkedin/app_logo)"
        )


def parse_strategy(strategy_str: str) -> ResizeStrategy:
    """Parse strategy string into ResizeStrategy enum."""
    try:
        return ResizeStrategy(strategy_str.lower())
    except ValueError:
        valid = [s.value for s in ResizeStrategy]
        raise argparse.ArgumentTypeError(
            f"Invalid strategy: '{strategy_str}'. Valid options: {', '.join(valid)}"
        )


def parse_format(format_str: str) -> OutputFormat:
    """Parse format string into OutputFormat enum."""
    try:
        return OutputFormat(format_str.lower())
    except ValueError:
        valid = [f.value for f in OutputFormat]
        raise argparse.ArgumentTypeError(
            f"Invalid format: '{format_str}'. Valid options: {', '.join(valid)}"
        )


def print_presets():
    """Print all available presets in a formatted way."""
    print("\nAvailable Image Size Presets")
    print("=" * 60)

    for platform, presets in SIZE_PRESETS.items():
        print(f"\n{platform.upper()}")
        print("-" * 40)
        for name, (width, height) in sorted(presets.items()):
            aspect = f"{width/height:.2f}" if height > 0 else "N/A"
            print(f"  {name:25} {width:4} x {height:4}  (ratio: {aspect})")

    print("\nUsage examples:")
    print("  --preset linkedin/app_logo")
    print("  --preset ios/icon_1024")
    print("  --preset twitter/profile_photo")


def print_result(result: OptimizationResult, verbose: bool = False):
    """Print optimization result."""
    if result.success:
        print(f"  [OK] {result.output_path}")
        if verbose:
            print(f"       Original: {result.original_size[0]}x{result.original_size[1]} ({result.original_file_size/1024:.1f} KB)")
            print(f"       New:      {result.new_size[0]}x{result.new_size[1]} ({result.new_file_size/1024:.1f} KB)")
            if result.size_reduction_percent > 0:
                print(f"       Size reduction: {result.size_reduction_percent:.1f}%")
    else:
        print(f"  [FAIL] {result.message}")


def main(argv: Optional[List[str]] = None):
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog='image-optimizer',
        description='Optimize and resize images for various app platforms with intelligent aspect ratio handling.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Resize to specific dimensions with center crop
  %(prog)s logo.png --size 180x180 -o logo_linkedin.png

  # Use a platform preset
  %(prog)s logo.png --preset linkedin/app_logo

  # Generate all iOS app icons
  %(prog)s app_icon.png --ios-icons --output-dir ./ios_icons

  # Generate all Android icons
  %(prog)s app_icon.png --android-icons --output-dir ./android_icons

  # Use fit strategy (letterbox) instead of crop
  %(prog)s photo.jpg --size 1200x627 --strategy fit --bg-color white

  # High quality JPEG output
  %(prog)s photo.png --size 800x800 --format jpeg --quality 95

  # List all available presets
  %(prog)s --list-presets
        """
    )

    # Positional argument
    parser.add_argument(
        'image',
        nargs='?',
        help='Path to the source image file'
    )

    # Size options
    size_group = parser.add_argument_group('Size Options')
    size_group.add_argument(
        '-s', '--size',
        type=parse_size,
        help='Target size as WIDTHxHEIGHT (e.g., 180x180)'
    )
    size_group.add_argument(
        '-p', '--preset',
        type=parse_preset,
        action='append',
        dest='presets',
        metavar='PLATFORM/PRESET',
        help='Use a platform preset (e.g., linkedin/app_logo). Can be used multiple times.'
    )

    # Batch generation options
    batch_group = parser.add_argument_group('Batch Generation')
    batch_group.add_argument(
        '--ios-icons',
        action='store_true',
        help='Generate all iOS app icon sizes'
    )
    batch_group.add_argument(
        '--android-icons',
        action='store_true',
        help='Generate all Android app icon sizes'
    )
    batch_group.add_argument(
        '--social-profiles',
        action='store_true',
        help='Generate profile images for all social platforms'
    )
    batch_group.add_argument(
        '--favicons',
        action='store_true',
        help='Generate all favicon sizes for web'
    )

    # Output options
    output_group = parser.add_argument_group('Output Options')
    output_group.add_argument(
        '-o', '--output',
        type=Path,
        help='Output file path (for single image operations)'
    )
    output_group.add_argument(
        '-d', '--output-dir',
        type=Path,
        help='Output directory (for batch operations)'
    )
    output_group.add_argument(
        '-f', '--format',
        type=parse_format,
        help='Output format: png, jpeg, webp, ico, bmp, tiff'
    )
    output_group.add_argument(
        '-q', '--quality',
        type=int,
        choices=range(1, 101),
        metavar='1-100',
        default=95,
        help='Output quality for JPEG/WebP (default: 95)'
    )

    # Resize strategy options
    strategy_group = parser.add_argument_group('Resize Strategy')
    strategy_group.add_argument(
        '--strategy',
        type=parse_strategy,
        default=ResizeStrategy.CROP_CENTER,
        help='''Resize strategy:
  crop_center - Crop from center (default)
  crop_top    - Crop keeping top
  crop_bottom - Crop keeping bottom
  fit         - Fit within dimensions (may letterbox)
  fill        - Fill dimensions completely
  pad         - Fit and pad with background
  stretch     - Stretch to exact size (NOT recommended)
  thumbnail   - Create thumbnail
        '''
    )
    strategy_group.add_argument(
        '--bg-color',
        default='transparent',
        help='Background color for padding (e.g., white, black, transparent, #FF0000)'
    )

    # Info options
    info_group = parser.add_argument_group('Information')
    info_group.add_argument(
        '--list-presets',
        action='store_true',
        help='List all available platform presets'
    )
    info_group.add_argument(
        '--info',
        action='store_true',
        help='Show information about the source image'
    )
    info_group.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show detailed output'
    )

    args = parser.parse_args(argv)

    # Handle list-presets
    if args.list_presets:
        print_presets()
        return 0

    # Require image for all other operations
    if not args.image:
        parser.error('Image path is required (use --list-presets to see available presets)')

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Error: Image file not found: {image_path}")
        return 1

    # Initialize optimizer
    try:
        optimizer = ImageOptimizer(
            default_quality=args.quality,
            default_format=args.format or OutputFormat.PNG,
            default_strategy=args.strategy,
        )
    except ImportError as e:
        print(f"Error: {e}")
        print("Install Pillow with: pip install Pillow")
        return 1

    # Handle --info
    if args.info:
        info = optimizer.get_image_info(image_path)
        print(f"\nImage Information: {info['filename']}")
        print("-" * 40)
        print(f"  Path:        {info['path']}")
        print(f"  Format:      {info['format']}")
        print(f"  Mode:        {info['mode']}")
        print(f"  Size:        {info['width']} x {info['height']}")
        print(f"  Aspect:      {info['aspect_ratio']}")
        print(f"  File size:   {info['file_size_kb']} KB")
        print(f"  Has alpha:   {info['has_alpha']}")
        return 0

    # Parse background color
    bg_color = parse_bg_color(args.bg_color)

    results: List[OptimizationResult] = []

    # Handle batch operations
    if args.ios_icons:
        output_dir = args.output_dir or Path('./ios_icons')
        print(f"Generating iOS icons to {output_dir}/")
        results.extend(optimizer.generate_all_ios_icons(image_path, output_dir))

    if args.android_icons:
        output_dir = args.output_dir or Path('./android_icons')
        print(f"Generating Android icons to {output_dir}/")
        results.extend(optimizer.generate_all_android_icons(image_path, output_dir))

    if args.social_profiles:
        output_dir = args.output_dir or Path('./social_profiles')
        print(f"Generating social profile images to {output_dir}/")
        results.extend(optimizer.generate_social_profile_images(image_path, output_dir))

    if args.favicons:
        output_dir = args.output_dir or Path('./favicons')
        print(f"Generating favicons to {output_dir}/")
        presets = [
            ("web", "favicon_16"),
            ("web", "favicon_32"),
            ("web", "favicon_192"),
            ("web", "favicon_512"),
            ("web", "apple_touch_icon"),
        ]
        results.extend(optimizer.batch_optimize(
            image_path, presets, output_dir,
            output_format=args.format,
        ))

    # Handle preset-based resizing
    if args.presets:
        for platform, preset_name in args.presets:
            print(f"Optimizing for {platform}/{preset_name}")
            result = optimizer.optimize_for_preset(
                image_path=image_path,
                platform=platform,
                preset_name=preset_name,
                output_path=args.output if len(args.presets) == 1 else None,
                output_format=args.format,
            )
            results.append(result)

    # Handle direct size specification
    if args.size:
        width, height = args.size
        print(f"Resizing to {width}x{height}")
        result = optimizer.optimize_image(
            image_path=image_path,
            target_width=width,
            target_height=height,
            output_path=args.output,
            output_format=args.format,
            background_color=bg_color,
        )
        results.append(result)

    # If no operation specified
    if not results:
        parser.error('Specify --size, --preset, or a batch operation (--ios-icons, --android-icons, etc.)')

    # Print results
    print("\nResults:")
    success_count = 0
    for result in results:
        print_result(result, args.verbose)
        if result.success:
            success_count += 1

    print(f"\nCompleted: {success_count}/{len(results)} successful")
    return 0 if success_count == len(results) else 1


def parse_bg_color(color_str: str) -> tuple:
    """Parse a color string into RGBA tuple."""
    color_str = color_str.lower().strip()

    # Named colors
    named_colors = {
        'transparent': (255, 255, 255, 0),
        'white': (255, 255, 255, 255),
        'black': (0, 0, 0, 255),
        'red': (255, 0, 0, 255),
        'green': (0, 255, 0, 255),
        'blue': (0, 0, 255, 255),
        'gray': (128, 128, 128, 255),
        'grey': (128, 128, 128, 255),
    }

    if color_str in named_colors:
        return named_colors[color_str]

    # Hex color
    if color_str.startswith('#'):
        hex_str = color_str[1:]
        if len(hex_str) == 6:
            r = int(hex_str[0:2], 16)
            g = int(hex_str[2:4], 16)
            b = int(hex_str[4:6], 16)
            return (r, g, b, 255)
        elif len(hex_str) == 8:
            r = int(hex_str[0:2], 16)
            g = int(hex_str[2:4], 16)
            b = int(hex_str[4:6], 16)
            a = int(hex_str[6:8], 16)
            return (r, g, b, a)

    # Default to transparent
    return (255, 255, 255, 0)


if __name__ == '__main__':
    sys.exit(main())
