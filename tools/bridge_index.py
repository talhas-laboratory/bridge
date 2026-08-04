#!/usr/bin/env python3
"""Automatic bridge module/feature indexer.

Scans the repository, categorizes core vs extension surfaces, and writes:
  - docs/bridge-index.json  (machine-readable)
  - docs/BRIDGE_INDEX.md    (human-readable)

Stdlib only. Safe to run without network. Prefer regenerating after any
feature, extension, schema, or example change.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src" / "reasoning_bridge"
SCHEMA_ROOT = REPO_ROOT / "schemas" / "v1"
EXAMPLES_ROOT = REPO_ROOT / "examples"
DOCS_ROOT = REPO_ROOT / "docs"
INDEX_JSON = DOCS_ROOT / "bridge-index.json"
INDEX_MD = DOCS_ROOT / "BRIDGE_INDEX.md"

CORE_MODULES = frozenset(
    {
        "__init__",
        "adapters",
        "behaviors",
        "contracts",
        "policy",
        "routing",
        "runtime",
    }
)

CATEGORY_ORDER = (
    "core",
    "extension_hook",
    "extension",
    "schema",
    "example",
    "docs",
    "tooling",
)


@dataclass
class SymbolInfo:
    name: str
    kind: str
    qualname: str = ""
    bases: tuple[str, ...] = ()
    docstring: str = ""


@dataclass
class ModuleInfo:
    module_id: str
    path: str
    category: str
    subcategory: str
    layer: str
    summary: str = ""
    exports: tuple[str, ...] = ()
    symbols: tuple[SymbolInfo, ...] = ()
    tags: tuple[str, ...] = ()
    last_commit: str = ""
    last_commit_date: str = ""
    last_commit_subject: str = ""


@dataclass
class AssetInfo:
    asset_id: str
    path: str
    category: str
    subcategory: str
    summary: str = ""
    tags: tuple[str, ...] = ()
    related_modules: tuple[str, ...] = ()
    last_commit: str = ""
    last_commit_date: str = ""
    last_commit_subject: str = ""


@dataclass
class BridgeIndex:
    generated_at: str
    package: str
    version: str
    categories: dict[str, list[str]] = field(default_factory=dict)
    modules: list[ModuleInfo] = field(default_factory=list)
    assets: list[AssetInfo] = field(default_factory=list)
    extensions: list[str] = field(default_factory=list)
    update_log: list[dict[str, str]] = field(default_factory=list)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _first_docstring(tree: ast.AST) -> str:
    doc = ast.get_docstring(tree) or ""
    return " ".join(doc.strip().split())


def _base_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return node.__class__.__name__


def _extract_symbols(tree: ast.AST, module_id: str) -> tuple[SymbolInfo, ...]:
    symbols: list[SymbolInfo] = []
    for node in tree.body if isinstance(tree, ast.Module) else []:
        if isinstance(node, ast.ClassDef):
            symbols.append(
                SymbolInfo(
                    name=node.name,
                    kind="class",
                    qualname=f"{module_id}.{node.name}",
                    bases=tuple(_base_name(base) for base in node.bases),
                    docstring=_first_docstring(node),
                )
            )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                symbols.append(
                    SymbolInfo(
                        name=node.name,
                        kind="function",
                        qualname=f"{module_id}.{node.name}",
                        docstring=_first_docstring(node),
                    )
                )
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    symbols.append(
                        SymbolInfo(
                            name=target.id,
                            kind="constant",
                            qualname=f"{module_id}.{target.id}",
                        )
                    )
    return tuple(symbols)


def _extract_all(tree: ast.AST) -> tuple[str, ...]:
    for node in tree.body if isinstance(tree, ast.Module) else []:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    try:
                        value = ast.literal_eval(node.value)
                    except Exception:
                        return ()
                    if isinstance(value, (list, tuple)):
                        return tuple(str(item) for item in value)
    return ()


def _git_last_commit(path: Path) -> tuple[str, str, str]:
    try:
        completed = subprocess.run(
            [
                "git",
                "log",
                "-1",
                "--format=%H%x09%cI%x09%s",
                "--",
                str(path.relative_to(REPO_ROOT)),
            ],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return "", "", ""
    if completed.returncode != 0 or not completed.stdout.strip():
        return "", "", ""
    parts = completed.stdout.strip().split("\t", 2)
    if len(parts) != 3:
        return "", "", ""
    return parts[0][:12], parts[1], parts[2]


def _git_update_log(limit: int = 20) -> list[dict[str, str]]:
    try:
        completed = subprocess.run(
            ["git", "log", f"-{limit}", "--format=%h%x09%cI%x09%s"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return []
    if completed.returncode != 0:
        return []
    rows: list[dict[str, str]] = []
    for line in completed.stdout.splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        rows.append({"commit": parts[0], "date": parts[1], "subject": parts[2]})
    return rows


def _package_version() -> str:
    text = _read_text(REPO_ROOT / "pyproject.toml")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, flags=re.MULTILINE)
    return match.group(1) if match else "0.0.0"


def _module_id_for(path: Path) -> str:
    rel = path.relative_to(SRC_ROOT)
    parts = list(rel.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(("reasoning_bridge", *parts)) if parts else "reasoning_bridge"


def _classify_python_module(path: Path) -> tuple[str, str, str, tuple[str, ...]]:
    rel = path.relative_to(SRC_ROOT)
    parts = rel.parts
    if len(parts) == 1:
        name = path.stem
        if name in CORE_MODULES or name == "__init__":
            return "core", name if name != "__init__" else "package", "core", ("core",)
        return "core", name, "core", ("core", "uncategorized")
    if parts[0] == "extensions":
        if len(parts) == 2 and parts[1] == "__init__.py":
            return "extension_hook", "plan_extension", "extensions", ("extension", "hook")
        if len(parts) >= 2:
            ext_name = parts[1]
            sub = path.stem if path.stem != "__init__" else "package"
            return "extension", f"{ext_name}.{sub}", f"extension:{ext_name}", ("extension", ext_name)
    return "core", "/".join(parts), "core", ("core",)


def _tags_for_symbols(symbols: Iterable[SymbolInfo]) -> tuple[str, ...]:
    tags: set[str] = set()
    for symbol in symbols:
        lowered = symbol.name.lower()
        if symbol.name.endswith("Extension") or "PlanExtension" in symbol.bases:
            tags.add("plan-extension")
        if symbol.name.endswith("Port"):
            tags.add("adapter-port")
        if symbol.name.endswith("Registry"):
            tags.add("registry")
        if symbol.name.endswith("Runtime"):
            tags.add("runtime")
        if "recipe" in lowered:
            tags.add("recipe")
        if "packet" in lowered:
            tags.add("packet")
        if "policy" in lowered:
            tags.add("policy")
        if symbol.kind == "class" and "JsonRecord" in symbol.bases:
            tags.add("contract")
    return tuple(sorted(tags))


def scan_modules() -> list[ModuleInfo]:
    modules: list[ModuleInfo] = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        if path.name == "__pycache__" or "__pycache__" in path.parts:
            continue
        source = _read_text(path)
        tree = ast.parse(source, filename=str(path))
        module_id = _module_id_for(path)
        category, subcategory, layer, base_tags = _classify_python_module(path)
        exports = _extract_all(tree)
        symbols = _extract_symbols(tree, module_id)
        commit, date, subject = _git_last_commit(path)
        tags = tuple(sorted(set(base_tags) | set(_tags_for_symbols(symbols))))
        modules.append(
            ModuleInfo(
                module_id=module_id,
                path=str(path.relative_to(REPO_ROOT)),
                category=category,
                subcategory=subcategory,
                layer=layer,
                summary=_first_docstring(tree),
                exports=exports,
                symbols=symbols,
                tags=tags,
                last_commit=commit,
                last_commit_date=date,
                last_commit_subject=subject,
            )
        )
    return modules


def _schema_subcategory(name: str) -> str:
    if name.startswith(("packet-", "context-packet")):
        return "extension:packet"
    if name.startswith(("lens-", "world-manifest", "definition-binding")):
        return "extension:progressive"
    return "core"


def _example_subcategory(name: str) -> str:
    if "progressive" in name:
        return "extension:progressive"
    if "packet" in name:
        return "extension:packet"
    return "core"


def _doc_subcategory(name: str) -> str:
    lowered = name.lower()
    if "progressive" in lowered:
        return "extension:progressive"
    if "packet" in lowered:
        return "extension:packet"
    if name.upper().startswith("BRIDGE_INDEX") or name.startswith("bridge-index"):
        return "index"
    return "general"


def scan_assets() -> list[AssetInfo]:
    assets: list[AssetInfo] = []

    if SCHEMA_ROOT.exists():
        for path in sorted(SCHEMA_ROOT.glob("*.json")):
            commit, date, subject = _git_last_commit(path)
            data = json.loads(_read_text(path))
            assets.append(
                AssetInfo(
                    asset_id=f"schema:{path.stem}",
                    path=str(path.relative_to(REPO_ROOT)),
                    category="schema",
                    subcategory=_schema_subcategory(path.name),
                    summary=str(data.get("title") or path.stem),
                    tags=("schema", "protocol"),
                    related_modules=(
                        ("reasoning_bridge.contracts",)
                        if _schema_subcategory(path.name) == "core"
                        else (
                            ("reasoning_bridge.extensions.progressive",)
                            if _schema_subcategory(path.name) == "extension:progressive"
                            else ("reasoning_bridge.extensions.packet",)
                        )
                    ),
                    last_commit=commit,
                    last_commit_date=date,
                    last_commit_subject=subject,
                )
            )

    if EXAMPLES_ROOT.exists():
        for path in sorted(EXAMPLES_ROOT.glob("*.py")):
            commit, date, subject = _git_last_commit(path)
            tree = ast.parse(_read_text(path), filename=str(path))
            assets.append(
                AssetInfo(
                    asset_id=f"example:{path.stem}",
                    path=str(path.relative_to(REPO_ROOT)),
                    category="example",
                    subcategory=_example_subcategory(path.stem),
                    summary=_first_docstring(tree) or f"Example script `{path.name}`",
                    tags=("example",),
                    related_modules=(),
                    last_commit=commit,
                    last_commit_date=date,
                    last_commit_subject=subject,
                )
            )

    if DOCS_ROOT.exists():
        for path in sorted(DOCS_ROOT.glob("*.md")):
            if path.name == "BRIDGE_INDEX.md":
                continue
            commit, date, subject = _git_last_commit(path)
            first_line = next((line.strip("# ").strip() for line in _read_text(path).splitlines() if line.strip()), path.stem)
            assets.append(
                AssetInfo(
                    asset_id=f"docs:{path.stem}",
                    path=str(path.relative_to(REPO_ROOT)),
                    category="docs",
                    subcategory=_doc_subcategory(path.name),
                    summary=first_line,
                    tags=("docs",),
                    related_modules=(),
                    last_commit=commit,
                    last_commit_date=date,
                    last_commit_subject=subject,
                )
            )

    tools_dir = REPO_ROOT / "tools"
    if tools_dir.exists():
        for path in sorted(tools_dir.glob("*.py")):
            commit, date, subject = _git_last_commit(path)
            tree = ast.parse(_read_text(path), filename=str(path))
            assets.append(
                AssetInfo(
                    asset_id=f"tool:{path.stem}",
                    path=str(path.relative_to(REPO_ROOT)),
                    category="tooling",
                    subcategory="index" if "index" in path.stem else "tool",
                    summary=_first_docstring(tree) or f"Tool `{path.name}`",
                    tags=("tooling",),
                    related_modules=(),
                    last_commit=commit,
                    last_commit_date=date,
                    last_commit_subject=subject,
                )
            )

    agents = REPO_ROOT / "AGENTS.md"
    if agents.exists():
        commit, date, subject = _git_last_commit(agents)
        assets.append(
            AssetInfo(
                asset_id="docs:AGENTS",
                path="AGENTS.md",
                category="docs",
                subcategory="agent-guidance",
                summary="Agent working rules for modular bridge development",
                tags=("docs", "agents", "modularity"),
                related_modules=("reasoning_bridge.extensions",),
                last_commit=commit,
                last_commit_date=date,
                last_commit_subject=subject,
            )
        )
    return assets


def build_index() -> BridgeIndex:
    modules = scan_modules()
    assets = scan_assets()
    extensions = sorted(
        {
            module.layer.removeprefix("extension:")
            for module in modules
            if module.category == "extension" and module.layer.startswith("extension:")
        }
    )
    categories: dict[str, list[str]] = {key: [] for key in CATEGORY_ORDER}
    for module in modules:
        categories.setdefault(module.category, []).append(module.module_id)
    for asset in assets:
        categories.setdefault(asset.category, []).append(asset.asset_id)
    for key, values in categories.items():
        categories[key] = sorted(set(values))
    return BridgeIndex(
        generated_at=datetime.now(timezone.utc).isoformat(),
        package="reasoning-bridge",
        version=_package_version(),
        categories=categories,
        modules=modules,
        assets=assets,
        extensions=extensions,
        update_log=_git_update_log(),
    )


def _md_escape(text: str) -> str:
    return text.replace("|", "\\|")


def render_markdown(index: BridgeIndex) -> str:
    lines: list[str] = [
        "# Bridge Index",
        "",
        "Automatically generated catalog of Reasoning Bridge modules, extensions,",
        "schemas, examples, and recent updates.",
        "",
        f"- Generated at: `{index.generated_at}`",
        f"- Package version: `{index.version}`",
        f"- Known extensions: {', '.join(f'`{name}`' for name in index.extensions) or '_none_'}",
        "",
        "Regenerate with:",
        "",
        "```bash",
        "python tools/bridge_index.py",
        "```",
        "",
        "## Category map",
        "",
        "| Category | Entries |",
        "|---|---|",
    ]
    for category in CATEGORY_ORDER:
        entries = index.categories.get(category, [])
        lines.append(f"| `{category}` | {len(entries)} |")

    lines.extend(["", "## Modules", ""])
    by_category: dict[str, list[ModuleInfo]] = {}
    for module in index.modules:
        by_category.setdefault(module.category, []).append(module)

    for category in CATEGORY_ORDER:
        modules = by_category.get(category, [])
        if not modules:
            continue
        lines.append(f"### {category}")
        lines.append("")
        lines.append("| Module | Layer | Summary | Tags | Last update |")
        lines.append("|---|---|---|---|---|")
        for module in modules:
            summary = _md_escape(module.summary[:120] + ("…" if len(module.summary) > 120 else ""))
            tags = ", ".join(module.tags)
            update = module.last_commit_subject or "—"
            if module.last_commit:
                update = f"`{module.last_commit}` {_md_escape(update)}"
            lines.append(
                f"| `{module.module_id}` | `{module.layer}` | {summary or '—'} | {tags or '—'} | {update} |"
            )
            if module.exports:
                export_list = ", ".join(f"`{name}`" for name in module.exports[:12])
                if len(module.exports) > 12:
                    export_list += ", …"
                lines.append(f"| ↳ exports | | {export_list} | | |")
        lines.append("")

    lines.extend(["## Assets", "", "| Asset | Category | Summary | Related | Last update |", "|---|---|---|---|---|"])
    for asset in index.assets:
        related = ", ".join(f"`{item}`" for item in asset.related_modules) or "—"
        update = asset.last_commit_subject or "—"
        if asset.last_commit:
            update = f"`{asset.last_commit}` {_md_escape(update)}"
        lines.append(
            f"| `{asset.asset_id}` | `{asset.category}/{asset.subcategory}` | {_md_escape(asset.summary)} | {related} | {update} |"
        )

    lines.extend(["", "## Recent repository updates", "", "| Commit | Date | Subject |", "|---|---|---|"])
    for row in index.update_log:
        lines.append(f"| `{row['commit']}` | {row['date']} | {_md_escape(row['subject'])} |")

    lines.extend(
        [
            "",
            "## How agents should use this",
            "",
            "1. Check this index before adding a feature to see whether a module/extension already covers it.",
            "2. Place new domain capabilities under `src/reasoning_bridge/extensions/<name>/`.",
            "3. Regenerate the index after adding/changing modules, schemas, examples, or docs.",
            "4. Keep core entries free of domain-specific packet/memory/eval logic.",
            "",
        ]
    )
    return "\n".join(lines)


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {key: _to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    return value


def write_index(index: BridgeIndex) -> None:
    DOCS_ROOT.mkdir(parents=True, exist_ok=True)
    INDEX_JSON.write_text(json.dumps(_to_jsonable(index), indent=2) + "\n", encoding="utf-8")
    INDEX_MD.write_text(render_markdown(index), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the Reasoning Bridge module/feature index.")
    parser.add_argument("--check", action="store_true", help="Exit non-zero if generated files would change.")
    args = parser.parse_args(argv)
    index = build_index()
    markdown = render_markdown(index)
    payload = json.dumps(_to_jsonable(index), indent=2) + "\n"

    if args.check:
        current_json = INDEX_JSON.read_text(encoding="utf-8") if INDEX_JSON.exists() else ""
        current_md = INDEX_MD.read_text(encoding="utf-8") if INDEX_MD.exists() else ""
        # Ignore generated_at churn for check stability by comparing structure without timestamp.
        def strip_generated(text: str) -> str:
            data = json.loads(text) if text else {}
            if isinstance(data, dict):
                data.pop("generated_at", None)
            return json.dumps(data, indent=2)

        proposed = json.loads(payload)
        proposed.pop("generated_at", None)
        existing = json.loads(current_json) if current_json else {}
        if isinstance(existing, dict):
            existing.pop("generated_at", None)
        md_existing = re.sub(r"- Generated at: `[^`]+`", "- Generated at: `<timestamp>`", current_md)
        md_proposed = re.sub(r"- Generated at: `[^`]+`", "- Generated at: `<timestamp>`", markdown)
        if existing != proposed or md_existing != md_proposed:
            print("Bridge index is out of date. Run: python tools/bridge_index.py")
            return 1
        print("Bridge index is up to date.")
        return 0

    write_index(index)
    print(f"Wrote {INDEX_JSON.relative_to(REPO_ROOT)}")
    print(f"Wrote {INDEX_MD.relative_to(REPO_ROOT)}")
    print(f"Indexed {len(index.modules)} modules and {len(index.assets)} assets.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
