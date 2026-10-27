"""Operation history Python is readable and does not copy parameter values."""

from veri_ufku.exports.operation_python import operation_history_python


def test_history_lists_kind_and_version_without_parameter_values():
    secret = "s3cr3t-deger"
    text = operation_history_python(
        [
            {
                "output_version_id": "dv:11111111-1111-1111-1111-111111111111",
                "spec": {
                    "kind": "replace",
                    "input_version_id": "dv:22222222-2222-2222-2222-222222222222",
                    "column_ids": ["col:abc"],
                    "parameters": {
                        "replacement": secret,
                        "token": "hidden-token",
                    },
                },
            }
        ]
    )
    assert "çalıştırılmaz" in text
    assert '"kind": "replace"' in text
    assert "dv:11111111-1111-1111-1111-111111111111" in text
    assert "col:abc" in text
    assert "replacement" in text
    assert secret not in text
    assert "hidden-token" not in text
    assert "token" not in text


def test_empty_history_is_not_invented():
    assert "uydurulmaz" in operation_history_python([])
