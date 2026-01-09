"""Integration tests for product images API endpoints."""

import pytest
from httpx import AsyncClient
from uuid import uuid4
from io import BytesIO
from PIL import Image

from app.models.product import Product


def create_test_image(width: int = 200, height: int = 100, format: str = "JPEG") -> bytes:
    """Create a test image in memory."""
    mode = "RGBA" if format == "PNG" else "RGB"
    img = Image.new(mode, (width, height), color="red")
    buffer = BytesIO()
    img.save(buffer, format=format)
    buffer.seek(0)
    return buffer.getvalue()


class TestProductImagesEndpoints:
    """Test product images API endpoints."""

    @pytest.mark.asyncio
    async def test_upload_product_image(
        self, client: AsyncClient, auth_headers: dict, test_product: Product
    ):
        """Test uploading an image to a product."""
        image_data = create_test_image()

        response = await client.post(
            f"/api/v1/products/{test_product.id}/images",
            headers=auth_headers,
            files={"file": ("test.jpg", image_data, "image/jpeg")},
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert "id" in data
        assert "image_url" in data
        assert "thumbnail_url" in data

    @pytest.mark.asyncio
    async def test_list_product_images(
        self, client: AsyncClient, auth_headers: dict, test_product_with_image: tuple
    ):
        """Test listing images for a product."""
        product, image = test_product_with_image

        response = await client.get(
            f"/api/v1/products/{product.id}/images",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "images" in data
        assert len(data["images"]) >= 1


class TestProductImageRotation:
    """Test product image rotation functionality."""

    @pytest.mark.asyncio
    async def test_rotate_image_90_degrees(
        self, client: AsyncClient, auth_headers: dict, test_product_with_image: tuple
    ):
        """Test rotating an image 90 degrees clockwise."""
        product, image = test_product_with_image

        response = await client.post(
            f"/api/v1/products/{product.id}/images/{image.id}/rotate?degrees=90",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(image.id)

    @pytest.mark.asyncio
    async def test_rotate_image_180_degrees(
        self, client: AsyncClient, auth_headers: dict, test_product_with_image: tuple
    ):
        """Test rotating an image 180 degrees."""
        product, image = test_product_with_image

        response = await client.post(
            f"/api/v1/products/{product.id}/images/{image.id}/rotate?degrees=180",
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rotate_image_270_degrees(
        self, client: AsyncClient, auth_headers: dict, test_product_with_image: tuple
    ):
        """Test rotating an image 270 degrees clockwise."""
        product, image = test_product_with_image

        response = await client.post(
            f"/api/v1/products/{product.id}/images/{image.id}/rotate?degrees=270",
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rotate_image_default_90_degrees(
        self, client: AsyncClient, auth_headers: dict, test_product_with_image: tuple
    ):
        """Test rotating an image without specifying degrees defaults to 90."""
        product, image = test_product_with_image

        response = await client.post(
            f"/api/v1/products/{product.id}/images/{image.id}/rotate",
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rotate_image_invalid_degrees(
        self, client: AsyncClient, auth_headers: dict, test_product_with_image: tuple
    ):
        """Test rotating with invalid degrees returns 400."""
        product, image = test_product_with_image

        response = await client.post(
            f"/api/v1/products/{product.id}/images/{image.id}/rotate?degrees=45",
            headers=auth_headers,
        )
        assert response.status_code == 400
        data = response.json()
        assert "90, 180, or 270" in data["detail"]

    @pytest.mark.asyncio
    async def test_rotate_nonexistent_image(
        self, client: AsyncClient, auth_headers: dict, test_product: Product
    ):
        """Test rotating a non-existent image returns 404."""
        fake_image_id = uuid4()

        response = await client.post(
            f"/api/v1/products/{test_product.id}/images/{fake_image_id}/rotate",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_rotate_image_wrong_product(
        self, client: AsyncClient, auth_headers: dict, test_product_with_image: tuple
    ):
        """Test rotating an image with wrong product ID returns 404."""
        product, image = test_product_with_image
        fake_product_id = uuid4()

        response = await client.post(
            f"/api/v1/products/{fake_product_id}/images/{image.id}/rotate",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestUploadsProxyEndpoint:
    """Test the /uploads/ proxy endpoint for serving images."""

    @pytest.mark.asyncio
    async def test_serve_image_returns_content(
        self, client: AsyncClient, test_product_with_image: tuple
    ):
        """Test that /uploads/ endpoint returns image content."""
        product, image = test_product_with_image

        # Extract path from image_url (e.g., /uploads/products/{id}/{filename})
        response = await client.get(image.image_url)
        assert response.status_code == 200
        assert response.headers.get("content-type") in ["image/jpeg", "image/png"]

    @pytest.mark.asyncio
    async def test_serve_image_has_cache_control_header(
        self, client: AsyncClient, test_product_with_image: tuple
    ):
        """Test that served images include Cache-Control headers."""
        product, image = test_product_with_image

        response = await client.get(image.image_url)
        assert response.status_code == 200
        assert "cache-control" in response.headers
        assert "no-cache" in response.headers["cache-control"]

    @pytest.mark.asyncio
    async def test_serve_thumbnail_returns_content(
        self, client: AsyncClient, test_product_with_image: tuple
    ):
        """Test that /uploads/ endpoint returns thumbnail content."""
        product, image = test_product_with_image

        response = await client.get(image.thumbnail_url)
        assert response.status_code == 200
        assert response.headers.get("content-type") in ["image/jpeg", "image/png"]

    @pytest.mark.asyncio
    async def test_serve_nonexistent_image_returns_404(self, client: AsyncClient):
        """Test that requesting a non-existent image returns 404."""
        fake_product_id = uuid4()

        response = await client.get(f"/uploads/products/{fake_product_id}/nonexistent.jpg")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Image not found"

    @pytest.mark.asyncio
    async def test_serve_image_after_upload(
        self, client: AsyncClient, auth_headers: dict, test_product: Product
    ):
        """Test that newly uploaded images are immediately servable."""
        # Upload an image
        image_data = create_test_image()
        upload_response = await client.post(
            f"/api/v1/products/{test_product.id}/images",
            headers=auth_headers,
            files={"file": ("test.jpg", image_data, "image/jpeg")},
        )
        assert upload_response.status_code in [200, 201]
        image_info = upload_response.json()

        # Fetch the uploaded image via /uploads/ proxy
        serve_response = await client.get(image_info["image_url"])
        assert serve_response.status_code == 200
        assert serve_response.headers.get("content-type") == "image/jpeg"

        # Verify the served content is valid image data
        assert len(serve_response.content) > 0

    @pytest.mark.asyncio
    async def test_serve_image_correct_content_type_jpeg(
        self, client: AsyncClient, auth_headers: dict, test_product: Product
    ):
        """Test that JPEG images are served with correct content type."""
        image_data = create_test_image(format="JPEG")
        upload_response = await client.post(
            f"/api/v1/products/{test_product.id}/images",
            headers=auth_headers,
            files={"file": ("test.jpg", image_data, "image/jpeg")},
        )
        assert upload_response.status_code in [200, 201]
        image_info = upload_response.json()

        response = await client.get(image_info["image_url"])
        assert response.headers.get("content-type") == "image/jpeg"

    @pytest.mark.asyncio
    async def test_serve_image_correct_content_type_png(
        self, client: AsyncClient, auth_headers: dict, test_product: Product
    ):
        """Test that PNG images are served with correct content type."""
        image_data = create_test_image(format="PNG")
        upload_response = await client.post(
            f"/api/v1/products/{test_product.id}/images",
            headers=auth_headers,
            files={"file": ("test.png", image_data, "image/png")},
        )
        assert upload_response.status_code in [200, 201]
        image_info = upload_response.json()

        response = await client.get(image_info["image_url"])
        assert response.headers.get("content-type") == "image/png"
