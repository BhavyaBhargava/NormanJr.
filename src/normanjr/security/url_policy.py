"""URL policy and SSRF prevention controls."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from normanjr.config import ExplorationSettings, SafetySettings

# Disallowed IP networks by default
BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("10.0.0.0/8"),  # RFC1918 private
    ipaddress.ip_network("172.16.0.0/12"),  # RFC1918 private
    ipaddress.ip_network("192.168.0.0/16"),  # RFC1918 private
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local / Cloud metadata (AWS, GCP, etc.)
    ipaddress.ip_network("224.0.0.0/4"),  # Multicast
    ipaddress.ip_network("0.0.0.0/8"),  # Current network
    ipaddress.ip_network("::1/128"),  # IPv6 Loopback
    ipaddress.ip_network("fc00::/7"),  # IPv6 Unique Local
    ipaddress.ip_network("fe80::/10"),  # IPv6 Link-local
]


class UrlPolicyError(Exception):
    """Raised when a URL violates security policy."""


class UrlPolicy:
    """Enforces scheme, SSRF restrictions, and origin boundaries."""

    def __init__(
        self,
        exploration_settings: ExplorationSettings,
        safety_settings: SafetySettings,
        initial_origin: str | None = None,
    ) -> None:
        self.exploration = exploration_settings
        self.safety = safety_settings
        if initial_origin:
            try:
                p = urlparse(initial_origin)
                self.initial_origin = f"{p.scheme}://{p.netloc}".rstrip("/").lower() if p.netloc else initial_origin.rstrip("/").lower()
            except Exception:
                self.initial_origin = initial_origin.rstrip("/").lower()
        else:
            self.initial_origin = None

    def validate_url(self, url: str) -> bool:
        """Validate that a URL is safe to navigate to under current policy."""
        try:
            parsed = urlparse(url)
        except Exception as e:
            raise UrlPolicyError(f"Malformed URL: {url} ({e})") from e

        scheme = (parsed.scheme or "").lower()
        if scheme not in ("http", "https"):
            raise UrlPolicyError(
                f"Disallowed URL scheme '{scheme}'. Only HTTP and HTTPS are permitted."
            )

        hostname = parsed.hostname
        if not hostname:
            raise UrlPolicyError(f"Missing hostname in URL: {url}")

        # Check for userinfo (e.g. http://user:pass@host)
        if parsed.username or parsed.password:
            raise UrlPolicyError("URLs with embedded credentials are not permitted.")

        # SSRF IP address validation
        if not self.safety.allow_private_target:
            self._verify_not_private_ip(hostname)

        # Same-origin enforcement
        if self.exploration.same_origin_only and self.initial_origin:
            target_origin = f"{scheme}://{parsed.netloc}".rstrip("/").lower()
            if target_origin != self.initial_origin:
                allowed = [o.rstrip("/").lower() for o in self.exploration.allowed_origins]
                if target_origin not in allowed:
                    raise UrlPolicyError(
                        f"External navigation blocked by policy: {target_origin} does not match initial origin {self.initial_origin}."
                    )

        # Check explicit denied URL patterns
        for pattern in self.exploration.denied_url_patterns:
            if pattern in url:
                raise UrlPolicyError(f"URL matches denied pattern '{pattern}': {url}")

        return True

    def _verify_not_private_ip(self, hostname: str) -> None:
        """Resolve hostname to IPs and verify none fall in private/loopback/metadata ranges."""
        # Try direct IP parsing first
        try:
            ip_obj = ipaddress.ip_address(hostname)
            ips = [ip_obj]
        except ValueError:
            # Resolve DNS
            try:
                addr_info = socket.getaddrinfo(hostname, None)
                ips = [ipaddress.ip_address(info[4][0]) for info in addr_info]
            except Exception as e:
                raise UrlPolicyError(f"DNS resolution failed for hostname '{hostname}': {e}") from e

        for ip in ips:
            for blocked in BLOCKED_NETWORKS:
                if ip in blocked:
                    raise UrlPolicyError(
                        f"SSRF violation: Host '{hostname}' resolves to restricted IP {ip} in {blocked}. "
                        f"Set allow_private_target = true to allow local testing."
                    )
