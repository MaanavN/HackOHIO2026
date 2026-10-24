import re
import requests
import instaloader
from instaloader import Post

def get_shortcode(url):
    """Extracts the unique shortcode from an Instagram URL."""
    # Clean query parameters out of the URL
    clean_url = url.split('?')[0]
    pattern = r'instagram\.com/(?:[^/]+/)?(?:reel|p)/([^/?]+)'
    match = re.search(pattern, clean_url)
    if not match:
        raise ValueError("Invalid Instagram Reel URL structure.")
    return match.group(1)

def download_reel(reel_url, output_filename="reel.mp4"):
    """Downloads the Instagram Reel video file using Instaloader."""
    # Extract shortcode from URL
    shortcode = get_shortcode(reel_url)
    print(f"Extracted Shortcode: {shortcode}")
    
    # Initialize Instaloader context
    loader = instaloader.Instaloader()
    
    try:
        # Load post data from Instagram
        post = Post.from_shortcode(loader.context, shortcode)
        video_url = post.video_url  # Target the direct CDN video link
        
        print("Downloading video stream...")
        # Stream download chunks to handle large video files efficiently
        response = requests.get(video_url, stream=True)
        if response.status_code == 200:
            with open(output_filename, 'wb') as file:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        file.write(chunk)
            print(f"Success! Reel saved as '{output_filename}'")
        else:
            print(f"Failed to fetch video stream. HTTP Status: {response.status_code}")
            
    except Exception as e:
        print(f"An error occurred: {e}")

# Example Usage
if __name__ == "__main__":
    target_url = "https://www.instagram.com/p/Dbd8mmKFgyN/" 
    download_reel(target_url, "reel.mp4")
