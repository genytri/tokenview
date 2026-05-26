"""Parse output of `claude plugin details <name>`."""

from __future__ import annotations

import re
import subprocess

from tokenview.models import Plugin, PluginComponent, PluginComponentType

_HEADER_RE = re.compile(r"^(?P<name>\S+)\s+(?P<version>\S+)$")
_ALWAYS_ON_RE = re.compile(r"Always-on:\s+~?(?P<n>[\d.]+)(?P<unit>[kKmM]?)\s*tok")
_COMPONENT_LINE_RE = re.compile(
    r"^\s*(?P<name>\S+)\s+~?(?P<ao>[\d.]+)(?P<aou>[kKmM]?)\s+~?(?P<oi>[\d.]+)(?P<oiu>[kKmM]?)\s*$"
)
_INVENTORY_RE = re.compile(
    r"^\s*(?P<bucket>Skills|Agents|MCP servers|LSP servers)\s+\(\d+\)\s+(?P<list>.*)$"
)


def _to_tokens(n: str, unit: str) -> int:
    value = float(n)
    multiplier = {"": 1, "k": 1000, "K": 1000, "m": 1_000_000, "M": 1_000_000}[unit]
    return round(value * multiplier)


_BUCKET_TO_TYPE: dict[str, PluginComponentType] = {
    "Skills": "skill",
    "Agents": "agent",
    "MCP servers": "mcp",
    "LSP servers": "lsp",
}


def parse_details_output(text: str, *, marketplace: str) -> Plugin:
    """Parse `claude plugin details` stdout into a Plugin dataclass.

    Hooks are intentionally excluded from `components` because they run in
    the harness and contribute no model context cost.
    """
    lines = text.splitlines()

    name = ""
    version = ""
    for line in lines:
        m = _HEADER_RE.match(line.strip())
        if m and not line.startswith(" "):
            name = m.group("name")
            version = m.group("version")
            break

    always_on = 0
    for line in lines:
        m = _ALWAYS_ON_RE.search(line)
        if m:
            always_on = _to_tokens(m.group("n"), m.group("unit"))
            break

    name_to_type: dict[str, PluginComponentType] = {}
    for line in lines:
        m = _INVENTORY_RE.match(line)
        if not m:
            continue
        bucket = m.group("bucket")
        if bucket not in _BUCKET_TO_TYPE:
            continue
        ctype = _BUCKET_TO_TYPE[bucket]
        for raw in m.group("list").split(","):
            comp = raw.strip()
            if comp and "(" not in comp:
                name_to_type[comp] = ctype

    components: list[PluginComponent] = []
    in_table = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("component"):
            in_table = True
            continue
        if not in_table:
            continue
        if not stripped or stripped.startswith("On-invoke") or stripped.startswith("Token counts"):
            continue
        m = _COMPONENT_LINE_RE.match(line)
        if not m:
            continue
        cname = m.group("name")
        ctype = name_to_type.get(cname, "skill")
        components.append(
            PluginComponent(
                name=cname,
                type=ctype,
                always_on_tokens=_to_tokens(m.group("ao"), m.group("aou")),
                on_invoke_tokens=_to_tokens(m.group("oi"), m.group("oiu")),
            )
        )

    return Plugin(
        name=name,
        marketplace=marketplace,
        version=version,
        always_on_tokens=always_on,
        components=components,
    )


def fetch_plugin_details(plugin_id: str) -> Plugin:
    """Shell out to `claude plugin details <plugin_id>` and parse.

    `plugin_id` is `name@marketplace` form.
    """
    _name, marketplace = plugin_id.split("@", 1)
    result = subprocess.run(
        ["claude", "plugin", "details", plugin_id],
        capture_output=True,
        text=True,
        check=True,
    )
    return parse_details_output(result.stdout, marketplace=marketplace)
