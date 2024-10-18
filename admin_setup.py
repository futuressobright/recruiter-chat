import os
import json
from urllib.parse import urlparse
import requests
from PIL import Image
import io
import shutil

def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

def is_valid_linkedin_url(url):
    return is_valid_url(url) and "linkedin.com" in url

def is_valid_youtube_url(url):
    return is_valid_url(url) and ("youtube.com" in url or "youtu.be" in url)

def prompt_for_url(prompt_text, validator_func):
    while True:
        url = input(prompt_text).strip()
        if validator_func(url):
            return url
        else:
            print("Please enter a valid URL.")

def setup_candidate_info():
    candidate_info = {
        'linkedin_url': prompt_for_url("Enter the candidate's LinkedIn profile URL: ", is_valid_linkedin_url),
        'video_url': prompt_for_url("Enter the URL of the candidate's video (YouTube): ", is_valid_youtube_url),
        'resume_url': prompt_for_url("Enter the URL of the candidate's resume: ", is_valid_url)
    }

    with open('candidate_info.json', 'w') as f:
        json.dump(candidate_info, f)

    print("Candidate information has been saved.")

def validate_image(file_path):
    try:
        with Image.open(file_path) as img:
            if img.format not in ['PNG', 'JPEG']:
                raise ValueError("Only PNG and JPEG formats are supported")
        if os.path.getsize(file_path) > 5 * 1024 * 1024:  # 5MB limit
            raise ValueError("File size exceeds the maximum limit of 5MB")
        return True
    except Exception as e:
        raise ValueError(f"Invalid image: {str(e)}")

def download_image(url, save_path):
    response = requests.get(url)
    if response.status_code == 200:
        with open(save_path, 'wb') as f:
            f.write(response.content)
        validate_image(save_path)
        return save_path
    else:
        raise ValueError(f"Failed to download image. Status code: {response.status_code}")

def prompt_for_employer_name():
    while True:
        name = input("Enter the employer's name (letters and numbers only, no spaces): ").strip()
        if name.replace('-', '').isalnum():
            return name.lower()
        else:
            print("Please enter a valid name using only letters, numbers, and hyphens.")

def setup_config():
    employer_name = prompt_for_employer_name()
    config = {
        'employer_name': employer_name,
        'company_logo': ''  # This will be set by setup_company_logo()
    }
    with open('config.json', 'w') as f:
        json.dump(config, f)
    print(f"Employer name '{employer_name}' has been saved to config.")


import os
import json
from urllib.parse import urlparse
import requests
from PIL import Image
import io
import shutil


# ... (keep all the existing functions up to setup_config() unchanged)

def setup_company_logo():
    os.makedirs('static/images', exist_ok=True)

    while True:
        logo_input = input("Enter the path to the company logo file (PNG or JPEG, max 5MB) or a URL: ").strip()

        try:
            if is_valid_url(logo_input):
                file_name = "company_logo.png"  # Default name for downloaded files
                save_path = os.path.join('static', 'images', file_name)
                downloaded_path = download_image(logo_input, save_path)
            elif os.path.exists(logo_input):
                validate_image(logo_input)
                file_name = os.path.basename(logo_input)
                save_path = os.path.join('static', 'images', file_name)
                if os.path.abspath(logo_input) != os.path.abspath(save_path):
                    shutil.copy2(logo_input, save_path)
                # If the file is already in the correct location, we don't need to copy it
            else:
                raise ValueError("File not found. Please enter a valid file path or URL.")

            break
        except Exception as e:
            print(f"Error: {str(e)}")
            print("Please try again.")

    with open('config.json', 'r') as f:
        config = json.load(f)
    config['company_logo'] = file_name  # Store only the filename
    with open('config.json', 'w') as f:
        json.dump(config, f)

    print(f"Company logo has been saved: {file_name}")


if __name__ == "__main__":
    print("Welcome to the admin setup!")
    setup_config()
    setup_candidate_info()
    setup_company_logo()
    print("Setup complete!")