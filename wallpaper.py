#!/usr/bin/env python3

import sys
from PIL import Image
import subprocess
import subprocess
import logging

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


def merge_images(img1_path, img2_path, resolution1, resolution2, output_path):
    # Parse resolutions
    width1, height1 = int(resolution1[0]), int(resolution1[1])
    width2, height2 = int(resolution2[0]), int(resolution2[1])

    

    # Open the images
    img1 = Image.open(img1_path)
    img2 = Image.open(img2_path)

    # Resize the images to the respective monitor's resolution
    img1 = img1.resize((width1, height1))
    img2 = img2.resize((width2, height2))

    # Create a new image with combined width and max height of the two
    merged_img = Image.new('RGB', (width1 + width2, max(height1, height2)))

    # Paste the images side by side on the new image
    merged_img.paste(img1, (0, 0))
    merged_img.paste(img2, (width1, 0))

    # Save the merged image
    merged_img.save(output_path)


import os
import requests
import random
from datetime import datetime, timedelta

def get_random_date(start_date_str, end_date_str):
    # Convert string dates to datetime objects
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

    # Generate a random timedelta between start and end dates
    random_days = random.randint(0, (end_date - start_date).days)
    
    # Return the random date formatted as a string
    return (start_date + timedelta(days=random_days)).strftime("%Y-%m-%d")

def set_wallpaper(file_path):
    subprocess.run(['gsettings', 'set', 'org.gnome.desktop.background', 'picture-uri', f"file://{file_path}"])


if __name__ == '__main__':

    monitors = get_monitor_info()

    # Here's an example of how you'd access the data for the first two monitors:
    monitor1_name, resolution1, scale1 = monitors[0]
    monitor2_name, resolution2, scale2 = monitors[1]

    # Adjust the resolutions based on the scaling factors
    adjusted_res1 = (int(resolution1.split('x')[0]) * scale1, int(resolution1.split('x')[1]) * scale1)
    adjusted_res2 = (int(resolution2.split('x')[0]) * scale2, int(resolution2.split('x')[1]) * scale2)


    # Directory to save the wallpaper
    WALLPAPER_DIR = os.path.join(os.getenv("HOME"), "Pictures/nasa")

    # Create directory if it doesn't exist
    if not os.path.exists(WALLPAPER_DIR):
        os.makedirs(WALLPAPER_DIR)

    # Your NASA API key
    NASA_API_KEY = os.environ['NASA_API_KEY']

    # Get two random dates
    first_random_date = get_random_date("1995-06-16", datetime.now().strftime("%Y-%m-%d"))
    second_random_date = get_random_date("1995-06-16", datetime.now().strftime("%Y-%m-%d"))

    logger.info('Fetching image 1')

    # Fetch and download image for the first random date
    response1 = requests.get(f"https://api.nasa.gov/planetary/apod?api_key={NASA_API_KEY}&date={first_random_date}")
    response1.raise_for_status()

    image_url1 = response1.json()["url"]
    img1_path = os.path.join(WALLPAPER_DIR, f"nasa_apod_{first_random_date}.jpg")        

    with open(img1_path, 'wb') as f:
        f.write(requests.get(image_url1).content)

    
    logger.info('Fetching image 2')

    # Fetch and download image for the second random date
    response2 = requests.get(f"https://api.nasa.gov/planetary/apod?api_key={NASA_API_KEY}&date={second_random_date}")
    response2.raise_for_status()
    
    image_url2 = response2.json()["url"]
    img2_path = os.path.join(WALLPAPER_DIR, f"nasa_apod_{second_random_date}.jpg")
    with open(img2_path, 'wb') as f:
        f.write(requests.get(image_url2).content)

    logger.info( f'Monitor resolutions {adjusted_res1} {adjusted_res2}'  )

    output_path = os.path.join(os.getenv("HOME"), "Pictures/", "merged.jpg")

    merge_images(img1_path, img2_path, adjusted_res2, adjusted_res1, output_path)
    logger.info(f"Merged wallpaper saved at {output_path}")

    set_wallpaper( output_path )


