# 🙏 Live Darshan Automation

Automatically finds and updates live temple darshan streams from YouTube.

## 📺 Live Streams JSON

Your app can fetch live streams from:
```
https://raw.githubusercontent.com/YOUR_USERNAME/livedarshan_automation/main/live_streams.json
```

### Response Format:
```json
{
  "last_updated": "2024-01-15T10:30:00Z",
  "stream_count": 8,
  "streams": [
    {
      "temple_id": "tirupati",
      "temple_name": "Tirumala Tirupati Balaji",
      "video_id": "abc123xyz",
      "url": "https://www.youtube.com/watch?v=abc123xyz",
      "embed_url": "https://www.youtube.com/embed/abc123xyz",
      "title": "LIVE Darshan from Tirumala",
      "channel": "TTD Official",
      "viewer_count": 15000,
      "thumbnail": "https://img.youtube.com/vi/abc123xyz/hqdefault.jpg"
    }
  ]
}
```

## 🛕 Temples Tracked

1. Tirumala Tirupati Balaji
2. Vaishno Devi
3. Shirdi Sai Baba
4. Siddhivinayak Mumbai
5. Golden Temple Amritsar
6. Kashi Vishwanath Varanasi
7. ISKCON Mayapur
8. Jagannath Puri
9. Somnath Temple
10. Mahakaleshwar Ujjain
11. Meenakshi Temple Madurai
12. Kedarnath Temple
13. Badrinath Temple
14. Dwarkadhish Temple
15. Ram Mandir Ayodhya

## ⚙️ How It Works

1. **GitHub Actions** runs every 15 minutes
2. **yt-dlp** searches YouTube for live streams
3. Filters only **embeddable** videos
4. Updates `live_streams.json`
5. Your app reads the JSON via raw.githubusercontent.com

## 🚀 Setup

1. Fork this repository
2. Go to **Settings** → **Actions** → **General**
3. Enable "Allow all actions"
4. The workflow will start running automatically!

## 🧪 Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Run the script
python find_live_streams.py
```

## 📱 Using in Your App

### JavaScript/React:
```javascript
const fetchStreams = async () => {
  const response = await fetch(
    'https://raw.githubusercontent.com/YOUR_USERNAME/livedarshan_automation/main/live_streams.json'
  );
  const data = await response.json();
  return data.streams;
};

// Use in video player
<iframe 
  src={stream.embed_url} 
  allowFullScreen 
  allow="autoplay"
/>
```

### Flutter/Dart:
```dart
final response = await http.get(Uri.parse(
  'https://raw.githubusercontent.com/YOUR_USERNAME/livedarshan_automation/main/live_streams.json'
));
final streams = jsonDecode(response.body)['streams'];
```

## 📄 License

MIT - Use freely for any purpose.
