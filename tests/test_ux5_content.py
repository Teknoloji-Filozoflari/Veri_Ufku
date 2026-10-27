"""UX5: draft stage texts, glossary terms, tour flag without learning-catalog schema."""

from veri_ufku.ui.ux_content import UxContentController, load_ux_content


def test_ux5_stages_and_glossary_are_draft_turkish():
    content = load_ux_content()
    assert "taslak" in content["status"].lower()
    assert len(content["stages"]) == 10
    assert {s["id"] for s in content["stages"]} == {
        "goal",
        "load",
        "columns",
        "summary",
        "missing",
        "explore",
        "outliers",
        "prepare",
        "model",
        "report",
    }
    terms = {g["term"] for g in content["glossary"]}
    for required in (
        "sütun",
        "satır",
        "eksik değer",
        "aykırı değer",
        "korelasyon",
        "sızıntı",
    ):
        assert required in terms


def test_ux5_tour_dismiss_persists(tmp_path):
    controller = UxContentController(tmp_path)
    assert controller.tourOpen or not controller.tourSeen
    controller.dismissTour()
    assert controller.tourSeen and not controller.tourOpen
    again = UxContentController(tmp_path)
    assert again.tourSeen and not again.tourOpen
    again.reopenTour()
    assert again.tourOpen
