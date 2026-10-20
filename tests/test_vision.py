"""Real immutable image inputs, hand metrics and bounded CPU tasks."""

import json
from contextlib import closing

import numpy as np
import pytest
from PIL import Image

from veri_ufku.importers.delimited import Control, hash_artifact
from veri_ufku.importers.images import annotation, decode, scan
from veri_ufku.importers.native import StructuredSettings
from veri_ufku.importers.registry import detect, get_adapter
from veri_ufku.importers.sources import capture_source, unpack
from veri_ufku.modeling.vision import calculate, predict, transform
from veri_ufku.modeling.vision_contracts import VisionSpec
from veri_ufku.modeling.vision_metrics import (
    detection_metrics,
    iou,
    segmentation_metrics,
)
from veri_ufku.storage.neural_store import load, publish
from veri_ufku.storage.project_model import ProjectError
from veri_ufku.storage.project_store import ProjectStore
from veri_ufku.storage.vision_store import export_annotations, export_weights, review


def images(folder, seed=57, n=40, prefix="bankA", human=True):
    folder.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        rgb = rng.integers(
            100 if prefix == "bankB" else 0,
            170 if prefix == "bankB" else 70,
            (16, 16, 3),
            dtype=np.uint8,
        )
        left = int(rng.integers(1, 7))
        top = int(rng.integers(1, 7))
        edge = int(rng.integers(4, 8))
        right = min(16, left + edge)
        bottom = min(16, top + edge)
        color = [230, 20, 20] if i % 2 == 0 else [20, 20, 230]
        rgb[top:bottom, left:right] = color
        mask = np.zeros((16, 16), dtype=np.uint8)
        mask[top:bottom, left:right] = 1
        name = f"image-{i}.png"
        m = f"mask-{i}.png"
        Image.fromarray(rgb).save(folder / name)
        Image.fromarray(mask).save(folder / m)
        rows.append(
            dict(
                id=prefix + str(i),
                file=name,
                subject=f"{prefix}-subject-{i // 4}",
                video_source=f"{prefix}-video-{i // 4}",
                sequence="sequence0",
                frame_index=i,
                time_seconds=float(i) / 10,
                annotation=dict(
                    label="red" if i % 2 == 0 else "blue",
                    boxes=[
                        dict(
                            id=f"b{i}", label="object", xyxy=[left, top, right, bottom]
                        )
                    ],
                    mask=m,
                    status="human" if human else "model",
                    reviewer="Fixture human" if human else "",
                    reviewed_at="2026-10-14",
                ),
            )
        )
    manifest = dict(
        schema="VisionManifest/v1",
        classes=["red", "blue"],
        mask_labels=["background", "object"],
        images=rows,
    )
    (folder / "images.json").write_text(json.dumps(manifest))
    return manifest


def fixture(tmp_path, seed=57, prefix="bankA"):
    folder = tmp_path / "images"
    images(folder, seed=seed, prefix=prefix)
    work = tmp_path / "work"
    work.mkdir()
    control = Control()
    snapshot = unpack(capture_source(folder, work, control), work, control)
    assert detect(snapshot) == "image_dataset"
    result = get_adapter("image_dataset").import_data(
        snapshot, StructuredSettings(adapter_id="image_dataset"), work, control
    )
    store = ProjectStore.create(tmp_path / "project")
    store.publish_import(result)
    d = store.state["datasets"][-1]
    source = store.state["sources"][-1]
    assert source["copy_uri"]
    request = dict(
        path=str(store.path(d["snapshot_uri"])),
        fingerprint=hash_artifact(store.path(d["snapshot_uri"]), control),
        columns=d["import_metadata"]["columns"],
        row_count=d["import_metadata"]["row_count"],
        version_id=d["version_id"],
        origin_version=d["version_id"],
        source_snapshot_id=d["import_metadata"]["source_snapshot_id"],
        snapshot_uri=d["snapshot_uri"],
        config_revision=0,
        run_id="run:vision57",
        prior_test_use_ids=[],
        image_bundle=str(store.path(source["copy_uri"])),
        image_fingerprint=source["fingerprint"],
        image_catalog=result["diagnostics"]["format_metadata"],
        image_column=next(
            c["id"] for c in d["import_metadata"]["columns"] if c["name"] == "member"
        ),
    )
    return store, request, work, folder


