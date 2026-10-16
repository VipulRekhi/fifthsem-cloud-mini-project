import os
import json
import hashlib
from pathlib import Path
import boto3
from botocore.exceptions import (
    NoCredentialsError,
    PartialCredentialsError,
    ClientError,
    EndpointConnectionError
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import crypto_utils

# Base paths
BASE_DIR = Path(__file__).resolve().parent
DOWNLOADED_BLOCKS_DIR = BASE_DIR / "downloaded_blocks"

# S3 Configuration
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "cloud-mini-project-vipul-2026")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")


def init_s3_storage():
    """Ensure downloaded_blocks directory exists locally."""
    DOWNLOADED_BLOCKS_DIR.mkdir(parents=True, exist_ok=True)


def get_s3_client():
    """Create a boto3 S3 client using standard AWS credential chain."""
    return boto3.client("s3", region_name=AWS_REGION)


def check_s3_connection() -> dict:
    """
    Test S3 connectivity and verify that the specified bucket exists and is accessible.
    """
    try:
        s3 = get_s3_client()
        s3.head_bucket(Bucket=S3_BUCKET_NAME)
        return {
            "status": "success",
            "message": "S3 connection successful",
            "bucket": S3_BUCKET_NAME,
            "region": AWS_REGION
        }
    except Exception as e:
        return handle_s3_exception(e)


def handle_s3_exception(e: Exception) -> dict:
    """Format known AWS/S3 exceptions into user-friendly error dictionaries."""
    if isinstance(e, (NoCredentialsError, PartialCredentialsError)):
        return {
            "status": "error",
            "error": "AWS credentials not found. Please ensure AWS CLI is configured with 'aws configure'.",
            "code": "NO_CREDENTIALS"
        }
    if isinstance(e, EndpointConnectionError):
        return {
            "status": "error",
            "error": f"Failed to connect to AWS S3 endpoint in region {AWS_REGION}. Check network connection.",
            "code": "CONNECTION_ERROR"
        }
    if isinstance(e, ClientError):
        code = e.response.get("Error", {}).get("Code", "ClientError")
        message = e.response.get("Error", {}).get("Message", str(e))
        if code in ("NoSuchBucket", "404"):
            return {
                "status": "error",
                "error": f"S3 bucket '{S3_BUCKET_NAME}' does not exist or is inaccessible.",
                "code": "NO_SUCH_BUCKET"
            }
        if code in ("AccessDenied", "403"):
            return {
                "status": "error",
                "error": f"Access denied to bucket '{S3_BUCKET_NAME}'. Check IAM permissions.",
                "code": "ACCESS_DENIED"
            }
        return {
            "status": "error",
            "error": f"S3 Client Error ({code}): {message}",
            "code": code
        }
    return {
        "status": "error",
        "error": f"Unexpected error: {str(e)}",
        "code": "GENERAL_ERROR"
    }


def upload_single_block_to_s3(file_id: str, block_index: int) -> dict:
    """
    Upload a single encrypted block to:
    s3://cloud-mini-project-vipul-2026/encrypted-files/<file_id>/block_XXX.enc
    Preserves ordering (block_001.enc, block_002.enc, ...)
    """
    metadata = crypto_utils.get_file_metadata(file_id)
    blocks = metadata.get("blocks", [])

    if block_index < 0 or block_index >= len(blocks):
        raise IndexError(f"Block index {block_index} out of range (total: {len(blocks)}).")

    block_info = blocks[block_index]
    local_block_path = crypto_utils.BLOCKS_DIR / block_info["filename"]

    if not local_block_path.exists():
        raise FileNotFoundError(f"Local block file {block_info['filename']} not found.")

    s3_filename = f"block_{block_index + 1:03d}.enc"
    s3_key = f"encrypted-files/{file_id}/{s3_filename}"

    s3 = get_s3_client()
    s3.upload_file(
        Filename=str(local_block_path),
        Bucket=S3_BUCKET_NAME,
        Key=s3_key,
        ExtraArgs={
            "Metadata": {
                "nonce": block_info["nonce_hex"],
                "block-index": str(block_index),
                "original-chunk-size": str(block_info["original_chunk_size"])
            }
        }
    )

    s3_uri = f"s3://{S3_BUCKET_NAME}/{s3_key}"

    # If this is the last block, also upload metadata manifest for completeness
    if block_index == len(blocks) - 1:
        meta_path = crypto_utils.METADATA_DIR / f"{file_id}.json"
        if meta_path.exists():
            s3.upload_file(
                Filename=str(meta_path),
                Bucket=S3_BUCKET_NAME,
                Key=f"encrypted-files/{file_id}/metadata.json"
            )

    return {
        "status": "success",
        "file_id": file_id,
        "block_index": block_index,
        "total_blocks": len(blocks),
        "s3_key": s3_key,
        "s3_uri": s3_uri,
        "s3_filename": s3_filename
    }


