import os
import uuid
from werkzeug.utils import secure_filename
from app import app

def save_image(form_image):
    """
    Save uploaded image with a unique filename
    
    Args:
        form_image: The FileStorage object from the form submission
        
    Returns:
        str: The filename of the saved image
    """
    # Generate unique filename to prevent overwrites
    _, file_extension = os.path.splitext(form_image.filename)
    filename = secure_filename(str(uuid.uuid4()) + file_extension)
    
    # Create the full path where the file will be saved
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    # Save the image
    form_image.save(file_path)
    
    return filename
