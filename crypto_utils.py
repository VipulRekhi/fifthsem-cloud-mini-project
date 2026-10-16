import os
import uuid
import json
import hashlib
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Directory paths
BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"
BLOCKS_DIR = STORAGE_DIR / "encrypted_blocks"
RECONSTRUCTED_DIR = STORAGE_DIR / "reconstructed"
METADATA_DIR = STORAGE_DIR / "metadata"
KEYS_DIR = STORAGE_DIR / "keys"

KEY_FILE = KEYS_DIR / "master.key"
BLOCK_SIZE = 1024 * 1024  # 1 MB blocks


def init_storage():
    """Ensure all required local storage directories exist."""
    BLOCKS_DIR.mkdir(parents=True, exist_ok=True)
    RECONSTRUCTED_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    KEYS_DIR.mkdir(parents=True, exist_ok=True)


def get_or_create_key() -> bytes:
    """
    Retrieve existing 256-bit AES key:
    1. Check ENCRYPTION_MASTER_KEY_HEX environment variable (primary for production).
    2. Fall back to local KEY_FILE if present (for local development continuity).
    3. Generate and persist a new key only if neither is available.
    Never logs or exposes key material.
    """
    init_storage()

    # 1. Check production environment variable
    env_key_hex = os.getenv("ENCRYPTION_MASTER_KEY_HEX")
    if env_key_hex and env_key_hex.strip():
        cleaned_hex = env_key_hex.strip()
        try:
            key = bytes.fromhex(cleaned_hex)
            if len(key) != 32:
                raise ValueError(
                    f"ENCRYPTION_MASTER_KEY_HEX must decode to 32 bytes (256 bits). Got {len(key)} bytes."
                )
            return key
        except ValueError as e:
            raise ValueError(f"Invalid ENCRYPTION_MASTER_KEY_HEX format: {e}")

    # 2. Check local key file
    if KEY_FILE.exists():
        with open(KEY_FILE, "rb") as f:
            key = f.read()
            if len(key) == 32:
                return key

    # 3. Generate new key if neither is found
    key = AESGCM.generate_key(bit_length=256)
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    return key


