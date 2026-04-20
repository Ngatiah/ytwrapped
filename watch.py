from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs
import datetime
import sys
import getopt
import json
import sqlite3
import requests
import re
import os

load_dotenv()

analyzeYear = datetime.datetime.now().year
verbose = False
duration = False
moreDetails = False
log = open('log.dat', 'w', encoding="utf8")


def flags():
    opts, args = getopt.getopt(sys.argv[2:], "d:y:mv", ["duration", "year=", "api-key="])
    for o, token in opts:
        if o == "-v":
            global verbose
            verbose = True
        elif o == "-m":
            global moreDetails
            moreDetails = True
        elif o in ("-d", "--duration"):
            global duration
            duration = True
        elif o == "--api-key":
            os.environ["YOUTUBE_API_KEY"] = token
        elif o in ("-y", "--year"):
            global analyzeYear
            analyzeYear = token


def get_api_key():
    """Retrieve API key from environment, exit with clear message if missing."""
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        print(
            "Error: YouTube API key not found.\n"
            "Provide it via the YOUTUBE_API_KEY environment variable in your .env file,\n"
            "or pass it with --api-key <YOUR_KEY>."
        )
        sys.exit(1)
    return key


def should_not_ignore(title, year, header, analyzeYear):
    if header == "YouTube Music":
        if title[:7] == "Watched":
            return year[:4] == str(analyzeYear)
    return False


def open_file():
    if sys.argv[1].endswith('.json'):
        try:
            return open(sys.argv[1], "r", encoding="utf8")
        except OSError:
            print("Could not open your history file")
            sys.exit(1)
    else:
        print("Your history file should be a json file")
        sys.exit(1)


def extract_video_id(url):
    """Robustly extract the video ID from any YouTube or YouTube Music URL."""
    parsed = urlparse(url)
    video_id = parse_qs(parsed.query).get('v', [None])[0]
    if not video_id:
        print(f"Warning: could not extract video ID from URL: {url}", file=log)
    return video_id


def parse_json(file, cursor):
    json_object = json.load(file)
    for obj in json_object:
        if should_not_ignore(obj['title'], obj['time'], obj['header'], analyzeYear):
            video_id = extract_video_id(obj['titleUrl']) if 'titleUrl' in obj else None
            if not video_id:
                continue
            if 'subtitles' in obj:
                cursor.execute(
                    """INSERT INTO songs(title, artist, year, url) VALUES(?, ?, ?, ?)""",
                    (obj['title'][8:], obj['subtitles'][0]['name'], obj['time'], video_id)
                )
            elif duration:
                cursor.execute(
                    """INSERT INTO songs(title, artist, year, url) VALUES(?, ?, ?, ?)""",
                    ("parseme", "parseme", obj['time'], video_id)
                )


def print_db(cursor):
    print("####################Full List#####################", file=log)
    cursor.execute("""SELECT id, artist, title, url, year FROM songs""")
    for row in cursor.fetchall():
        print('{0} : {1} - {2} - {4} - {3}'.format(row[0], row[1], row[2], row[3], row[4]), file=log)

    print("####################Non-Duplicate List#####################", file=log)
    cursor.execute("""SELECT id, artist, title, url, occurence FROM report""")
    for row in cursor.fetchall():
        print('{0} : {1} - {2} - {3} - {4}'.format(row[0], row[1], row[2], row[3], row[4]), file=log)


def prepare_tops(cursor):
    # Artist top
    cursor.execute("""SELECT artist FROM report GROUP BY artist""")
    for res in cursor.fetchall():
        occurences = 0
        total_duration = 0
        cursor.execute("""SELECT occurence, duration FROM report WHERE artist = ?""", (res[0],))
        for occ in cursor.fetchall():
            occurences += occ[0]
            total_duration += occ[1]
        cursor.execute(
            """INSERT INTO artist_count(artist, occurence, duration) VALUES(?, ?, ?)""",
            (res[0], occurences, total_duration)
        )

    # Song top
    cursor.execute("""SELECT title, artist, occurence FROM report GROUP BY url""")
    for res_song in cursor.fetchall():
        cursor.execute(
            """INSERT INTO songs_count(title, artist, occurence) VALUES(?, ?, ?)""",
            (res_song[0], res_song[1], res_song[2])
        )


def delete_duplicate(cursor):
    cursor.execute("""SELECT title, COUNT(*), artist, url FROM songs GROUP BY url""")
    for res in cursor.fetchall():
        title, count, artist, url = res[0], res[1], res[2], res[3]
        cursor.execute(
            """INSERT INTO report(title, artist, occurence, url, duration) VALUES(?, ?, ?, ?, 0)""",
            (title, artist, count, url)
        )

    cursor.execute("""SELECT id, artist, title, url FROM report WHERE title = 'parseme'""")
    for row in cursor.fetchall():
        cursor.execute(
            """SELECT artist, title FROM songs WHERE url = ? AND title != ?""", (row[3], "parseme")
        )
        match = cursor.fetchone()
        if match:
            cursor.execute(
                """UPDATE report SET artist = ?, title = ? WHERE id = ?""", (match[0], match[1], row[0])
            )

    if not duration:
        cursor.execute("""DELETE FROM report WHERE title = 'parseme'""")


