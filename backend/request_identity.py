from ipaddress import ip_address, ip_network

from fastapi import Request


def parse_trusted_proxy_networks(value: str | None):
    networks = []
    for entry in (value or "").split(","):
        cleaned = entry.strip()
        if not cleaned:
            continue
        try:
            networks.append(ip_network(cleaned, strict=False))
        except ValueError as error:
            raise RuntimeError(f"Invalid TRUSTED_PROXY_IPS entry: {cleaned}") from error
    return tuple(networks)


def client_address(request: Request, trusted_proxy_networks=()) -> str:
    immediate_address = request.client.host if request.client else "unknown"
    try:
        immediate_ip = ip_address(immediate_address)
    except ValueError:
        return immediate_address

    if not any(immediate_ip in network for network in trusted_proxy_networks):
        return immediate_address

    forwarded_for = request.headers.get("x-forwarded-for", "")
    forwarded_addresses = [part.strip() for part in forwarded_for.split(",") if part.strip()]
    if not forwarded_addresses:
        return immediate_address

    for forwarded_address in reversed(forwarded_addresses):
        try:
            forwarded_ip = ip_address(forwarded_address)
        except ValueError:
            return immediate_address
        if not any(forwarded_ip in network for network in trusted_proxy_networks):
            return str(forwarded_ip)
    return immediate_address
