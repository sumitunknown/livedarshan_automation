#!/usr/bin/env python3
"""
Live Darshan Stream Finder v3 - Optimized YouTube API Version
- Phase 1: Global search (100 units)
- Phase 2: Get video details (1 unit)
- Phase 3: Smart matching with trusted channel priority
- Phase 4: Fallback for missing temples only
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
        req = Request(url, headers={'User-Agent': 'LiveDarshan/3.0'})
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except HTTPError as e:
        print(f"  API Error: {e.code} - {e.reason}")
        return {}
    except Exception as e:
        print(f"  Error: {e}")
        return {}


def get_today_date_str() -> str:
    """Get today's date in '30 Jan' format for search queries."""
    now = datetime.now(IST)
    return now.strftime("%d %b")  # e.g., "30 Jan"


def global_search(queries: list, max_results: int = 50) -> list:
    """
    Phase 1: Search for live darshan streams.
    Cost: 100 units per query
    """
    all_results = []
    seen_ids = set()
    
    # Replace {date} placeholder with today's date
    date_str = get_today_date_str()
    
    for query_template in queries:
        query = query_template.replace("{date}", date_str)
        print(f"  Searching: '{query}'")
        params = {
            'part': 'snippet',
            'q': query,
            'type': 'video',
            'eventType': 'live',
            'videoEmbeddable': 'true',
            'maxResults': max_results,
        }
        
        data = api_request('search', params)
        items = data.get('items', [])
        
        for item in items:
            video_id = item.get('id', {}).get('videoId')
            if video_id and video_id not in seen_ids:
                seen_ids.add(video_id)
                all_results.append(item)
        
        print(f"    Found {len(items)} results ({len(all_results)} total unique)")
        time.sleep(0.3)
    
    return all_results


def get_video_details(video_ids: list) -> dict:
    """
    Phase 2: Get detailed info for videos.
    Cost: 1 unit (can batch up to 50 IDs)
    """
    if not video_ids:
        return {}
    
    all_details = {}
    
    # Batch in groups of 50
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        params = {
            'part': 'snippet,liveStreamingDetails,status',
            'id': ','.join(batch),
        }
        
        data = api_request('videos', params)
        for item in data.get('items', []):
            all_details[item['id']] = item
    
    return all_details


def find_matching_temple(title: str, channel_id: str, temples: list) -> tuple:
    """
    Match a video to a temple based on title keywords.
    Returns (temple_id, is_trusted_channel)
    """
    title_lower = title.lower()
    
    for temple in temples:
        for keyword in temple.get('title_keywords', []):
            if keyword.lower() in title_lower:
                # Found a match - check if trusted channel
                trusted_ids = [ch['id'] for ch in temple.get('trusted_channels', [])]
                is_trusted = channel_id in trusted_ids
                return temple['id'], is_trusted
    
    return None, False


def passes_filters(video: dict, filters: dict, is_trusted: bool) -> tuple:
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
    
    # Check viewer count (only for non-trusted channels)
    if not is_trusted:
        min_viewers = filters.get('min_viewer_count_untrusted', 0)
        viewer_count = live_details.get('concurrentViewers', '0')
        try:
            viewer_count = int(viewer_count)
        except:
            viewer_count = 0
        
        if viewer_count < min_viewers:
            return False, f"only {viewer_count} viewers (min: {min_viewers})"
    
    return True, "passed"


def extract_stream_info(video_id: str, video: dict, temple: dict, is_trusted: bool) -> dict:
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
        "is_trusted_channel": is_trusted,
        "stream_started_at": live_details.get('actualStartTime', ''),
        "published_at": snippet.get('publishedAt', ''),
        "thumbnail": snippet.get('thumbnails', {}).get('high', {}).get('url', 
            f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"),
    }


def fallback_search(temple: dict, filters: dict) -> dict | None:
    """
    Phase 4: Individual search for a missing temple.
    Cost: 100 units
    """
    query = temple.get('fallback_search', f"{temple['name']} live darshan")
    print(f"  Fallback search: '{query}'")
    
    params = {
        'part': 'snippet',
        'q': query,
        'type': 'video',
        'eventType': 'live',
        'videoEmbeddable': 'true',
        'maxResults': 10,
    }
    
    data = api_request('search', params)
    items = data.get('items', [])
    
    if not items:
        return None
    
    # Get video IDs
    video_ids = [item['id']['videoId'] for item in items if 'videoId' in item.get('id', {})]
    if not video_ids:
        return None
    
    # Get details
    details = get_video_details(video_ids)
    
    # Find best match
    trusted_ids = [ch['id'] for ch in temple.get('trusted_channels', [])]
    
    # First try trusted channels
    for video_id in video_ids:
        if video_id not in details:
            continue
        video = details[video_id]
        channel_id = video.get('snippet', {}).get('channelId', '')
        is_trusted = channel_id in trusted_ids
        
        if is_trusted:
            passed, reason = passes_filters(video, filters, is_trusted=True)
            if passed:
                return extract_stream_info(video_id, video, temple, is_trusted=True)
    
    # Then try any passing video
    for video_id in video_ids:
        if video_id not in details:
            continue
        video = details[video_id]
        channel_id = video.get('snippet', {}).get('channelId', '')
        is_trusted = channel_id in trusted_ids
        
        passed, reason = passes_filters(video, filters, is_trusted)
        if passed:
            return extract_stream_info(video_id, video, temple, is_trusted)
    
    return None


