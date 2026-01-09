#!/usr/bin/env python3
"""
Diagnostic script to identify model file upload issues.

Run from the backend directory:
    poetry run python scripts/diagnose_model_file_upload.py

This script checks:
1. Storage configuration
2. S3/MinIO connectivity (if using s3 storage)
3. Database model_files table existence
4. Upload functionality with a test file
"""

import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def diagnose():
    """Run diagnostics for model file upload."""
    print("=" * 60)
    print("Model File Upload Diagnostics")
    print("=" * 60)

    # 1. Check configuration
    print("\n1. CONFIGURATION")
    print("-" * 40)
    from app.config import get_settings

    settings = get_settings()

    print(f"   Storage Type: {settings.storage_type}")
    print(f"   Storage Path: {settings.storage_path}")

    if settings.storage_type == "s3":
        print(f"   S3 Bucket: {settings.storage_s3_bucket}")
        print(f"   S3 Endpoint: {settings.storage_s3_endpoint or 'AWS S3 (default)'}")
        print(f"   S3 Region: {settings.storage_s3_region}")
        print(f"   S3 Access Key: {'SET' if settings.storage_s3_access_key else 'NOT SET'}")
        print(f"   S3 Secret Key: {'SET' if settings.storage_s3_secret_key else 'NOT SET'}")

    # 2. Check local storage path
    if settings.storage_type == "local":
        print("\n2. LOCAL STORAGE CHECK")
        print("-" * 40)
        base_path = Path(settings.storage_path)
        models_path = base_path / "models"

        print(f"   Base path exists: {base_path.exists()}")
        print(f"   Base path writable: {base_path.exists() and base_path.stat().st_mode & 0o200}")
        print(f"   Models dir exists: {models_path.exists()}")

        if not models_path.exists():
            print("   Creating models directory...")
            try:
                models_path.mkdir(parents=True, exist_ok=True)
                print("   SUCCESS: Created models directory")
            except Exception as e:
                print(f"   FAILED: {e}")

    # 3. Check S3 connectivity
    if settings.storage_type == "s3":
        print("\n2. S3/MINIO CONNECTIVITY CHECK")
        print("-" * 40)

        import boto3
        from botocore.exceptions import ClientError, EndpointConnectionError

        s3_config = {}
        if settings.storage_s3_endpoint:
            s3_config["endpoint_url"] = settings.storage_s3_endpoint

        try:
            s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.storage_s3_access_key,
                aws_secret_access_key=settings.storage_s3_secret_key,
                region_name=settings.storage_s3_region,
                **s3_config,
            )

            # List buckets
            print("   Listing buckets...")
            response = s3_client.list_buckets()
            buckets = [b["Name"] for b in response["Buckets"]]
            print(f"   Found buckets: {buckets}")

            # Check if our bucket exists
            if settings.storage_s3_bucket in buckets:
                print(f"   SUCCESS: Bucket '{settings.storage_s3_bucket}' exists")
            else:
                print(f"   WARNING: Bucket '{settings.storage_s3_bucket}' does NOT exist!")
                print(f"   Available buckets: {buckets}")

            # Try to list objects in bucket
            print(f"\n   Listing objects in '{settings.storage_s3_bucket}'...")
            try:
                response = s3_client.list_objects_v2(Bucket=settings.storage_s3_bucket, MaxKeys=5)
                objects = [obj["Key"] for obj in response.get("Contents", [])]
                print(f"   First 5 objects: {objects if objects else '(empty)'}")
            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                print(f"   ERROR: {error_code} - {e.response['Error']['Message']}")

        except EndpointConnectionError as e:
            print("   ERROR: Cannot connect to S3/MinIO endpoint")
            print(f"   Details: {e}")
        except ClientError as e:
            print("   ERROR: S3 client error")
            print(f"   Code: {e.response['Error']['Code']}")
            print(f"   Message: {e.response['Error']['Message']}")
        except Exception as e:
            print(f"   ERROR: {type(e).__name__}: {e}")

    # 4. Check database
    print("\n3. DATABASE CHECK")
    print("-" * 40)

    try:
        from sqlalchemy import text
        from app.database import async_session_maker

        async with async_session_maker() as session:
            # Check if model_files table exists
            result = await session.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename='model_files'"
                )
            )
            exists = result.scalar_one_or_none()

            if exists:
                print("   SUCCESS: model_files table exists")

                # Count rows
                result = await session.execute(text("SELECT COUNT(*) FROM model_files"))
                count = result.scalar()
                print(f"   Row count: {count}")
            else:
                print("   WARNING: model_files table does NOT exist!")
                print("   Run: alembic upgrade head")

    except Exception as e:
        print(f"   ERROR: Database check failed: {e}")

    # 5. Test file validation
    print("\n4. FILE VALIDATION CHECK")
    print("-" * 40)

    from app.services.model_file_service import ALLOWED_EXTENSIONS, MAX_FILE_SIZE

    print(f"   Allowed extensions: {ALLOWED_EXTENSIONS}")
    print(f"   Max file size: {MAX_FILE_SIZE / 1024 / 1024:.0f} MB")

    # Test extension validation
    test_files = ["test.stl", "test.3mf", "test.gcode", "test.txt", "test.obj"]
    for f in test_files:
        ext = Path(f).suffix.lower()
        status = "OK" if ext in ALLOWED_EXTENSIONS else "REJECTED"
        print(f"   {f}: {status}")

    print("\n" + "=" * 60)
    print("Diagnostics complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(diagnose())
