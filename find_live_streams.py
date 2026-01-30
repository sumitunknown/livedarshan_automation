#!/usr/bin/env python3
"""
Live Darshan Stream Finder (yt-dlp version)
Uses same algorithm as API version but with yt-dlp for searching.
Works offline without API key.
"""

import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yt_dlp

# IST timezone
IST = timezone(timedelta(hours=5, minutes=30))


def get_today_date_str() -> str:
    """Get today's date in '30 Jan' format for search queries."""
    now = datetime.now(IST)
    return now.strftime("%d %b")


def search_youtube_live(query: str, max_results: int = 50) -> list:
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
            search_url = f"ytsearch{max_results}:{query}"
            result = ydl.extract_info(search_url, download=False)
            
            if not result or 'entries' not in result:
                return []
            
            videos = []
            for entry in result['entries']:
                if entry and entry.get('is_live'):
                    videos.append(entry)
            
            return videos
    
    except Exception as e:
        print(f"  Error searching: {e}")
        return []


def is_embeddable(video_info: dict) -> bool:
    """Check if video is embeddable."""
    if video_info.get('playable_in_embed') is False:
        return False
    return True


def find_matching_temple(video: dict, temples: list) -> dict | None:
    """
    Match a video to a temple based on title keywords.
    Returns the temple config if matched, None otherwise.
    """
    title = (video.get('title') or '').lower()
    channel_id = video.get('channel_id', '')
    
    for temple in temples:
        # Check if video is from trusted channel
        trusted_ids = [tc['id'] for tc in temple.get('trusted_channels', [])]
        if channel_id in trusted_ids:
            return temple
        
        # Check title keywords
        keywords = temple.get('title_keywords', [])
        for keyword in keywords:
            if keyword.lower() in title:
                return temple
    
    return None


def passes_filters(video: dict, temple: dict, filters: dict) -> bool:
    """
    Check if video passes quality filters.
    """
    title = (video.get('title') or '').lower()
    
    # Check exclude keywords
    exclude_keywords = filters.get('exclude_title_keywords', [])
    for keyword in exclude_keywords:
        if keyword.lower() in title:
            return False
    
    # Check embeddability
    if not is_embeddable(video):
        return False
    
    # For non-trusted channels, check viewer count
    channel_id = video.get('channel_id', '')
    trusted_ids = [tc['id'] for tc in temple.get('trusted_channels', [])]
    
    if channel_id not in trusted_ids:
        min_viewers = filters.get('min_viewer_count_untrusted', 5)
        viewer_count = video.get('concurrent_view_count', video.get('view_count', 0)) or 0
        if viewer_count < min_viewers:
            return False
    
    return True


def is_trusted_channel(video: dict, temple: dict) -> bool:
    """Check if video is from a trusted channel for this temple."""
    channel_id = video.get('channel_id', '')
    trusted_ids = [tc['id'] for tc in temple.get('trusted_channels', [])]
    return channel_id in trusted_ids


def format_stream(video: dict, temple: dict) -> dict:
    """Format video info into stream output format."""
    video_id = video.get('id')
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
        "is_trusted_channel": is_trusted_channel(video, temple),
        "thumbnail": video.get('thumbnail', f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"),
    }


def fallback_search(temple: dict, filters: dict) -> dict | None:
    """
    Fallback: Search specifically for a temple that wasn't found in global search.
    """
    query = temple.get('fallback_search', temple['name'] + ' live darshan')
    print(f"  Fallback search: '{query}'")
    
    videos = search_youtube_live(query, max_results=10)
    
    # Sort: trusted channels first, then by viewer count
    def sort_key(v):
        is_trusted = is_trusted_channel(v, temple)
        viewers = v.get('concurrent_view_count', v.get('view_count', 0)) or 0
        return (0 if is_trusted else 1, -viewers)
    
    videos.sort(key=sort_key)
    
    for video in videos:
        if passes_filters(video, temple, filters):
            return format_stream(video, temple)
    
    return None


def main():
    print("=" * 60)
    print("Live Darshan Stream Finder (yt-dlp)")
    print(f"Time: {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')} IST")
    print("=" * 60)
    
    # Load temple config (using v3 config)
    config_path = Path(__file__).parent / "temples_v3.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    temples = config['temples']
    filters = config.get('filters', {})
    search_queries = config.get('global_search_queries', ['live darshan today'])
    
    # Sort temples by priority
    temples.sort(key=lambda t: t.get('priority', 999))
    
    # ===== PHASE 1: Global Search =====
    print("\n[Phase 1] Global Search")
    
    all_videos = []
    seen_ids = set()
    date_str = get_today_date_str()
    
    for query_template in search_queries:
        query = query_template.replace("{date}", date_str)
        print(f"  Searching: '{query}'")
        
        videos = search_youtube_live(query, max_results=50)
        
        for video in videos:
            video_id = video.get('id')
            if video_id and video_id not in seen_ids:
                seen_ids.add(video_id)
                all_videos.append(video)
        
        print(f"    Found {len(videos)} live streams ({len(all_videos)} total unique)")
        time.sleep(1)
    
    # ===== PHASE 2: Match & Assign =====
    print(f"\n[Phase 2] Matching {len(all_videos)} videos to {len(temples)} temples")
    
    results = {}  # temple_id -> best stream
    
    for video in all_videos:
        temple = find_matching_temple(video, temples)
        if not temple:
            continue
        
        temple_id = temple['id']
        
        if not passes_filters(video, temple, filters):
            continue
        
        # Check if we should use this video
        current = results.get(temple_id)
        if not current:
            results[temple_id] = format_stream(video, temple)
            print(f"  ✓ {temple['name']}: {video.get('title', '')[:40]}...")
        else:
            # Prefer trusted channel
            new_is_trusted = is_trusted_channel(video, temple)
            current_is_trusted = current.get('is_trusted_channel', False)
            
            if new_is_trusted and not current_is_trusted:
                results[temple_id] = format_stream(video, temple)
                print(f"  ↑ {temple['name']}: upgraded to trusted channel")
    
    found_count = len(results)
    print(f"\n  Matched {found_count}/{len(temples)} temples")
    
    # ===== PHASE 3: Fallback Search =====
    missing = [t for t in temples if t['id'] not in results]
    
    if missing:
        print(f"\n[Phase 3] Fallback search for {len(missing)} missing temples")
        
        for temple in missing:
            print(f"  {temple['name']}...")
            stream = fallback_search(temple, filters)
            if stream:
                results[temple['id']] = stream
                print(f"    ✓ Found: {stream['title'][:40]}...")
            else:
                print(f"    ✗ No stream found")
            time.sleep(2)
    
    # ===== PHASE 4: Output =====
    print(f"\n[Phase 4] Generating Output")
    
    # Sort by temple priority
    live_streams = []
    for temple in temples:
        if temple['id'] in results:
            live_streams.append(results[temple['id']])
    
    output = {
        "last_updated": datetime.now(IST).isoformat(),
        "stream_count": len(live_streams),
        "total_temples": len(temples),
        "streams": live_streams
    }
    
    # Write output
    output_path = Path(__file__).parent / "live_streams.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'=' * 60}")
    print(f"✓ Found {len(live_streams)}/{len(temples)} live streams")
    print(f"✓ Output: {output_path}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
