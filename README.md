# Cloud Computing Mini-Project
## Cloud File Security & Storage System with AWS S3, CloudFront CDN & HTTPS

A complete client-side encrypted cloud storage architecture combining 1 MB file chunking, AES-256-GCM authenticated encryption, private AWS S3 bucket synchronization, end-to-end SHA-256 integrity verification, and a portfolio website delivered via Amazon CloudFront CDN with HTTPS.

---

### Project Architecture Overview

```
                                  +-----------------------------+
                                  |         User File           |
                                  +--------------+--------------+
                                                 |
                                                 v
                                  +-----------------------------+
                                  |   1 MB Block Segmentation   |
                                  |   (Block 1, Block 2, ...)   |
                                  +--------------+--------------+
                                                 |
                                                 v
                                  +-----------------------------+
                                  |   AES-256-GCM Encryption    |
                                  |  (Unique Nonce per Block)   |
                                  +--------------+--------------+
                                                 |
                            +--------------------+--------------------+
                            |                                         |
                            v                                         v
               +-------------------------+              +---------------------------+
               |   Local Block Storage   |              |       AWS S3 Upload       |
               | (storage/encrypted_blocks)             | (s3://.../encrypted-files/|
               +-------------------------+              |       <file-id>/...)      |
                                                        +-------------+-------------+
                                                                      |
                                                                      v
                                                        +---------------------------+
                                                        |      AWS S3 Download      |
                                                        |    (downloaded_blocks/)   |
                                                        +-------------+-------------+
                                                                      |
                                                                      v
                                                        +---------------------------+
                                                        |   AES-256-GCM Decrypt     |
                                                        +-------------+-------------+
                                                                      |
                                                                      v
                                                        +---------------------------+
                                                        |    File Reconstruction    |
                                                        +-------------+-------------+
                                                                      |
                                                                      v
                                                        +---------------------------+
                                                        |  SHA-256 Integrity Check  |
                                                        |     "SHA-256 MATCH ✓"     |
                                                        +---------------------------+

=============================================================================================
                          PHASE 3: PORTFOLIO CDN HOSTING ARCHITECTURE
=============================================================================================

          User / Browser
                |
                |  (1) HTTPS Request
                v
       Amazon CloudFront CDN (Global Edge)
                |
                |  (2) Origin Access Control (OAC) Authenticated Request
                v
       Private Amazon S3 Bucket (cloud-mini-project-vipul-2026)
                |
                +---> s3://.../portfolio/index.html (Delivered to User via HTTPS)
                |
                +---> s3://.../encrypted-files/ (Remains completely private to backend)
```

---

### AWS Configuration Details

- **S3 Bucket Name**: `cloud-mini-project-vipul-2026`
- **AWS Region**: `ap-south-1` (Asia Pacific - Mumbai)
- **Encrypted Blocks Prefix**: `s3://cloud-mini-project-vipul-2026/encrypted-files/<file-id>/`
- **Portfolio Website Prefix**: `s3://cloud-mini-project-vipul-2026/portfolio/`

#### How Boto3 Obtains AWS Credentials
The application relies on Boto3's standard AWS credential chain. It automatically discovers credentials in the following order:
1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. AWS CLI credentials file (`~/.aws/credentials` created via `aws configure`)
3. AWS config file (`~/.aws/config`)
4. Instance metadata service (if running on EC2)

*No access keys or secret keys are hardcoded in the codebase, and no credentials are ever transmitted to or exposed in the frontend.*

---

### Project File Structure

```
Cloud mini project/
├── requirements.txt         # Dependencies (Flask, cryptography, boto3)
├── app.py                   # Flask server (File processing APIs + Portfolio preview)
├── crypto_utils.py          # 1 MB chunking, AES-256-GCM encryption/decryption, SHA-256
├── s3_utils.py              # AWS S3 upload, download, and verification logic
├── upload_portfolio_to_s3.py# Deployment script for portfolio to S3
├── templates/
│   └── index.html           # Main web application UI
├── static/
│   ├── css/
│   │   └── style.css        # Application dark theme stylesheet
│   └── js/
│       └── main.js          # File processing and S3 live progress handling
├── portfolio/               # Phase 3 Portfolio & Documentation Website
│   ├── index.html           # Portfolio homepage (7 project sections)
│   ├── style.css            # Responsive, modern styling
│   └── script.js            # Navigation and scroll interactions
├── downloaded_blocks/       # Temporary storage for blocks downloaded from S3
├── storage/                 # Local data storage
│   ├── encrypted_blocks/    # Stored 1 MB encrypted .enc files
│   ├── reconstructed/       # Assembled files after decryption
│   ├── metadata/            # Metadata and block nonces (JSON)
│   └── keys/                # 256-bit AES master key
├── .env.example             # Optional environment variable configuration
├── .gitignore               # Excludes keys, .env, and downloaded blocks
└── README.md                # Project documentation & CloudFront deployment guide
```

---

### How to Install and Run Locally

#### 1. Navigate to Project Directory
```powershell
cd "c:\Vipul Coading Projects\Cloud mini project"
```

#### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

#### 3. Run the Application
```powershell
python app.py
```

