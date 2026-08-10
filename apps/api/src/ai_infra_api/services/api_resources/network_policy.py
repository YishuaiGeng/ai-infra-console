import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit

from ai_infra_api.core.config import Settings

BLOCKED_METADATA_IPS = {
    ipaddress.ip_address("169.254.169.254"),
    ipaddress.ip_address("100.100.100.200"),
}


class NetworkPolicyError(ValueError):
    pass


async def validate_external_base_url(url: str, settings: Settings) -> str:
    parsed = urlsplit(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise NetworkPolicyError("only HTTP and HTTPS base URLs are supported")
    if parsed.username or parsed.password:
        raise NetworkPolicyError("credentials are not allowed in the base URL")
    if not parsed.hostname:
        raise NetworkPolicyError("base URL must include a hostname")
    if parsed.scheme == "http" and settings.environment == "production":
        raise NetworkPolicyError("production external API base URLs must use HTTPS")

    host = parsed.hostname.lower().rstrip(".")
    allowed_hosts = {item.lower().rstrip(".") for item in settings.external_api_allowed_hosts}
    allowed_networks = _allowed_networks(settings)
    try:
        addresses = {ipaddress.ip_address(host)}
    except ValueError:
        addresses = await _resolve(host, parsed.port or (443 if parsed.scheme == "https" else 80))

    for address in addresses:
        if address in BLOCKED_METADATA_IPS or address.is_link_local or address.is_loopback:
            raise NetworkPolicyError("base URL resolves to a blocked address")
        if address.is_private and not _private_address_allowed(
            host, address, settings, allowed_hosts, allowed_networks
        ):
            raise NetworkPolicyError("private network base URLs are not allowed")
    normalized_path = parsed.path.rstrip("/")
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{parsed.hostname}{port}{normalized_path}"


def _allowed_networks(
    settings: Settings,
) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    try:
        return tuple(
            ipaddress.ip_network(item, strict=False) for item in settings.external_api_allowed_cidrs
        )
    except ValueError as error:
        raise NetworkPolicyError("configured external API CIDR is invalid") from error


def _private_address_allowed(
    host: str,
    address: ipaddress.IPv4Address | ipaddress.IPv6Address,
    settings: Settings,
    allowed_hosts: set[str],
    allowed_networks: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...],
) -> bool:
    if settings.external_api_allow_private_networks:
        return True
    if host in allowed_hosts:
        return True
    return any(address in network for network in allowed_networks)


async def _resolve(host: str, port: int) -> set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    loop = asyncio.get_running_loop()
    try:
        records = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        raise NetworkPolicyError("base URL hostname could not be resolved") from error
    return {ipaddress.ip_address(record[4][0]) for record in records}