def upload_all_blocks_to_s3(file_id: str) -> dict:
    """
    Upload all encrypted blocks of a file to S3 in batch mode.
    """
    metadata = crypto_utils.get_file_metadata(file_id)
    blocks = metadata.get("blocks", [])
    total_blocks = len(blocks)
    uploaded_keys = []

    for idx in range(total_blocks):
        result = upload_single_block_to_s3(file_id, idx)
        uploaded_keys.append(result["s3_uri"])

    s3_prefix = f"s3://{S3_BUCKET_NAME}/encrypted-files/{file_id}/"

    return {
        "status": "success",
        "file_id": file_id,
        "s3_prefix": s3_prefix,
        "uploaded_blocks_count": total_blocks,
        "uploaded_keys": uploaded_keys,
        "message": "Upload completed successfully."
    }


def recover_metadata_from_s3(file_id: str) -> dict:
    """
    Attempt to recover metadata.json for file_id from S3 if local metadata is missing.
    Saves it locally to crypto_utils.METADATA_DIR for subsequent operations.
    """
    if not crypto_utils.validate_file_id(file_id):
        raise ValueError(f"Invalid file_id format: '{file_id}'")

    crypto_utils.init_storage()
    local_meta_path = crypto_utils.METADATA_DIR / f"{file_id}.json"
    if local_meta_path.exists():
        with open(local_meta_path, "r", encoding="utf-8") as mf:
            return json.load(mf)

    s3_key = f"encrypted-files/{file_id}/metadata.json"
    s3 = get_s3_client()
    try:
        response = s3.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        data = json.loads(response["Body"].read().decode("utf-8"))
        with open(local_meta_path, "w", encoding="utf-8") as mf:
            json.dump(data, mf, indent=2)
        return data
    except Exception as e:
        raise FileNotFoundError(
            f"Metadata for file ID '{file_id}' not found locally or in S3 ({str(e)})."
        )


def get_metadata_with_s3_fallback(file_id: str) -> dict:
    """Retrieve metadata from local disk, or recover from S3 if missing."""
    try:
        return crypto_utils.get_file_metadata(file_id)
    except FileNotFoundError:
        return recover_metadata_from_s3(file_id)


def cleanup_downloaded_blocks(file_id: str) -> int:
    """Safely remove locally downloaded encrypted blocks for a given file_id."""
    if not crypto_utils.validate_file_id(file_id):
        raise ValueError(f"Invalid file_id format: '{file_id}'")

    file_download_dir = DOWNLOADED_BLOCKS_DIR / file_id
    deleted = 0
    if file_download_dir.exists():
        for f in file_download_dir.iterdir():
            if f.is_file():
                try:
                    f.unlink()
                    deleted += 1
                except OSError:
                    pass
        try:
            file_download_dir.rmdir()
        except OSError:
            pass
    return deleted


