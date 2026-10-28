import io
import math
import os
import urllib.request
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps
from app.config import settings

logger = logging.getLogger(__name__)


class CollageThumbnailService:
    WIDTH = 1080
    HEIGHT = 1920

    def __init__(self):
        self.font_paths = self._find_font_paths()

    def _find_font_paths(self) -> Dict[str, str]:
        candidates = {
            "impact": [
                r"C:\Windows\Fonts\impact.ttf",
                r"C:\Windows\Fonts\arialbd.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            ],
            "bold": [
                r"C:\Windows\Fonts\arialbd.ttf",
                r"C:\Windows\Fonts\segoeuib.ttf",
                r"C:\Windows\Fonts\calibrib.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            ],
        }
        found: Dict[str, str] = {}
        for key, paths in candidates.items():
            for p in paths:
                if os.path.exists(p):
                    found[key] = p
                    break
        return found

    def _get_font(self, font_type: str, size: int) -> ImageFont.FreeTypeFont:
        font_path = self.font_paths.get(font_type)
        if font_path and os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                pass
        return ImageFont.load_default()

    def _download_image(self, url: str) -> Optional[Image.Image]:
        if not url:
            return None
        # If local path
        if os.path.exists(url):
            try:
                return Image.open(url).convert("RGBA")
            except Exception:
                return None
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
                return Image.open(io.BytesIO(data)).convert("RGBA")
        except Exception as exc:
            logger.warning("Could not download poster %s: %s", url, exc)
            return None

    def _create_bordered_card(
        self,
        img: Image.Image,
        target_size: Tuple[int, int],
        border_width: int = 12,
        corner_radius: int = 18,
    ) -> Image.Image:
        w, h = target_size
        img_resized = img.resize((w, h), Image.Resampling.LANCZOS)
        card = Image.new("RGBA", (w + 2 * border_width, h + 2 * border_width), (0, 0, 0, 0))
        draw = ImageDraw.Draw(card)
        draw.rounded_rectangle(
            [(0, 0), (w + 2 * border_width, h + 2 * border_width)],
            radius=corner_radius,
            fill=(255, 255, 255, 255),
        )
        card.paste(img_resized, (border_width, border_width))
        return card

    def _draw_text_box(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont,
        center_x: int,
        y: int,
        bg_color: Tuple[int, int, int],
        text_color: Tuple[int, int, int],
        padding_x: int = 36,
        padding_y: int = 18,
        border_radius: int = 16,
    ) -> int:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        box_w = text_w + padding_x * 2
        box_h = text_h + padding_y * 2
        box_x0 = center_x - box_w // 2
        box_y0 = y
        box_x1 = box_x0 + box_w
        box_y1 = box_y0 + box_h

        draw.rounded_rectangle(
            [(box_x0, box_y0), (box_x1, box_y1)],
            radius=border_radius,
            fill=bg_color,
        )

        draw.text(
            (box_x0 + padding_x, box_y0 + padding_y - bbox[1]),
            text,
            fill=text_color,
            font=font,
        )
        return box_h

    def generate_shorts_collage(
        self,
        movies: List[Dict[str, Any]],
        output_path: str,
        top_text: str = "SUPER ADDICTIVE",
        bottom_text: str = "MASTERPIECES!",
        rating_text: str = "",
        layout: str = "poster_focus",
    ) -> Dict[str, Any]:
        if layout not in ('poster_focus', 'cinema', 'classic'):
            raise ValueError('Unknown thumbnail layout')
        if not movies:
            raise ValueError('At least one movie is required')
        if layout != 'classic':
            return self._poster_layout(movies, output_path, top_text, bottom_text, rating_text, layout)
        canvas = Image.new("RGBA", (self.WIDTH, self.HEIGHT), (15, 17, 23, 255))
        images = []
        for m in movies:
            p_url = m.get("poster_url")
            img = self._download_image(p_url) if p_url else None
            if img:
                images.append(img)
            else:
                placeholder = Image.new("RGBA", (500, 750), (40, 44, 52, 255))
                images.append(placeholder)

        # Background ambient blur from first poster
        if images:
            bg_ambient = images[0].resize((self.WIDTH, self.HEIGHT), Image.Resampling.LANCZOS)
            bg_ambient = bg_ambient.filter(ImageFilter.GaussianBlur(radius=60))
            enhancer = ImageEnhance.Brightness(bg_ambient)
            bg_ambient = enhancer.enhance(0.40)
            canvas.paste(bg_ambient, (0, 0))

        count = len(images)
        if count == 1:
            card_w, card_h = (580, 870)
        elif count <= 3:
            card_w, card_h = (480, 720)
        else:
            card_w, card_h = (440, 660)

        # Layout arrangements
        if count == 1:
            slots = [
                {"idx": 0, "angle": 0, "pos": (540, 880)},
            ]
        elif count == 2:
            slots = [
                {"idx": 0, "angle": -9, "pos": (290, 850)},
                {"idx": 1, "angle": 9, "pos": (790, 890)},
            ]
        elif count == 3:
            slots = [
                {"idx": 0, "angle": -14, "pos": (260, 920)},
                {"idx": 2, "angle": 14, "pos": (820, 920)},
                {"idx": 1, "angle": 0, "pos": (540, 800)},
            ]
        else: # 4 movies
            slots = [
                {"idx": 0, "angle": -12, "pos": (280, 720)},
                {"idx": 1, "angle": 12, "pos": (800, 720)},
                {"idx": 2, "angle": -6, "pos": (300, 1180)},
                {"idx": 3, "angle": 6, "pos": (780, 1180)},
            ]

        for s in slots:
            idx = s["idx"]
            if idx >= len(images):
                continue
            card = self._create_bordered_card(images[idx], (card_w, card_h))
            rotated = card.rotate(s["angle"], expand=True, resample=Image.Resampling.BICUBIC)
            rw, rh = rotated.size
            cx, cy = s["pos"]
            x = cx - rw // 2
            y = cy - rh // 2
            canvas.paste(rotated, (x, y), rotated)

        draw = ImageDraw.Draw(canvas)

        # Top Rating Pill
        if not rating_text:
            avg = sum(m.get("vote_average") or 8.0 for m in movies) / max(len(movies), 1)
            rating_text = f"★ {round(avg, 1)}/10"

        star_font = self._get_font("bold", 54)
        self._draw_text_box(
            draw=draw,
            text=rating_text,
            font=star_font,
            center_x=self.WIDTH // 2,
            y=120,
            bg_color=(20, 20, 20),
            text_color=(255, 215, 0),
            padding_x=40,
            padding_y=16,
            border_radius=30,
        )

        # Bottom 2-Tier High-Impact Hook Banner
        hook_font = self._get_font("impact", 72)
        hook_y = self.HEIGHT - 440
        h1 = self._draw_text_box(
            draw=draw,
            text=top_text.upper(),
            font=hook_font,
            center_x=self.WIDTH // 2,
            y=hook_y,
            bg_color=(10, 10, 10),
            text_color=(255, 255, 255),
            padding_x=45,
            padding_y=18,
            border_radius=18,
        )

        self._draw_text_box(
            draw=draw,
            text=bottom_text.upper(),
            font=hook_font,
            center_x=self.WIDTH // 2,
            y=hook_y + h1 + 18,
            bg_color=(245, 190, 11),
            text_color=(10, 10, 10),
            padding_x=45,
            padding_y=18,
            border_radius=18,
        )

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        final_rgb = canvas.convert("RGB")
        final_rgb.save(out, format="JPEG", quality=95)

        return {
            "success": True,
            "output_path": str(out).replace("\\", "/"),
            "width": self.WIDTH,
            "height": self.HEIGHT,
            "top_text": top_text,
            "bottom_text": bottom_text,
            "rating_text": rating_text,
            "layout": layout,
        }

    def _fit_text(self, draw, text, max_width, size=96, kind='impact'):
        font = self._get_font(kind, size)
        while draw.textbbox((0, 0), text, font=font)[2] > max_width and size > 8:
            size -= 2
            font = self._get_font(kind, size)
        return font

    def _poster_layout(self, movies, output_path, top_text, bottom_text, rating_text, layout):
        """Keep authentic poster art large and undistorted; reserve space for titles."""
        if len(movies) > 7:
            raise ValueError('A thumbnail supports at most seven movies')
        posters = []
        for movie in movies:
            poster = self._download_image(movie.get('poster_url'))
            if poster is None:
                raise ValueError(f"Poster unavailable for {movie.get('title', 'movie')}; choose another poster and retry.")
            posters.append(poster)
        canvas = ImageOps.fit(posters[0], (1080, 1920)).filter(ImageFilter.GaussianBlur(65))
        canvas = ImageEnhance.Brightness(canvas).enhance(.22).convert('RGBA')
        bounds = []
        single = len(posters) == 1
        if single:
            box = (0, 0, 1080, 1620) if layout == 'cinema' else (42, 140, 996, 1494)
            slots = [box]
        else:
            cols = 2 if len(posters) <= 4 else 3
            rows = math.ceil(len(posters) / cols)
            width = (996 - (cols - 1) * 18) // cols
            height = min(int(width * 1.5), (1370 - (rows - 1) * 36) // rows)
            width = int(height / 1.5)
            slots = []
            for index in range(len(posters)):
                row, col = divmod(index, cols)
                in_row = min(cols, len(posters) - row * cols)
                left = (1080 - in_row * width - (in_row - 1) * 18) // 2
                slots.append((left + col * (width + 18), 200 + row * (height + 36), width, height))
        for index, (poster, (x, y, w, h)) in enumerate(zip(posters, slots)):
            fitted = ImageOps.contain(poster, (w, h), Image.Resampling.LANCZOS)
            px, py = x + (w - fitted.width) // 2, y + (h - fitted.height) // 2
            canvas.alpha_composite(fitted, (px, py))
            bounds.append([px, py, fitted.width, fitted.height])
            if not single:
                draw = ImageDraw.Draw(canvas)
                title = str(movies[index].get('title') or 'Movie').upper()
                font = self._fit_text(draw, title, w - 12, 32, 'bold')
                draw.text((x + w // 2, y + h + 4), title, font=font, fill='white', anchor='mt')
        # Cinema uses a bottom fade; Spotlight leaves the complete poster unobscured.
        if layout == 'cinema' and single:
            fade = Image.new('RGBA', (1080, 570))
            fd = ImageDraw.Draw(fade)
            for yy in range(570):
                fd.line((0, yy, 1080, yy), fill=(7, 11, 18, int(255 * min(1, yy / 270))))
            canvas.alpha_composite(fade, (0, 1350))
        draw = ImageDraw.Draw(canvas)
        accent = (85, 236, 222) if layout == 'poster_focus' else (255, 203, 64)
        if not rating_text:
            ratings = [m.get('vote_average') for m in movies if m.get('vote_average')]
            rating_text = f'{sum(ratings) / len(ratings):.1f}/10' if ratings else ''
        if layout == 'poster_focus' or not single:
            draw.text((54, 60), 'MOVIE PICK' if single else f'{len(movies)} MOVIES TO WATCH',
                      font=self._get_font('bold', 32), fill=accent)
            if rating_text:
                draw.text((1026, 60), rating_text, font=self._fit_text(draw, rating_text, 340, 40, 'bold'), fill='white', anchor='rt')
        elif rating_text:
            font = self._fit_text(draw, rating_text, 320, 46, 'bold')
            self._draw_text_box(draw, rating_text, font, 210, 64, (7, 11, 18), accent, 25, 15)
        title = str(movies[0].get('title') or 'Movie').upper() if single else 'YOUR NEXT WATCH'
        title_y = 1550 if layout == 'cinema' and single else 1660
        title_font = self._fit_text(draw, title, 960, 146 if layout == 'cinema' else 105)
        draw.text((540, title_y), title, font=title_font, fill='white', anchor='mt', stroke_width=1)
        hook = top_text.strip().upper()
        hook_y = 1735 if layout == 'cinema' else 1785
        draw.rectangle((54, hook_y - 18, 1026, hook_y - 13), fill=accent)
        draw.text((540, hook_y), hook, font=self._fit_text(draw, hook, 948, 65), fill=accent, anchor='mt')
        if bottom_text.strip() and layout == 'cinema':
            draw.text((540, 1830), bottom_text.strip().upper(), font=self._fit_text(draw, bottom_text.upper(), 948, 38, 'bold'), fill='white', anchor='mt')
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        canvas.convert('RGB').save(out, 'JPEG', quality=95)
        return {'success': True, 'output_path': out.as_posix(), 'width': 1080, 'height': 1920,
                'top_text': top_text, 'bottom_text': bottom_text, 'rating_text': rating_text,
                'layout': layout, 'poster_bounds': bounds}


collage_thumbnail_service = CollageThumbnailService()
