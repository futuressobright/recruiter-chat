import os
import json
from urllib.parse import urlparse
import requests
from PIL import Image
import io
import shutil
from path_config import PathConfig  # Add this import



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


def prompt_for_candidate_name():
    while True:
        name = input("Enter the candidate's first name: ").strip()
        if name and name.replace(' ', '').isalpha():
            return name
        else:
            print("Please enter a valid name using only letters.")


def setup_config():
    employer_name = prompt_for_employer_name()
    config = {
        'employer_name': employer_name,
        'company_logo': ''  # This will be set by setup_company_logo()
    }
    with open('config.json', 'w') as f:
        json.dump(config, f)
    print(f"Employer name '{employer_name}' has been saved to config.")


def setup_company_logo():
    os.makedirs(PathConfig.UPLOADS_DIR, exist_ok=True)

    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            employer_name = config.get('employer_name', 'company')  # fallback to 'company' if not found
    except FileNotFoundError:
        print("Error: config.json not found. Please run setup_config() first.")
        return

    while True:
        logo_input = input("Enter the path to the company logo file (PNG or JPEG, max 5MB) or a URL: ").strip()

        try:
            if is_valid_url(logo_input):
                response = requests.head(logo_input)
                content_type = response.headers.get('content-type', '')
                if 'png' in content_type.lower():
                    extension = '.png'
                elif 'jpeg' in content_type.lower() or 'jpg' in content_type.lower():
                    extension = '.jpg'
                else:
                    extension = '.png'  # default to png if content-type is unclear

                file_name = f"{employer_name}_logo{extension}"
                save_path = PathConfig.get_upload_path(file_name)
                downloaded_path = download_image(logo_input, save_path)
            elif os.path.exists(logo_input):
                extension = os.path.splitext(logo_input)[1].lower()
                if extension not in ['.png', '.jpg', '.jpeg']:
                    raise ValueError("Only PNG and JPEG formats are supported")

                file_name = f"{employer_name}_logo{extension}"
                save_path = PathConfig.get_upload_path(file_name)
                validate_image(logo_input)
                if os.path.abspath(logo_input) != os.path.abspath(save_path):
                    shutil.copy2(logo_input, save_path)
            else:
                raise ValueError("File not found. Please enter a valid file path or URL.")

            break
        except Exception as e:
            print(f"Error: {str(e)}")
            print("Please try again.")

    config['company_logo'] = file_name
    with open('config.json', 'w') as f:
        json.dump(config, f)

    print(f"Company logo has been saved: {file_name}")


def setup_candidate_info():
    candidate_info = {
        'first_name': prompt_for_candidate_name(),
        'linkedin_url': prompt_for_url("Enter candidate's LinkedIn profile URL: ", is_valid_linkedin_url),
        'video_url': prompt_for_url("Enter URL candidate's video (YouTube) URL: ", is_valid_youtube_url),
        'resume_url': prompt_for_url("Enter candidate's resume URL: ", is_valid_url)
    }

    with open('candidate_info.json', 'w') as f:
        json.dump(candidate_info, f)

    print("Candidate information has been saved.")


if __name__ == "__main__":
    print("Welcome to the admin setup!")
    setup_candidate_info()
    setup_config()
    setup_company_logo()
    print("Setup complete!")