"""Strict YAML loader that preserves strings and rejects duplicate keys."""

from pathlib import Path
from typing import Any
import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode


class StrictYAMLError(Exception):
    """Raised when strict YAML parsing or validation fails."""

    def __init__(
        self, message: str, line: int | None = None, column: int | None = None
    ):
        super().__init__(message)
        self.line = line
        self.column = column


class StrictLoader(yaml.SafeLoader):
    """PyYAML SafeLoader subclass with strict string preservation and duplicate key checks."""

    def construct_mapping(
        self, node: MappingNode, deep: bool = False
    ) -> dict[str, Any]:
        if not isinstance(node, MappingNode):
            raise ConstructorError(
                None,
                None,
                f"expected a mapping node, but found {node.id}",
                node.start_mark,
            )
        mapping: dict[str, Any] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            line = key_node.start_mark.line + 1 if key_node.start_mark else None
            col = key_node.start_mark.column + 1 if key_node.start_mark else None
            if not isinstance(key, str):
                raise StrictYAMLError(
                    f"Mapping keys must be strings, got {type(key).__name__} at line {line}, column {col}",
                    line=line,
                    column=col,
                )
            if key in mapping:
                raise StrictYAMLError(
                    f"Duplicate key '{key}' found at line {line}, column {col}",
                    line=line,
                    column=col,
                )
            value = self.construct_object(value_node, deep=deep)
            mapping[key] = value
        return mapping


# Keep only null implicit resolver so all other scalars (numbers, booleans, dates) stay strings
_null_resolvers: dict[str, list[tuple[str, Any]]] = {}
for ch, resolver_list in yaml.SafeLoader.yaml_implicit_resolvers.items():
    kept = [r for r in resolver_list if r[0] == "tag:yaml.org,2002:null"]
    if kept:
        _null_resolvers[ch] = kept
StrictLoader.yaml_implicit_resolvers = _null_resolvers


def load_strict_yaml(text_or_path: str | Path) -> Any:
    """Load YAML strictly from text or a file path.

    - Rejects duplicate keys with line and column information.
    - Preserves scalars (booleans, numbers, dates) as strings.
    - Resolves null / ~ to None.
    - Rejects non-string mapping keys.
    """
    if isinstance(text_or_path, Path):
        try:
            content = text_or_path.read_text(encoding="utf-8")
        except OSError as e:
            raise StrictYAMLError(f"Failed to read file {text_or_path}: {e}") from e
    else:
        content = text_or_path

    try:
        return yaml.load(content, Loader=StrictLoader)
    except StrictYAMLError:
        raise
    except yaml.YAMLError as e:
        line = getattr(e, "problem_mark", None)
        line_num = line.line + 1 if line else None
        col_num = line.column + 1 if line else None
        raise StrictYAMLError(
            f"YAML parse error: {e}", line=line_num, column=col_num
        ) from e
