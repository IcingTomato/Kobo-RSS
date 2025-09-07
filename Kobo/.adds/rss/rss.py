#!/mnt/onboard/.niluje/python3/bin/ python3.9
# -*- coding: utf-8 -*-

"""
RSS to EPUB Converter for Kobo E-Reader

This script fetches RSS feeds from a config file and converts them 
into a single EPUB file optimized for Kobo e-readers.

Author: GitHub @IcingTomato
License: MIT License
Created: 2025
Version: 1.0

Copyright (c) 2025 IcingTomato

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Features:
- Fetches RSS feeds from config file
- Generates random identicon covers
- Resizes images to 30% of original size
- Creates EPUB with proper Chinese language support
- Optimized for Kobo e-reader devices
- DRM-free output

Usage:
    python rss.py

Requirements:
    - feedparser
    - requests
    - beautifulsoup4
    - ebooklib
    - Pillow
"""

import feedparser
import requests
from bs4 import BeautifulSoup
from ebooklib import epub
import os
import datetime
import pathlib
from urllib.parse import urlparse
import random
from PIL import Image, ImageDraw 
import uuid 
import stat


def read_config():
    """Read RSS links from config file in the same directory"""
    print("Reading config file...")
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
    
    if not os.path.exists(config_path):
        print("Error: Config file not found at", config_path)
        return []
    
    with open(config_path, 'r') as f:
        links = [line.strip() for line in f.readlines() if line.strip() and not line.startswith('#')]
        print(f"Found {len(links)} RSS links in config file")
        return links


def fetch_rss_content(url):
    """Fetch and parse RSS feed content"""
    print(f"Fetching RSS from: {url}")
    
    # Add headers to simulate a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/rss+xml, application/xml, text/xml, */*'
    }
    
    try:
        # First try to get the raw content with requests
        response = requests.get(url, headers=headers, timeout=30)
        print(f"HTTP status code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Warning: HTTP error {response.status_code} when accessing {url}")
            return feedparser.FeedParserDict({'entries': []})
        
        # Pass the raw content to feedparser
        feed = feedparser.parse(response.content)
        
        # Check if we got a valid feed
        if 'status' in feed and feed.status != 200:
            print(f"Warning: Feed status {feed.status} for {url}")
        
        if not feed.entries:
            print(f"Warning: No entries found in feed: {url}")
            print(f"Feed structure: {feed.keys()}")
            if 'bozo_exception' in feed:
                print(f"Feed parser exception: {feed.bozo_exception}")
            return feed
        
        # Print some debug info about the feed
        print(f"Feed contains {len(feed.entries)} entries")
        print(f"Feed title: {feed.feed.get('title', 'Unknown')}")
        
        # Limit to just 5 most recent entries
        feed.entries = feed.entries[:10]
        print(f"Retrieved {len(feed.entries)} entries from {url}")
        return feed
        
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        # Return an empty feed
        return feedparser.FeedParserDict({'entries': []})


def clean_html(html_content):
    """Clean HTML content, keep main text and images"""
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    
    return str(soup)


