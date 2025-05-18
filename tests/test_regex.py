import re

import pytest

from app.regex_helper import (build_tag_regex, build_ver_regex, regex_gt,
                              regex_gte)


def regex_test_helper_fn(item, should_match, should_not_match, pattern):
    for s in should_match:
        assert pattern.match(s), \
            f"Expected '{s}' to match regex for '{item}'"
    for s in should_not_match:
        assert not pattern.match(s), \
            f"Did NOT expect '{s}' to match regex for '{item}'"


test_versions = [
    (
        "12", regex_gte, "Major, GTE",
        ["12", "13", "123", "999"],
        ["11", "10", "1", "0", "12.0", "12.1"]
    ),
    (
        "12", regex_gt, "Major, GT",
        ["13", "123", "999"],
        ["12", "11", "10", "1", "0", "12.0", "12.1"]
    ),
    (
        "2.1", regex_gte, "Major.Minor, GTE",
        ["2.1", "2.2", "3.0", "10.0"],
        ["2.0", "1.9", "1.0", "2.0.1", "2.1.1"]
    ),
    (
        "2.1", regex_gt, "Major.Minor, GT",
        ["2.2", "3.0", "10.0"],
        ["2.1", "2.0", "1.9", "1.0", "2.0.1", "2.1.1"]
    ),
    (
        "1.2.3", regex_gte, "Major.Minor.Patch, GTE",
        ["1.2.3", "1.2.4", "1.3.0", "2.0.0"],
        ["1.2.2", "1.1.9", "0.9.9", "1.2.3.1"]
    ),
    (
        "1.2.3", regex_gt, "Major.Minor.Patch, GT",
        ["1.2.4", "1.3.0", "2.0.0"],
        ["1.2.3", "1.2.2", "1.1.9", "0.9.9", "1.2.3.1"]
    ),
    (
        "3.4.5.6", regex_gte, "Major.Minor.Patch.Build, GTE",
        ["3.4.5.6", "3.4.5.7", "3.4.6.0", "3.5.0.0", "4.0.0.0"],
        ["3.4.5.5", "3.4.4.9", "2.9.9.9"]
    ),
    (
        "3.4.5.6", regex_gt, "Major.Minor.Patch.Build, GT",
        ["3.4.5.7", "3.4.6.0", "3.5.0.0", "4.0.0.0"],
        ["3.4.5.6", "3.4.5.5", "3.4.4.9", "2.9.9.9"]
    ),
]

test_tags_valid = [
    (
        "2.1.4", "Major.Minor.Patch",
        ["2.1.4", "2.1.5", "2.2.0", "3.0.0"],
        ["2.1.3", "1.0.0", "v2.1.4", "v2.1.4-alpine", "v2.1.4-alpine3.18"]
    ),
    (
        "2.1", "Major.Minor",
        ["2.1", "2.2", "3.0"],
        ["2.0", "1.0", "2.1.5", "v2.1", "v2.1-alpine", "v2.1-alpine3.18"]
    ),
    (
        "2", "Major",
        ["2", "3"],
        ["1", "0", "2.1", "v2", "v2-alpine", "v2-alpine3.18"]
    ),
    (
        "1.0.0-alpine", "Major.Minor.Patch-suffix",
        ["1.0.0-alpine", "1.0.1-alpine", "1.1.0-alpine", "2.0.0-alpine"],
        ["1.0.0", "1.0.0-alpine3.18", "v1.0.0-alpine"]
    ),
    (
        "v1.0.0", "vMajor.Minor.Patch",
        ["v1.0.0", "v1.0.1", "v1.1.0", "v2.0.0"],
        ["1.0.0", "v1.0.0-alpine", "v1.0.0-alpine3.18"]
    ),
    (
        "v1.0.0-alpine3.18", "vMajor.Minor.Patch-suffix-version",
        ["v1.0.0-alpine3.18", "v1.0.1-alpine3.18", "v1.1.0-alpine3.18",
         "v2.0.0-alpine3.18", "v1.0.0-alpine3.19", "v1.2.0-alpine3.17"],
        ["v1.0.0-alpine", "v1.0.0", "1.0.0-alpine3.18", "v1.0.0-alpine3.18.1",
         "v1.0.0-alpine3.18-rc1", "v1.0.0-alpine3.18-beta"]
    ),
    (
        "pg14-v0.2.0", "prefix-Major.Minor.Patch",
        ["pg14-v0.2.0", "pg14-v0.2.1", "pg14-v0.3.0", "pg14-v1.0.0"],
        ["pg13-v0.2.0", "pg14-v0.1.9", "pg14-v0.2.0-alpine"]
    ),
    (
        "8-bookworm", "Major-suffix",
        ["8-bookworm", "9-bookworm", "10-bookworm"],
        ["7-bookworm", "8-bullseye", "8"]
    ),
]

test_versions_ids = [test[2] for test in test_versions]
test_tags_ids = [test[1] for test in test_tags_valid]


@pytest.mark.parametrize(
    "version, cmp_func, test_name, should_match, should_not_match",
    test_versions,
    ids=test_versions_ids
)
def test_build_ver_regex(version, cmp_func, test_name,
                                should_match, should_not_match):
    pattern = re.compile(f"^{build_ver_regex(version, cmp_func)}$")
    regex_test_helper_fn(version, should_match, should_not_match, pattern)


@pytest.mark.parametrize(
    "tag, test_name, should_match, should_not_match",
    test_tags_valid,
    ids=test_tags_ids
)
def test_build_tag_regex(tag, test_name, should_match, should_not_match):
    regex = build_tag_regex(tag)
    assert regex is not None, f"Regex should not be None for tag: {tag}"
    pattern = re.compile(regex)
    regex_test_helper_fn(tag, should_match, should_not_match, pattern)


@pytest.mark.parametrize("invalid_tag", [
    "not-a-version",
    "v",
    "alpine",
    "latest",
    "beta",
    "latest-alpine",
    "foo-bar",
    "1..0",
    "1.0..0",
    "1.0.0..1",
])
def test_build_tag_regex_invalid(invalid_tag):
    regex = build_tag_regex(invalid_tag)
    assert regex is None, f"Expected None for invalid tag: {invalid_tag}"
