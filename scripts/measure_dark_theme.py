"""Capture actual theme screens and measure rendered token contrast in isolated XDG."""

import json
import os
import platform
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path


def contrast(first, second):
    def luminance(value):
        channels = [int(value[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [
            c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
            for c in channels
        ]
        return sum(c * weight for c, weight in zip(linear, (0.2126, 0.7152, 0.0722)))

    low, high = sorted((luminance(first), luminance(second)))
    return (high + 0.05) / (low + 0.05)


def main():
    from PySide6.QtCore import QObject
    from PySide6.QtQml import QQmlEngine, QQmlExpression
    from PySide6.QtTest import QTest

    from veri_ufku.app import create_application

    output = Path(__file__).resolve().parents[1] / "docs/evidence/ui-multicolor"
    output.mkdir(parents=True, exist_ok=True)
    record = {
        "date_utc": datetime.now(UTC).isoformat(),
        "python": platform.python_version(),
        "os": platform.platform(),
        "screenshots": [],
        "contrast": [],
        "checks": [],
    }
    with tempfile.TemporaryDirectory(prefix="veri-ufku-dark-") as temporary:
        for key in ("CONFIG", "STATE", "CACHE"):
            os.environ[f"XDG_{key}_HOME"] = str(Path(temporary) / key)
        legacy = Path(temporary) / "CONFIG/veri_ufku/ui-preferences.json"
        legacy.parent.mkdir(parents=True)
        original = json.dumps(
            {"schema_version": 2, "theme": "light", "view": "advanced"}
        ).encode()
        legacy.write_bytes(original)
        app, window, bridge = create_application()
        assert window.property("darkTheme")
        assert window.findChild(QObject, "themeButton") is None
        assert window.findChild(QObject, "beginnerButton") is not None
        assert window.findChild(QObject, "advancedButton") is not None
        preferences = app._veri_ufku_resources[-2]
        assert preferences.view == "advanced" and legacy.read_bytes() == original
        preferences.setView("beginner")
        assert json.loads(legacy.read_text()) == {
            "schema_version": 3,
            "view": "beginner",
        }
        record["checks"].append(
            "Legacy light ignored; fixed dark; no theme button; schema3 persists only level"
        )
        engine = app._veri_ufku_resources[0]
        guide, charts = engine._guide_resources, engine._charts_resources
        record["qt_platform"] = app.platformName()

        def wait(predicate):
            deadline = time.monotonic() + 30
            while not predicate():
                assert time.monotonic() < deadline, "GUI timed out"
                app.processEvents()
                QTest.qWait(10)

        def token(name):
            expression = QQmlExpression(
                QQmlEngine.contextForObject(window),
                window,
                f"Theme.{name}.toString()",
            )
            value = expression.evaluate()[0]
            assert not expression.hasError()
            return value

        def capture(name, width=1366, height=900):
            window.setWidth(width)
            window.setHeight(height)
            app.processEvents()
            QTest.qWait(180)
            if window.property("infoOpen") and not window.property("dockInfo"):
                drawer = window.findChild(QObject, "informationDrawer")
                wait(lambda: drawer.property("position") >= 0.999)
                QTest.qWait(40)
            target = output / (name + ".png")
            assert window.grabWindow().save(str(target))
            record["screenshots"].append(str(target.relative_to(output.parent)))

        try:
            for foreground, background, minimum in (
                ("text", "surface", 4.5),
                ("text", "raised", 4.5),
                ("secondary", "surface", 4.5),
                ("accentText", "accent", 4.5),
                ("accentText", "accentHover", 4.5),
                ("accentText", "accentPressed", 4.5),
                ("accent", "accentSoft", 4.5),
                ("accent", "raised", 3),
                ("controlBorder", "raised", 3),
                ("dataTone", "chrome", 3),
                ("modelTone", "chrome", 3),
                ("learningTone", "chrome", 3),
                ("modelTone", "violetSurface", 4.5),
                ("learningTone", "mintSurface", 4.5),
                ("dataTone", "cyanSurface", 4.5),
                ("text", "mintSurface", 4.5),
                ("secondary", "mintSurface", 4.5),
                ("modelTone", "raised", 3),
                ("learningTone", "raised", 3),
            ):
                ratio = contrast(token(foreground), token(background))
                assert ratio >= minimum, (foreground, background, ratio)
                record["contrast"].append(
                    {
                        "pair": [foreground, background],
                        "ratio": ratio,
                        "target": minimum,
                    }
                )
            capture("home-dark")
            capture("home-dark-small", 720, 560)
            guide.createExample("sales", temporary)
            wait(lambda: not guide.busy)
            assert engine._dataset_resources.datasets, guide.message
            guide.close()
            window.setProperty("selectedSection", 1)
            capture("data-dark")
            window.setProperty("selectedSection", 3)
            window.findChild(QObject, "chartX").setProperty("currentIndex", 5)
            window.findChild(QObject, "chartCreate").clicked.emit()
            wait(lambda: not charts.busy)
            assert charts.current, charts.errorText
            capture("chart-dark")
            window.setProperty("selectedSection", 6)
            capture("report-dark")
            for tone in ("warm", "violet", "mint", "cyan"):
                for state in ("toneColor", "toneHover", "tonePressed"):
                    expression = QQmlExpression(
                        QQmlEngine.contextForObject(window),
                        window,
                        f'Theme.{state}("{tone}").toString()',
                    )
                    color = expression.evaluate()[0]
                    ratio = contrast(token("accentText"), color)
                    assert ratio >= 4.5, (tone, state, ratio)
                    record["contrast"].append(
                        {
                            "pair": ["accentText", f"{tone}.{state}"],
                            "ratio": ratio,
                            "target": 4.5,
                        }
                    )
            window.setProperty("selectedSection", 2)
            capture("prepare-violet")
            window.setProperty("selectedSection", 5)
            capture("model-violet")
            window.setProperty("selectedSection", 7)
            capture("learn-mint")
            window.findChild(QObject, "helpButton").clicked.emit()
            capture("learn-mint-help")
            capture("learn-mint-small", 720, 560)
            record["checks"].append(
                "Warm/cyan/violet/mint roles captured; real chart worker unchanged"
            )
        finally:
            bridge.session.manager.shutdown()
            app._veri_ufku_resources[-1]()
            window.deleteLater()
            app.processEvents()
    (output / "render.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    )
    print("DARK_THEME_RENDER PASS")


if __name__ == "__main__":
    main()
