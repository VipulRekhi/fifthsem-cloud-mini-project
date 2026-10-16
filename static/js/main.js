document.addEventListener("DOMContentLoaded", () => {
    // -------------------------------------------------------------------------
    // DOM Elements
    // -------------------------------------------------------------------------
    const s3ConnBanner = document.getElementById("s3ConnBanner");
    const s3ConnStatus = document.getElementById("s3ConnStatus");

    const dropzone = document.getElementById("dropzone");
    const fileInput = document.getElementById("fileInput");
    const selectedFilePreview = document.getElementById("selectedFilePreview");
    const previewFileName = document.getElementById("previewFileName");
    const previewFileSize = document.getElementById("previewFileSize");
    const btnEncrypt = document.getElementById("btnEncrypt");

    const loadingSpinner = document.getElementById("loadingSpinner");
    const spinnerText = document.getElementById("spinnerText");
    const errorBanner = document.getElementById("errorBanner");
    const errorMessage = document.getElementById("errorMessage");

    // Phase 1 Elements
    const resultsSection = document.getElementById("resultsSection");
    const displayFilename = document.getElementById("displayFilename");
    const displayFilesize = document.getElementById("displayFilesize");
    const displayBlockSize = document.getElementById("displayBlockSize");
    const displayTotalBlocks = document.getElementById("displayTotalBlocks");
    const displayStatusText = document.getElementById("displayStatusText");
    const displayOriginalHash = document.getElementById("displayOriginalHash");
    const blocksCountBadge = document.getElementById("blocksCountBadge");
    const blocksList = document.getElementById("blocksList");
    const btnDecrypt = document.getElementById("btnDecrypt");

    const verificationSection = document.getElementById("verificationSection");
    const matchBadge = document.getElementById("matchBadge");
    const matchIcon = document.getElementById("matchIcon");
    const matchTitle = document.getElementById("matchTitle");
    const matchSubtitle = document.getElementById("matchSubtitle");
    const verifyOriginalHash = document.getElementById("verifyOriginalHash");
    const verifyReconstructedHash = document.getElementById("verifyReconstructedHash");
    const btnDownload = document.getElementById("btnDownload");

    // Phase 2 Elements (AWS S3)
    const s3Section = document.getElementById("s3Section");
    const btnS3Upload = document.getElementById("btnS3Upload");
    const btnS3Download = document.getElementById("btnS3Download");
    const s3StatusFeedBox = document.getElementById("s3StatusFeedBox");
    const s3StatusFeedList = document.getElementById("s3StatusFeedList");
    const s3CurrentStatusBadge = document.getElementById("s3CurrentStatusBadge");

    const s3DetailsPanel = document.getElementById("s3DetailsPanel");
    const s3BucketInfo = document.getElementById("s3BucketInfo");
    const s3PrefixDisplay = document.getElementById("s3PrefixDisplay");
    const s3UploadedCount = document.getElementById("s3UploadedCount");
    const s3DownloadedCount = document.getElementById("s3DownloadedCount");
    const s3UploadStatusPill = document.getElementById("s3UploadStatusPill");
    const s3UploadStatusText = document.getElementById("s3UploadStatusText");
    const s3DownloadStatusPill = document.getElementById("s3DownloadStatusPill");
    const s3DownloadStatusText = document.getElementById("s3DownloadStatusText");

    const s3ObjectsBox = document.getElementById("s3ObjectsBox");
    const s3ObjectsList = document.getElementById("s3ObjectsList");

    const s3VerificationBox = document.getElementById("s3VerificationBox");
    const s3MatchBadge = document.getElementById("s3MatchBadge");
    const s3MatchIcon = document.getElementById("s3MatchIcon");
    const s3MatchTitle = document.getElementById("s3MatchTitle");
    const s3MatchSubtitle = document.getElementById("s3MatchSubtitle");
    const s3VerifyOriginalHash = document.getElementById("s3VerifyOriginalHash");
    const s3VerifyReconstructedHash = document.getElementById("s3VerifyReconstructedHash");
    const btnS3DownloadFile = document.getElementById("btnS3DownloadFile");

    const resetBar = document.getElementById("resetBar");
    const btnReset = document.getElementById("btnReset");

    // State Variables
    let currentFile = null;
    let currentFileId = null;
    let currentTotalBlocks = 0;
    let currentUploadedKeys = [];

    // -------------------------------------------------------------------------
    // Utilities
    // -------------------------------------------------------------------------
    function formatBytes(bytes, decimals = 2) {
        if (!+bytes) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
    }

    function showError(msg) {
        errorMessage.textContent = msg;
        errorBanner.style.display = "flex";
    }

    function clearError() {
        errorBanner.style.display = "none";
        errorMessage.textContent = "";
    }

    function showLoading(text) {
        spinnerText.textContent = text;
        loadingSpinner.style.display = "block";
    }

    function hideLoading() {
        loadingSpinner.style.display = "none";
    }

    function logFeed(message, type = "feed-info") {
        s3StatusFeedBox.style.display = "block";
        const timeStr = new Date().toLocaleTimeString();
        const item = document.createElement("div");
        item.className = `feed-item ${type}`;
        item.innerHTML = `<span class="feed-time">[${timeStr}]</span> <span>${message}</span>`;
        s3StatusFeedList.appendChild(item);
        s3StatusFeedList.scrollTop = s3StatusFeedList.scrollHeight;
    }

    // -------------------------------------------------------------------------
    // Initial S3 Connectivity Check
    // -------------------------------------------------------------------------
    async function checkS3Connection() {
        try {
            const res = await fetch("/api/s3/test-connection");
            const data = await res.json();
            if (res.ok && data.status === "success") {
                s3ConnBanner.className = "s3-conn-banner connected";
                s3ConnStatus.textContent = `S3 Connection Successful (${data.bucket} • ${data.region})`;
                s3BucketInfo.textContent = `${data.bucket} (${data.region})`;
                return true;
            } else {
                s3ConnBanner.className = "s3-conn-banner error";
                s3ConnStatus.textContent = data.error || "Failed to connect to AWS S3.";
                return false;
            }
        } catch (e) {
            s3ConnBanner.className = "s3-conn-banner error";
            s3ConnStatus.textContent = "Unable to reach server to test S3 connection.";
            return false;
        }
    }

    checkS3Connection();

    // -------------------------------------------------------------------------
    // Drag and Drop & File Input Handlers
    // -------------------------------------------------------------------------
    ["dragenter", "dragover"].forEach(name => {
        dropzone.addEventListener(name, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add("dragover");
        });
    });

    ["dragleave", "drop"].forEach(name => {
        dropzone.addEventListener(name, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove("dragover");
        });
    });

    dropzone.addEventListener("drop", (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            handleFileSelect(files[0]);
        }
    });

    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });

    function handleFileSelect(file) {
        currentFile = file;
        clearError();
        previewFileName.textContent = file.name;
        previewFileSize.textContent = `${formatBytes(file.size)} (${file.size.toLocaleString()} bytes)`;
        selectedFilePreview.style.display = "flex";

        // Reset later sections
        resultsSection.style.display = "none";
        s3Section.style.display = "none";
        verificationSection.style.display = "none";
        resetBar.style.display = "none";
    }

    // -------------------------------------------------------------------------
    // Phase 1: Local File Encrypt & Chunk Handler
    // -------------------------------------------------------------------------
    btnEncrypt.addEventListener("click", async () => {
        if (!currentFile) {
            showError("Please select a file first.");
            return;
        }

        clearError();
        showLoading("Splitting into 1 MB chunks and encrypting with AES-256-GCM...");
        btnEncrypt.disabled = true;

        const formData = new FormData();
        formData.append("file", currentFile);

        try {
            const response = await fetch("/api/upload", {
                method: "POST",
                body: formData
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || "Failed to process file.");
            }

            const data = result.data;
            currentFileId = data.file_id;
            currentTotalBlocks = data.total_blocks;
            currentUploadedKeys = [];

            // Populate Phase 1 UI requirements
            displayFilename.textContent = data.original_filename;
            displayFilesize.textContent = `${formatBytes(data.original_file_size)} (${data.original_file_size.toLocaleString()} bytes)`;
            displayBlockSize.textContent = `${formatBytes(data.block_size)} (${data.block_size.toLocaleString()} bytes)`;
            displayTotalBlocks.textContent = `${data.total_blocks} block${data.total_blocks > 1 ? 's' : ''}`;
            displayStatusText.textContent = `${data.encryption_status} (${data.encryption_algorithm})`;
            displayOriginalHash.textContent = data.original_sha256;

            // Render block breakdown
            blocksCountBadge.textContent = `${data.total_blocks} Stored Block${data.total_blocks > 1 ? 's' : ''}`;
            blocksList.innerHTML = "";

            data.blocks.forEach((block) => {
                const item = document.createElement("div");
                item.className = "block-item";
                item.innerHTML = `
                    <span class="block-title">Block #${block.block_index + 1}: ${block.filename}</span>
                    <span class="block-meta">Original: ${formatBytes(block.original_chunk_size)} | Encrypted: ${formatBytes(block.encrypted_chunk_size)}</span>
                `;
                blocksList.appendChild(item);
            });

            // Initialize Phase 2 S3 Section State
            s3PrefixDisplay.textContent = `s3://cloud-mini-project-vipul-2026/encrypted-files/${currentFileId}/`;
            s3UploadedCount.textContent = "0";
            s3DownloadedCount.textContent = "0";
            s3UploadStatusPill.className = "status-pill";
            s3UploadStatusText.textContent = "Ready to Upload";
            s3DownloadStatusPill.className = "status-pill";
            s3DownloadStatusText.textContent = "Pending Upload";

            btnS3Upload.disabled = false;
            btnS3Download.disabled = true;
            s3StatusFeedList.innerHTML = "";
            s3StatusFeedBox.style.display = "none";
            s3DetailsPanel.style.display = "block";
            s3ObjectsBox.style.display = "none";
            s3VerificationBox.style.display = "none";

            resultsSection.style.display = "block";
            s3Section.style.display = "block";
            resetBar.style.display = "block";

            s3Section.scrollIntoView({ behavior: "smooth" });

        } catch (err) {
            showError(err.message || "An unexpected error occurred during encryption.");
        } finally {
            hideLoading();
            btnEncrypt.disabled = false;
        }
    });

    // -------------------------------------------------------------------------
    // Phase 2: Upload Encrypted Blocks to S3
    // -------------------------------------------------------------------------
    btnS3Upload.addEventListener("click", async () => {
        if (!currentFileId) {
            showError("No active encrypted file to upload.");
            return;
        }

        clearError();
        btnS3Upload.disabled = true;
        btnS3Download.disabled = true;

        s3StatusFeedBox.style.display = "block";
        s3CurrentStatusBadge.className = "status-badge running";
        s3CurrentStatusBadge.textContent = "Uploading...";

        s3UploadStatusPill.className = "status-pill in-progress";
        s3UploadStatusText.textContent = "Uploading...";

        // Step 1: Verify S3 Connection
        const isConnected = await checkS3Connection();
        if (!isConnected) {
            logFeed("S3 connection error. Aborting upload.", "feed-error");
            showError("Cannot connect to AWS S3. Please verify AWS credentials.");
            btnS3Upload.disabled = false;
            s3CurrentStatusBadge.className = "status-badge";
            s3CurrentStatusBadge.textContent = "Failed";
            s3UploadStatusPill.className = "status-pill error";
            s3UploadStatusText.textContent = "Connection Error";
            return;
        }

        logFeed("S3 connection successful", "feed-success");
        logFeed("Upload started", "feed-info");

        currentUploadedKeys = [];
        s3ObjectsList.innerHTML = "";

        try {
            for (let i = 0; i < currentTotalBlocks; i++) {
                logFeed(`Uploading block ${i + 1} of ${currentTotalBlocks}...`, "feed-alert");

                const res = await fetch(`/api/s3/upload-block/${currentFileId}/${i}`, {
                    method: "POST"
                });
                const result = await res.json();

                if (!res.ok || result.status !== "success") {
                    throw new Error(result.error || `Failed to upload block ${i + 1}`);
                }

                currentUploadedKeys.push(result.s3_uri);
                s3UploadedCount.textContent = `${i + 1} / ${currentTotalBlocks}`;

                // Add to S3 objects display
                const objItem = document.createElement("div");
                objItem.className = "s3-obj-item";
                objItem.textContent = result.s3_uri;
                s3ObjectsList.appendChild(objItem);
            }

            logFeed("Upload completed successfully.", "feed-success");

            s3CurrentStatusBadge.className = "status-badge success";
            s3CurrentStatusBadge.textContent = "Upload Completed";

            s3UploadStatusPill.className = "status-pill success";
            s3UploadStatusText.textContent = "Completed";

            s3ObjectsBox.style.display = "block";
            btnS3Download.disabled = false;

        } catch (err) {
            logFeed(`Upload failed: ${err.message}`, "feed-error");
            showError(`S3 Upload failed: ${err.message}`);
            s3CurrentStatusBadge.className = "status-badge";
            s3CurrentStatusBadge.textContent = "Failed";
            s3UploadStatusPill.className = "status-pill error";
            s3UploadStatusText.textContent = "Upload Failed";
            btnS3Upload.disabled = false;
        }
    });

    // -------------------------------------------------------------------------
    // Phase 2: Download Encrypted Blocks from S3, Decrypt & Verify
    // -------------------------------------------------------------------------
    btnS3Download.addEventListener("click", async () => {
        if (!currentFileId) {
            showError("No active file ID to download.");
            return;
        }

        clearError();
        btnS3Download.disabled = true;

        s3CurrentStatusBadge.className = "status-badge running";
        s3CurrentStatusBadge.textContent = "Downloading & Verifying...";

        s3DownloadStatusPill.className = "status-pill in-progress";
        s3DownloadStatusText.textContent = "Downloading...";

        logFeed("Download started", "feed-info");

        try {
            const res = await fetch(`/api/s3/download-and-verify/${currentFileId}`, {
                method: "POST"
            });
            const result = await res.json();

            if (!res.ok || result.status !== "success") {
                throw new Error(result.error || "Failed to download and verify from S3.");
            }

            const data = result;

            logFeed("Download completed", "feed-success");
            logFeed("Decryption completed", "feed-info");
            logFeed("File reconstructed", "feed-info");

            s3DownloadedCount.textContent = `${data.downloaded_blocks_count}`;
            s3DownloadStatusPill.className = "status-pill success";
            s3DownloadStatusText.textContent = "Completed";

            // Verify hashes
            s3VerifyOriginalHash.textContent = data.original_sha256;
            s3VerifyReconstructedHash.textContent = data.reconstructed_sha256;
            btnS3DownloadFile.href = data.download_url;
            btnS3DownloadFile.setAttribute("download", data.original_filename);

            if (data.matches) {
                logFeed("SHA-256 MATCH ✓", "feed-success");
                s3MatchBadge.className = "verification-badge match";
                s3MatchIcon.textContent = "✓";
                s3MatchTitle.textContent = "SHA-256 MATCH ✓";
                s3MatchSubtitle.textContent = `All ${data.downloaded_blocks_count} blocks downloaded from S3 and verified. File is identical to the original.`;
            } else {
                logFeed("SHA-256 FAILED ✗", "feed-error");
                s3MatchBadge.className = "verification-badge mismatch";
                s3MatchIcon.textContent = "✗";
                s3MatchTitle.textContent = "SHA-256 FAILED ✗";
                s3MatchSubtitle.textContent = "Checksum mismatch detected between original file and reconstructed file.";
            }

            s3VerificationBox.style.display = "block";
            s3CurrentStatusBadge.className = "status-badge success";
            s3CurrentStatusBadge.textContent = "Verification Done";

            s3VerificationBox.scrollIntoView({ behavior: "smooth" });

        } catch (err) {
            logFeed(`Download/Verification failed: ${err.message}`, "feed-error");
            showError(`S3 Download/Verification failed: ${err.message}`);
            s3CurrentStatusBadge.className = "status-badge";
            s3CurrentStatusBadge.textContent = "Failed";
            s3DownloadStatusPill.className = "status-pill error";
            s3DownloadStatusText.textContent = "Failed";
            btnS3Download.disabled = false;
        }
    });

    // -------------------------------------------------------------------------
    // Phase 1: Local Decrypt & Reconstruct Handler (preserved)
    // -------------------------------------------------------------------------
    btnDecrypt.addEventListener("click", async () => {
        if (!currentFileId) {
            showError("No active encrypted file to decrypt.");
            return;
        }

        clearError();
        showLoading("Decrypting blocks with AES-256-GCM & verifying SHA-256 hashes locally...");
        btnDecrypt.disabled = true;

        try {
            const response = await fetch(`/api/decrypt/${currentFileId}`, {
                method: "POST"
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || "Failed to decrypt and reconstruct file.");
            }

            const data = result.data;

            // Fill verification section
            verifyOriginalHash.textContent = data.original_sha256;
            verifyReconstructedHash.textContent = data.reconstructed_sha256;
            btnDownload.href = data.download_url;
            btnDownload.setAttribute("download", data.original_filename);

            if (data.matches) {
                matchBadge.className = "verification-badge match";
                matchIcon.textContent = "✓";
                matchTitle.textContent = "SHA-256 HASHES MATCH (100% IDENTICAL)";
                matchSubtitle.textContent = `All ${data.total_blocks_processed} blocks decrypted correctly. File data integrity is fully preserved.`;
            } else {
                matchBadge.className = "verification-badge mismatch";
                matchIcon.textContent = "✗";
                matchTitle.textContent = "HASH MISMATCH DETECTED";
                matchSubtitle.textContent = "The reconstructed file checksum does not match the original file.";
            }

            verificationSection.style.display = "block";
            verificationSection.scrollIntoView({ behavior: "smooth" });

        } catch (err) {
            showError(err.message || "An error occurred during local decryption.");
        } finally {
            hideLoading();
            btnDecrypt.disabled = false;
        }
    });

    // -------------------------------------------------------------------------
    // Reset Handler
    // -------------------------------------------------------------------------
    btnReset.addEventListener("click", () => {
        currentFile = null;
        currentFileId = null;
        currentTotalBlocks = 0;
        currentUploadedKeys = [];
        fileInput.value = "";
        selectedFilePreview.style.display = "none";
        resultsSection.style.display = "none";
        s3Section.style.display = "none";
        verificationSection.style.display = "none";
        resetBar.style.display = "none";
        clearError();
        window.scrollTo({ top: 0, behavior: "smooth" });
    });
});
