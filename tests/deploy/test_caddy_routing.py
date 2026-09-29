"""Caddy edge routing expectations (static file checks)."""

from pathlib import Path


def test_caddy_protects_app_and_exposes_status() -> None:
    caddyfile = Path("deploy/caddy/Caddyfile").read_text(encoding="utf-8")
    assert "handle /app*" in caddyfile
    assert "basic_auth" in caddyfile
    assert "handle /status*" in caddyfile
    assert "reverse_proxy status:8502" in caddyfile
    assert caddyfile.index("handle /status") < caddyfile.index("handle /app")
