"""
Platform-specific size presets for image optimization.

Contains predefined dimensions for common app platforms and use cases.
All dimensions are in pixels (width, height).
"""

from typing import Dict, List, Tuple, Optional

# Size presets organized by platform/category
SIZE_PRESETS: Dict[str, Dict[str, Tuple[int, int]]] = {
    # iOS App Icons
    "ios": {
        "icon_1024": (1024, 1024),      # App Store
        "icon_180": (180, 180),          # iPhone @3x
        "icon_167": (167, 167),          # iPad Pro @2x
        "icon_152": (152, 152),          # iPad @2x
        "icon_120": (120, 120),          # iPhone @2x, Spotlight @3x
        "icon_87": (87, 87),             # Settings @3x
        "icon_80": (80, 80),             # Spotlight @2x
        "icon_76": (76, 76),             # iPad @1x
        "icon_60": (60, 60),             # iPhone @1x
        "icon_58": (58, 58),             # Settings @2x
        "icon_40": (40, 40),             # Spotlight @1x
        "icon_29": (29, 29),             # Settings @1x
        "icon_20": (20, 20),             # Notification @1x
    },

    # Android App Icons
    "android": {
        "icon_xxxhdpi": (192, 192),     # xxxhdpi (4.0x)
        "icon_xxhdpi": (144, 144),      # xxhdpi (3.0x)
        "icon_xhdpi": (96, 96),         # xhdpi (2.0x)
        "icon_hdpi": (72, 72),          # hdpi (1.5x)
        "icon_mdpi": (48, 48),          # mdpi (1.0x baseline)
        "icon_ldpi": (36, 36),          # ldpi (0.75x)
        "adaptive_foreground": (432, 432),  # Adaptive icon foreground
        "play_store": (512, 512),       # Google Play Store
    },

    # LinkedIn
    "linkedin": {
        "profile_photo": (400, 400),              # Profile photo
        "profile_photo_display": (200, 200),      # Displayed size
        "company_logo": (300, 300),               # Company logo
        "company_logo_display": (60, 60),         # Displayed company logo
        "cover_photo": (1584, 396),               # Personal cover
        "company_cover": (1128, 191),             # Company page cover
        "post_image": (1200, 627),                # Shared post image
        "post_image_square": (1200, 1200),        # Square post image
        "article_cover": (744, 400),              # Article cover image
        "carousel_slide": (1080, 1080),           # Carousel document slide
        "app_logo": (180, 180),                   # LinkedIn app/integration logo
    },

    # Twitter/X
    "twitter": {
        "profile_photo": (400, 400),              # Profile image
        "header_photo": (1500, 500),              # Header/banner
        "post_image": (1200, 675),                # In-stream image (16:9)
        "post_image_square": (1200, 1200),        # Square image
        "card_image": (800, 418),                 # Summary card
        "card_image_large": (1200, 628),          # Large summary card
    },

    # Facebook
    "facebook": {
        "profile_photo": (180, 180),              # Profile picture
        "cover_photo": (820, 312),                # Cover photo
        "post_image": (1200, 630),                # Shared link image
        "post_image_square": (1200, 1200),        # Square post
        "event_cover": (1920, 1080),              # Event cover
        "page_profile": (170, 170),               # Page profile
    },

    # Instagram
    "instagram": {
        "profile_photo": (320, 320),              # Profile picture
        "post_square": (1080, 1080),              # Square post
        "post_portrait": (1080, 1350),            # Portrait (4:5)
        "post_landscape": (1080, 608),            # Landscape (1.91:1)
        "story": (1080, 1920),                    # Story/Reel (9:16)
        "carousel": (1080, 1080),                 # Carousel slide
    },

    # Web/General
    "web": {
        "favicon_ico": (48, 48),                  # ICO favicon
        "favicon_16": (16, 16),                   # Favicon 16x16
        "favicon_32": (32, 32),                   # Favicon 32x32
        "favicon_192": (192, 192),                # Android Chrome
        "favicon_512": (512, 512),                # PWA icon
        "apple_touch_icon": (180, 180),           # Apple touch icon
        "og_image": (1200, 630),                  # Open Graph image
        "twitter_card": (1200, 628),              # Twitter card
        "thumbnail_small": (150, 150),            # Small thumbnail
        "thumbnail_medium": (300, 300),           # Medium thumbnail
        "thumbnail_large": (600, 600),            # Large thumbnail
    },

    # E-commerce
    "ecommerce": {
        "product_thumb": (100, 100),              # Product thumbnail
        "product_small": (300, 300),              # Product small
        "product_medium": (600, 600),             # Product medium
        "product_large": (1200, 1200),            # Product large
        "product_zoom": (2000, 2000),             # Product zoom
        "banner_wide": (1920, 600),               # Wide banner
        "banner_square": (600, 600),              # Square banner
    },

    # App Store Assets
    "app_store": {
        "ios_app_store": (1024, 1024),            # iOS App Store icon
        "google_play": (512, 512),                # Google Play icon
        "mac_app_store": (1024, 1024),            # Mac App Store
        "windows_store": (300, 300),              # Windows Store tile
        "windows_store_wide": (558, 270),         # Windows Store wide tile
    },

    # Messaging Apps
    "messaging": {
        "slack_emoji": (128, 128),                # Slack custom emoji
        "slack_app_icon": (512, 512),             # Slack app icon
        "discord_emoji": (128, 128),              # Discord emoji
        "discord_server_icon": (512, 512),        # Discord server icon
        "discord_banner": (960, 540),             # Discord server banner
        "teams_app_icon": (192, 192),             # Microsoft Teams app
        "whatsapp_sticker": (512, 512),           # WhatsApp sticker
    },
}


