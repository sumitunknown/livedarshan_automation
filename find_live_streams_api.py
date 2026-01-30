#!/usr/bin/env python3
"""
Live Darshan Stream Finder - YouTube Data API Version
Searches YouTube for live temple darshan streams using official API.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import HTTPError


API_KEY = os.environ.get('YOUTUBE_API_KEY', '')
BASE_URL = "https://www.googleapis.com/youtube/v3"


def search_youtube_live(query: str, max_results: int = 5) -> list:
    """
    Search YouTube for live streams matching the query.
    Returns list of video info dicts.
    """
    params = {
        'part': 'snippet',
        'q': query,
        'type': 'video',
        'eventType': 'live',
        'videoEmbeddable': 'true',
        'maxResults': max_results,
        'key': API_KEY,
    }
    
    url = f"{BASE_URL}/search?{urlencode(params)}"
    
    try:
        req = Request(url, headers={'User-Agent': 'LiveDarshan/1.0'})
        with urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            return data.get('items', [])
    except HTTPError as e:
        print(f"API Error for '{query}': {e.code} - {e.reason}")
        return []
    except Exception as e:
        print(f"Error searching for '{query}': {e}")
        return []


def get_video_details(video_ids: list) -> dict:
    """
    Get detailed info for videos (viewer count, etc.)
    Returns dict of video_id -> details
    """
    if not video_ids:
        return {}
    
    params = {
        'part': 'snippet,liveStreamingDetails,status',
        'id': ','.join(video_ids),
        'key': API_KEY,
    }
    
    url = f"{BASE_URL}/videos?{urlencode(params)}"
    
    try:
        req = Request(url, headers={'User-Agent': 'LiveDarshan/1.0'})
        with urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            return {
                item['id']: item 
                for item in data.get('items', [])
            }
    except Exception as e:
        print(f"Error getting video details: {e}")
        return {}


def find_streams_for_temple(temple: dict) -> dict | None:
    """
    Find the best live stream for a temple.
    Returns stream info or None if no stream found.
    """
    print(f"Searching for: {temple['name']}")
    
    for query in temple['search_queries']:
        results = search_youtube_live(query, max_results=3)
        
        if not results:
            continue
        
        # Get video IDs
        video_ids = [item['id']['videoId'] for item in results if 'videoId' in item.get('id', {})]
        
        if not video_ids:
            continue
        
        # Get detailed info
        details = get_video_details(video_ids)
        
        for video_id in video_ids:
            if video_id not in details:
                continue
            
            video = details[video_id]
            snippet = video.get('snippet', {})
            live_details = video.get('liveStreamingDetails', {})
            status = video.get('status', {})
            
            # Check if embeddable
            if not status.get('embeddable', True):
                print(f"  Skipping {video_id} - not embeddable")
                continue
            
            # Get viewer count
            viewer_count = live_details.get('concurrentViewers', '0')
            try:
                viewer_count = int(viewer_count)
            except:
                viewer_count = 0
            
            # Get timing info
            actual_start = live_details.get('actualStartTime', '')
            scheduled_start = live_details.get('scheduledStartTime', '')
            published_at = snippet.get('publishedAt', '')
            
            return {
                "temple_id": temple['id'],
                "temple_name": temple['name'],
                "video_id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "embed_url": f"https://www.youtube.com/embed/{video_id}",
                "title": snippet.get('title', ''),
                "channel": snippet.get('channelTitle', ''),
                "channel_id": snippet.get('channelId', ''),
                "viewer_count": viewer_count,
                "stream_started_at": actual_start or scheduled_start,
                "published_at": published_at,
                "thumbnail": snippet.get('thumbnails', {}).get('high', {}).get('url', 
                    f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"),
            }
        
        # Small delay between searches
        time.sleep(0.5)
    
    print(f"  No live stream found for {temple['name']}")
    return None


def main():
    if not API_KEY:
        print("ERROR: YOUTUBE_API_KEY environment variable not set!")
        return
    
    # Load temple config
    config_path = Path(__file__).parent / "temples.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    temples = config['temples']
    
    # Find streams for all temples
    live_streams = []
    
    for temple in temples:
        stream = find_streams_for_temple(temple)
        if stream:
            live_streams.append(stream)
            print(f"  ✓ Found: {stream['title'][:50]}...")
        
        # Delay between temples to be nice to API
        time.sleep(1)
    
    # Sort by priority (temple order)
    temple_order = {t['id']: t['priority'] for t in temples}
    live_streams.sort(key=lambda x: temple_order.get(x['temple_id'], 999))
    
    # Create output
    output = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "stream_count": len(live_streams),
        "streams": live_streams
    }
    
    # Write output
    output_path = Path(__file__).parent / "live_streams.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Found {len(live_streams)} live streams")
    print(f"✓ Output written to {output_path}")


if __name__ == "__main__":
    main()