def main():
    if not API_KEY:
        print("ERROR: YOUTUBE_API_KEY environment variable not set!")
        return
    
    # Load config
    config_path = Path(__file__).parent / "temples_v3.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    temples = config['temples']
    filters = config.get('filters', {})
    global_queries = config.get('global_search_queries', ['live darshan'])
    
    # Build temple lookup
    temple_by_id = {t['id']: t for t in temples}
    
    print("=" * 60)
    print("PHASE 1: Global Search")
    print("=" * 60)
    
    search_results = global_search(global_queries, max_results=50)
    print(f"\nTotal unique results: {len(search_results)}")
    
    # Get all video IDs
    video_ids = [item['id']['videoId'] for item in search_results if 'videoId' in item.get('id', {})]
    
    print("\n" + "=" * 60)
    print("PHASE 2: Get Video Details")
    print("=" * 60)
    
    video_details = get_video_details(video_ids)
    print(f"Got details for {len(video_details)} videos")
    
    print("\n" + "=" * 60)
    print("PHASE 3: Match & Assign")
    print("=" * 60)
    
    # Track assignments: temple_id -> {video_info, is_trusted, viewer_count}
    assigned = {}
    unmatched = []
    
    for item in search_results:
        video_id = item.get('id', {}).get('videoId')
        if not video_id or video_id not in video_details:
            continue
        
        video = video_details[video_id]
        snippet = video.get('snippet', {})
        title = snippet.get('title', '')
        channel_id = snippet.get('channelId', '')
        channel_name = snippet.get('channelTitle', '')
        
        # Find matching temple
        temple_id, is_trusted = find_matching_temple(title, channel_id, temples)
        
        if not temple_id:
            unmatched.append({
                'video_id': video_id,
                'title': title,
                'channel_id': channel_id,
                'channel_name': channel_name,
            })
            continue
        
        temple = temple_by_id[temple_id]
        
        # Check filters
        passed, reason = passes_filters(video, filters, is_trusted)
        if not passed:
            print(f"  ✗ {temple['name']}: {title[:40]}... - {reason}")
            continue
        
        # Get viewer count for priority
        live_details = video.get('liveStreamingDetails', {})
        viewer_count = int(live_details.get('concurrentViewers', 0) or 0)
        
        # Should we assign/replace?
        should_assign = False
        
        if temple_id not in assigned:
            should_assign = True
        else:
            current = assigned[temple_id]
            # Replace if: new is trusted and current isn't
            # OR both same trust level but new has more viewers
            if is_trusted and not current['is_trusted']:
                should_assign = True
            elif is_trusted == current['is_trusted'] and viewer_count > current['viewer_count']:
                should_assign = True
        
        if should_assign:
            assigned[temple_id] = {
                'stream': extract_stream_info(video_id, video, temple, is_trusted),
                'is_trusted': is_trusted,
                'viewer_count': viewer_count,
            }
            trust_label = "✓ TRUSTED" if is_trusted else "○"
            print(f"  {trust_label} {temple['name']}: {channel_name} ({viewer_count} viewers)")
    
    print(f"\nAssigned: {len(assigned)}/{len(temples)} temples")
    print(f"Unmatched videos: {len(unmatched)}")
    
    # Phase 4: Fallback for missing temples
    missing_temples = [t for t in temples if t['id'] not in assigned]
    
    if missing_temples:
        print("\n" + "=" * 60)
        print(f"PHASE 4: Fallback Search ({len(missing_temples)} missing)")
        print("=" * 60)
        
        for temple in missing_temples:
            print(f"\n{temple['name']}:")
            
            # First check unmatched videos for this temple's trusted channels
            trusted_ids = [ch['id'] for ch in temple.get('trusted_channels', [])]
            found_in_unmatched = False
            
            for item in unmatched:
                if item['channel_id'] in trusted_ids:
                    video_id = item['video_id']
                    if video_id in video_details:
                        video = video_details[video_id]
                        passed, reason = passes_filters(video, filters, is_trusted=True)
                        if passed:
                            assigned[temple['id']] = {
                                'stream': extract_stream_info(video_id, video, temple, is_trusted=True),
                                'is_trusted': True,
                                'viewer_count': int(video.get('liveStreamingDetails', {}).get('concurrentViewers', 0) or 0),
                            }
                            print(f"  ✓ Found in unmatched: {item['channel_name']}")
                            found_in_unmatched = True
                            break
            
            if found_in_unmatched:
                continue
            
            # Do fallback search
            stream = fallback_search(temple, filters)
            if stream:
                assigned[temple['id']] = {
                    'stream': stream,
                    'is_trusted': stream['is_trusted_channel'],
                    'viewer_count': stream['viewer_count'],
                }
                print(f"  ✓ Found via search: {stream['channel']}")
            else:
                print(f"  ✗ No live stream found")
            
            time.sleep(0.5)
    
    # Phase 5: Output
    print("\n" + "=" * 60)
    print("PHASE 5: Output")
    print("=" * 60)
    
    # Collect streams sorted by priority
    live_streams = []
    for temple in temples:
        if temple['id'] in assigned:
            live_streams.append(assigned[temple['id']]['stream'])
    
    output = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "stream_count": len(live_streams),
        "streams": live_streams
    }
    
    # Write output
    output_path = Path(__file__).parent / "live_streams.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    # Summary
    trusted_count = sum(1 for s in live_streams if s['is_trusted_channel'])
    
    print(f"\n✓ Found {len(live_streams)}/{len(temples)} temples")
    print(f"  - Trusted channels: {trusted_count}")
    print(f"  - Other channels: {len(live_streams) - trusted_count}")
    print(f"✓ Output written to {output_path}")


if __name__ == "__main__":
    main()
