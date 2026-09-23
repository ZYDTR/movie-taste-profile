"""Combine the reading views and verbatim feedback into one portable document."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(filename):
    return json.loads((ROOT / filename).read_text())


def section(filename):
    text = (ROOT / filename).read_text()
    return re.sub(r"^(#{1,5}) ", r"#\1 ", text, flags=re.MULTILINE).strip()


summary = load("data/verification.json")
preferences = load("data/personal_preferences.json")
watchlist = load("data/watchlist.json")
oral_titles = "、".join(
    f"《{row['title_zh']}》" for row in preferences["self_reported_watched"]
)
watchlist_text = "# 想看清单\n\n" + "\n".join(
    f"{row['rank']}. [{row['title']}]({row['url']})"
    for row in sorted(watchlist["items"], key=lambda row: row["rank"])
) + "\n"
(ROOT / "想看清单.md").write_text(watchlist_text)

parts = [
    "# 我的完整观影资料",
    f"更新于 {preferences['updated_on']}。此文件汇总全部阅读内容，适合转发或交给其他 AI 阅读。"
    "原始字段、结构化偏好和来源校验另保留在 [仓库首页](README.md) 所列文件中。",
    f"豆瓣快照 {summary['watched_total']} 条：{summary['rated_movies']} 部已评级电影、"
    f"{summary['rated_tv']} 条已评级电视节目、{summary['unrated_total']} 部未评级电影；"
    f"其中 {summary['comment_count']} 条有短评。口述补充 {oral_titles} 后，"
    f"按 subject ID 合并共 {summary['known_watched_including_self_reported']} 条。"
    "剧名级口述补充单独保留，避免与分季条目重复计数。"
    f"另有 {len(watchlist['items'])} 部明确考虑观看的电影，尚无看后反馈。",
    section("观影画像与推荐.md"),
    section("想看清单.md"),
    "## 用户补充原话",
    "以下按记录顺序保留个人诉求及补充反馈。英文、措辞和不确定表达按原话保留。"
    "其中初始诉求为原请求的相关摘录；后续反馈的归纳与边界见 "
    "[反馈数据](data/feedback.json)。",
]

feedback = load("data/feedback.json")
for entry in feedback["entries"]:
    parts.extend([
        f"### {entry['date']} · {entry['id']}",
        entry["source"],
        "\n".join("> " + line if line else ">" for line in entry["verbatim"].splitlines()),
    ])
    if entry.get("source_url"):
        parts.append(f"[来源对话]({entry['source_url']})；摘录边界：{entry.get('quote_scope', '见原始来源')}。")
    if entry.get("additional_verbatim"):
        parts.append("补充原话：\n\n" + "\n".join(
            "> " + line if line else ">"
            for line in entry["additional_verbatim"].splitlines()
        ))

parts.extend(section(name) for name in ["电影评分.md", "剧集评分.md", "未评级记录.md", "历史推荐.md", "数据说明.md"])
output = ROOT / "完整资料.md"
output.write_text("\n\n".join(parts) + "\n")
print(f"{output.name}: {output.stat().st_size} bytes")
