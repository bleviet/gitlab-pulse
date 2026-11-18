"""Characterization of ``sort_hierarchy``: order and indentation of the rows."""

import pandas as pd

from app.dashboard.utils import sort_hierarchy


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": [13, 11, 15, 12, 14],
            "iid": [3, 1, 5, 2, 4],
            "parent_id": [12, None, 99, 11, 11],
            "title": ["grandchild", "root", "orphan", "child", "other child"],
        },
        index=[40, 30, 20, 10, 50],
    )


def test_children_follow_their_parent_in_original_order() -> None:
    result = sort_hierarchy(_frame())

    assert result["iid"].tolist() == [1, 2, 3, 4, 5]
    assert result.index.tolist() == [30, 10, 40, 50, 20]


def test_children_are_indented_by_depth() -> None:
    result = sort_hierarchy(_frame())

    assert result["title"].tolist() == [
        "root",
        "    ↳ child",
        "        ↳ grandchild",
        "    ↳ other child",
        "orphan",
    ]


def test_frame_without_parent_column_is_returned_unchanged() -> None:
    frame = _frame().drop(columns="parent_id")

    assert sort_hierarchy(frame) is frame


def test_empty_frame_is_returned_unchanged() -> None:
    frame = _frame().iloc[0:0]

    assert sort_hierarchy(frame) is frame


def test_root_title_is_converted_with_str() -> None:
    frame = pd.DataFrame({"id": [1], "parent_id": [None], "title": [123]})

    assert sort_hierarchy(frame)["title"].tolist() == ["123"]
