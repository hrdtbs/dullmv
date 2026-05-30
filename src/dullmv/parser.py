"""DSL Parser for effect description language."""

import re


def parse_value(s):
    """Parse a single value string into Python object."""
    s = s.strip()
    if not s:
        return ""

    # Double-quoted string (expression or literal)
    if s.startswith('"') and s.endswith('"') and len(s) >= 2:
        return s[1:-1]

    # Single-quoted string
    if s.startswith("'") and s.endswith("'") and len(s) >= 2:
        return s[1:-1]

    # Tuple: ( ... )
    if s.startswith("(") and s.endswith(")"):
        inner = s[1:-1]
        # Split by comma, but respect nested tuples (simple heuristic: no nesting expected)
        parts = [p.strip() for p in inner.split(",")]
        return tuple(parse_value(p) for p in parts if p)

    # List: comma-separated values that are NOT a tuple and NOT a quoted string
    if "," in s:
        parts = [p.strip() for p in s.split(",")]
        return [parse_value(p) for p in parts if p]

    # Number
    try:
        if "." in s or "e" in s.lower():
            return float(s)
        return int(s)
    except ValueError:
        pass

    # Bare identifier / unquoted string
    return s


def parse_dsl(text):
    """Parse DSL text into a structured dict.

    Returns:
        {
            "globals": { key: value, ... },
            "effects": [
                {"_name": "effect_name", ...},
                ...
            ]
        }
    """
    lines = text.split("\n")
    root = {"globals": {}, "effects": []}
    stack = []  # Stack of containers (dicts)
    current = root["globals"]

    i = 0
    while i < len(lines):
        line = lines[i]
        # Remove comment
        if "#" in line:
            line = line[: line.index("#")]
        line = line.strip()
        if not line:
            i += 1
            continue

        # Block start detection
        # Patterns:
        #   effect name {
        #   name {
        if line.endswith("{"):
            prefix = line[:-1].strip()
            parts = prefix.split()
            if len(parts) >= 2 and parts[0] == "effect":
                # effect <name> {
                effect_name = parts[1]
                effect_def = {"_name": effect_name}
                root["effects"].append(effect_def)
                stack.append(current)
                current = effect_def
            else:
                # Sub-block: <name> {
                block_name = parts[0]
                new_block = {}
                if block_name in current:
                    existing = current[block_name]
                    if isinstance(existing, list):
                        existing.append(new_block)
                    else:
                        current[block_name] = [existing, new_block]
                else:
                    current[block_name] = new_block
                stack.append(current)
                current = new_block
            i += 1
            continue

        if line == "}":
            if stack:
                current = stack.pop()
            i += 1
            continue

        # Key-value pair
        # Split by first whitespace
        m = re.match(r"(\S+)\s+(.*)", line)
        if m:
            key = m.group(1)
            value_str = m.group(2).strip()
            value = parse_value(value_str)
        else:
            key = line
            value = True  # Flag-style key without value

        if key in current:
            existing = current[key]
            if isinstance(existing, list):
                existing.append(value)
            else:
                current[key] = [existing, value]
        else:
            current[key] = value

        i += 1

    return root


def parse_file(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    return parse_dsl(text)