def download_and_verify_from_s3(file_id: str) -> dict:
    """
    1. Downloads all encrypted blocks for file_id from S3 into downloaded_blocks/<file_id>/
    2. Decrypts blocks using AES-256-GCM
    3. Reconstructs original file
    4. Computes SHA-256 of reconstructed file
    5. Compares with original file's SHA-256
    """
    init_s3_storage()
    metadata = get_metadata_with_s3_fallback(file_id)
    total_expected_blocks = metadata["total_blocks"]

    # Local target directory for downloaded encrypted blocks
    file_download_dir = DOWNLOADED_BLOCKS_DIR / file_id
    file_download_dir.mkdir(parents=True, exist_ok=True)

    s3 = get_s3_client()
    s3_prefix_key = f"encrypted-files/{file_id}/"

    # List objects in S3 folder
    response = s3.list_objects_v2(
        Bucket=S3_BUCKET_NAME,
        Prefix=s3_prefix_key
    )

    if "Contents" not in response or len(response["Contents"]) == 0:
        raise FileNotFoundError(f"No encrypted blocks found in S3 under {s3_prefix_key}")

    # Identify and sort encrypted block objects (block_001.enc, block_002.enc, ...)
    block_objects = [
        obj["Key"] for obj in response["Contents"]
        if obj["Key"].endswith(".enc") and "block_" in obj["Key"]
    ]
    block_objects.sort()

    if len(block_objects) < total_expected_blocks:
        raise ValueError(
            f"Incomplete download: Expected {total_expected_blocks} blocks, but found {len(block_objects)} in S3."
        )

    downloaded_files = []
    # Download each encrypted block to downloaded_blocks/<file_id>/
    for key in block_objects:
        filename = Path(key).name
        target_path = file_download_dir / filename
        s3.download_file(
            Bucket=S3_BUCKET_NAME,
            Key=key,
            Filename=str(target_path)
        )
        downloaded_files.append({
            "s3_key": key,
            "filename": filename,
            "local_path": str(target_path),
            "size": target_path.stat().st_size
        })

    # Decrypt and Reconstruct using existing AES-256-GCM logic
    key = crypto_utils.get_or_create_key()
    aesgcm = AESGCM(key)

    reconstructed_dir = crypto_utils.RECONSTRUCTED_DIR
    reconstructed_dir.mkdir(parents=True, exist_ok=True)
    reconstructed_filename = f"s3_reconstructed_{metadata['original_filename']}"
    reconstructed_path = reconstructed_dir / f"{file_id}_{reconstructed_filename}"

    with open(reconstructed_path, "wb") as rf:
        for idx, block_meta in enumerate(metadata["blocks"]):
            expected_block_name = f"block_{idx + 1:03d}.enc"
            local_block_path = file_download_dir / expected_block_name

            if not local_block_path.exists():
                raise FileNotFoundError(f"Downloaded block {expected_block_name} is missing.")

            with open(local_block_path, "rb") as bf:
                encrypted_data = bf.read()

            nonce = bytes.fromhex(block_meta["nonce_hex"])
            decrypted_chunk = aesgcm.decrypt(nonce, encrypted_data, None)
            rf.write(decrypted_chunk)

    # Compute SHA-256 and compare
    reconstructed_sha256 = crypto_utils.compute_file_sha256(reconstructed_path)
    original_sha256 = metadata["original_sha256"]
    hashes_match = (reconstructed_sha256.lower() == original_sha256.lower())

    s3_prefix_uri = f"s3://{S3_BUCKET_NAME}/encrypted-files/{file_id}/"

    return {
        "status": "success",
        "file_id": file_id,
        "original_filename": metadata["original_filename"],
        "reconstructed_filename": reconstructed_filename,
        "s3_prefix": s3_prefix_uri,
        "downloaded_blocks_count": len(downloaded_files),
        "downloaded_files": [d["filename"] for d in downloaded_files],
        "original_sha256": original_sha256,
        "reconstructed_sha256": reconstructed_sha256,
        "matches": hashes_match,
        "match_message": "SHA-256 MATCH ✓" if hashes_match else "SHA-256 FAILED ✗",
        "download_url": f"/api/download/{file_id}?source=s3"
    }
