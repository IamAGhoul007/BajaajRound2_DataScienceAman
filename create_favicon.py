from PIL import Image
import os

def create_favicon():
    # Create a 32x32 image with a white background
    img = Image.new('RGB', (32, 32), color='white')
    
    # Create the static directory if it doesn't exist
    os.makedirs('static', exist_ok=True)
    
    # Save as ICO file
    img.save('static/favicon.ico', format='ICO') 