def download_images(html_content, book, feed_title):
    """Download images in HTML content and replace with local paths"""
    soup = BeautifulSoup(html_content, 'html.parser')
    images = soup.find_all('img')
    
    for i, img in enumerate(images):
        try:
            img_url = img.get('src')
            if not img_url:
                continue
                
            # Handle relative URLs
            if not img_url.startswith(('http://', 'https://')):
                parsed_url = urlparse(img_url)
                if not parsed_url.netloc:
                    base_url = img.get('data-src')
                    if base_url:
                        img_url = base_url
            
            print(f"Downloading image: {img_url}")
            # Download image
            img_resp = requests.get(img_url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }, timeout=10)
            
            if img_resp.status_code == 200:
                # Process and resize image
                try:
                    from PIL import Image
                    import io
                    
                    # Load image from response content
                    original_image = Image.open(io.BytesIO(img_resp.content))
                    
                    # Get original size
                    original_width, original_height = original_image.size
                    print(f"Original image size: {original_width}x{original_height}")
                    
                    # Calculate new size (30% of original)
                    new_width = int(original_width * 0.3)
                    new_height = int(original_height * 0.3)
                    
                    # Resize image
                    resized_image = original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    print(f"Resized image to: {new_width}x{new_height}")
                    
                    # Save resized image to bytes
                    img_bytes = io.BytesIO()
                    
                    # Determine format and save
                    if original_image.format in ['JPEG', 'JPG']:
                        # Convert RGBA to RGB if necessary for JPEG
                        if resized_image.mode == 'RGBA':
                            rgb_image = Image.new('RGB', resized_image.size, (255, 255, 255))
                            rgb_image.paste(resized_image, mask=resized_image.split()[-1])
                            resized_image = rgb_image
                        resized_image.save(img_bytes, format='JPEG', quality=85, optimize=True)
                        img_filename = f"image_{feed_title.replace(' ', '_')}_{i}.jpg"
                        media_type = 'image/jpeg'
                    else:
                        # Save as PNG for other formats
                        resized_image.save(img_bytes, format='PNG', optimize=True)
                        img_filename = f"image_{feed_title.replace(' ', '_')}_{i}.png"
                        media_type = 'image/png'
                    
                    resized_content = img_bytes.getvalue()
                    
                    # Add resized image to ebook
                    img_item = epub.EpubItem(
                        uid=f'image_{feed_title}_{i}',
                        file_name=f'images/{img_filename}',
                        media_type=media_type,
                        content=resized_content
                    )
                    book.add_item(img_item)
                    
                    # 强制居中：包装图片在div容器中
                    img_parent = img.parent
                    new_div = soup.new_tag('div', **{'class': 'image-container', 'style': 'text-align: center; margin: 1em 0;'})
                    new_img = soup.new_tag('img', src=f'images/{img_filename}', alt=img.get('alt', ''), style='max-width: 100%; height: auto; display: block; margin: 0 auto;')
                    
                    new_div.append(new_img)
                    img.replace_with(new_div)
                    
                    print(f"Resized image saved as: {img_filename}")
                    
                except Exception as resize_error:
                    print(f"Failed to resize image, using original: {resize_error}")
                    # Fallback to original image if resize fails
                    img_filename = f"image_{feed_title.replace(' ', '_')}_{i}.jpg"
                    img_item = epub.EpubItem(
                        uid=f'image_{feed_title}_{i}',
                        file_name=f'images/{img_filename}',
                        media_type='image/jpeg',
                        content=img_resp.content
                    )
                    book.add_item(img_item)
                    
                    # 强制居中：包装图片在div容器中
                    img_parent = img.parent
                    new_div = soup.new_tag('div', **{'class': 'image-container', 'style': 'text-align: center; margin: 1em 0;'})
                    new_img = soup.new_tag('img', src=f'images/{img_filename}', alt=img.get('alt', ''), style='max-width: 100%; height: auto; display: block; margin: 0 auto;')
                    
                    new_div.append(new_img)
                    img.replace_with(new_div)
                    
                    print(f"Original image saved as: {img_filename}")
                    
        except Exception as e:
            print(f"Failed to download image: {e}")
    
    return str(soup)

def generate_identicon(width=1264, height=1680, block_size=140, background_color=(255, 255, 255), colors=None):
    """
    Generate a random identicon similar to GitHub default avatars, with fixed resolution for Kobo
    
    Args:
        width: Image width in pixels (1264 for Kobo)
        height: Image height in pixels (1680 for Kobo)
        block_size: Size of each block in the grid
        background_color: Background color as RGB tuple
        colors: List of colors to use for blocks, if None random colors will be used
        
    Returns:
        PIL Image object with the generated identicon
    """
    print("Generating random identicon cover image...")
    
    # Calculate grid dimensions
    grid_width = width // block_size
    grid_height = height // block_size
    
    # Make grid width odd for symmetry
    if grid_width % 2 == 0:
        grid_width -= 1
    
    # Create a new image with white background
    img = Image.new('RGB', (width, height), background_color)
    draw = ImageDraw.Draw(img)
    
    # Generate random colors if not provided
    if colors is None:
        # Generate a random highlight color (more vibrant)
        hue = random.randint(0, 360)
        saturation = random.randint(70, 100)
        value = random.randint(50, 90)
        
        # Convert HSV to RGB
        h_float = hue / 360.0
        s_float = saturation / 100.0
        v_float = value / 100.0
        
        if h_float == 0:
            r, g, b = v_float, v_float, v_float
        else:
            i = int(h_float * 6.0)
            f = (h_float * 6.0) - i
            p = v_float * (1.0 - s_float)
            q = v_float * (1.0 - s_float * f)
            t = v_float * (1.0 - s_float * (1.0 - f))
            i = i % 6
            
            if i == 0: r, g, b = v_float, t, p
            elif i == 1: r, g, b = q, v_float, p
            elif i == 2: r, g, b = p, v_float, t
            elif i == 3: r, g, b = p, q, v_float
            elif i == 4: r, g, b = t, p, v_float
            elif i == 5: r, g, b = v_float, p, q
        
        color = (int(r * 255), int(g * 255), int(b * 255))
    else:
        color = random.choice(colors)
    
    print(f"Using color: RGB{color} for identicon")
    
    # Generate half of the random pattern (for horizontal symmetry)
    half_grid_width = grid_width // 2 + 1
    pattern = []
    
    # Create a pattern for the entire height
    for i in range(grid_height):
        row = []
        for j in range(half_grid_width):
            # More filled blocks than empty (70% chance of a block)
            if random.random() < 0.7:
                row.append(1)
            else:
                row.append(0)
        pattern.append(row)
    
    # Draw the pattern with horizontal symmetry
    for i in range(grid_height):
        for j in range(half_grid_width):
            if pattern[i][j]:
                # Left side
                x = j * block_size
                y = i * block_size
                draw.rectangle([x, y, x + block_size, y + block_size], fill=color)
                
                # Right side (mirror)
                mirror_j = grid_width - j - 1
                if mirror_j != j:  # Don't duplicate the middle column
                    x = mirror_j * block_size
                    y = i * block_size
                    draw.rectangle([x, y, x + block_size, y + block_size], fill=color)
    
    print("Random identicon generated")
    return img

