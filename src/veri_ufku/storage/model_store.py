"""Non executable model artifact adoption; hash references are project manifest members."""

from pathlib import Path

from veri_ufku.storage.project_model import ProjectError, uid
from veri_ufku.storage.project_store import file_hash


def adopt(store, run, package):
    path = Path(package["path"])
    if path.is_symlink() or file_hash(path) != package["fingerprint"]:
        raise ProjectError("Model paketi çıktısı değiştirilmiş.")
    if run.get("uncertainty"):
        import json
        import zipfile

        try:
            with zipfile.ZipFile(path) as archive:
                if len(archive.namelist()) != 3 or set(archive.namelist()) != {
                    "card.json",
                    "pipeline.skops",
                    "integrity.json",
                }:
                    raise ProjectError("Calibration package arşiv şeması geçersiz.")
                info = archive.getinfo("card.json")
                if (
                    info.file_size > 4 * 1024**2
                    or json.loads(archive.read("card.json")) != run["model_card"]
                ):
                    raise ProjectError("Calibration package kartı raporla uyuşmuyor.")
        except (zipfile.BadZipFile, KeyError, UnicodeError, ValueError) as error:
            raise ProjectError(
                "Calibration package safe JSON kartı okunamadı."
            ) from error
    # No deserialization in the UI/project-write process.
    uri = "sources/" + uid() + ".bin"
    store.pending[uri] = (
        path,
        dict(**package["fingerprint"], kind="source", rows=None, schema=None),
    )
    run["model_package_uri"] = uri
    run["model_package_fingerprint"] = package["fingerprint"]


def validate_links(state, artifacts):
    for record in state["results"]:
        for key in ("baseline", "unsupervised"):
            run = record.get(key, {})
            if "model_package_uri" not in run:
                continue
            info = artifacts.get(run["model_package_uri"])
            card = run.get("model_card", {})
            if (
                not info
                or info["kind"] != "source"
                or {k: info[k] for k in ("sha256", "size")}
                != run["model_package_fingerprint"]
                or card.get("schema") != "ModelCard/v1"
                or card.get("dataset_version") != run["dataset_version"]
                or card.get("run_id") != run["run_id"]
            ):
                raise ProjectError("Model kartı/paket artifact bağı geçersiz.")
