import openai
from googleapiclient.discovery import build
import isodate
import requests

def get_video_details(youtube, video_ids):
    titles = []
    links = []
    response = youtube.videos().list(
        part="snippet,contentDetails",
        id=",".join(video_ids)
    ).execute()

    for item in response["items"]:
        duration = isodate.parse_duration(item["contentDetails"]["duration"]).total_seconds() / 60
        if 4 <= duration <= 20:
            titles.append(item["snippet"]["title"])
            links.append(f"https://www.youtube.com/watch?v={item['id']}")

    return titles, links

def analyze_titles(user_query, titles, links, api_key):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    prompt = f"""User query: {user_query}
Video titles:
{chr(10).join([f"{i+1}. {title}" for i, title in enumerate(titles)])}

Pick the most relevant title based on the query. Output:
1. Title
2. Reason
3. Index of title in list
"""
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.5},
    }

    response = requests.post(f"{url}?key={api_key}", json=data, headers=headers)
    text = response.json()['candidates'][0]['content']['parts'][0]['text']
    
    import re
    match = re.search(r"(?i)index.*?(\d+)", text)
    idx = int(match.group(1)) - 1 if match else 0
    return titles[idx], links[idx], text