@pytest.mark.parametrize(
    "task", ["scan", "classification", "detection", "segmentation"]
)
def test_real_adapter_cpu_tasks_safe_roundtrip_and_prediction(tmp_path, task):
    store, r, work, folder = fixture(tmp_path)
    with closing(store):
        before = {p.name: p.read_bytes() for p in folder.iterdir()}
        out = calculate(r, VisionSpec(task=task, epochs=3).data(), work)
        assert out["status"] == "completed"
        assert len(out["images"]) == 40
        a = set(out["plan"]["membership"]["train"])
        b = set(out["plan"]["membership"]["validation"])
        test = set(out["plan"]["membership"]["test"])
        assert a.isdisjoint(b | test)
        assert set(out["tensor_schema"]["fit_row_ids"]) <= a
        groups = {v["row_id"]: v["leakage_component"] for v in out["images"]}
        assert {groups[i] for i in a}.isdisjoint({groups[i] for i in b | test})
        if task == "classification":
            assert sum(map(sum, out["metrics"]["confusion"])) == len(b)
            assert len(out["curves"]) == 3
        if task == "detection":
            assert out["metrics"]["by_class_threshold"]
        if task == "segmentation":
            assert out["metrics"]["pixels"] == len(b) * 64
        state = publish(store, store.state, out)
        loaded = load(store, state["results"][-1])
        assert loaded["metrics"] == out["metrics"]
        if task != "scan":
            predictions = predict(loaded, r)
            assert len(predictions["predictions"]) == 40 and predictions["fit"] is False
            assert {p["row_id"] for p in predictions["predictions"]} == {
                i["row_id"] for i in out["images"]
            }
        assert before == {p.name: p.read_bytes() for p in folder.iterdir()}


def test_metric_hand_references_duplicate_matching_and_absent_classes():
    assert iou([0, 0, 2, 2], [1, 0, 3, 2]) == pytest.approx(1 / 3)
    ground = [dict(id="g1", image_id="i", label="object", xyxy=[0, 0, 2, 2])]
    predictions = [
        dict(id="fp", image_id="i", label="object", xyxy=[4, 4, 6, 6], score=0.99),
        dict(id="tp", image_id="i", label="object", xyxy=[0, 0, 2, 2], score=0.9),
        dict(id="dup", image_id="i", label="object", xyxy=[0, 0, 2, 2], score=0.8),
    ]
    result = detection_metrics(ground, predictions, ["object", "absent"], [0.5, 0.75])
    assert result["map"] == 0.5
    first = result["by_class_threshold"][0]
    assert first["tp"] == 1 and first["fp"] == 2 and first["fn"] == 0
    assert sum(m["ground_id"] == "g1" for m in first["matches"]) == 1
    assert result["by_class_threshold"][1]["ap"] is None
    g = np.array([[1, 0], [1, 0]], dtype=np.uint8)
    p = np.array([[1, 1], [0, 0]], dtype=np.uint8)
    metrics = segmentation_metrics([g], [p], ["background", "object"])
    assert metrics["by_class"][1]["iou"] == pytest.approx(1 / 3)
    assert metrics["by_class"][1]["dice"] == 0.5


def test_corrupt_large_alpha_and_annotation_mismatch(tmp_path):
    with pytest.raises(ProjectError):
        decode(b"broken png")
    p = tmp_path / "large.png"
    Image.new("RGB", (2001, 2000)).save(p)
    with pytest.raises(ProjectError, match="pixel"):
        decode(p.read_bytes())
    p = tmp_path / "alpha.png"
    Image.new("RGBA", (2, 2)).save(p)
    with pytest.raises(ProjectError, match="kanal"):
        decode(p.read_bytes())
    with pytest.raises(ProjectError, match="BBox"):
        annotation(
            dict(boxes=[dict(id="a", label="object", xyxy=[0, 0, 99, 99])]),
            [16, 16],
            ["red"],
            ["background", "object"],
        )


