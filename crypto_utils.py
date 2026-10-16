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
    """Retrieve existing 256-bit AES key or generate a new one."""
    init_storage()
    if KEY_FILE.exists():
        with open(KEY_FILE, "rb") as f:
            return f.read()
    else:
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


def get_file_metadata(file_id: str) -> dict:
    """Load metadata by file ID."""
    metadata_path = METADATA_DIR / f"{file_id}.json"
    if not metadata_path.exists():
        raise FileNotFoundError("Metadata not found")
    with open(metadata_path, "r", encoding="utf-8") as mf:
        return json.load(mf)
