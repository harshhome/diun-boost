import re
import pytest

from app.regex_helper import regex_gte, generate_version_regex


@pytest.mark.parametrize(
    "n, should_match, should_not_match", [
    (5, ["5", "6", "7", "8", "9", "10", "99", "123"], ["0", "1", "4"]),
    (99, ["99", "100", "101"], ["0", "98", "10", "50"]),
    (123, ["123", "124", "999", "1000"], ["0", "10", "122"]),
])
def test_regex_gte(n, should_match, should_not_match):
    pattern = re.compile(f"^{regex_gte(n)}$")

    for number in should_match:
        assert pattern.match(number), \
            f"Expected {number} to match {pattern.pattern}"
    
    for number in should_not_match:
        assert not pattern.match(number), \
            f"Did NOT expect {number} to match {pattern.pattern}"


@pytest.mark.parametrize(
    "version, should_match, should_not_match", [
    ("1", ["1", "2", "10", "99"], ["0"]),
    ("1.2", ["1.2", "1.3", "2.0", "5.9"], ["1.0", "1.1", "0.9"]),
    ("2.5.7", ["2.5.7", "2.5.8", "2.6.0", "3.0.0"], ["2.5.6", "2.4.9", "1.9.9"]),
    ("v3.3.4", ["v3.3.4", "v3.3.5", "v3.4.0", "v4.0.0"], ["v3.3.3", "v3.2.9", "v2.9.9"]),
    ("2025.1.1", ["2025.1.1", "2025.1.2", "2025.2.0", "2026.0.0"], ["2025.0.9", "2024.12.31"]),
])
def test_generate_version_regex(version, should_match, should_not_match):
    pattern = re.compile(generate_version_regex(version))

    for ver in should_match:
        assert pattern.match(ver), \
            f"Expected {ver} to match {pattern.pattern}"
    
    for ver in should_not_match:
        assert not pattern.match(ver), \
            f"Did NOT expect {ver} to match {pattern.pattern}"
