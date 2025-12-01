#!/usr/bin/env python3
# 保存为 scripts/generate_stats_card.py
# 用法:
#   python3 scripts/generate_stats_card.py --user github653224 --out assets/github_stats.png

import os
import sys
import argparse
import requests
from PIL import Image, ImageDraw, ImageFont

GITHUB_GRAPHQL = "https://api.github.com/graphql"

# Simple color palette inspired by your sample
BG = (34, 26, 53)         # 深紫
ACCENT = (233, 87, 143)   # 粉色
TEXT = (220, 220, 230)    # 文字浅色
MUTED = (170, 170, 170)

FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Ubuntu runner
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]

def load_font(size):
    for p in FONT_PATHS:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()

def graphql_query(token, query, variables=None):
    headers = {"Authorization": f"bearer {token}"}
    payload = {"query": query, "variables": variables or {}}
    resp = requests.post(GITHUB_GRAPHQL, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()

def get_user_stats(token, user):
    query = """
    query($login:String!) {
      user(login: $login) {
        repositories(first: 100, ownerAffiliations: OWNER) {
          nodes {
            stargazerCount
          }
        }
        repositoriesContributedTo {
          totalCount
        }
        contributionsCollection {
          totalCommitContributions
          totalPullRequestContributions
          totalIssueContributions
          contributionCalendar {
            totalContributions
          }
        }
        pullRequests {
          totalCount
        }
        issues {
          totalCount
        }
      }
    }
    """
    data = graphql_query(token, query, {"login": user})
    if "errors" in data:
        raise RuntimeError(data["errors"])
    u = data["data"]["user"]
    stars = sum([n["stargazerCount"] for n in u["repositories"]["nodes"]]) if u["repositories"]["nodes"] else 0
    stats = {
        "total_stars": stars,
        "total_commits": u["contributionsCollection"]["totalCommitContributions"],
        "total_prs": u["pullRequests"]["totalCount"],
        "total_issues": u["issues"]["totalCount"],
        "contributed_to": u["repositoriesContributedTo"]["totalCount"],
        "year_contributions": u["contributionsCollection"]["contributionCalendar"]["totalContributions"],
        "pr_contribs": u["contributionsCollection"]["totalPullRequestContributions"],
        "issue_contribs": u["contributionsCollection"]["totalIssueContributions"],
    }
    return stats

def score_from_stats(stats):
    # 简单打分规则（可调整）
    score = stats["total_commits"] / 10.0 + stats["total_prs"] * 0.6 + stats["total_stars"] * 0.15 + stats["contributed_to"] * 1.0
    score = max(0, min(100, score))
    return int(score)

def grade_from_score(score):
    if score >= 90:
        return "A++"
    if score >= 75:
        return "A+"
    if score >= 60:
        return "A"
    if score >= 40:
        return "B"
    if score >= 20:
        return "C"
    return "D"

def draw_card(stats, score, grade, out_path):
    W, H = 820, 200
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    font_title = load_font(20)
    font_big = load_font(36)
    font_med = load_font(18)
    font_small = load_font(14)

    padding = 28
    left_w = 520

    # Title
    d.text((padding, 18), f"{os.environ.get('GITHUB_USER','GitHub')}'s GitHub Stats", font=font_title, fill=TEXT)

    # Left metrics
    labels = [
        ("Total Stars:", stats["total_stars"]),
        ("Total Commits:", stats["total_commits"]),
        ("Total PRs:", stats["total_prs"]),
        ("Total Issues:", stats["total_issues"]),
        ("Contributed to:", stats["contributed_to"]),
    ]
    y = 56
    for label, value in labels:
        d.text((padding, y), label, font=font_med, fill=(255,180,210))
        d.text((padding + 180, y), str(value), font=font_big, fill=TEXT)
        y += 34

    # Right: circular score ring
    cx, cy = left_w + 180, H // 2
    radius = 64
    thickness = 12
    bbox = [cx - radius, cy - radius, cx + radius, cy + radius]
    d.ellipse(bbox, outline=(60,60,80), width=thickness)
    start = -90
    end = start + int(360 * (score / 100.0))
    d.arc(bbox, start=start, end=end, fill=ACCENT, width=thickness)

    # grade text in center
    w, h = d.textsize(grade, font=font_big)
    d.text((cx - w/2, cy - h/2), grade, font=font_big, fill=TEXT)

    # small caption showing percent
    pct = f"{score}%"
    w2, h2 = d.textsize(pct, font=font_small)
    d.text((cx - w2/2, cy + 34), pct, font=font_small, fill=MUTED)

    # footer
    d.text((padding, H - 26), f"Generated for {os.environ.get('GITHUB_USER','GitHub')}", font=font_small, fill=MUTED)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    im.save(out_path, optimize=True)
    print("Saved image to", out_path)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", required=True, help="GitHub username")
    parser.add_argument("--out", default="assets/github_stats.png", help="Output image path")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Missing GITHUB_TOKEN in env", file=sys.stderr)
        sys.exit(2)

    os.environ["GITHUB_USER"] = args.user

    stats = get_user_stats(token, args.user)
    score = score_from_stats(stats)
    grade = grade_from_score(score)
    draw_card(stats, score, grade, args.out)

if __name__ == "__main__":
    main()
