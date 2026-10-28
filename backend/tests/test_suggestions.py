from app.services.suggestion_service import suggestion_service


def test_preset_categories():
    categories = suggestion_service.get_categories()
    assert len(categories) >= 4
    cat_ids = [c["id"] for c in categories]
    assert "mind_bending_thrillers" in cat_ids
    assert "survival_movies" in cat_ids
