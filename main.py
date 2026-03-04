import os
import json
import feedparser
import requests
import gemini
from requests_oauthlib import OAuth1

def is_proceeded(url):
    kv_origin = os.getenv('KV_ORIGIN')
    proceeded = requests.get(f'{kv_origin}/hatena/{url}').text
    if proceeded:
        return True
    requests.put(f'{kv_origin}/hatena/{url}', '1')
    return False

def post_comment(url, comment):
    print(url, comment)
    client_key, client_secret, token_key, token_secret = os.getenv('HATENA_TOKEN').split(',')
    requests.post("https://bookmark.hatenaapis.com/rest/1/my/bookmark", {"url": url, "comment": comment}, auth=OAuth1(client_key, client_secret, token_key, token_secret))

def get_entries():
    _entries = []
    for category in ['it', 'all', 'social', 'life', 'economics', 'knowledge', 'entertainment', 'fun', 'game', 'general']:
        try:
            rss_entries = feedparser.parse(f"https://b.hatena.ne.jp/entrylist/{category}.rss").entries
            print('category:', category, 'rss_entries:', len(rss_entries))
            for entry in rss_entries:
                if entry.link.startswith('https://anond.hatelabo.jp'):
                    continue
                if is_proceeded(entry.link):
                    continue
                _entries.append({
                    "title": entry.title,
                    "summary": entry.summary,
                    "url": entry.link
                })
                if len(_entries) >= 20:
                    return _entries
        except Exception as e:
            print(e)
    return _entries

entries = get_entries()

if entries:
    print('ENTRIES:', len(entries))
    context = json.dumps(entries[:20], ensure_ascii=False)
    response, failed_urls = gemini.generate_content(context)
    print('response.text', response.text)
    comments = json.loads(response.text)
    urls = [entry['url'] for entry in entries]
    for comment in comments:
        if comment['url'] not in urls:
            print('NOT_IN_URLS:', comment['url'])
            continue
        if comment['is_content_unavailable']:
            print('IS_CONTENT_UNAVAILABLE:', comment)
            continue
        if comment['is_inappropriate']:
            print('IS_INAPPROPRIATE:', comment)
            continue
        if comment['url'] in failed_urls:
            print('FAILED_URLS:', comment)
            continue
        if not comment['is_japanese_article']:
            post_comment(comment['url'], comment['comment'])
            continue
        if comment['predicted_hatebu_count'] < 100:
            print('PREDICTED_HATEBU_COUNT:', comment)
            continue
        post_comment(comment['url'], comment['comment'])







