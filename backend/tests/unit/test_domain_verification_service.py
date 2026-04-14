"""Unit tests for DomainVerificationService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import dns.resolver
import dns.exception

from app.services.domain_verification import DomainVerificationService, SHOPS_DOMAIN


@pytest.fixture
def service() -> DomainVerificationService:
    return DomainVerificationService(db=AsyncMock())


class TestGenerateVerificationToken:
    """Tests for DomainVerificationService.generate_verification_token."""

    def test_returns_string(self, service: DomainVerificationService):
        assert isinstance(service.generate_verification_token(), str)

    def test_starts_with_prefix(self, service: DomainVerificationService):
        assert service.generate_verification_token().startswith("batchivo-verify-")

    def test_tokens_are_unique(self, service: DomainVerificationService):
        tokens = {service.generate_verification_token() for _ in range(10)}
        assert len(tokens) == 10

    def test_token_has_minimum_length(self, service: DomainVerificationService):
        # "batchivo-verify-" = 16 chars + 43-char URL-safe base64 = at least 40+ chars
        token = service.generate_verification_token()
        assert len(token) > 40


class TestVerifyCname:
    """Tests for DomainVerificationService.verify_cname."""

    @pytest.mark.asyncio
    async def test_matching_cname_returns_true(self, service: DomainVerificationService):
        mock_rdata = MagicMock()
        mock_rdata.target = MagicMock()
        mock_rdata.target.__str__ = lambda self: f"{SHOPS_DOMAIN}."

        with patch("dns.resolver.resolve", return_value=[mock_rdata]):
            success, error = await service.verify_cname("shop.example.com")

        assert success is True
        assert error is None

    @pytest.mark.asyncio
    async def test_wrong_cname_target_returns_false(self, service: DomainVerificationService):
        mock_rdata = MagicMock()
        mock_rdata.target = MagicMock()
        mock_rdata.target.__str__ = lambda self: "other.host.com."

        with patch("dns.resolver.resolve", return_value=[mock_rdata]):
            success, error = await service.verify_cname("shop.example.com")

        assert success is False
        assert error is not None
        assert "other.host.com" in error

    @pytest.mark.asyncio
    async def test_nxdomain_returns_false(self, service: DomainVerificationService):
        with patch("dns.resolver.resolve", side_effect=dns.resolver.NXDOMAIN()):
            success, error = await service.verify_cname("nonexistent.example.com")

        assert success is False
        assert "not found" in error.lower() or "nxdomain" in error.lower()

    @pytest.mark.asyncio
    async def test_no_answer_returns_false(self, service: DomainVerificationService):
        with patch("dns.resolver.resolve", side_effect=dns.resolver.NoAnswer()):
            success, error = await service.verify_cname("shop.example.com")

        assert success is False
        assert error is not None

    @pytest.mark.asyncio
    async def test_no_nameservers_returns_false(self, service: DomainVerificationService):
        with patch("dns.resolver.resolve", side_effect=dns.resolver.NoNameservers()):
            success, error = await service.verify_cname("shop.example.com")

        assert success is False
        assert "nameservers" in error.lower()

    @pytest.mark.asyncio
    async def test_timeout_returns_false(self, service: DomainVerificationService):
        with patch("dns.resolver.resolve", side_effect=dns.exception.Timeout()):
            success, error = await service.verify_cname("shop.example.com")

        assert success is False
        assert "timed out" in error.lower()

    @pytest.mark.asyncio
    async def test_custom_expected_target(self, service: DomainVerificationService):
        mock_rdata = MagicMock()
        mock_rdata.target = MagicMock()
        mock_rdata.target.__str__ = lambda self: "custom.target.com."

        with patch("dns.resolver.resolve", return_value=[mock_rdata]):
            success, error = await service.verify_cname(
                "shop.example.com", expected_target="custom.target.com"
            )

        assert success is True
        assert error is None


class TestVerifyTxt:
    """Tests for DomainVerificationService.verify_txt."""

    @pytest.mark.asyncio
    async def test_matching_token_returns_true(self, service: DomainVerificationService):
        mock_rdata = MagicMock()
        token = "batchivo-verify-abc123"
        mock_rdata.strings = [token.encode()]

        with patch("dns.resolver.resolve", return_value=[mock_rdata]):
            success, error = await service.verify_txt("example.com", token)

        assert success is True
        assert error is None

    @pytest.mark.asyncio
    async def test_token_not_in_txt_returns_false(self, service: DomainVerificationService):
        mock_rdata = MagicMock()
        mock_rdata.strings = [b"some-other-value"]

        with patch("dns.resolver.resolve", return_value=[mock_rdata]):
            success, error = await service.verify_txt("example.com", "batchivo-verify-abc123")

        assert success is False
        assert error is not None

    @pytest.mark.asyncio
    async def test_resolves_at_correct_hostname(self, service: DomainVerificationService):
        """verify_txt should query _batchivo-verify.{domain}."""
        with patch("dns.resolver.resolve", side_effect=dns.resolver.NXDOMAIN()) as mock_resolve:
            await service.verify_txt("example.com", "token")
            mock_resolve.assert_called_once_with("_batchivo-verify.example.com", "TXT")

    @pytest.mark.asyncio
    async def test_nxdomain_returns_false(self, service: DomainVerificationService):
        with patch("dns.resolver.resolve", side_effect=dns.resolver.NXDOMAIN()):
            success, error = await service.verify_txt("example.com", "token")

        assert success is False
        assert error is not None

    @pytest.mark.asyncio
    async def test_timeout_returns_false(self, service: DomainVerificationService):
        with patch("dns.resolver.resolve", side_effect=dns.exception.Timeout()):
            success, error = await service.verify_txt("example.com", "token")

        assert success is False
        assert "timed out" in error.lower()

    @pytest.mark.asyncio
    async def test_multi_part_txt_record_joined(self, service: DomainVerificationService):
        """Multi-part TXT records should be joined before comparison."""
        mock_rdata = MagicMock()
        token = "batchivo-verify-abc123"
        # Token is split across two string parts
        mock_rdata.strings = [b"batchivo-verify-", b"abc123"]

        with patch("dns.resolver.resolve", return_value=[mock_rdata]):
            success, error = await service.verify_txt("example.com", token)

        assert success is True
        assert error is None