def get_preset(platform: str, preset_name: str) -> Optional[Tuple[int, int]]:
    """
    Get a specific size preset.

    Args:
        platform: Platform name (e.g., 'ios', 'linkedin')
        preset_name: Preset name (e.g., 'icon_1024', 'app_logo')

    Returns:
        Tuple of (width, height) or None if not found

    Example:
        >>> get_preset('linkedin', 'app_logo')
        (180, 180)
    """
    platform_presets = SIZE_PRESETS.get(platform.lower())
    if platform_presets:
        return platform_presets.get(preset_name)
    return None


def list_presets(platform: Optional[str] = None) -> Dict:
    """
    List available presets.

    Args:
        platform: Optional platform to filter by

    Returns:
        Dictionary of presets
    """
    if platform:
        return {platform: SIZE_PRESETS.get(platform.lower(), {})}
    return SIZE_PRESETS


def get_all_sizes_for_platform(platform: str) -> List[Tuple[str, Tuple[int, int]]]:
    """
    Get all size presets for a platform as a list.

    Args:
        platform: Platform name

    Returns:
        List of (preset_name, (width, height)) tuples
    """
    platform_presets = SIZE_PRESETS.get(platform.lower(), {})
    return list(platform_presets.items())


def find_presets_by_size(width: int, height: int) -> List[Tuple[str, str]]:
    """
    Find all presets that match a given size.

    Args:
        width: Target width
        height: Target height

    Returns:
        List of (platform, preset_name) tuples
    """
    matches = []
    for platform, presets in SIZE_PRESETS.items():
        for name, (w, h) in presets.items():
            if w == width and h == height:
                matches.append((platform, name))
    return matches


# Common size groups for batch operations
COMMON_SIZE_GROUPS = {
    "ios_icons_all": [
        ("ios", name) for name in SIZE_PRESETS["ios"].keys()
    ],
    "android_icons_all": [
        ("android", name) for name in SIZE_PRESETS["android"].keys()
    ],
    "social_profiles": [
        ("linkedin", "profile_photo"),
        ("twitter", "profile_photo"),
        ("facebook", "profile_photo"),
        ("instagram", "profile_photo"),
    ],
    "social_posts": [
        ("linkedin", "post_image"),
        ("twitter", "post_image"),
        ("facebook", "post_image"),
        ("instagram", "post_square"),
    ],
    "favicons_all": [
        ("web", "favicon_16"),
        ("web", "favicon_32"),
        ("web", "favicon_ico"),
        ("web", "favicon_192"),
        ("web", "favicon_512"),
        ("web", "apple_touch_icon"),
    ],
}
