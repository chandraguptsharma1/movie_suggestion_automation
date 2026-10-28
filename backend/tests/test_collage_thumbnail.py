from pathlib import Path
import pytest
from PIL import Image
from app.services.collage_thumbnail_service import collage_thumbnail_service


def test_generate_shorts_collage(tmp_path):
    # Dummy posters
    test_movies = []
    for i in range(3):
        img = Image.new("RGBA", (300, 450), ((i + 1) * 60, 40, 100, 255))
        p = tmp_path / f"poster_{i}.png"
        img.save(p)
        test_movies.append({
            "title": f"Movie {i+1}",
            "poster_url": str(p),
            "vote_average": 8.0 + i * 0.3,
        })

    out_file = tmp_path / "test_collage.jpg"
    res = collage_thumbnail_service.generate_shorts_collage(
        movies=test_movies,
        output_path=str(out_file),
        top_text="SUPER ADDICTIVE",
        bottom_text="MASTERPIECES!",
        rating_text="8.5/10",
    )

    assert res["success"] is True
    assert res["width"] == 1080
    assert res["height"] == 1920
    assert out_file.exists()

    saved_img = Image.open(out_file)
    assert saved_img.size == (1080, 1920)
    assert saved_img.format == "JPEG"


@pytest.mark.parametrize('layout', ['poster_focus', 'cinema'])
def test_single_poster_is_large_and_keeps_its_aspect(tmp_path, layout):
    poster = tmp_path / 'poster.jpg'
    Image.new('RGB', (400, 600), 'red').save(poster)
    result = collage_thumbnail_service.generate_shorts_collage(
        [{'title': 'Runner', 'poster_url': str(poster)}], str(tmp_path / 'out.jpg'), layout=layout)
    x, y, width, height = result['poster_bounds'][0]
    assert width >= 990
    assert height / width == pytest.approx(1.5, abs=.01)
    assert x >= 0 and y >= 0 and x + width <= 1080 and y + height <= 1920


def test_missing_poster_does_not_silently_render_blank_card(tmp_path):
    with pytest.raises(ValueError, match='Poster unavailable'):
        collage_thumbnail_service.generate_shorts_collage([{'title': 'Runner'}], str(tmp_path / 'out.jpg'))
