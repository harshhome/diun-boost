import re


def regex_gte(n: int) -> str:
    """Generate a regex pattern that matches numbers greater than or equal to n.

    Args:
        n (int): The number to compare against.

    Returns:
        str: A regex pattern that matches numbers greater than or equal to n.
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


def generate_version_regex(version: str) -> str:
    """Generate a regex pattern for current or higher semver version.

    Args:
        version (str): The version string to generate the regex for.

    Returns:
        str: A regex pattern that matches the specified version or higher.
    """
    version_prefix = "v" if version.startswith("v") else ""
    version = version.lstrip("v")
    parts = version.split(".")
    depth = len(parts)

    if depth == 1:
        major = int(parts[0])
        major_gt = regex_gte(major)
        return rf"^{version_prefix}({major_gt})$"

    elif depth == 2:
        major, minor = map(int, parts)
        minor_gt = regex_gte(minor)
        major_gt = regex_gte(major + 1)
        return (
            rf"^{version_prefix}({major}\.{minor_gt}"
            rf"|{major_gt}\.\d+)$"
        )

    elif depth == 3:
        major, minor, patch = map(int, parts)
        patch_gt = regex_gte(patch)
        minor_gt = regex_gte(minor + 1)
        major_gt = regex_gte(major + 1)

        return (
            rf"^{version_prefix}({major}\.{minor}\.{patch_gt}"
            rf"|{major}\.{minor_gt}\.\d+"
            rf"|{major_gt}\.\d+\.\d+)$"
        )
    else:
        raise ValueError("Unsupported version format.")
