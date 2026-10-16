"""
Utility script to deploy the portfolio website to Amazon S3.
Uploads portfolio/ files (index.html, style.css, script.js) to the private S3 bucket
cloud-mini-project-vipul-2026 with correct Content-Type headers for CloudFront delivery.
"""

import os
import mimetypes
from pathlib import Path
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "cloud-mini-project-vipul-2026")
REGION_NAME = os.getenv("AWS_REGION", "ap-south-1")
PORTFOLIO_DIR = Path(__file__).resolve().parent / "portfolio"


def upload_portfolio(target_prefix="portfolio"):
    """
    Uploads portfolio files to S3.
    target_prefix: 'portfolio' (s3://bucket/portfolio/...) or '' for bucket root.
    """
    print(f"Connecting to AWS S3 ({REGION_NAME})...")
    s3 = boto3.client("s3", region_name=REGION_NAME)

    if not PORTFOLIO_DIR.exists():
        print(f"Error: Directory {PORTFOLIO_DIR} not found.")
        return

    files_to_upload = [f for f in PORTFOLIO_DIR.iterdir() if f.is_file()]
    print(f"Found {len(files_to_upload)} files in {PORTFOLIO_DIR.name}/ to upload.")

    for file_path in files_to_upload:
        filename = file_path.name
        content_type, _ = mimetypes.guess_type(str(file_path))
        if filename.endswith(".css"):
            content_type = "text/css"
        elif filename.endswith(".js"):
            content_type = "application/javascript"
        elif filename.endswith(".html"):
            content_type = "text/html"

        s3_key = f"{target_prefix}/{filename}".lstrip("/")

        print(f"Uploading {filename} -> s3://{BUCKET_NAME}/{s3_key} [{content_type}]...")
        s3.upload_file(
            Filename=str(file_path),
            Bucket=BUCKET_NAME,
            Key=s3_key,
            ExtraArgs={
                "ContentType": content_type or "application/octet-stream"
            }
        )

    print(f"\nPortfolio successfully uploaded to s3://{BUCKET_NAME}/{target_prefix}/")


if __name__ == "__main__":
    try:
        upload_portfolio(target_prefix="portfolio")
    except NoCredentialsError:
        print("Error: AWS credentials not found. Run 'aws configure' first.")
    except Exception as e:
        print(f"Error during upload: {e}")
