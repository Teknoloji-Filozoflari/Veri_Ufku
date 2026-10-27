"""Veri panel adapter rows stay status-only."""

from veri_ufku.ui.data_workspace import core_adapters, special_adapters


def test_core_adapters_list_installed_status_without_download():
    rows = core_adapters()
    assert any(r["id"] == "csv" for r in rows)
    assert all("status" in r and "installed" in r for r in rows)


def test_special_adapters_do_not_invent_install_actions():
    rows = special_adapters()
    assert rows
    assert all("indir" not in r["status"].lower() for r in rows)
