from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Any
import pytesseract
from PIL import Image
import re
import io
import cv2
import numpy as np
import logging
from pathlib import Path
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def find_tesseract():
    common_locations = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\HP\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
        r"C:\Users\HP\AppData\Local\Tesseract-OCR\tesseract.exe"
    ]
    
    from shutil import which
    tesseract_cmd = which('tesseract')
    if tesseract_cmd:
        return tesseract_cmd
    
    for location in common_locations:
        if os.path.isfile(location):
            return location
    
    return None

app = FastAPI(title="Lab Report Analysis API")

static_dir = Path("static")
static_dir.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

tesseract_path = find_tesseract()
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
    logger.info(f"Using Tesseract from: {tesseract_path}")
else:
    logger.error("Tesseract not found in common locations!")

@app.get("/favicon.ico")
async def get_favicon():
    return FileResponse("static/favicon.ico")

def preprocess_image(image: Image.Image) -> np.ndarray:
    img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    binary = cv2.adaptiveThreshold(
        gray, 
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11,  # Block size
        2    # C constant
    )
    
    denoised = cv2.fastNlMeansDenoising(binary)
    
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2,1))
    dilated = cv2.dilate(denoised, kernel, iterations=1)
    
    return dilated

def extract_lab_data(text: str) -> List[Dict[str, Any]]:
    patterns = [
        r"(?P<test_name>[A-Z][A-Z\s\(\)\/]+)\s+(?P<test_value>\d+\.?\d*)\s*(?P<unit>[a-zA-Z%\/]+)?\s*(?P<ref_range>\d+\.?\d*\s*-\s*\d+\.?\d*)",
        r"(?P<test_name>[A-Z][A-Z\s\(\)\/]+):\s*(?P<test_value>\d+\.?\d*)\s*(?P<unit>[a-zA-Z%\/]+)?\s*[\(\[]?(?P<ref_range>\d+\.?\d*\s*-\s*\d+\.?\d*)[\)\]]?",
        r"(?P<test_name>[A-Z][A-Z\s\(\)\/]+)\s*=\s*(?P<test_value>\d+\.?\d*)\s*(?P<unit>[a-zA-Z%\/]+)?\s*[\(\[]?(?P<ref_range>\d+\.?\d*\s*-\s*\d+\.?\d*)[\)\]]?",
        r"(?P<test_name>[A-Z][A-Z\s\(\)\/]+)\s*-\s*(?P<test_value>\d+\.?\d*)\s*(?P<unit>[a-zA-Z%\/]+)?\s*[\(\[]?(?P<ref_range>\d+\.?\d*\s*-\s*\d+\.?\d*)[\)\]]?"
    ]
    
    results = []
    processed_tests = set()
    
    text = text.replace('\n', ' ').replace('\r', ' ')
    text = re.sub(r'\s+', ' ', text)
    
    for pattern in patterns:
        regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        matches = regex.finditer(text)
        
        for match in matches:
            try:
                test_name = match.group("test_name").strip().upper()
                
                if test_name in processed_tests:
                    continue
                
                test_value = float(match.group("test_value"))
                test_unit = match.group("unit").strip() if match.group("unit") else ""
                ref_range = match.group("ref_range").replace(" ", "")
                
                if "-" in ref_range:
                    ref_low, ref_high = map(float, ref_range.split("-"))
                elif "to" in ref_range.lower():
                    ref_low, ref_high = map(float, ref_range.lower().split("to"))
                else:
                    continue
                
                out_of_range = not (ref_low <= test_value <= ref_high)
                
                results.append({
                    "test_name": test_name,
                    "test_value": str(test_value),
                    "bio_reference_range": f"{ref_low}-{ref_high}",
                    "test_unit": test_unit,
                    "lab_test_out_of_range": out_of_range
                })
                
                processed_tests.add(test_name)
                
            except (ValueError, AttributeError) as e:
                logger.warning(f"Error processing match {match.group(0)}: {str(e)}")
                continue
    
    return results

@app.post("/get-lab-tests")
async def get_lab_tests(file: UploadFile = File(...)) -> Dict[str, Any]:
    if not tesseract_path:
        return JSONResponse(content={"is_success": False, "error": "Tesseract OCR is not properly installed. Please install Tesseract OCR and ensure it's in your PATH.", "data": []}, status_code=500)
    
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        processed_image = preprocess_image(image)
        
        custom_config = r'--oem 3 --psm 6 -l eng --dpi 300'
        text = pytesseract.image_to_string(processed_image, config=custom_config)
        
        logger.debug(f"Extracted text:\n{text}")
        
        lab_data = extract_lab_data(text)
        
        if not lab_data:
            logger.warning("No lab data found in the image")
            return JSONResponse(content={"is_success": True, "data": [], "message": "No lab test data found in the image"})
        
        return JSONResponse(content={"is_success": True, "data": lab_data})
        
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        return JSONResponse(content={"is_success": False, "error": str(e), "data": []}, status_code=500)

@app.get("/health")
async def health_check():
    if tesseract_path:
        return {"status": "healthy", "tesseract_path": tesseract_path}
    return {"status": "unhealthy", "error": "Tesseract OCR not found"}