def create_combined_epub(feeds):
    """Create EPUB file from multiple RSS feeds"""
    # Initialize EPUB book
    book = epub.EpubBook()
    
    # Set book metadata
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    book_title = f"RSS Feeds {current_date}"
    print(f"Creating EPUB titled: {book_title}")
    
    book.set_title(book_title)
    # book.set_language('en')
    book.set_language('zh-CN')
    book.add_author("GitHub @IcingTomato")

    simple_id = f"rss-feeds-{datetime.datetime.now().strftime('%Y%m%d')}"
    book.set_identifier(simple_id)

    book.set_identifier(str(uuid.uuid4()))
    book.add_metadata('DC', 'creator', 'RSS Feed Reader')
    book.add_metadata('DC', 'date', current_date)
    
    # Create chapter lists
    chapters = []
    toc = []
    
    # Add CSS style
    style = '''
    body { 
        font-family: sans-serif; 
        font-size: 0.9em;  
        line-height: 1.4; 
    }
    h1 { 
        text-align: center; 
        font-size: 1.1em;  
        margin: 0.8em 0;   
    }
    h2 { 
        text-align: center; 
        font-size: 0.9em;  
        margin: 0.8em 0;   
        color: #555; 
    }
    h3 { 
        font-size: 0.8em;  
        margin: 0.6em 0; 
    }
    p { 
        font-size: 0.85em; 
        margin: 0.5em 0; 
    }
    img { 
        max-width: 100%; 
        height: auto; 
    }
    .cover-image { 
        display: block; 
        margin: 0 auto; 
        max-width: 100%; 
    }
    a {
        font-size: 0.8em;  
    }
    .image-container {
        text-align: center;
        margin: 1em 0;
    }
    '''
    css = epub.EpubItem(
        uid="style_default",
        file_name="style/default.css",
        media_type="text/css",
        content=style
    )
    book.add_item(css)
    
    # Random identicon as cover image
    identicon = generate_identicon(width=1264, height=1680, block_size=140)
    
    # Convert identicon to bytes
    import io
    img_bytes = io.BytesIO()
    identicon.save(img_bytes, format='PNG')
    cover_image_content = img_bytes.getvalue()
    
    # Create cover image item
    cover_image = epub.EpubItem(
        uid="cover_image",
        file_name="images/cover.png",
        media_type="image/png",
        content=cover_image_content
    )
    book.add_item(cover_image)
    
    # Set cover image
    # book.set_cover("images/cover.png", cover_image_content)
    
    # Create cover page
    cover = epub.EpubHtml(title='Cover', file_name='cover.xhtml')
    cover.content = f'''
    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <title>Cover</title>
        <link rel="stylesheet" type="text/css" href="style/default.css"/>
    </head>
    <body>
        <div style="text-align: center;">
            <img src="images/cover.png" alt="Cover" style="max-width: 100%; height: auto;"/>
        </div>
    </body>
    </html>
    '''
    
    book.add_item(cover)
    chapters.append(cover)
    toc.append(cover)
    
    # Create table of contents
    toc_page = epub.EpubHtml(title='Contents', file_name='toc.xhtml')
    toc_content = f'''
    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <title>Contents</title>
        <link rel="stylesheet" type="text/css" href="style/default.css"/>
    </head>
    <body>
        <h1>Contents</h1>
        <p>RSS Collection {current_date}</p>
    '''
    
    chapter_index = 0
    
    # Process each feed
    for feed_index, feed in enumerate(feeds):
        if not feed.entries:
            continue
            
        # Add feed title to TOC
        feed_title = feed.feed.title if hasattr(feed.feed, 'title') else f"Feed {feed_index+1}"
        toc_content += f'<h2>{feed_title}</h2>\n<ul>\n'
        
        # Add feed section
        feed_section = epub.EpubHtml(
            title=feed_title,
            file_name=f'feed_{feed_index}.xhtml'
        )
        feed_section.content = f'''
        <html>
        <head>
            <title>{feed_title}</title>
            <link rel="stylesheet" href="style/default.css" />
        </head>
        <body>
            <h1>{feed_title}</h1>
        </body>
        </html>
        '''
        book.add_item(feed_section)
        chapters.append(feed_section)
        toc.append(feed_section)
        
        # Process each article in the feed
        for entry_index, entry in enumerate(feed.entries):
            chapter_index += 1
            title = entry.title
            print(f"Processing article: {title}")
            
            # Get article content
            if hasattr(entry, 'content'):
                content = entry.content[0].value
            elif hasattr(entry, 'description'):
                content = entry.description
            else:
                content = f"<p>Could not retrieve article content. Please visit <a href='{entry.link}'>{entry.link}</a></p>"
            
            # Clean HTML content
            content = clean_html(content)
            
            # Download images
            content = download_images(content, book, f"{feed_index}_{entry_index}")
            
            # Create chapter
            chapter = epub.EpubHtml(
                title=title,
                file_name=f'chapter_{chapter_index}.xhtml'
            )
            
            # Set chapter content
            published_date = ""
            if hasattr(entry, 'published'):
                published_date = f"<p>Published: {entry.published}</p>"
                
            chapter.content = f'''
            <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
            <html xmlns="http://www.w3.org/1999/xhtml">
            <head>
                <title>{title}</title>
                <link rel="stylesheet" type="text/css" href="style/default.css"/>
            </head>
            <body>
                <h1>{title}</h1>
                <h2>From: {feed_title}</h2>
                {published_date}
                <p><a href="{entry.link}">Original Link</a></p>
                <div>{content}</div>
            </body>
            </html>
            '''
            
            # Add chapter to book
            book.add_item(chapter)
            chapters.append(chapter)
            toc.append(chapter)
            
            # Add entry to TOC
            toc_content += f'<li><a href="chapter_{chapter_index}.xhtml">{title}</a></li>\n'
        
        toc_content += '</ul>\n'
    
    toc_content += '''
    </body>
    </html>
    '''
    toc_page.content = toc_content
    book.add_item(toc_page)
    chapters.insert(1, toc_page)
    toc.insert(1, toc_page)
    
    # Create table of contents
    book.toc = toc
    
    # Add default NCX and Nav
    nav = epub.EpubNav()
    book.add_item(nav)
    
    ncx = epub.EpubNcx()
    book.add_item(ncx)
    
    # Set spine
    # book.spine = ['nav'] + chapters
    book.spine = [cover] + chapters[1:] 
    
    # Generate output filename and path
    output_dir = "/mnt/onboard/RSS"
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    output_filename = f"RSSFeeds_{datetime.datetime.now().strftime('%Y%m%d')}.epub"
    output_path = os.path.join(output_dir, output_filename)
    
    # Write EPUB file
    print(f"Writing EPUB file to: {output_path}")
    epub.write_epub(output_path, book)
    try:
        os.chmod(output_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
        print(f"Set file permissions for: {output_path}")
    except Exception as e:
        print(f"Could not set file permissions: {e}")
    
    print(f"EPUB file successfully created: {output_path}")
    return output_path


def main():
    try:
        print("Starting RSS to EPUB conversion...")
        
        # Read RSS links from config
        rss_links = read_config()
        if not rss_links:
            print("Error: No RSS links found in config file")
            return
        
        # Fetch content for each RSS feed
        feeds = []
        for link in rss_links:
            try:
                feed = fetch_rss_content(link)
                if feed.entries:
                    feeds.append(feed)
                    print(f"Successfully added feed: {feed.feed.get('title', 'Unknown')}")
                else:
                    print(f"Skipping empty feed: {link}")
            except Exception as e:
                print(f"Error processing feed {link}: {e}")
        
        if not feeds:
            print("Error: Could not retrieve any content from the RSS feeds")
            print("Troubleshooting tips:")
            print("1. Check your internet connection")
            print("2. Verify the RSS URLs in your config file")
            print("3. Try opening the RSS URLs in a web browser")
            print("4. Some websites may block automated requests")
            return
        
        # Create combined EPUB
        epub_file = create_combined_epub(feeds)
        print(f"EPUB creation complete: {epub_file}")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        print(traceback.format_exc())


if __name__ == "__main__":
    main()