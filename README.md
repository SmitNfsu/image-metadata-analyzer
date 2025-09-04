# Image Metadata Analyzer (Streamlit)

A simple web app to extract image metadata (EXIF/IPTC), decode GPS, run OCR (Tesseract), and detect the OCR text language.

## Features
- Extract EXIF (camera model, datetime, GPSInfo, etc.)
- Decode GPS to decimal and open Google Maps link
- Extract IPTC (if present)
- OCR via Tesseract (optional)
- Language detection for OCR text (optional)
- Download consolidated results as JSON

## Quick Start

### 1) Install system dependencies

- macOS (Homebrew):
```bash
brew install tesseract
```
- Ubuntu/Debian:
```bash
sudo apt-get update && sudo apt-get install -y tesseract-ocr
```

OCR and language detection are optional. If Tesseract is not installed, the app will still run but OCR will be disabled.

### 2) Create venv and install Python deps
```bash
cd "01_Image Metadata Analysis"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3) Run the app
```bash
streamlit run streamlit_app.py
```

Open the URL printed in the terminal (usually http://localhost:8501).

## Usage
1. Upload an image (JPG/JPEG/PNG/TIFF/WEBP)
2. Review preview and metadata panels
3. If GPS is present, click the Google Maps link
4. (Optional) Enable OCR and language detection in the sidebar
5. Download the combined JSON result

## Notes
- For GPS to be present in mobile photos, location services must have been enabled when the photo was taken.
- IPTC extraction uses `iptcinfo3`. Some images may not contain IPTC.
- If OCR returns empty text, it may be due to low contrast, unusual fonts, or the image not containing text.

## Tech Stack
- Streamlit, Pillow, pytesseract, langdetect, iptcinfo3

## License
MIT
