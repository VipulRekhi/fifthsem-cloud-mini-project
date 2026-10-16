import os
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from flask_cors import CORS
import crypto_utils
import s3_utils

# Load environment variables from .env if present
load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 MB limit

# CORS Configuration: allow Cloudflare Pages portfolio and local dev by default
DEFAULT_ORIGINS = [
    "https://quiet-night-ad88.vipulrekhi.workers.dev",
    "http://127.0.0.1:5000",
    "http://localhost:5000",
]
env_cors = os.getenv("CORS_ORIGINS", "")
if env_cors.strip():
    allowed_origins = [orig.strip() for orig in env_cors.split(",") if orig.strip()]
else:
    allowed_origins = DEFAULT_ORIGINS

CORS(app, resources={r"/api/*": {"origins": allowed_origins}}, supports_credentials=True)

# Initialize storage and S3 download folders
crypto_utils.init_storage()
s3_utils.init_s3_storage()


@app.route("/healthz", methods=["GET"])
def health_check():
    """Health check endpoint for Render deployment monitoring."""
    return jsonify({
        "status": "healthy",
        "service": "cloud-file-security-storage",
        "version": "1.0.0",
        "s3_bucket": s3_utils.S3_BUCKET_NAME,
        "aws_region": s3_utils.AWS_REGION
    }), 200


@app.route("/")
def index():
    """Render the main single-page UI."""
    return render_template("index.html")


# =====================================================================
# Phase 1: Local Chunking & Encryption APIs
# =====================================================================

