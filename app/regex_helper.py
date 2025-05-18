import re
from typing import Callable


def regex_gt(n: int) -> str:
    """Generate regex pattern that matches numbers strictly greater than n.

    Args:
        n (int): The number to compare against.

    Returns:
        str: A regex pattern that matches numbers strictly greater than n.
    """
    n_str = str(n)
    patterns = []

    for i in range(len(n_str)):
        prefix = n_str[:i]
        current_digit = int(n_str[i])
        if current_digit < 9:
            greater_range = f"[{current_digit + 1}-9]"
            suffix = r"\d" * (len(n_str) - i - 1)
            patterns.append(f"{prefix}{greater_range}{suffix}")

    patterns.append(r"\d{" + str(len(n_str) + 1) + r",}")
    return "(?:" + "|".join(patterns) + ")"


def regex_gte(n: int) -> str:
    """Generate regex pattern that matches numbers greater or equal to n.

    Args:
        n (int): The number to compare against.

    Returns:
        str: A regex pattern that matches numbers greater or equal to n.
    """
    n_str = str(n)
    patterns = [re.escape(n_str)]

    for i in range(len(n_str)):
        prefix = n_str[:i]
        current_digit = int(n_str[i])
        if current_digit < 9:
            greater_range = f"[{current_digit + 1}-9]"
            suffix = r"\d" * (len(n_str) - i - 1)
            patterns.append(f"{prefix}{greater_range}{suffix}")

    patterns.append(r"\d{" + str(len(n_str) + 1) + r",}")
    return "(?:" + "|".join(patterns) + ")"


def build_ver_regex(version: str, cmp_func: Callable[[int], str]) -> str:
    """Generate a regex pattern for current or higher semver version.

    Args:
        version (str): The version string to generate the regex for.
        cmp_func (Callable[[int], str]): 
            The comparison function to use (regex_gt or regex_gte).

    Returns:
        str: A regex pattern that matches the specified version or higher.
    """
    parts = [int(p) for p in version.split(".")]
    rparts = [cmp_func(p) for p in parts]
    hparts = [cmp_func(p+1) if cmp_func == regex_gte else cmp_func(p)
              for p in parts]

    depth = len(parts)
    patterns = [""] * depth
    for i in range(depth):
        prefix = ".".join(str(parts[j]) for j in range(i))

        if i == depth - 1:
            current = rparts[i]
        else:
            current = hparts[i]

        suffix = "".join(rf"\.\d+" for _ in range(depth - i - 1))

        if prefix:
            patterns[i] = rf"{prefix}\.{current}{suffix}"
        else:
            patterns[i] = rf"{current}{suffix}"

    pattern = "|".join(patterns)
    pattern = "(" + pattern + ")"
    return pattern


def build_tag_regex(tag: str) -> str:
    """Generate a regex pattern for the given tag.

    Args:
        tag (str): The tag string to generate the regex for.

    Returns:
        str: A regex pattern that matches the specified tag.
    """
    pattern = (
        r"^([a-zA-Z]+-?)?"
        r"(\d+(?:\.\d+)*)"
        r"(?:-([a-zA-Z]+[.-]?)?"
        r"(?:[.-]?(\d+(?:\.\d+)*))?)?$"
    )
    parts = re.match(pattern, tag)

    if parts:
        prefix, version, suffix, suffix_version = (
            p or "" for p in parts.groups()
        )
        suffix = f"-{suffix}" if suffix or suffix_version else ""
        version_gte_regex = build_ver_regex(version, regex_gte)
        if suffix_version:
            suffix_gte_regex = build_ver_regex(suffix_version, regex_gte)
            suffix_all_regex = r"\.".join(
                [r"\d+" for _ in suffix_version.split(".")]
            )
            version_gt_regex = build_ver_regex(version, regex_gt)
            version_same_regex = (
                rf"{prefix}({r'\.'.join(version.split('.'))})"
                f"{suffix}{suffix_gte_regex}"
            )
            higher_version_regex = (
                rf"{prefix}{version_gt_regex}{suffix}{suffix_all_regex}"
            )
            return rf"^({version_same_regex}|{higher_version_regex})$"
        return rf"^{prefix}{version_gte_regex}{suffix}$"
    else:
        return None
