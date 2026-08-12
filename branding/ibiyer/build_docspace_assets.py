from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).parent
SOURCE = ROOT / "ibiyer-logo-transparent.png"
FONT = r"C:\Windows\Fonts\msyhbd.ttc"


def cropped_logo() -> Image.Image:
    image = Image.open(SOURCE).convert("RGBA")
    bbox = image.getchannel("A").getbbox()
    if not bbox:
        raise RuntimeError("Logo has no visible pixels")
    return image.crop(bbox)


def fit(image: Image.Image, width: int, height: int) -> Image.Image:
    copy = image.copy()
    copy.thumbnail((width, height), Image.Resampling.LANCZOS)
    return copy


def save_icon(logo: Image.Image, size: int, filename: str) -> None:
    padding = max(2, round(size * 0.08))
    icon = fit(logo, size - padding * 2, size - padding * 2)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(icon, ((size - icon.width) // 2, (size - icon.height) // 2))
    canvas.save(ROOT / filename, optimize=True)


def save_lockup(
    logo: Image.Image,
    size: tuple[int, int],
    filename: str,
    text: str,
    text_color: tuple[int, int, int, int],
) -> None:
    width, height = size
    margin = max(4, round(height * 0.08))
    mark = fit(logo, height - margin * 2, height - margin * 2)
    font_size = round(height * 0.40)
    font = ImageFont.truetype(FONT, font_size)
    draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    text_box = draw.textbbox((0, 0), text, font=font)
    text_width = text_box[2] - text_box[0]
    gap = round(height * 0.14)
    content_width = mark.width + gap + text_width
    x = max(margin, (width - content_width) // 2)
    y = (height - mark.height) // 2

    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.alpha_composite(mark, (x, y))
    text_x = x + mark.width + gap
    text_y = (height - (text_box[3] - text_box[1])) // 2 - text_box[1]
    ImageDraw.Draw(canvas).text((text_x, text_y), text, font=font, fill=text_color)
    canvas.save(ROOT / filename, optimize=True)


logo = cropped_logo()
save_icon(logo, 32, "ibiyer-favicon-32.png")
save_icon(logo, 56, "ibiyer-menu-56.png")
save_lockup(logo, (422, 48), "ibiyer-header-light-422x48.png", "IBiyer 协作空间", (35, 52, 84, 255))
save_lockup(logo, (422, 48), "ibiyer-header-dark-422x48.png", "IBiyer 协作空间", (255, 255, 255, 255))
save_lockup(logo, (810, 92), "ibiyer-login-light-810x92.png", "IBiyer 协作空间", (35, 52, 84, 255))
save_lockup(logo, (810, 92), "ibiyer-login-dark-810x92.png", "IBiyer 协作空间", (255, 255, 255, 255))