@app.route("/api/upload", methods=["POST"])
def upload_and_encrypt():
    """
    Accepts a file upload, splits into 1 MB blocks, encrypts each block
    using AES-256-GCM, stores blocks locally, and returns processing info.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    safe_name = secure_filename(file.filename) or "uploaded_file"

    try:
        metadata = crypto_utils.process_and_encrypt_file(file.stream, safe_name)
        return jsonify({
            "status": "success",
            "message": "File chunked and encrypted successfully.",
            "data": {
                "file_id": metadata["file_id"],
                "original_filename": metadata["original_filename"],
                "original_file_size": metadata["original_file_size"],
                "block_size": metadata["block_size"],
                "total_blocks": metadata["total_blocks"],
                "encryption_status": metadata["encryption_status"],
                "encryption_algorithm": metadata["encryption_algorithm"],
                "original_sha256": metadata["original_sha256"],
                "blocks": metadata["blocks"]
            }
        })
    except Exception as e:
        return jsonify({"error": f"Encryption failed: {str(e)}"}), 500


@app.route("/api/decrypt/<file_id>", methods=["POST"])
def decrypt_and_reconstruct_local(file_id: str):
    """
    Decrypts locally stored blocks for the file, reconstructs the original,
    computes SHA-256 for original & reconstructed files, and checks match.
    """
    try:
        result = crypto_utils.decrypt_and_reconstruct_file(file_id)
        return jsonify({
            "status": "success",
            "message": "File decrypted and reconstructed successfully.",
            "data": result
        })
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Local decryption failed: {str(e)}"}), 500


@app.route("/api/download/<file_id>", methods=["GET"])
def download_reconstructed(file_id: str):
    """Allows downloading the reconstructed file (local or S3 source)."""
    try:
        metadata = s3_utils.get_metadata_with_s3_fallback(file_id)
        source = request.args.get("source", "local")

        if source == "s3":
            rec_filename = f"s3_reconstructed_{metadata['original_filename']}"
        else:
            rec_filename = f"reconstructed_{metadata['original_filename']}"

        reconstructed_path = crypto_utils.RECONSTRUCTED_DIR / f"{file_id}_{rec_filename}"

        # Fallback if specific source file isn't found
        if not reconstructed_path.exists():
            alt_filename = f"reconstructed_{metadata['original_filename']}" if source == "s3" else f"s3_reconstructed_{metadata['original_filename']}"
            reconstructed_path = crypto_utils.RECONSTRUCTED_DIR / f"{file_id}_{alt_filename}"

        if not reconstructed_path.exists():
            return jsonify({"error": "Reconstructed file not found. Decrypt it first."}), 404

        return send_file(
            reconstructed_path,
            as_attachment=True,
            download_name=metadata["original_filename"]
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 404


# =====================================================================
# Phase 2: AWS S3 Integration APIs
# =====================================================================

@app.route("/api/s3/test-connection", methods=["GET"])
def test_s3_connection():
    """Verify AWS S3 connectivity and bucket access."""
    res = s3_utils.check_s3_connection()
    if res.get("status") == "success":
        return jsonify(res)
    return jsonify(res), 500


@app.route("/api/s3/upload-block/<file_id>/<int:block_index>", methods=["POST"])
def s3_upload_block(file_id: str, block_index: int):
    """
    Upload a single encrypted block to:
    s3://cloud-mini-project-vipul-2026/encrypted-files/<file_id>/block_XXX.enc
    """
    try:
        result = s3_utils.upload_single_block_to_s3(file_id, block_index)
        return jsonify(result)
    except Exception as e:
        err_dict = s3_utils.handle_s3_exception(e)
        return jsonify(err_dict), 500


@app.route("/api/s3/upload/<file_id>", methods=["POST"])
def s3_upload_all(file_id: str):
    """Batch upload all encrypted blocks for a given file ID to S3."""
    try:
        result = s3_utils.upload_all_blocks_to_s3(file_id)
        return jsonify(result)
    except Exception as e:
        err_dict = s3_utils.handle_s3_exception(e)
        return jsonify(err_dict), 500


@app.route("/api/s3/download-and-verify/<file_id>", methods=["POST"])
def s3_download_and_verify(file_id: str):
    """
    1. Downloads encrypted blocks from S3 to downloaded_blocks/<file_id>/
    2. Decrypts blocks using AES-256-GCM
    3. Reconstructs original file
    4. Computes SHA-256 and compares with original
    """
    try:
        result = s3_utils.download_and_verify_from_s3(file_id)
        return jsonify(result)
    except Exception as e:
        err_dict = s3_utils.handle_s3_exception(e)
        return jsonify(err_dict), 500


@app.route("/api/cleanup/<file_id>", methods=["POST", "DELETE"])
def cleanup_file(file_id: str):
    """Purge locally cached blocks and reconstructed files for a given file ID."""
    try:
        res_local = crypto_utils.cleanup_local_file_data(file_id)
        res_downloaded = s3_utils.cleanup_downloaded_blocks(file_id)
        return jsonify({
            "status": "success",
            "file_id": file_id,
            "deleted_local_blocks": res_local["deleted_blocks"],
            "deleted_reconstructed": res_local["deleted_reconstructed"],
            "deleted_downloaded_blocks": res_downloaded
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Cleanup failed: {str(e)}"}), 500


# =====================================================================
# Phase 3: Portfolio Website Route
# =====================================================================

@app.route("/portfolio/")
def portfolio_index():
    """Serve the portfolio index page."""
    portfolio_dir = Path(__file__).resolve().parent / "portfolio"
    return send_from_directory(portfolio_dir, "index.html")


@app.route("/portfolio/<path:filename>")
def portfolio_static(filename):
    """Serve static assets for portfolio website."""
    portfolio_dir = Path(__file__).resolve().parent / "portfolio"
    return send_from_directory(portfolio_dir, filename)


# Fallbacks to ensure stylesheet and script load under all base URL resolutions
@app.route("/style.css")
def portfolio_style_fallback():
    portfolio_dir = Path(__file__).resolve().parent / "portfolio"
    return send_from_directory(portfolio_dir, "style.css")


@app.route("/script.js")
def portfolio_script_fallback():
    portfolio_dir = Path(__file__).resolve().parent / "portfolio"
    return send_from_directory(portfolio_dir, "script.js")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() in ("true", "1", "t")
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