def test_orientation_and_crop_mask_reference(tmp_path):
    pixels = np.zeros((4, 6, 3), dtype=np.uint8)
    pixels[1:3, 2:4] = 255
    mask = np.zeros((4, 6), dtype=np.uint8)
    mask[1:3, 2:4] = 1
    rgb, target, box = transform(
        pixels, VisionSpec(size=4, crop=(1 / 3, 0.25, 2 / 3, 0.75)), mask
    )
    assert box == (2, 1, 4, 3) and np.all(rgb == 255) and np.all(target == 1)
    p = tmp_path / "oriented.jpg"
    exif = Image.Exif()
    exif[274] = 6
    Image.fromarray(pixels).save(p, exif=exif)
    oriented, info = decode(p.read_bytes())
    assert (
        info["orientation"] == 6
        and info["original_size"] == [6, 4]
        and info["size"] == [4, 6]
    )
    assert oriented.shape == (6, 4, 3)


def test_duplicate_components_and_video_identity(tmp_path):
    store, r, work, folder = fixture(tmp_path)
    with closing(store):
        rows = r["image_catalog"]["images"]
        assert rows[0]["video_source"] == rows[1]["video_source"]
        assert rows[0]["leakage_component"] == rows[1]["leakage_component"]
        assert rows[1]["frame_index"] == 1 and rows[1]["time_seconds"] == 0.1
        snap = unpack(capture_source(folder, work, Control()), work, Control())
        (folder / "image-4.png").write_bytes((folder / "image-0.png").read_bytes())
        snap2 = unpack(capture_source(folder, work, Control()), work, Control())
        cat = scan(snap2)
        assert any(
            p["left"] == rows[4]["image_id"]
            and p["right"] == rows[0]["image_id"]
            and p["exact"]
            for p in cat["duplicates"]
        )
        assert (
            cat["images"][4]["leakage_component"]
            == cat["images"][0]["leakage_component"]
        )
        assert snap["fingerprint"] != snap2["fingerprint"]


def test_transfer_real_frozen_backbone_and_overlap_rejection(tmp_path):
    a = tmp_path / "a"
    a.mkdir()
    store, r, work, _ = fixture(a)
    with closing(store):
        pretrained = calculate(r, VisionSpec(epochs=2).data(), work)
        model = tmp_path / "model"
        model.mkdir()
        export_weights(
            pretrained, model / "model.json", "CC0 fixture", "independent bank A"
        )
        leaky = tmp_path / "leaky"
        leaky.mkdir()
        payload = json.loads((model / "model.json").read_text())
        held = next(
            i
            for i in pretrained["images"]
            if i["row_id"] in pretrained["plan"]["membership"]["validation"]
        )
        payload["training_catalog"].append(
            {
                k: held[k]
                for k in (
                    "decoded_sha256",
                    "signature",
                    "group",
                    "subject",
                    "video_source",
                )
            }
        )
        (leaky / "model.json").write_text(json.dumps(payload))
        with pytest.raises(ProjectError, match="örtüş"):
            calculate(
                r,
                VisionSpec(task="transfer", epochs=2, model_folder=str(leaky)).data(),
                work,
            )
        b = tmp_path / "b"
        b.mkdir()
        other, rr, ww, _ = fixture(b, seed=158, prefix="bankB")
        with closing(other):
            out = calculate(
                rr,
                VisionSpec(task="transfer", epochs=2, model_folder=str(model)).data(),
                ww,
            )
            assert out["status"] == "completed" and out["backbone_frozen"] is True
            assert out["pretrained"]["license"] == "CC0 fixture"


