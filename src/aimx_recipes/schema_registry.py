"""Packaged schema loader, offline reference registry, and version dispatch."""

from __future__ import annotations

import importlib.resources
import json
from importlib.resources.abc import Traversable
from typing import Any
from jsonschema import Draft202012Validator, FormatChecker, validators
from referencing import Registry, Resource
from referencing.exceptions import NoSuchResource
from referencing.jsonschema import DRAFT202012

SUPPORTED_SCHEMA_VERSIONS = frozenset(["2.0.0"])


def _is_exact_integer(checker, instance: Any) -> bool:
    return isinstance(instance, int) and not isinstance(instance, bool)


def _is_exact_number(checker, instance: Any) -> bool:
    return (isinstance(instance, (int, float)) and not isinstance(instance, bool))


STRICT_TYPE_CHECKER = (
    Draft202012Validator.TYPE_CHECKER
    .redefine("integer", _is_exact_integer)
    .redefine("number", _is_exact_number)
)

StrictDraft202012Validator = validators.extend(
    Draft202012Validator,
    type_checker=STRICT_TYPE_CHECKER,
)


def _find_schemas_root() -> Traversable:
    """Use the same package resources for editable and wheel installations."""
    candidate = importlib.resources.files("aimx_recipes") / "_schemas"
    if not candidate.is_dir():
        raise RuntimeError("Packaged schema resources could not be found.")
    return candidate


class SchemaRegistry:
    """Manages closed offline schema registries and validators for supported versions."""

    def __init__(self) -> None:
        self._schemas_root = _find_schemas_root()
        self._raw_resources: dict[str, dict[str, Any]] = {}
        self._registry: Registry = Registry()
        self._validators: dict[tuple[str, str], StrictDraft202012Validator] = {}
        self._load_all_resources()

    def _load_all_resources(self) -> None:
        """Load and index all versioned schema and json files into the closed registry."""
        registry = Registry()
        for version in SUPPORTED_SCHEMA_VERSIONS:
            version_dir = self._schemas_root / version
            if not version_dir.is_dir():
                continue
            for file_path in sorted(version_dir.iterdir(), key=lambda item: item.name):
                if not file_path.name.endswith(".json"):
                    continue
                with file_path.open("r", encoding="utf-8") as f:
                    content = json.load(f)
                self._raw_resources[f"{version}:{file_path.name}"] = content
                schema_id = content.get("$id")
                if schema_id:
                    resource = Resource.from_contents(content, default_specification=DRAFT202012)
                    registry = registry.with_resource(schema_id, resource)

        self._registry = registry
        for version in sorted(SUPPORTED_SCHEMA_VERSIONS):
            for name in ("facet-vocabulary", "action-taxonomy"):
                schema = self.get_raw_resource(version, f"{name}.schema.json")
                data = self.get_raw_resource(version, f"{name}.json")
                StrictDraft202012Validator(
                    schema, registry=registry, format_checker=FormatChecker(),
                ).validate(data)

    @property
    def registry(self) -> Registry:
        return self._registry

    def get_raw_resource(self, version: str, filename: str) -> dict[str, Any]:
        key = f"{version}:{filename}"
        if key not in self._raw_resources:
            raise KeyError(f"Resource {key} not found in registry.")
        return self._raw_resources[key]

    def get_entity_schema(self, entity_type: str, version: str = "2.0.0") -> dict[str, Any]:
        filename = f"{entity_type}.schema.json"
        return self.get_raw_resource(version, filename)

    def get_vocabulary_data(self, version: str = "2.0.0") -> dict[str, Any]:
        return self.get_raw_resource(version, "facet-vocabulary.json")

    def get_taxonomy_data(self, version: str = "2.0.0") -> dict[str, Any]:
        return self.get_raw_resource(version, "action-taxonomy.json")

    def get_release_data(self, version: str = "2.0.0") -> dict[str, Any]:
        return self.get_raw_resource(version, "release.json")

    def get_validator(self, entity_type: str, version: str = "2.0.0") -> StrictDraft202012Validator:
        cache_key = (entity_type, version)
        if cache_key in self._validators:
            return self._validators[cache_key]

        schema = self.get_entity_schema(entity_type, version)
        validator = StrictDraft202012Validator(schema, registry=self._registry, format_checker=FormatChecker())
        self._validators[cache_key] = validator
        return validator


_GLOBAL_REGISTRY: SchemaRegistry | None = None


def get_global_registry() -> SchemaRegistry:
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = SchemaRegistry()
    return _GLOBAL_REGISTRY
