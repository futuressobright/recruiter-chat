import os
import json
import shutil
from colorthief import ColorThief
from PIL import Image
import imghdr

# Constants
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_image(image_path):
    if not os.path.exists(image_path):
        raise ValueError("File does not exist")

    if not allowed_file(image_path):
        raise ValueError("File type not allowed. Please use .jpg, .jpeg, .png, .gif, or .bmp")

    if os.path.getsize(image_path) > MAX_FILE_SIZE:
        raise ValueError(f"File size exceeds the maximum limit of {MAX_FILE_SIZE // (1024 * 1024)}MB")

    # Verify that the file is actually an image
    if imghdr.what(image_path) not in ALLOWED_EXTENSIONS:
        raise ValueError("File is not a valid image")

    # Check image dimensions and color depth
    with Image.open(image_path) as img:
        width, height = img.size
        if width < 800 or height < 600:
            print(f"Warning: Image dimensions ({width}x{height}) are below recommended size of 800x600")
        if img.mode not in ('RGB', 'RGBA'):
            print(f"Warning: Image color mode ({img.mode}) may result in suboptimal color extraction")


def get_background_image(config_file='config.json'):
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
            if 'background_image' in config:
                try:
                    validate_image(config['background_image'])
                    return config['background_image']
                except ValueError:
                    print("Stored image file is invalid. Please provide a new image.")

    while True:
        print("Please provide the path to the background image file:")
        print("(Accepted formats: .jpg, .jpeg, .png, .gif, .bmp, max size: 5MB)")
        image_path = input().strip()

        try:
            validate_image(image_path)
            break
        except ValueError as e:
            print(f"Error: {str(e)}")

    with open(config_file, 'w') as f:
        json.dump({'background_image': image_path}, f)

    return image_path


def get_color_scheme(image_path):
    color_thief = ColorThief(image_path)
    dominant_color = color_thief.get_color(quality=1)
    palette = color_thief.get_palette(color_count=5, quality=1)

    # Convert RGB to hex
    dominant_color_hex = '#{:02x}{:02x}{:02x}'.format(*dominant_color)
    palette_hex = ['#{:02x}{:02x}{:02x}'.format(*color) for color in palette]

    return {
        'dominant_color': dominant_color_hex,
        'palette': palette_hex
    }


def setup_background_image(app, background_image):
    background_image_filename = os.path.basename(background_image)
    destination = os.path.join(app.config['UPLOAD_FOLDER'], background_image_filename)

    if not os.path.exists(destination):
        shutil.copy(background_image, destination)

    return background_image_filename