def test_human_review_version_and_masked_export(tmp_path):
    store, r, work, _ = fixture(tmp_path)
    with closing(store):
        original = calculate(r, VisionSpec(task="scan").data(), work)
        state = publish(store, store.state, original)
        row = original["images"][0]
        state, rev = review(
            store,
            state,
            original,
            row["row_id"],
            dict(label="red", boxes=[], mask=""),
            "Human reviewer",
        )
        assert rev["annotation_parent"] == original["run_id"]
        assert not rev["model_weights"] and not rev["metrics"]
        export = tmp_path / "annotations.json"
        export_annotations(rev, export)
        raw = export.read_text()
        assert "Human reviewer" not in raw
        exported = json.loads(raw)
        assert exported["images"][0]["source_record_id"] == row["source_record_id"]
        assert exported["images"][0]["annotation"]["status"] == "human"
        with pytest.raises(ProjectError, match="eski"):
            review(store, state, original, row["row_id"], dict(label="red"), "someone")


def test_model_proposals_not_ground_truth_and_frozen_plan(tmp_path):
    store, r, work, _ = fixture(tmp_path)
    with closing(store):
        scanrun = calculate(r, VisionSpec(task="scan").data(), work)
        r["annotations"] = {
            v["row_id"]: dict(v["annotation"], status="model", reviewer="")
            for v in scanrun["images"]
        }
        with pytest.raises(ProjectError, match="insan"):
            calculate(r, VisionSpec(epochs=1).data(), work)
        r.pop("annotations")
        r["frozen_plan"] = scanrun["plan"]
        with pytest.raises(ProjectError, match="split değişti"):
            calculate(r, VisionSpec(seed=10).data(), work)


