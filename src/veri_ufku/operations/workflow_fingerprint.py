"""Lightweight code/env fingerprint; inspecting provenance never loads backends."""

import hashlib
import importlib.metadata as md
import platform
from pathlib import Path

from veri_ufku.modeling.validation import digest


def signature():
    root = Path(__file__).parents[1]
    modules = [
        root / p
        for p in (
            "operations/contracts.py",
            "operations/engine.py",
            "operations/workflow_contracts.py",
            "analytics/dataset.py",
            "analytics/quality.py",
            "statistics/models.py",
            "exports/data.py",
            "domain/capabilities.py",
            "operations/workflow.py",
            "operations/workflow_fingerprint.py",
            "jobs/resources.py",
            "jobs/admission.py",
            "jobs/memory.py",
            "domain/contracts.py",
            "jobs/limits.py",
            "importers/delimited.py",
        )
    ]
    return dict(
        code=digest(
            {
                str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in modules
            }
        ),
        environment=dict(
            python=platform.python_version(),
            machine=platform.machine(),
            **{
                n: md.version(n)
                for n in ("polars", "numpy", "scipy", "statsmodels", "scikit-learn")
            },
        ),
    )
