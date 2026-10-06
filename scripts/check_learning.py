"""Validate packaged offline content, action allowlist and UI/capability links."""

from pathlib import Path

from veri_ufku.learning.catalog import Catalog, validate_bindings

if __name__ == "__main__":
    catalog = Catalog()
    count = validate_bindings(Path(__file__).resolve().parents[1], catalog)
    print(
        f"PASS: {len(catalog.articles)} offline articles; {count} UI bindings; all capability links"
    )
