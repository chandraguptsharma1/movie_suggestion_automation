import pytest
from app.services.video_composer_service import video_composer_service


def test_build_shorts_filter_graph_with_crop():
    crop_info = {
        "detected": True,
        "original_width": 1920,
        "original_height": 1080,
        "crop_w": 1920,
        "crop_h": 800,
        "crop_x": 0,
        "crop_y": 140,
        "has_black_bars": True,
        "crop_applied": True,
        "crop_method": "cropdetect",
    }
    filter_graph, layout = video_composer_service.build_shorts_filter_graph(
        crop_info=crop_info,
        shorts_width=1080,
        shorts_height=1920,
        foreground_width=1220,
        foreground_zoom=1.70,
        background_blur=24,
    )

    # Verify black bar crop is in the source chain
    assert "crop=1920:800:0:140" in filter_graph
    assert "split=2[bgsrc][fgsrc]" in filter_graph
    # Verify background is scaled, blurred, and darkened
    assert "boxblur=24:1" in filter_graph
    assert "scale=1080:1920:force_original_aspect_ratio=increase" in filter_graph
    # Verify foreground zoom (1220 * 1.70 = 2074)
    expected_effective_width = int(1220 * 1.70)
    assert f"scale={expected_effective_width}:-2" in filter_graph
    # Verify overlay is centered horizontally
    assert "overlay=(W-w)/2:" in filter_graph

    assert layout["effective_width"] == expected_effective_width
    assert layout["foreground_zoom"] == 1.70


def test_build_shorts_filter_graph_fallback_crop():
    crop_info = {
        "detected": True,
        "original_width": 1920,
        "original_height": 1080,
        "crop_w": 1920,
        "crop_h": 800,
        "crop_x": 0,
        "crop_y": 140,
        "has_black_bars": True,
        "crop_applied": True,
        "crop_method": "fallback",
    }
    filter_graph, layout = video_composer_service.build_shorts_filter_graph(
        crop_info=crop_info,
        shorts_width=1080,
        shorts_height=1920,
        foreground_width=1220,
        foreground_zoom=1.70,
    )

    assert "crop=in_w:in_h*0.74:0:in_h*0.13" in filter_graph
    assert "boxblur=24:1" in filter_graph


def test_build_shorts_filter_graph_no_crop():
    crop_info = {
        "detected": False,
        "original_width": 1920,
        "original_height": 1080,
        "crop_applied": False,
        "crop_method": "none",
    }
    filter_graph, layout = video_composer_service.build_shorts_filter_graph(
        crop_info=crop_info,
        shorts_width=1080,
        shorts_height=1920,
        foreground_width=1020,
        foreground_zoom=1.50,
    )

    assert "crop=" not in filter_graph.split("split=2")[0]
    expected_width = int(1020 * 1.50)
    assert f"scale={expected_width}:-2" in filter_graph


def test_zoom_slider_produces_different_foreground_sizes():
    crop_info = {"original_width": 1920, "original_height": 1080, "crop_applied": False}
    _, subtle = video_composer_service.build_shorts_filter_graph(crop_info, foreground_zoom=1.2)
    _, strong = video_composer_service.build_shorts_filter_graph(crop_info, foreground_zoom=2.0)
    assert strong["foreground_height"] > subtle["foreground_height"]
    assert strong["effective_width"] > subtle["effective_width"] > 1080
    assert strong["overlay_y"] < subtle["overlay_y"]


def test_vertical_video_stays_full_frame():
    graph, layout = video_composer_service.build_shorts_filter_graph({
        "original_width": 1080, "original_height": 1920, "crop_applied": False,
    })
    assert layout["is_vertical_direct"] is True
    assert "split=2" not in graph
