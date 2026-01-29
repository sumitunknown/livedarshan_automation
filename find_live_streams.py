#!/usr/bin/env python3
"""
Live Darshan Stream Finder
Searches YouTube for live temple darshan streams and outputs embeddable URLs.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import yt_dlp


def search_youtube_live(query: str, max_results: int = 5) -> list:
    """
    Search YouTube for live streams matching the query.
    Returns list of video info dicts.
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'ignoreerrors': True,
        'no_color': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Search YouTube
            search_url = f"ytsearch{max_results}:{query} live"
            result = ydl.extract_info(search_url, download=False)
            
            if not result or 'entries' not in result:
                return []
            
            videos = []
            for entry in result['entries']:
                if entry and entry.get('is_live'):
                    videos.append(entry)
            
            return videos
    
    except Exception as e:
        print(f"Error searching for {query}: {e}")
        return []


def is_embeddable(video_info: dict) -> bool:
    """Check if video is embeddable."""
    # If playable_in_embed is False, it's not embeddable
    if video_info.get('playable_in_embed') is False:
        return False
    return True


def get_video_details(video_id: str) -> dict | None:
    """Get detailed info for a specific video to verify it's live and embeddable."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'no_color': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            url = f"https://www.youtube.com/watch?v={video_id}"
            return ydl.extract_info(url, download=False)
    except Exception as e:
        print(f"Error getting details for {video_id}: {e}")
        return None


def find_streams_for_temple(temple: dict) -> dict | None:
    """
    Find the best live stream for a temple.
    Returns stream info or None if no stream found.
    """
    print(f"Searching for: {temple['name']}")
    
    for query in temple['search_queries']:
        videos = search_youtube_live(query, max_results=5)
        
        for video in videos:
            video_id = video.get('id')
            if not video_id:
                continue
            
            # Check if it's actually live
            if not video.get('is_live'):
                continue
            
            # Check embeddability
            if not is_embeddable(video):
                print(f"  Skipping {video_id} - not embeddable")
                continue
            
            # Found a good stream
            return {
                "temple_id": temple['id'],
                "temple_name": temple['name'],
                "video_id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "embed_url": f"https://www.youtube.com/embed/{video_id}",
                "title": video.get('title', ''),
                "channel": video.get('channel', video.get('uploader', '')),
                "channel_id": video.get('channel_id', ''),
                "viewer_count": video.get('concurrent_view_count', video.get('view_count', 0)),
                "thumbnail": video.get('thumbnail', f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"),
            }
        
        # Small delay between searches to be nice to YouTube
        time.sleep(1)
    
    print(f"  No live stream found for {temple['name']}")
    return None


def main():
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
        
        # Delay between temples
        time.sleep(2)
    
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