def test_real_https_download_verified_cache_size_hash_and_cancel(tmp_path, monkeypatch):
    import http.server
    import ssl
    import subprocess
    import threading
    from functools import partial

    cert = tmp_path / "cert.pem"
    key = tmp_path / "key.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-days",
            "1",
            "-subj",
            "/CN=localhost",
            "-addext",
            "subjectAltName=DNS:localhost",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    folder = tmp_path / "https-model"
    import hashlib
    from pathlib import Path
    from threading import Event

    from veri_ufku.analytics.nlp_models import download as original_download
    from veri_ufku.importers.delimited import Canceled
    from veri_ufku.modeling.vision import parse_weights

    base = tmp_path / "base"
    base.mkdir()
    store, request, work, _ = fixture(base)
    try:
        value = calculate(
            request, VisionSpec(task="classification", epochs=2).data(), work
        )
        folder.mkdir()
        export_weights(value, folder / "model.json", "CC0-1.0", "Synthetic reference")
    finally:
        store.close()

    def download(*args):
        return original_download(
            *args, validator=parse_weights, namespace="vision-models"
        )

    raw = (folder / "model.json").read_bytes()
    h = hashlib.sha256(raw).hexdigest()

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(Handler, directory=str(folder))
    )
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert, key)
    server.socket = ctx.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("SSL_CERT_FILE", str(cert))
    url = f"https://localhost:{server.server_port}/model.json"
    try:
        target = download(url, h, len(raw), tmp_path / "cache")
        assert Path(target, "model.json").read_bytes() == raw
        with pytest.raises(ProjectError):
            download(url, "a" * 64, len(raw), tmp_path / "bad")
        with pytest.raises(ProjectError):
            download(url, h, len(raw) + 1, tmp_path / "bad-size")
        ev = Event()
        ev.set()
        with pytest.raises(Canceled):
            download(url, h, len(raw), tmp_path / "cancel", Control(ev))
        assert not list((tmp_path / "cancel").glob("**/model.json"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    # Offline verified cache does not contact the now-stopped service.
    target = download(url, h, len(raw), tmp_path / "cache")
    assert Path(target, "model.json").read_bytes() == raw
    assert "vision-models" in target


def test_fold_fit_isolation_augmentation_and_scan_to_training(tmp_path):
    import copy

    store, r, work, _ = fixture(tmp_path)
    with closing(store):
        scan_run = calculate(r, VisionSpec(task="scan").data(), work)
        from veri_ufku.modeling.vision import validate

        validate(dict(scan_run, status="budget_exhausted"))
        spec = VisionSpec(task="classification", epochs=1, flip=True)
        value = calculate(dict(r, frozen_plan=scan_run["plan"]), spec.data(), work)
        held = set(
            value["plan"]["membership"]["validation"]
            + value["plan"]["membership"]["test"]
        )
        overrides = copy.deepcopy(value["annotations"])
        for row_id in held:
            overrides[row_id]["label"] = (
                "blue" if overrides[row_id]["label"] == "red" else "red"
            )
        poisoned = calculate(
            dict(r, annotations=overrides, frozen_plan=value["plan"]), spec.data(), work
        )
        assert poisoned["model_weights"] == value["model_weights"]
        assert (
            poisoned["curves"][0]["training_loss"]
            == value["curves"][0]["training_loss"]
        )
        for row in value["transform"]["preview"]:
            if row["row_id"] in held:
                assert row["train_augmentation_preview"] is None
            elif row["train_augmentation_preview"]:
                assert row["train_augmentation_preview"] == [
                    list(reversed(p)) for p in row["transformed"]
                ]


def test_invalid_masks_review_and_safe_weights_are_controlled(tmp_path):
    import io

    from veri_ufku.importers.images import decode_mask
    from veri_ufku.modeling.vision import parse_weights

    raw = io.BytesIO()
    Image.fromarray(np.full((8, 8), 3, dtype=np.uint8)).save(raw, format="PNG")
    with pytest.raises(ProjectError):
        decode_mask(raw.getvalue(), [8, 8], ["background", "object"])
    with pytest.raises(ProjectError):
        decode_mask(raw.getvalue(), [16, 16], ["background", "object"])
    with pytest.raises(ProjectError):
        parse_weights(b'{"__reduce__":"arbitrary code"}')
    store, r, work, _ = fixture(tmp_path)
    with closing(store):
        value = calculate(r, VisionSpec().data(), work)
        state = publish(store, store.state, value)
        row = value["images"][0]["row_id"]
        before = len(state["results"])
        with pytest.raises(ProjectError, match="bulunamadı"):
            review(
                store,
                state,
                value,
                row,
                dict(label="red", boxes=[], mask="missing.png"),
                "Reviewer",
            )
        assert len(store.state["results"]) == before


def test_manifest_path_offline_reopen_and_artifact_corruption(tmp_path, monkeypatch):
    import socket

    store, r, work, folder = fixture(tmp_path)
    captured = unpack(
        capture_source(folder / "images.json", work, Control()), work, Control()
    )
    assert detect(captured) == "image_dataset"
    assert len(scan(captured)["images"]) == 40
    value = calculate(r, VisionSpec(epochs=2).data(), work)
    state = publish(store, store.state, value)
    record = state["results"][-1]
    root = store.root
    store.close()
    folder.rename(tmp_path / "original-not-present")

    def denied(*args, **kwargs):
        raise AssertionError("Offline local image open/prediction contacted network")

    monkeypatch.setattr(socket, "socket", denied)
    with closing(ProjectStore.open(root)) as reopened:
        d = reopened.state["datasets"][-1]
        source = reopened.state["sources"][-1]
        request = dict(
            r,
            path=str(reopened.path(d["snapshot_uri"])),
            image_bundle=str(reopened.path(source["copy_uri"])),
        )
        trained = load(reopened, record)
        result = predict(trained, request)
        assert len(result["predictions"]) == 40 and result["fit"] is False
        artifact = reopened.path(record["neural"]["details_uri"])
        artifact.chmod(0o600)
        artifact.write_bytes(b"{}")
        with pytest.raises(ProjectError, match="hash"):
            load(reopened, record)