def print_full_tops(cursor):
    print("####################Top Artists#####################", file=log)
    cursor.execute("""SELECT artist, occurence FROM artist_count ORDER by occurence DESC""")
    for row in cursor.fetchall():
        print('{0} - {1}'.format(row[0], row[1]), file=log)

    print("####################Top Songs#####################", file=log)
    cursor.execute("""SELECT artist, title, occurence FROM songs_count ORDER by occurence DESC""")
    for row in cursor.fetchall():
        print('{0} - {1} - {2}'.format(row[0], row[1], row[2]), file=log)


def parse_duration(duration_str):
    time = re.findall(r'\d+', duration_str)
    length = len(time)
    if length > 4:
        return 0
    if length == 4:
        return (int(time[0]) * 24 * 3600) + (int(time[1]) * 3600) + (int(time[2]) * 60) + int(time[3])
    elif length == 3:
        return (int(time[0]) * 3600) + (int(time[1]) * 60) + int(time[2])
    elif length == 2:
        return (int(time[0]) * 60) + int(time[1])
    elif length == 1:
        return int(time[0])
    return 0


def call_api(idlist, cursor):
    print("api called", file=log)
    ytAPIkey = get_api_key()
    parameters = {
        "part": "contentDetails,snippet",
        "id": ','.join(idlist),
        "key": ytAPIkey
    }
    response = requests.get("https://www.googleapis.com/youtube/v3/videos", params=parameters)
    if response.status_code == 200:
        items = response.json().get('items', [])
        print(f"API returned {len(items)} items for {len(idlist)} requested", file=log)
        for item in items:
            raw_duration = item['contentDetails']['duration']
            dur = parse_duration(raw_duration)
            artist = item['snippet']['channelTitle']
            title = item['snippet']['title']
            url = item['id']
            print(f"  {url}: raw={raw_duration} parsed={dur}s", file=log)
            cursor.execute(
                """UPDATE report SET duration = ?, artist = ?, title = ? WHERE url = ?""",
                (dur, artist, title, url)
            )
            print(f"  rows affected: {cursor.rowcount}", file=log)
    else:
        print(f"API error {response.status_code}: {response.text}", file=log)


def get_duration(cursor):
    cursor.execute("""SELECT id, artist, title, url FROM report""")
    rows = cursor.fetchall()
    print("\tNumber of videos: " + str(len(rows)))

    idlist = []
    calls = 0
    for row in rows:
        idlist.append(row[3])
        if len(idlist) == 50:
            print(f"\tGetting info on videos {1 + 50 * calls} - {50 + 50 * calls}")
            print(','.join(idlist), file=log)
            call_api(idlist, cursor)
            calls += 1
            idlist = []

    if idlist:
        print(f"\tGetting info on videos {1 + 50 * calls} - {len(rows)}")
        print(','.join(idlist), file=log)
        call_api(idlist, cursor)

    cursor.execute(
        """UPDATE report SET duration = ?, artist = ?, title = ? WHERE title = ?""",
        (0, "Unknown Artist", "Unavailable Video", "parseme")
    )

    song_count = 0
    total_duration = 0
    error_rate = 0

    if verbose:
        print("####################Full List WITHOUT DOUBLON AND DURATION#####################", file=log)

    cursor.execute("""SELECT id, artist, title, duration, occurence, url FROM report""")
    for row in cursor.fetchall():
        song_count = row[0]
        if verbose:
            print('{0} : {1} - {2} - {3} - occurence : {4} - {5}'.format(
                row[0], row[1], row[2], row[3], row[4], row[5]), file=log)
        total_duration += row[3] * row[4]
        if row[3] == 0:
            error_rate += 1

    return (total_duration, error_rate, song_count)


