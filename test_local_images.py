import os
from pathlib import Path
import pytesseract
from PIL import Image
import cv2
import numpy as np
from main import preprocess_image, extract_lab_data
import logging
import json
from datetime import datetime

# Create results directory if it doesn't exist
RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)

# Generate timestamp for file names
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# Configure logging to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(RESULTS_DIR / f'lab_results_{TIMESTAMP}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def process_image_file(image_path):
    """Process a single image file and extract lab data."""
    try:
        # Open and preprocess image
        image = Image.open(image_path)
        
        # Convert image to RGB if it's not
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Preprocess image
        processed_image = preprocess_image(image)
        
        # Perform OCR with custom configuration
        custom_config = r'--oem 3 --psm 6 -l eng --dpi 300'
        text = pytesseract.image_to_string(processed_image, config=custom_config)
        
        # Log the extracted text for debugging
        logger.info(f"\nProcessing file: {image_path}")
        logger.debug(f"Extracted text:\n{text}\n")
        
        # Extract lab data
        lab_data = extract_lab_data(text)
        
        return {
            "file": str(image_path),
            "is_success": True,
            "data": lab_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing {image_path}: {str(e)}")
        return {
            "file": str(image_path),
            "is_success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def save_results(all_results):
    """Save results to JSON file"""
    results_file = RESULTS_DIR / f'lab_results_{TIMESTAMP}.json'
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    logger.info(f"Results saved to {results_file}")

def main():
    # Path to the directory containing images
    image_dir = Path("lbmaske")
    
    if not image_dir.exists():
        logger.error(f"Directory '{image_dir}' does not exist!")
        return
    
    # Supported image extensions
    image_extensions = {'.png', '.jpg', '.jpeg', '.tiff', '.bmp'}
    
    # Store all results
    all_results = {
        "run_timestamp": TIMESTAMP,
        "total_files": 0,
        "successful_extractions": 0,
        "results": []
    }
    
    # Process each image file
    for file_path in image_dir.glob('*'):
        if file_path.suffix.lower() in image_extensions:
            all_results["total_files"] += 1
            logger.info(f"\n{'='*80}\nProcessing: {file_path}")
            
            result = process_image_file(file_path)
            all_results["results"].append(result)
            
            if result["is_success"]:
                if result["data"]:
                    all_results["successful_extractions"] += 1
                    logger.info(f"Found {len(result['data'])} test results:")
                    for test in result["data"]:
                        logger.info(f"  - {test['test_name']}: {test['test_value']} {test['test_unit']} (Range: {test['bio_reference_range']})")
                else:
                    logger.warning(f"No lab data found in {file_path}")
            else:
                logger.error(f"Failed to process {file_path}: {result['error']}")
    
    # Calculate success rate
    total_files = all_results["total_files"]
    successful = all_results["successful_extractions"]
    success_rate = (successful/total_files*100) if total_files > 0 else 0
    
    # Add summary to results
    all_results["summary"] = {
        "success_rate": f"{success_rate:.2f}%",
        "total_tests_found": sum(len(r["data"]) for r in all_results["results"] if r["is_success"])
    }
    
    # Print and save summary
    logger.info(f"\n{'='*80}")
    logger.info("Processing complete!")
    logger.info(f"Total files processed: {total_files}")
    logger.info(f"Successful extractions: {successful}")
    logger.info(f"Success rate: {success_rate:.2f}%")
    logger.info(f"Total tests found: {all_results['summary']['total_tests_found']}")
    
    # Save results to JSON file
    save_results(all_results)

if __name__ == "__main__":
    main() 