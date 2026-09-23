"""Build local reading/data views from a verified Douban UI snapshot. No network."""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATE = '20260923'


def load(name):
    return json.loads((ROOT / name).read_text())


def save(name, obj):
    target = ROOT / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def checksum(row):
    payload = json.dumps(row, ensure_ascii=False, separators=(',', ':')).encode('utf-16-le')
    h = 2166136261
    for i in range(0, len(payload), 2):
        h = ((h ^ int.from_bytes(payload[i:i+2], 'little')) * 16777619) & 0xffffffff
    return f'{h:08x}'


source = load(f'raw/collect-{DATE}.json')
manifest = load(f'raw/manifest-{DATE}.json')
expected = dict(load(f'raw/browser-checksums-{DATE}.json')['rows'])
rows = source['rows']
ids = [r[0] for r in rows]
movie_ids = set(manifest['movie_filter']['subject_ids'])
assert len(rows) == len(set(ids)) == source['source_total'] == 107
assert len(movie_ids) == 80 and movie_ids <= set(ids)
assert len(expected) == len(rows) and set(expected) == set(ids)
assert all(checksum(r) == expected[r[0]] for r in rows), 'Browser-to-disk field mismatch'

records = []
for index, row in enumerate(rows):
    sid, title, stars, marked, year, comment, tag_texts = row
    flags = []
    if stars is None:
        flags.append('no_star_rating_in_list_ui')
    if year is None:
        flags.append('release_year_not_extracted_from_list_prefix')
    if year and int(marked[:4]) < year:
        flags.append('marked_year_precedes_first_listed_release_year')
    if sid in {'36820950', '36810718', '1293981'}:
        flags.append('comment_mentions_half_star_score_keep_separate_from_ui_rating')
    page = manifest['collection_pages'][index // 15]
    records.append({
        'subject_id': sid,
        'title': title,
        'title_zh': title.split(' / ')[0],
        'url': f'https://movie.douban.com/subject/{sid}/',
        'douban_type': 'movie' if sid in movie_ids else 'tv',
        'rating_stars': stars,
        'rating_scale': 5,
        'marked_date': marked,
        'first_listed_release_year': year,
        'comment': comment,
        'tags': [tag for text in tag_texts for tag in text.removeprefix('标签: ').split()],
        'source_page_url': page['url'],
        'captured_at': page['captured_at'],
        'quality_flags': flags,
    })

rated = [r for r in records if r['rating_stars'] is not None]
movies = [r for r in rated if r['douban_type'] == 'movie']
tv = [r for r in rated if r['douban_type'] == 'tv']
save('data/watched.json', records)
save('data/rated.json', rated)
save('data/rated_movies.json', movies)
save('data/rated_tv.json', tv)

# Preserve website snapshots; combine separately with explicitly reported viewing.
preferences_path = ROOT / 'data/personal_preferences.json'
preferences = load('data/personal_preferences.json') if preferences_path.exists() else {}
known = [{**r, 'source_type': 'douban_snapshot'} for r in records]
known_ids = set(ids)
for extra in preferences.get('self_reported_watched', []):
    if extra['subject_id'] not in known_ids:
        known.append(extra)
        known_ids.add(extra['subject_id'])
save('data/known_watched.json', known)

summary = {
    'snapshot_date': '2026-09-23',
    'watched_total': len(records), 'movies_total': len(movie_ids), 'tv_total': len(tv),
    'rated_total': len(rated), 'rated_movies': len(movies), 'rated_tv': len(tv),
    'unrated_total': len(records) - len(rated),
    'comment_count': sum(bool(r['comment']) for r in records),
    'star_distribution_all': dict(sorted(Counter(r['rating_stars'] for r in rated).items())),
    'star_distribution_movies': dict(sorted(Counter(r['rating_stars'] for r in movies).items())),
    'marked_date_range': [min(r['marked_date'] for r in records), max(r['marked_date'] for r in records)],
    'browser_field_checksums_matched': len(rows),
    'known_watched_including_self_reported': len(known),
    'additional_self_reported_watched': len(known) - len(records),
    'movie_classification': '80 IDs read from all 6 movie-filter pages; complementary television filter heading independently confirmed 27',
    'flags': [{'subject_id': r['subject_id'], 'title': r['title'], 'flags': r['quality_flags']} for r in records if r['quality_flags']],
}
save('data/verification.json', summary)

def md_escape(value):
    return str(value).replace('|', '\\|').replace('\n', '<br>')


def write_table(name, title, items):
    text = [f'# {title}', '', '数据快照：2026-09-23。星级是个人在豆瓣实际标记的 1–5 星。日期为标记日期，可能不同于实际观看日期。', '', '| 作品 | 年份¹ | 个人评分 | 标记日期 | 短评 |', '|---|---:|---:|---|---|']
    for r in sorted(items, key=lambda x: (-(x['rating_stars'] or 0), x['marked_date']), reverse=False):
        title_link = f"[{md_escape(r['title'])}]({r['url']})"
        score = f"{r['rating_stars']}/5" if r['rating_stars'] else '未评级'
        text.append(f"| {title_link} | {r['first_listed_release_year'] or '未提取'} | {score} | {r['marked_date']} | {md_escape(r['comment'] or '')} |")
    text += ['', '¹ 年份来自列表简介中首个上映日期的年份，可能是影展年份；未逐片核对首映年。原短评保留错别字、空格和表达。']
    (ROOT / name).write_text('\n'.join(text) + '\n')

write_table('电影评分.md', '已评级电影 · 77 部', movies)
write_table('剧集评分.md', '已评级剧集及电视节目 · 27 部', tv)
write_table('未评级记录.md', '已看但未标星 · 3 部', [r for r in records if r['rating_stars'] is None])
print(json.dumps(summary, ensure_ascii=False, indent=2))