def gen_html_report(cursor, data, analyzeYear):
    with open('report_{0}.html'.format(str(analyzeYear)), 'w', encoding="utf8") as htmlreport:
        print("""<!DOCTYPE html><html><head>
<meta charset="utf-8">
<title>YTM Wrapped</title>
<style type="text/css">
@import url('https://fonts.googleapis.com/css2?family=PT+Sans&family=Roboto:wght@400;500&display=swap');
body{background-color: #000; color: #fff; font-family: "Roboto"; font-size: 14px;}
.center-div{margin: 100px auto; width: 720px; position: relative;}
.ytm_logo{height: 64px; position: absolute; top: 40px; 0;}
.title_logo{height: 64px; position: absolute; top: 40px; left: 80px;}
.right_title{position: absolute; top: 60px; right: 0; font-size: 2em; font-weight: 500;}
.container{position: absolute; top: 150px; left: 0; right: 0}
.minutes_title{font-size: 2em; font-weight: 500;}
.minutes{font-size: 6em;}
.row{display: flex;}
.column1{flex: 40%;}
.column2{flex: 60%;}
.list{font-size: 1.4em;}
.list div{margin-bottom: 0.5em;}
.list span{font-size: 0.75em; opacity: 0.75;}
</style></head><body><div class="center-div">
<img src="ytm_logo.png" class="ytm_logo">
<img src="title.png" class="title_logo"/>
<span class="right_title">""", file=htmlreport)
        print(str(analyzeYear), file=htmlreport)
        print(""" Wrapped</span><div class="container">
<div class="minutes_title">Minutes Listened</div>
<div class="minutes">""", file=htmlreport)

        print(str(data[0] // 60) if duration else "N/A", file=htmlreport)

        print("""</div><br><br><div class="row"><div class="column1">
<div class="minutes_title">Top Artists</div><div class="list">""", file=htmlreport)

        cursor.execute("""SELECT artist, occurence, duration FROM artist_count
            WHERE occurence > 5 ORDER BY occurence DESC LIMIT 10""")

        for row in cursor.fetchall():
            print("<div></div>", file=htmlreport)
            artist_name = str(row[0]).replace(' - Topic', '')
            if moreDetails:
                if duration:
                    print(f'{artist_name}<br><span>{row[1]} songs ({row[2] // 60} mins)</span>', file=htmlreport)
                else:
                    print(f'{artist_name}<br><span>{row[1]} songs</span>', file=htmlreport)
            else:
                print(artist_name, file=htmlreport)

        print("""</div></div><div class="column2">
<div class="minutes_title">Top Songs</div><div class="list">""", file=htmlreport)

        cursor.execute("""SELECT artist, title, occurence FROM songs_count ORDER by occurence DESC LIMIT 10""")
        for row in cursor.fetchall():
            print("<div></div>", file=htmlreport)
            artist_name = str(row[0]).replace(' - Topic', '')
            if moreDetails:
                print(f'{artist_name} - {row[1]}<br><span>{row[2]} plays</span>', file=htmlreport)
            else:
                print(row[1], file=htmlreport)

        print("""</div></div></div>
<button onclick="downloadReport()" style="
    position: fixed; bottom: 32px; right: 32px;
    background: #fff; color: #000;
    border: none; border-radius: 24px;
    padding: 12px 24px; font-family: Roboto; font-size: 14px; font-weight: 500;
    cursor: pointer; box-shadow: 0 4px 12px rgba(255,255,255,0.2);">&#8681; Download Report</button>
<script>
function downloadReport() {
    const html = document.documentElement.outerHTML;
    const blob = new Blob([html], { type: 'text/html' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'ytm_wrapped_""" + str(analyzeYear) + """.html';
    a.click();
    URL.revokeObjectURL(a.href);
}
</script>
</div></body></html>""", file=htmlreport)


def gen_report(cursor, data, analyzeYear):
    with open('report_{0}.dat'.format(str(analyzeYear)), 'w', encoding="utf8") as report:
        print("#################### Top Artists #####################", file=report)
        cursor.execute("""SELECT artist, occurence FROM artist_count ORDER by occurence DESC""")
        for row in cursor.fetchall():
            print('{0} - {1}'.format(row[0], row[1]), file=report)

        print("#################### Top Songs #####################", file=report)
        cursor.execute("""SELECT artist, title, occurence FROM songs_count ORDER by occurence DESC""")
        for row in cursor.fetchall():
            print('{0} - {1} - {2}'.format(row[0], row[1], row[2]), file=report)

        if duration:
            print("\n#################### Duration #####################", file=report)
            print('Total duration : {0}'.format(data[0]), file=report)
            print('Total song count : {0}'.format(data[2]), file=report)
            print('Error count : {0}'.format(data[1]), file=report)
            print('Error rate : {0}%'.format((float(data[1]) / data[2]) * 100), file=report)

    gen_html_report(cursor, data, analyzeYear)


def main():
    flags()

    # Validate API key early if duration mode is requested
    if duration:
        get_api_key()

    conn = sqlite3.connect('ytmusic.db')
    cursor = conn.cursor()
    with open('schema.sql') as fp:
        cursor.executescript(fp.read())

    file = open_file()

    print("Welcome to YouTube Music Year Wrapper.")
    print("We are now processing your file.")

    parse_json(file, cursor)
    print("Removing duplicates")
    delete_duplicate(cursor)

    if verbose:
        print_db(cursor)
    if duration:
        print("Getting durations. This may take a while.")
        data = get_duration(cursor)
    else:
        data = ""

    print("Getting top 10's")
    prepare_tops(cursor)
    if verbose:
        print_full_tops(cursor)

    log.close()
    print("Generating final report")
    gen_report(cursor, data, analyzeYear)
    conn.commit()
    conn.close()
    print("All done!")


if __name__ == "__main__":
    '''
   RUN in terminal: 
        python watch.py watch-history.json -d -m (minutes listened to WILL BE 0 if NO api key included)
         OR
        python watch.py watch-history.json -m -d --api-key YOUR_API_KEY  (ENSURE minutes listened to COMPUTED)
    '''
    main()