def get_color_scheme(image_path):
    """Return a simple fixed color scheme, since we're using standard colors in CSS"""
    return {
        'dominant_color': '#007bff',  # The blue we're already using in CSS
        'palette': ['#007bff', '#FFFFFF', '#f0f0f0', '#e0e0e0']  # Other colors from our CSS
    }

def validate_image(image_path):
    """Validate that the image file exists and is accessible"""
    if not os.path.exists(image_path):
        raise ValueError(f"Image not found at {image_path}")
    return True

def get_background_image(config):
    """Get the background image path from config"""
    return config.get('company_logo', 'default_background.png')

def setup_background_image(app, image_path):
    """Setup the background image in the Flask app"""
    if validate_image(image_path):
        app.config['BACKGROUND_IMAGE'] = image_path
        return True
    return False