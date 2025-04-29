# Lab Report Analysis API

A FastAPI-based service that analyzes lab report images using OCR (Optical Character Recognition) to extract and structure medical test results.

## Features

- Image preprocessing for better OCR accuracy
- Lab test data extraction with reference ranges
- Health check endpoint for service monitoring
- CORS enabled for cross-origin requests
- Automatic Tesseract OCR detection

## Prerequisites

- Python 3.7+
- Tesseract OCR installed on your system
- Required Python packages (see requirements.txt)

## Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd <repo-name>
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install Tesseract OCR:
- Windows: Download and install from [Tesseract GitHub releases](https://github.com/UB-Mannheim/tesseract/wiki)
- Linux: `sudo apt-get install tesseract-ocr`
- macOS: `brew install tesseract`

## Usage

1. Start the server:
```bash
uvicorn main:app --reload
```

2. The API will be available at `http://127.0.0.1:8000/docs`

3. Available endpoints:
- `POST /get-lab-tests` - Upload and analyze lab report images

## Testing

To test all images for ocr data:
```bash
pytest test_api.py
```
To test a specific lab report image:
```python
from test_api import test_lab_report_api
result = test_lab_report_api("path/to/your/lab_report.png")
print(result)
```
