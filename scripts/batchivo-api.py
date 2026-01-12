#!/usr/bin/env python3
"""
Batchivo API Client Script

A command-line tool for interacting with the Batchivo API.
Supports product creation, listing, and other operations.

Usage:
    # Login and save credentials
    ./batchivo-api.py login --email user@example.com --password yourpassword

    # Create a product
    ./batchivo-api.py create-product --name "Product Name" --sku "PROD-001"

    # List products
    ./batchivo-api.py list-products

    # Get product details
    ./batchivo-api.py get-product --id <uuid>

Environment variables:
    BATCHIVO_API_URL: API base URL (default: https://api.batchivo.com)
    BATCHIVO_EMAIL: Login email (alternative to --email)
    BATCHIVO_PASSWORD: Login password (alternative to --password)
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional
from decimal import Decimal

try:
    import requests
except ImportError:
    print("Error: requests library required. Install with: pip install requests")
    sys.exit(1)

# Configuration
DEFAULT_API_URL = "https://api.batchivo.com"
TOKEN_FILE = Path.home() / ".batchivo" / "credentials.json"


class BatchivoClient:
    """Client for interacting with the Batchivo API."""

    def __init__(self, base_url: str = DEFAULT_API_URL):
        self.base_url = base_url.rstrip("/")
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self._load_credentials()

    def _load_credentials(self):
        """Load saved credentials from file."""
        if TOKEN_FILE.exists():
            try:
                with open(TOKEN_FILE) as f:
                    data = json.load(f)
                    self.access_token = data.get("access_token")
                    self.refresh_token = data.get("refresh_token")
            except (json.JSONDecodeError, IOError):
                pass

    def _save_credentials(self):
        """Save credentials to file."""
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_FILE, "w") as f:
            json.dump(
                {
                    "access_token": self.access_token,
                    "refresh_token": self.refresh_token,
                },
                f,
                indent=2,
            )
        os.chmod(TOKEN_FILE, 0o600)  # Secure file permissions

    def _headers(self) -> dict:
        """Get headers with authorization."""
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> dict:
        """Make an API request."""
        url = f"{self.base_url}/api/v1{endpoint}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self._headers(),
                json=data,
                params=params,
                timeout=30,
            )
        except requests.RequestException as e:
            raise Exception(f"Request failed: {e}")

        # Handle 401 by attempting token refresh
        if response.status_code == 401 and self.refresh_token:
            if self._refresh_access_token():
                # Retry request with new token
                response = requests.request(
                    method=method,
                    url=url,
                    headers=self._headers(),
                    json=data,
                    params=params,
                    timeout=30,
                )

        if not response.ok:
            error_detail = response.text
            try:
                error_json = response.json()
                error_detail = error_json.get("detail", response.text)
            except json.JSONDecodeError:
                pass
            raise Exception(f"API Error ({response.status_code}): {error_detail}")

        if response.status_code == 204:
            return {}
        return response.json()

    def _refresh_access_token(self) -> bool:
        """Attempt to refresh the access token."""
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/auth/refresh",
                headers={"Content-Type": "application/json"},
                json={"refresh_token": self.refresh_token},
                timeout=30,
            )
            if response.ok:
                data = response.json()
                self.access_token = data["access_token"]
                self.refresh_token = data["refresh_token"]
                self._save_credentials()
                return True
        except requests.RequestException:
            pass
        return False

    def login(self, email: str, password: str) -> dict:
        """Login and get JWT tokens."""
        response = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            headers={"Content-Type": "application/json"},
            json={"email": email, "password": password},
            timeout=30,
        )

        if not response.ok:
            error_detail = response.text
            try:
                error_json = response.json()
                error_detail = error_json.get("detail", response.text)
            except json.JSONDecodeError:
                pass
            raise Exception(f"Login failed: {error_detail}")

        data = response.json()
        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]
        self._save_credentials()
        return {"status": "success", "message": "Logged in successfully"}

    def create_product(
        self,
        name: str,
        sku: str,
        description: Optional[str] = None,
        units_in_stock: int = 0,
        packaging_cost: float = 0.0,
        assembly_minutes: int = 0,
        is_active: bool = True,
        shop_visible: bool = False,
        print_to_order: bool = False,
        free_shipping: bool = False,
        shop_description: Optional[str] = None,
        is_featured: bool = False,
        is_dragon: bool = False,
        feature_title: Optional[str] = None,
        backstory: Optional[str] = None,
    ) -> dict:
        """Create a new product."""
        if not self.access_token:
            raise Exception("Not logged in. Run 'login' command first.")

        product_data = {
            "sku": sku,
            "name": name,
            "description": description,
            "units_in_stock": units_in_stock,
            "packaging_cost": str(packaging_cost),
            "assembly_minutes": assembly_minutes,
            "is_active": is_active,
            "shop_visible": shop_visible,
            "print_to_order": print_to_order,
            "free_shipping": free_shipping,
            "shop_description": shop_description,
            "is_featured": is_featured,
            "is_dragon": is_dragon,
            "feature_title": feature_title,
            "backstory": backstory,
        }

        # Remove None values
        product_data = {k: v for k, v in product_data.items() if v is not None}

        return self._request("POST", "/products", data=product_data)

    def list_products(
        self,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> dict:
        """List products with optional filtering."""
        if not self.access_token:
            raise Exception("Not logged in. Run 'login' command first.")

        params = {"skip": skip, "limit": limit}
        if is_active is not None:
            params["is_active"] = is_active
        if search:
            params["search"] = search

        return self._request("GET", "/products", params=params)

    def get_product(self, product_id: str) -> dict:
        """Get product details by ID."""
        if not self.access_token:
            raise Exception("Not logged in. Run 'login' command first.")

        return self._request("GET", f"/products/{product_id}")

    def update_product(self, product_id: str, **kwargs) -> dict:
        """Update a product."""
        if not self.access_token:
            raise Exception("Not logged in. Run 'login' command first.")

        # Convert Decimal to string for JSON
        update_data = {}
        for k, v in kwargs.items():
            if v is not None:
                if isinstance(v, (float, Decimal)):
                    update_data[k] = str(v)
                else:
                    update_data[k] = v

        return self._request("PUT", f"/products/{product_id}", data=update_data)

    def delete_product(self, product_id: str) -> dict:
        """Delete (deactivate) a product."""
        if not self.access_token:
            raise Exception("Not logged in. Run 'login' command first.")

        return self._request("DELETE", f"/products/{product_id}")


def main():
    parser = argparse.ArgumentParser(
        description="Batchivo API Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("BATCHIVO_API_URL", DEFAULT_API_URL),
        help="API base URL",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Login command
    login_parser = subparsers.add_parser("login", help="Login to Batchivo")
    login_parser.add_argument(
        "--email",
        default=os.environ.get("BATCHIVO_EMAIL"),
        help="Email address",
    )
    login_parser.add_argument(
        "--password",
        default=os.environ.get("BATCHIVO_PASSWORD"),
        help="Password",
    )

    # Create product command
    create_parser = subparsers.add_parser("create-product", help="Create a new product")
    create_parser.add_argument("--name", required=True, help="Product name")
    create_parser.add_argument("--sku", required=True, help="SKU (Stock Keeping Unit)")
    create_parser.add_argument("--description", help="Product description")
    create_parser.add_argument("--units-in-stock", type=int, default=0, help="Units in stock")
    create_parser.add_argument("--packaging-cost", type=float, default=0.0, help="Packaging cost")
    create_parser.add_argument("--assembly-minutes", type=int, default=0, help="Assembly time in minutes")
    create_parser.add_argument("--active", action="store_true", default=True, help="Product is active")
    create_parser.add_argument("--shop-visible", action="store_true", help="Visible in shop")
    create_parser.add_argument("--print-to-order", action="store_true", help="Print to order")
    create_parser.add_argument("--free-shipping", action="store_true", help="Free shipping")
    create_parser.add_argument("--shop-description", help="HTML description for shop")
    create_parser.add_argument("--featured", action="store_true", help="Featured product")
    create_parser.add_argument("--dragon", action="store_true", help="Part of Dragons collection")
    create_parser.add_argument("--feature-title", help="Custom title for featured display")
    create_parser.add_argument("--backstory", help="Backstory/lore for featured items")

    # List products command
    list_parser = subparsers.add_parser("list-products", help="List products")
    list_parser.add_argument("--skip", type=int, default=0, help="Skip N products")
    list_parser.add_argument("--limit", type=int, default=100, help="Limit results")
    list_parser.add_argument("--active-only", action="store_true", help="Only active products")
    list_parser.add_argument("--search", help="Search query")

    # Get product command
    get_parser = subparsers.add_parser("get-product", help="Get product details")
    get_parser.add_argument("--id", required=True, help="Product UUID")

    # Update product command
    update_parser = subparsers.add_parser("update-product", help="Update a product")
    update_parser.add_argument("--id", required=True, help="Product UUID")
    update_parser.add_argument("--name", help="Product name")
    update_parser.add_argument("--sku", help="SKU")
    update_parser.add_argument("--description", help="Product description")
    update_parser.add_argument("--units-in-stock", type=int, help="Units in stock")
    update_parser.add_argument("--shop-visible", action="store_true", help="Visible in shop")
    update_parser.add_argument("--active", action="store_true", help="Product is active")
    update_parser.add_argument("--inactive", action="store_true", help="Product is inactive")

    # Delete product command
    delete_parser = subparsers.add_parser("delete-product", help="Delete (deactivate) a product")
    delete_parser.add_argument("--id", required=True, help="Product UUID")

    # Status command
    subparsers.add_parser("status", help="Check login status")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    client = BatchivoClient(args.api_url)

    try:
        if args.command == "login":
            if not args.email or not args.password:
                print("Error: --email and --password required (or set BATCHIVO_EMAIL/BATCHIVO_PASSWORD)")
                sys.exit(1)
            result = client.login(args.email, args.password)
            print(json.dumps(result, indent=2))

        elif args.command == "create-product":
            result = client.create_product(
                name=args.name,
                sku=args.sku,
                description=args.description,
                units_in_stock=args.units_in_stock,
                packaging_cost=args.packaging_cost,
                assembly_minutes=args.assembly_minutes,
                is_active=args.active,
                shop_visible=args.shop_visible,
                print_to_order=args.print_to_order,
                free_shipping=args.free_shipping,
                shop_description=args.shop_description,
                is_featured=args.featured,
                is_dragon=args.dragon,
                feature_title=args.feature_title,
                backstory=args.backstory,
            )
            print(json.dumps(result, indent=2, default=str))
            print(f"\nProduct created: {result.get('name')} (ID: {result.get('id')})")

        elif args.command == "list-products":
            result = client.list_products(
                skip=args.skip,
                limit=args.limit,
                is_active=True if args.active_only else None,
                search=args.search,
            )
            products = result.get("products", [])
            print(f"Found {result.get('total', 0)} products:\n")
            for p in products:
                status = "Active" if p.get("is_active") else "Inactive"
                print(f"  [{p.get('sku')}] {p.get('name')} - {status} (ID: {p.get('id')})")

        elif args.command == "get-product":
            result = client.get_product(args.id)
            print(json.dumps(result, indent=2, default=str))

        elif args.command == "update-product":
            updates = {}
            if args.name:
                updates["name"] = args.name
            if args.sku:
                updates["sku"] = args.sku
            if args.description:
                updates["description"] = args.description
            if args.units_in_stock is not None:
                updates["units_in_stock"] = args.units_in_stock
            if args.shop_visible:
                updates["shop_visible"] = True
            if args.active:
                updates["is_active"] = True
            if args.inactive:
                updates["is_active"] = False

            if not updates:
                print("Error: No update fields specified")
                sys.exit(1)

            result = client.update_product(args.id, **updates)
            print(json.dumps(result, indent=2, default=str))
            print(f"\nProduct updated: {result.get('name')}")

        elif args.command == "delete-product":
            client.delete_product(args.id)
            print(f"Product {args.id} deleted (deactivated)")

        elif args.command == "status":
            if client.access_token:
                print("Status: Logged in")
                print(f"Token file: {TOKEN_FILE}")
            else:
                print("Status: Not logged in")
                print("Run 'batchivo-api.py login' to authenticate")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