def compute_file_sha256(filepath: Path) -> str:
    """Compute SHA-256 hash of a file efficiently by reading in chunks."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(64 * 1024):
            sha256.update(chunk)
    return sha256.hexdigest()


def process_and_encrypt_file(file_storage, filename: str) -> dict:
    """
    Saves uploaded stream, computes original SHA-256, splits into 1 MB blocks,
    encrypts each block using AES-256-GCM, and stores encrypted blocks locally.
    """
    init_storage()
    file_id = uuid.uuid4().hex[:12]
    key = get_or_create_key()
    aesgcm = AESGCM(key)

    original_sha256 = hashlib.sha256()
    blocks_info = []
    total_bytes = 0
    block_index = 0

    while True:
        chunk = file_storage.read(BLOCK_SIZE)
        if not chunk:
            # Handle empty file edge case (0 byte file)
            if block_index == 0:
                pass
            break

        chunk_size = len(chunk)
        total_bytes += chunk_size
        original_sha256.update(chunk)

        # 12-byte (96-bit) standard nonce for AES-GCM
        nonce = os.urandom(12)
        encrypted_chunk = aesgcm.encrypt(nonce, chunk, None)

        block_filename = f"{file_id}_block_{block_index}.enc"
        block_path = BLOCKS_DIR / block_filename

        with open(block_path, "wb") as bf:
            bf.write(encrypted_chunk)

        blocks_info.append({
            "block_index": block_index,
            "filename": block_filename,
            "original_chunk_size": chunk_size,
            "encrypted_chunk_size": len(encrypted_chunk),
            "nonce_hex": nonce.hex()
        })
        block_index += 1

    # Special handling if file was 0 bytes: create 1 empty block
    if block_index == 0:
        nonce = os.urandom(12)
        encrypted_chunk = aesgcm.encrypt(nonce, b"", None)
        block_filename = f"{file_id}_block_0.enc"
        block_path = BLOCKS_DIR / block_filename
        with open(block_path, "wb") as bf:
            bf.write(encrypted_chunk)
        blocks_info.append({
            "block_index": 0,
            "filename": block_filename,
            "original_chunk_size": 0,
            "encrypted_chunk_size": len(encrypted_chunk),
            "nonce_hex": nonce.hex()
        })
        block_index = 1

    original_hash = original_sha256.hexdigest()

    metadata = {
        "file_id": file_id,
        "original_filename": filename,
        "original_file_size": total_bytes,
        "block_size": BLOCK_SIZE,
        "total_blocks": len(blocks_info),
        "encryption_algorithm": "AES-256-GCM",
        "encryption_status": "Success",
        "original_sha256": original_hash,
        "blocks": blocks_info
    }

    metadata_path = METADATA_DIR / f"{file_id}.json"
    with open(metadata_path, "w", encoding="utf-8") as mf:
        json.dump(metadata, mf, indent=2)

    return metadata


def decrypt_and_reconstruct_file(file_id: str) -> dict:
    """
    Reads encrypted blocks, decrypts each block with AES-256-GCM,
    reconstructs original file, computes reconstructed SHA-256,
    and checks if it matches original SHA-256.
    """
    metadata_path = METADATA_DIR / f"{file_id}.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata for file ID '{file_id}' not found.")

    with open(metadata_path, "r", encoding="utf-8") as mf:
        metadata = json.load(mf)

    key = get_or_create_key()
    aesgcm = AESGCM(key)

    reconstructed_filename = f"reconstructed_{metadata['original_filename']}"
    reconstructed_path = RECONSTRUCTED_DIR / f"{file_id}_{reconstructed_filename}"

    with open(reconstructed_path, "wb") as rf:
        for block in metadata["blocks"]:
            block_file = BLOCKS_DIR / block["filename"]
            if not block_file.exists():
                raise FileNotFoundError(f"Block file {block['filename']} is missing.")

            with open(block_file, "rb") as bf:
                encrypted_data = bf.read()

            nonce = bytes.fromhex(block["nonce_hex"])
            decrypted_chunk = aesgcm.decrypt(nonce, encrypted_data, None)
            rf.write(decrypted_chunk)

    reconstructed_sha256 = compute_file_sha256(reconstructed_path)
    original_sha256 = metadata["original_sha256"]
    hashes_match = (reconstructed_sha256.lower() == original_sha256.lower())

    return {
        "file_id": file_id,
        "original_filename": metadata["original_filename"],
        "reconstructed_filename": reconstructed_filename,
        "original_sha256": original_sha256,
        "reconstructed_sha256": reconstructed_sha256,
        "matches": hashes_match,
        "total_blocks_processed": len(metadata["blocks"]),
        "download_url": f"/api/download/{file_id}"
    }


def validate_file_id(file_id: str) -> bool:
    """Validate that file_id contains only alphanumeric chars, hyphens, or underscores."""
    import re
    return bool(file_id and re.fullmatch(r"^[a-zA-Z0-9_-]{4,32}$", file_id))


def get_file_metadata(file_id: str) -> dict:
    """Load metadata by file ID with path sanitization."""
    if not validate_file_id(file_id):
        raise ValueError(f"Invalid file_id format: '{file_id}'")
    metadata_path = METADATA_DIR / f"{file_id}.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata for file ID '{file_id}' not found.")
    with open(metadata_path, "r", encoding="utf-8") as mf:
        return json.load(mf)


def cleanup_local_file_data(file_id: str) -> dict:
    """
    Safely purges locally stored temporary encrypted blocks and reconstructed files
    associated with a specific file_id.
    """
    if not validate_file_id(file_id):
        raise ValueError(f"Invalid file_id format: '{file_id}'")

    deleted_blocks = 0
    deleted_reconstructed = 0

    # Clean local encrypted blocks
    if BLOCKS_DIR.exists():
        for block_file in BLOCKS_DIR.glob(f"{file_id}_block_*.enc"):
            try:
                block_file.unlink()
                deleted_blocks += 1
            except OSError:
                pass

    # Clean local reconstructed files
    if RECONSTRUCTED_DIR.exists():
        for rec_file in RECONSTRUCTED_DIR.glob(f"{file_id}_*"):
            try:
                rec_file.unlink()
                deleted_reconstructed += 1
            except OSError:
                pass

    return {
        "status": "success",
        "file_id": file_id,
        "deleted_blocks": deleted_blocks,
        "deleted_reconstructed": deleted_reconstructed
    }


def cleanup_expired_files(max_age_seconds: int = 3600) -> int:
    """
    Removes temporary reconstructed files older than max_age_seconds
    to prevent ephemeral disk exhaustion on hosting services.
    """
    import time
    now = time.time()
    cleaned = 0

    if RECONSTRUCTED_DIR.exists():
        for item in RECONSTRUCTED_DIR.iterdir():
            if item.is_file():
                try:
                    if (now - item.stat().st_mtime) > max_age_seconds:
                        item.unlink()
                        cleaned += 1
                except OSError:
                    pass

    return cleaned
