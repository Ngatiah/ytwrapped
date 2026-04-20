# YTMusic Wrapped
---

## Requirements

- Python 3.7+
- A Google account with YouTube Music listening history
- A YouTube Data API v3 key (only needed for listening minutes — see below)

Install dependencies:

```bash
pip install requests python-dotenv
```

---

## Step 1 — Export your watch history via Google Takeout

1. Go to [https://takeout.google.com](https://takeout.google.com)
2. Click **Deselect all**, then scroll down and check **YouTube and YouTube Music**
3. Click **All YouTube data included**, then uncheck everything except **history**
4. Choose your export format — make sure it is set to **JSON** (not HTML)
5. Click **Next step**, then **Create export**
6. Once the export email arrives, download and unzip it
7. Find the file at:
   ```
   Takeout/YouTube and YouTube Music/history/watch-history.json
   ```
8. Copy `watch-history.json` into the same folder as `watch.py`

---

## Step 2 — Get a YouTube Data API v3 key (optional, needed for minutes listened)

You only need this if you want the **Minutes Listened** stat. Skip to Step 3 if you don't.

1. Go to [https://console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (or select an existing one)
3. Go to **APIs & Services → Library**
4. Search for **YouTube Data API v3** and click **Enable**
5. Go to **APIs & Services → Credentials**
6. Click **+ Create Credentials → API key**
7. Copy the generated key
8. Under **Application restrictions**, set it to **None** (so it works from the command line)
9. Under **API restrictions**, select **Restrict key** and choose **YouTube Data API v3**

> **Note:** The free quota is 10,000 units/day. Each batch of 50 videos costs 1 unit, so you would need over 500,000 unique songs to hit the limit — you are almost certainly fine.

You can provide the key in two ways:

**Option A — `.env` file** (recommended, keeps the key out of your terminal history):

Create a `.env` file in the same folder as `watch.py`:
```
YOUTUBE_API_KEY=your_key_here
```

**Option B — command line flag:**
```bash
--api-key YOUR_KEY
```

---

## Step 3 — Run the script

### Basic report (top artists and top songs, no minutes)

```bash
python watch.py watch-history.json
```

### With play counts and artist song counts shown

```bash
python watch.py watch-history.json -m
```

### With minutes listened (requires API key)

```bash
python watch.py watch-history.json -d
```

Or if passing the key inline:

```bash
python watch.py watch-history.json -d --api-key YOUR_KEY
```

### Full report — play counts + minutes listened

```bash
python watch.py watch-history.json -m -d
```

### Analyze a specific year (default is current year)

```bash
python watch.py watch-history.json -y 2024
```

### All flags combined

```bash
python watch.py watch-history.json -m -d -y 2024 --api-key YOUR_KEY
```

---

## Flags reference

| Flag | Long form | Description |
|---|---|---|
| `-m` | | Show play counts per artist and song |
| `-d` | `--duration` | Fetch video durations via YouTube API to calculate minutes listened |
| `-y YEAR` | `--year=YEAR` | Analyze a specific year (default: current year) |
| `-v` | | Verbose mode — writes detailed logs to `log.dat` |
| | `--api-key KEY` | Pass your YouTube Data API key inline |

---

## Output files

| File | Description |
|---|---|
| `report_YEAR.html` | Visual report — open in any browser. Includes a Download button to save a copy. |
| `report_YEAR.dat` | Plain text version of the top artists and songs |
| `log.dat` | Debug log — useful if something goes wrong |
| `ytmusic.db` | SQLite database generated during the run — safe to delete after |

> The HTML report is self-contained. Use the **⬇ Download Report** button in the bottom-right corner to save a portable copy you can share or open offline.

---

## Troubleshooting

**Minutes Listened shows 0**
- Make sure you passed `-d` and that your API key is set
- Verify YouTube Data API v3 is enabled in your Google Cloud project
- Test your key with: `curl "https://www.googleapis.com/youtube/v3/videos?part=snippet&id=dQw4w9WgXcQ&key=YOUR_KEY"`

**No artists or songs showing up**
- Make sure your `watch-history.json` contains YouTube Music entries (header: `"YouTube Music"`)
- Check that you selected the correct year with `-y` if your history spans multiple years
- Confirm the file is in JSON format, not HTML (re-export from Takeout if needed)

**API error: `accessNotConfigured`**
- YouTube Data API v3 is not enabled — go to Google Cloud Console → APIs & Services → Library and enable it

**API error: `keyInvalid`**
- Double-check the key was copied correctly with no extra spaces
