"""Combine the reading views and verbatim feedback into one portable document."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def section(filename):
    text = (ROOT / filename).read_text()
    return re.sub(r"^(#{1,5}) ", r"#\1 ", text, flags=re.MULTILINE).strip()


parts = [
    "# 我的完整观影资料",
    "更新于 2026-09-23。此文件汇总全部阅读内容，适合转发或交给其他 AI 阅读。"
    "原始字段、结构化偏好和来源校验另保留在 [仓库首页](README.md) 所列文件中。",
    "豆瓣快照 107 条：77 部已评级电影、27 条已评级电视节目、3 部未评级电影；"
    "其中 43 条有短评。口述《朗读者》另补入按 subject ID 合并的 108 条记录；"
    "剧名级口述补充单独保留，避免与分季条目重复计数。",
    section("观影画像与推荐.md"),
    "## 用户补充原话",
    "以下按记录顺序保留个人诉求及补充反馈。英文、措辞和不确定表达按原话保留。"
    "其中初始诉求为原请求的相关摘录；后续反馈的归纳与边界见 "
    "[反馈数据](data/feedback.json)。",
]

feedback = json.loads((ROOT / "data/feedback.json").read_text())
for entry in feedback["entries"]:
    parts.extend([
        f"### {entry['date']} · {entry['id']}",
        entry["source"],
        "\n".join("> " + line if line else ">" for line in entry["verbatim"].splitlines()),
    ])

parts.extend(section(name) for name in ["电影评分.md", "剧集评分.md", "未评级记录.md", "数据说明.md"])
output = ROOT / "完整资料.md"
output.write_text("\n\n".join(parts) + "\n")
print(f"{output.name}: {output.stat().st_size} bytes")
