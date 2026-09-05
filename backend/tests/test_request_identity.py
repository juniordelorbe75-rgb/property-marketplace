import unittest
from types import SimpleNamespace

from backend.request_identity import client_address, parse_trusted_proxy_networks


def request_from(address, forwarded_for=None):
    headers = {} if forwarded_for is None else {"x-forwarded-for": forwarded_for}
    client = None if address is None else SimpleNamespace(host=address)
    return SimpleNamespace(client=client, headers=headers)


class RequestIdentityTests(unittest.TestCase):
    def test_direct_visitors_cannot_spoof_a_forwarded_address(self):
        request = request_from("203.0.113.9", "198.51.100.7")

        self.assertEqual(client_address(request), "203.0.113.9")

    def test_trusted_proxy_uses_the_first_valid_forwarded_address(self):
        trusted = parse_trusted_proxy_networks("10.0.0.0/8, 127.0.0.1")
        request = request_from("10.2.3.4", "198.51.100.7, 10.2.3.4")

        self.assertEqual(client_address(request, trusted), "198.51.100.7")

    def test_spoofed_prefix_is_ignored_behind_a_trusted_proxy_chain(self):
        trusted = parse_trusted_proxy_networks("10.0.0.0/8")
        request = request_from(
            "10.2.3.4",
            "192.0.2.99, 198.51.100.7, 10.8.0.2",
        )

        self.assertEqual(client_address(request, trusted), "198.51.100.7")

    def test_invalid_or_missing_forwarded_address_falls_back_safely(self):
        trusted = parse_trusted_proxy_networks("10.0.0.0/8")

        self.assertEqual(client_address(request_from("10.2.3.4", "not-an-ip"), trusted), "10.2.3.4")
        self.assertEqual(client_address(request_from(None), trusted), "unknown")

    def test_invalid_proxy_configuration_is_rejected(self):
        with self.assertRaises(RuntimeError):
            parse_trusted_proxy_networks("10.0.0.0/8, not-a-network")


if __name__ == "__main__":
    unittest.main()
