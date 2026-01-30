#!/usr/bin/env python3
"""Extract channel info from known good video URLs"""

import yt_dlp
import json

videos = {
    "shirdi_sai": {
        "main": "pgCZr3rVSLY",
        "backup": ["_vLJMKZupwU", "vizQ7f2cC7Y"]
    },
    "somnath": {
        "main": "1EhD-r9vyrw",
        "backup": []
    },
    "salasar": {
        "main": "dcWTEYl2eNA",
        "backup": []
    },
    "dwarkadhish": {
        "main": "Qqsp91oVm5E",
        "backup": []
    },
    "radhavallabh": {
        "main": "5AiVlEPx_6c",
        "backup": []
    },
    "mahakal": {
        "main": "0kTCU1BGbEY",
        "backup": ["Ttki3DmWG_Y"]
    },
    "mahalakshmi": {
        "main": "XYeIK55k6rA",
        "backup": []
    },
    "naina_devi": {
        "main": "hIR-Zl8vVtI",
        "backup": []
    },
    "iskcon_juhu": {
        "main": "Zzfz8alu5-8",
        "backup": []
    },
    "pashupatinath": {
        "main": "lNCn60Re1kk",
        "backup": []
    },
    "jagannath": {
        "main": "_pplsMPNVmQ",
        "backup": []
    },
    "vishwanath": {
        "main": "djAqGUJEvuc",
        "backup": ["xft-HiDLnEc"]
    }
}

def get_channel_info(video_id):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            url = f"https://www.youtube.com/watch?v={video_id}"
            info = ydl.extract_info(url, download=False)
            return {
                "channel_name": info.get('channel', info.get('uploader', '')),
                "channel_id": info.get('channel_id', ''),
                "channel_url": info.get('channel_url', ''),
            }
    except Exception as e:
        print(f"Error for {video_id}: {e}")
        return None

results = {}

for temple, data in videos.items():
    print(f"\n=== {temple.upper()} ===")
    
    # Main channel
    main_id = data["main"]
    info = get_channel_info(main_id)
    if info:
        print(f"Main: {info['channel_name']} ({info['channel_id']})")
        results[temple] = {
            "main_channel": info,
            "backup_channels": []
        }
    
    # Backup channels
    for backup_id in data.get("backup", []):
        info = get_channel_info(backup_id)
        if info:
            print(f"Backup: {info['channel_name']} ({info['channel_id']})")
            if temple in results:
                results[temple]["backup_channels"].append(info)

# Save results
with open("trusted_channels.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("\n\n✓ Saved to trusted_channels.json")
