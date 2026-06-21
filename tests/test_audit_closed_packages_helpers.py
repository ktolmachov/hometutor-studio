from __future__ import annotations

import datetime
import textwrap

import yaml

from scripts import audit_closed_packages_helpers as ach


def test_dstr_none_empty_and_iso() -> None:
    assert ach.dstr(None) == ""
    assert ach.dstr("") == ""
    d = datetime.date(2026, 4, 15)
    assert ach.dstr(d) == "2026-04-15"
    assert ach.dstr("2026-04-20") == "2026-04-20"


def test_iter_registry_items_prefers_items() -> None:
    data = {
        "packages": [{"id": "from-packages", "status": "closed"}],
        "items": [{"id": "from-items", "status": "closed"}],
    }
    ids = [p.get("id") for p in ach.iter_registry_items(data)]
    assert ids == ["from-items"]


def test_iter_closed_packages_for_month_pyyaml_dates_and_scopes() -> None:
    yml = textwrap.dedent(
        """
        items:
          - id: a-closed
            status: closed
            last_review: 2026-04-10
            blocks: "Hello"
            exit_artifact: "ea-a"
          - id: b-march
            status: closed
            last_review: 2026-03-10
            blocks: "x"
          - id: c-wip
            status: wip
            last_review: 2026-04-10
            blocks: "w"
    """
    )
    data = yaml.safe_load(yml)
    out = list(ach.iter_closed_packages_for_month(data, "2026-04", ["closed"]))
    assert [x["id"] for x in out] == ["a-closed"]
    assert out[0]["title"] == "Hello"
    assert out[0]["date_for_display"].startswith("2026-04")
    assert out[0]["exit_artifact"] == "ea-a"


def test_iter_closed_packages_closed_date_alternative() -> None:
    data = {
        "items": [
            {
                "id": "p1",
                "status": "closed",
                "last_review": None,
                "closed_date": "2026-04-01",
                "notes": "n",
            }
        ]
    }
    out = list(ach.iter_closed_packages_for_month(data, "2026-04", ["closed"]))
    assert len(out) == 1
    assert out[0]["id"] == "p1"


def test_parse_scope_csv() -> None:
    assert ach.parse_scope_csv(" closed , wip , ") == ["closed", "wip"]


def test_find_closed_iteration_headings_for_month() -> None:
    content = textwrap.dedent(
        """
        ## Индекс
        | E1 | 2026-04-13 |

        ### epoch-foo — 2026-04-20
        body

        ### epoch-bar — 2026-05-01
    """
    )
    got = ach.find_closed_iteration_headings_for_month(content, "2026-04")
    assert got == [("epoch-foo", "2026-04-20")]


def test_user_stories_by_package_for_month_items_and_us_id() -> None:
    data = {
        "version": 1,
        "items": [
            {
                "us_id": "US-1.1",
                "covered_by": "pkg-a",
                "closed_date": "2026-04-10",
            },
            {
                "us_id": "US-2.1",
                "covered_by": "pkg-b",
                "closed_date": "2026-04-11",
            },
            {
                "us_id": "US-9.9",
                "covered_by": "pkg-a",
                "closed_date": "2026-05-01",
            },
        ],
    }
    got = ach.user_stories_by_package_for_month(data, "2026-04")
    assert got == {"pkg-a": ["US-1.1"], "pkg-b": ["US-2.1"]}


def test_user_stories_legacy_stories_key_and_id() -> None:
    data = {
        "stories": [
            {
                "id": "US-OLD",
                "covered_by": "legacy-pkg",
                "closed_date": "2026-04-20",
            }
        ]
    }
    got = ach.user_stories_by_package_for_month(data, "2026-04")
    assert got == {"legacy-pkg": ["US-OLD"]}


def test_user_stories_root_list() -> None:
    data = [
        {
            "us_id": "US-L",
            "covered_by": "p",
            "closed_date": "2026-04-01",
        }
    ]
    got = ach.user_stories_by_package_for_month(data, "2026-04")
    assert got == {"p": ["US-L"]}


def test_parse_period_month_two_months_and_exact_days() -> None:
    d = datetime.date
    assert ach.parse_period("2026-04") == (d(2026, 4, 1), d(2026, 4, 30))
    assert ach.parse_period("2026-03..2026-05") == (d(2026, 3, 1), d(2026, 5, 31))
    assert ach.parse_period("2026-04-10..2026-04-12") == (d(2026, 4, 10), d(2026, 4, 12))
    assert ach.parse_period("2026-04-12..2026-04-10") == (d(2026, 4, 10), d(2026, 4, 12))


def test_iter_closed_packages_for_period_exact_dates() -> None:
    data = {
        "items": [
            {
                "id": "in-range",
                "status": "closed",
                "last_review": "2026-04-05",
                "notes": "n",
            },
            {
                "id": "outside",
                "status": "closed",
                "last_review": "2026-04-28",
                "notes": "n",
            },
        ]
    }
    start, end = ach.parse_period("2026-04-01..2026-04-10")
    out = list(ach.iter_closed_packages_for_period(data, start, end, ["closed"]))
    assert [x["id"] for x in out] == ["in-range"]


def test_find_headings_for_period_spans_months() -> None:
    content = "### a — 2026-04-30\n### b — 2026-05-02\n"
    start, end = ach.parse_period("2026-04..2026-05")
    got = ach.find_closed_iteration_headings_for_period(content, start, end)
    assert got == [("a", "2026-04-30"), ("b", "2026-05-02")]


def test_get_registry_item_and_exit_artifact() -> None:
    data = {
        "items": [
            {"id": "x", "status": "closed", "exit_artifact": "path/artifact.md"},
        ]
    }
    assert ach.get_registry_item(data, "x")["status"] == "closed"
    assert ach.get_exit_artifact(data, "x") == "path/artifact.md"
    assert ach.get_registry_item(data, "missing") is None
    assert ach.get_exit_artifact(data, "missing") == "NOT_FOUND"
