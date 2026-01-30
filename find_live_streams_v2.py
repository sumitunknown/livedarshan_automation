#!/usr/bin/env python3
"""
Live Darshan Stream Finder v2 - YouTube Data API with Trusted Channels
Priority: Check trusted channels first, then fallback to search.
Filters: Exclude old videos, minimum viewers, stream start time.
"""

import json
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import HTTPError


API_KEY = os.environ.get('YOUTUBE_API_KEY', '')
BASE_URL = "https://www.googleapis.com/youtube/v3"
IST = timezone(timedelta(hours=5, minutes=30))


def api_request(endpoint: str, params: dict) -> dict:
    """Make YouTube API request."""
    params['key'] = API_KEY
    url = f"{BASE_URL}/{endpoint}?{urlencode(params)}"
    
    try:
        req = Request(url, headers={'User-Agent': 'LiveDarshan/2.0'})
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except HTTPError as e:
        print(f"  API Error: {e.code} - {e.reason}")
        return {}
    except Exception as e:
        print(f"  Error: {e}")
        return {}


def search_channel_live(channel_id: str) -> list:
    """Search for live streams on a specific channel. Cost: 100 units"""
    params = {
        'part': 'snippet',
        'channelId': channel_id,
        'type': 'video',
        'eventType': 'live',
        'videoEmbeddable': 'true',
        'maxResults': 3,
    }
    
    data = api_request('search', params)
    return data.get('items', [])


def search_youtube_live(query: str, max_results: int = 5) -> list:
    """General search for live streams. Cost: 100 units"""
    params = {
        'part': 'snippet',
        'q': query,
        'type': 'video',
        'eventType': 'live',
        'videoEmbeddable': 'true',
        'maxResults': max_results,
    }
    
    data = api_request('search', params)
    return data.get('items', [])


def get_video_details(video_ids: list) -> dict:
    """Get detailed info for videos. Cost: 1 unit"""
    if not video_ids:
        return {}
    
    params = {
        'part': 'snippet,liveStreamingDetails,status',
        'id': ','.join(video_ids),
    }
    
    data = api_request('videos', params)
    return {item['id']: item for item in data.get('items', [])}


def passes_filters(video: dict, filters: dict) -> tuple[bool, str]:
    """Check if video passes all filters. Returns (passed, reason)"""
    snippet = video.get('snippet', {})
    live_details = video.get('liveStreamingDetails', {})
    status = video.get('status', {})
    title = snippet.get('title', '').lower()
    
    # Check embeddable
    if not status.get('embeddable', True):
        return False, "not embeddable"
    
    # Check excluded keywords in title
    for keyword in filters.get('exclude_title_keywords', []):
        if keyword.lower() in title:
            return False, f"title contains '{keyword}'"
    
    # Check viewer count
    min_viewers = filters.get('min_viewer_count', 0)
    viewer_count = live_details.get('concurrentViewers', '0')
    try:
        viewer_count = int(viewer_count)
    except:
        viewer_count = 0
    
    if viewer_count < min_viewers:
        return False, f"only {viewer_count} viewers (min: {min_viewers})"
    
    # Check stream start time (must be after X hour IST today)
    min_hour = filters.get('stream_must_start_after_hour_ist', 0)
    if min_hour > 0:
        start_time_str = live_details.get('actualStartTime', '')
        if start_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                start_time_ist = start_time.astimezone(IST)
                
                # Get today's minimum start time in IST
                now_ist = datetime.now(IST)
                min_start = now_ist.replace(hour=min_hour, minute=0, second=0, microsecond=0)
                
                # If stream started before min_hour today, it might be from yesterday (24/7 stream)
                # We'll allow it if it started within last 24 hours
                hours_ago = (now_ist - start_time_ist).total_seconds() / 3600
                if hours_ago > 24:
                    return False, f"stream started {hours_ago:.0f} hours ago"
            except:
                pass  # If we can't parse, allow it
    
    return True, "passed"


def extract_stream_info(video_id: str, video: dict, temple: dict) -> dict:
    """Extract stream info from video details."""
    snippet = video.get('snippet', {})
    live_details = video.get('liveStreamingDetails', {})
    
    viewer_count = live_details.get('concurrentViewers', '0')
    try:
        viewer_count = int(viewer_count)
    except:
        viewer_count = 0
    
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
        "stream_started_at": live_details.get('actualStartTime', ''),
        "published_at": snippet.get('publishedAt', ''),
        "thumbnail": snippet.get('thumbnails', {}).get('high', {}).get('url', 
            f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"),
        "is_trusted_channel": snippet.get('channelId', '') in [
            ch['id'] for ch in temple.get('trusted_channels', [])
        ]
    }


def find_stream_for_temple(temple: dict, filters: dict) -> dict | None:
    """Find live stream for temple. Priority: trusted channels first."""
    print(f"\nSearching for: {temple['name']}")
    
    # STEP 1: Check trusted channels first
    trusted_channels = temple.get('trusted_channels', [])
    
    for channel in trusted_channels:
        channel_id = channel['id']
        channel_name = channel['name']
        print(f"  Checking trusted: {channel_name}")
        
        results = search_channel_live(channel_id)
        if not results:
            continue
        
        video_ids = [item['id']['videoId'] for item in results if 'videoId' in item.get('id', {})]
        if not video_ids:
            continue
        
        details = get_video_details(video_ids)
        
        for video_id in video_ids:
            if video_id not in details:
                continue
            
            video = details[video_id]
            passed, reason = passes_filters(video, filters)
            
            if passed:
                print(f"  ✓ Found on trusted channel: {channel_name}")
                return extract_stream_info(video_id, video, temple)
            else:
                print(f"    Skipped: {reason}")
        
        time.sleep(0.3)
    
    # STEP 2: Fallback to general search
    print(f"  Trying search fallback...")
    
    for query in temple.get('search_queries', []):
        results = search_youtube_live(query, max_results=5)
        
        if not results:
            continue
        
        video_ids = [item['id']['videoId'] for item in results if 'videoId' in item.get('id', {})]
        if not video_ids:
            continue
        
        details = get_video_details(video_ids)
        
        for video_id in video_ids:
            if video_id not in details:
                continue
            
            video = details[video_id]
            passed, reason = passes_filters(video, filters)
            
            if passed:
                print(f"  ✓ Found via search: {video['snippet'].get('title', '')[:40]}...")
                return extract_stream_info(video_id, video, temple)
            else:
                print(f"    Skipped: {reason}")
        
        time.sleep(0.3)
    
    print(f"  ✗ No live stream found")
    return None


def main():
    if not API_KEY:
        print("ERROR: YOUTUBE_API_KEY environment variable not set!")
        return
    
    # Load temple config
    config_path = Path(__file__).parent / "temples_v2.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    temples = config['temples']
    filters = config.get('filters', {})
    
    print(f"Filters: {filters}")
    
    # Find streams for all temples
    live_streams = []
    
    for temple in temples:
        stream = find_stream_for_temple(temple, filters)
        if stream:
            live_streams.append(stream)
        time.sleep(0.5)
    
    # Sort by priority
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
    
    print(f"\n{'='*50}")
    print(f"✓ Found {len(live_streams)} live streams")
    print(f"✓ Output written to {output_path}")


if __name__ == "__main__":
    main()