#### 4. Access Local Interfaces
- **File Security Application**: [http://127.0.0.1:5000](http://127.0.0.1:5000)
- **Portfolio & Documentation**: [http://127.0.0.1:5000/portfolio](http://127.0.0.1:5000/portfolio)
  *(You can also open `portfolio/index.html` directly in any web browser without running a server).*

---

### Step-by-Step Guide: Hosting Portfolio on AWS CloudFront via Private S3 (OAC + HTTPS)

Follow these exact steps to host your portfolio securely using **Origin Access Control (OAC)** and **HTTPS** without making your S3 bucket public:

---

#### Step 1: Upload Portfolio Files to S3

You can upload the `portfolio/` files using the included Python script or AWS CLI:

**Option A (Using the included Python script):**
```powershell
python upload_portfolio_to_s3.py
```

**Option B (Using AWS CLI):**
```powershell
aws s3 sync portfolio/ s3://cloud-mini-project-vipul-2026/portfolio/
```

Verify that the following files are in your bucket:
- `s3://cloud-mini-project-vipul-2026/portfolio/index.html`
- `s3://cloud-mini-project-vipul-2026/portfolio/style.css`
- `s3://cloud-mini-project-vipul-2026/portfolio/script.js`

---

#### Step 2: Create a CloudFront Distribution

1. Open the [AWS CloudFront Console](https://console.aws.amazon.com/cloudfront/).
2. Click **Create distribution**.

---

#### Step 3: Configure S3 Origin

1. **Origin domain**: Select your existing S3 bucket:
   `cloud-mini-project-vipul-2026.s3.ap-south-1.amazonaws.com`
2. **Origin path (Optional)**: Enter `/portfolio` so CloudFront automatically serves from the portfolio folder.
3. **Name**: Keep the auto-generated name or specify `S3-cloud-mini-project-vipul-2026`.

---

#### Step 4: Configure Origin Access Control (OAC)

1. Under **Origin access**: Select **Origin access control settings (recommended)**.
2. Click **Create control setting**:
   - **Name**: `cloud-mini-project-oac`
   - **Signing protocol**: `SIGV4`
   - **Origin type**: `S3`
   - **Signing behavior**: `Sign requests (recommended)`
   - Click **Create**.
3. Select your newly created OAC from the dropdown.

> [!IMPORTANT]
> A banner will appear reminding you to update the S3 bucket policy after creating the distribution. Click **Copy policy** when prompted.

---

#### Step 5: Configure Default Cache Behavior & HTTPS

1. **Viewer protocol policy**: Select **Redirect HTTP to HTTPS** (ensures all traffic is encrypted with TLS/HTTPS).
2. **Allowed HTTP methods**: Select **GET, HEAD**.
3. **Cache policy**: Select **CachingOptimized** (recommended for static web assets).

---

#### Step 6: Set Default Root Object

1. Scroll down to the **Settings** panel.
2. In the **Default root object** field, enter:
   ```
   index.html
   ```
3. Leave custom SSL certificate and alternate domain names empty (CloudFront provides a free default `*.cloudfront.net` certificate).
4. Click **Create distribution**.

---

#### Step 7: Update S3 Bucket Policy for CloudFront OAC

1. Open the [AWS S3 Console](https://s3.console.aws.amazon.com/s3/).
2. Select your bucket: `cloud-mini-project-vipul-2026`.
3. Go to the **Permissions** tab.
4. Ensure **Block public access (bucket settings)** remains **ON** (all 4 checkboxes checked).
5. Scroll down to **Bucket policy** and click **Edit**.
6. Paste the following policy (replace `<DISTRIBUTION_ID>` with your CloudFront distribution ID and `<ACCOUNT_ID>` with your 12-digit AWS Account ID):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowCloudFrontServicePrincipalReadOnly",
            "Effect": "Allow",
            "Principal": {
                "Service": "cloudfront.amazonaws.com"
            },
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::cloud-mini-project-vipul-2026/portfolio/*",
            "Condition": {
                "StringEquals": {
                    "AWS:SourceArn": "arn:aws:cloudfront::<ACCOUNT_ID>:distribution/<DISTRIBUTION_ID>"
                }
            }
        }
    ]
}
```

7. Click **Save changes**.

> [!TIP]
> Notice that the `Resource` specifies `.../portfolio/*`. This grants CloudFront read access strictly to your website assets while keeping `encrypted-files/*` completely inaccessible from the web.

---

#### Step 8: Test the CloudFront URL

1. Return to the CloudFront console and copy the **Distribution domain name**, for example:
   ```
   https://d123456abcdef8.cloudfront.net
   ```
2. Wait a few minutes until the distribution status changes from **Deploying** to **Enabled**.
3. Open the URL in your browser:
   - Notice the secure padlock icon (**HTTPS**).
   - Your portfolio website will load with full styling and interactivity.
   - The S3 bucket remains 100% private.

---

### Security & Privacy Summary

| Component | Security Mechanism | Protection Level |
| :--- | :--- | :--- |
| **File Chunking** | 1 MB deterministic segmentation | Limits exposure of large single payloads |
| **Block Encryption** | AES-256-GCM (Authenticated AEAD) | Confidentiality + 16-byte tamper detection tag |
| **Block Nonces** | Unique 96-bit (12-byte) initialization vectors | Prevents replay attacks & ciphertext pattern analysis |
| **AWS S3 Storage** | Block Public Access Enabled | Bucket is completely private; no public web access |
| **Content Delivery** | Amazon CloudFront CDN + HTTPS | Free SSL/TLS encryption in transit across edge locations |
| **S3 Access Control** | CloudFront Origin Access Control (OAC) | Only authenticated CloudFront edge nodes can fetch website files |
| **Credentials** | Standard AWS CLI Credential Chain | Zero credentials in frontend code or Git repositories |
| **Integrity Verification** | End-to-end SHA-256 hashing | Mathematical guarantee of bit-for-bit file reconstruction |
