#!/usr/bin/env python3

import sys
from PIL import Image
import subprocess
import subprocess
import logging
import os
import requests
import random
import datetime
import time


log_fmt ='%(asctime)s [%(levelname)s] %(message)s'
logging.basicConfig(format=log_fmt, level=logging.INFO)
logger = logging.getLogger(__name__)

def get_monitor_info():
    result = subprocess.run(['xrandr'], stdout=subprocess.PIPE).stdout.decode('utf-8')
    
    # Find lines with connected monitors
    lines = [line for line in result.splitlines() if ' connected ' in line]

    monitor_info = []

    for line in lines:
        parts = line.split()
        name = parts[0]
        
        # Search for the resolution pattern in the line
        resolution = None
        for part in parts:
            if 'x' in part and '+' in part:
                resolution = part.split('+')[0]
                break

        if not resolution:
            continue  # Skip if we couldn't find a resolution
        
        # Fetch the scaling factor from dconf for this monitor
        scale_value = subprocess.run(['dconf', 'read', f"/org/gnome/desktop/interface/x11-monitor/{name}ScalingFactor"], stdout=subprocess.PIPE).stdout.decode('utf-8').strip()

        if not scale_value:
            scale_value = "1.0"  # Default scaling factor if not set

        monitor_info.append((name, resolution, float(scale_value)))

    return monitor_info


def resize_and_crop(image, target_width, target_height):
    # Calculate the aspect ratio of the image and target dimensions
    img_aspect = image.width / image.height
    target_aspect = target_width / target_height

    # Determine the dimensions to resize to while maintaining aspect ratio
    if img_aspect > target_aspect:
        # Image is wider than the target dimension
        width = int(target_height * img_aspect)
        height = target_height
    else:
        # Image is taller or equal to the target dimension
        height = int(target_width / img_aspect)
        width = target_width

    # Resize the image while maintaining its aspect ratio
    new_size = (width, height)
    image = image.resize( new_size )

    # Calculate the position to crop the image to the target size
    x_offset = (width - target_width) // 2
    y_offset = (height - target_height) // 2

    # Crop the image
    image = image.crop((x_offset, y_offset, x_offset + target_width, y_offset + target_height))

    return image


def make_safe_filename(s):
    def safe_char(c):
        if c.isalnum() or c=='.':
            return c
        else:
            return "_"

    safe = ""
    last_safe=False
    for c in s:
      if len(safe) > 200:
        return safe + "_" + str(time.time_ns() // 1000000)

      safe_c = safe_char(c)
      curr_safe = c != safe_c
      if not last_safe or not curr_safe:
        safe += safe_c
      last_safe=curr_safe
    return safe

def merge_images(image_list, output_path):
  # Open the images and resize them without distortion
  images = []
  widths = []
  heights = []
  for image_path, resolution in image_list:
    image = Image.open(image_path)
    width, height = resolution
    image = resize_and_crop(image, width, height)
    images.append(image)
    widths.append(width)
    heights.append(height)

  # Create a new image with combined width and max height of the images
  merged_img = Image.new('RGB', (sum(widths), max(heights)))

  # Paste the images side by side on the new image
  x_offset = 0
  for i, image in enumerate(images):
    merged_img.paste(image, (x_offset, 0))
    x_offset += widths[i]

  # Save the merged image
  merged_img.save(output_path)

def fetch_bing_image(output_path, days_in_past=0):
    # Base URL for Bing Image of the Day API with a placeholder for the idx value
    BASE_URL = "https://www.bing.com/HPImageArchive.aspx?format=js&idx={idx}&n=1&mkt=en-US"
    
    
    # Make a request to the Bing API with idx
    response = requests.get(BASE_URL.format(idx=days_in_past))
    response.raise_for_status()  # Raise an error for failed requests
    
    # Extract image URL from the JSON response
    data = response.json()
    image_url = "https://www.bing.com" + data["images"][0]["url"]
    image_title = data["images"][0]["title"]
    
    # Download the image
    image_response = requests.get(image_url, stream=True)
    image_response.raise_for_status()
    
    # Save the image to the specified path
    fn = os.path.join(output_path, make_safe_filename(image_title)+'.jpg')
    with open( fn, 'wb') as file:
        for chunk in image_response.iter_content(1024):
            file.write(chunk)

    logger.info(f"Downloaded random Bing image from {days_in_past} days ago to {fn}")
    return fn

def fetch_nasa_image(output_path, days_in_past=0):
    
    NASA_API_ENDPOINT = "https://api.nasa.gov/planetary/apod"
    NASA_API_KEY = os.environ['NASA_API_KEY']

    # Calculate date
    desired_date = datetime.date.today() - datetime.timedelta(days=days_in_past)
    
    params = {
        'api_key': NASA_API_KEY,
        'date': desired_date.isoformat()
    }
    response = requests.get(NASA_API_ENDPOINT, params=params)
    response.raise_for_status()
    
    data = response.json()
    
    # Check if the returned data has an image (and not a video or something else)
    if data['media_type'] == 'image':
        image_url = data['url']
        image_title = data.get('title', 'nasa_apod').replace(' ', '_')  # Use the title or default to 'nasa_apod'
        image_response = requests.get(image_url, stream=True)
        image_response.raise_for_status()
        
        # Save the image with a meaningful title
        filename = f"{image_title}_{desired_date}.jpg"
        full_output_path = os.path.join(output_path, make_safe_filename(filename))
        
        with open(full_output_path, 'wb') as file:
            for chunk in image_response.iter_content(1024):
                file.write(chunk)

        print(f"Downloaded NASA APOD titled '{image_title}' for {desired_date} to {full_output_path}")
    else:
        print(f"Media for {desired_date} is not an image. Skipping.")

    return full_output_path
    

def set_wallpaper(file_path):
    subprocess.run(['gsettings', 'set', 'org.gnome.desktop.background', 'picture-uri', f"file://{file_path}"])


wallpaper_providers = [fetch_bing_image, fetch_nasa_image]

if __name__ == '__main__':

    monitors = get_monitor_info()

    # Adjust the resolutions based on the scaling factors for all monitors
    adjusted_resolutions = []
    for monitor in monitors:
      monitor_name, resolution, scale = monitor
      adjusted_resolutions.append(
         (int(int(resolution.split('x')[0]) * scale), 
          int(int(resolution.split('x')[1]) * scale)))

    logger.info(f"Monitor resolutions: {adjusted_resolutions}")

    # Directory to save the wallpaper
    WALLPAPER_DIR = os.path.join(os.getenv("HOME"), "Pictures/wallpaper")

    # Create directory if it doesn't exist
    if not os.path.exists(WALLPAPER_DIR):
      os.makedirs(WALLPAPER_DIR)

    output_path = os.path.join(WALLPAPER_DIR, "merged.jpg")

    # Loop through the resolutions and alternate between Bing and NASA images
    images = []
    for i, resolution in enumerate(adjusted_resolutions):
      wallpaper_providers_index = i % len(wallpaper_providers)
      img_path = wallpaper_providers[wallpaper_providers_index](WALLPAPER_DIR)
      images.append((img_path, resolution))
      logger.info(f"Wallpaper saved at {output_path} for resolution {resolution}")

    merge_images(images, output_path)

    set_wallpaper(output_path)


