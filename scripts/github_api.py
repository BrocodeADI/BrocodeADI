"""GitHub GraphQL API client and deterministic data processing layer."""

from __future__ import annotations

import datetime
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import requests

from .config import Config

logger = logging.getLogger(__name__)

# GraphQL query for user contributions and public repositories
USER_DATA_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    name
    login
    bio
    company
    location
    avatarUrl
    createdAt
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      totalRepositoryContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            color
            weekday
          }
        }
      }
    }
    repositories(
      first: 100
      ownerAffiliations: OWNER
      isFork: false
      privacy: PUBLIC
      orderBy: {field: PUSHED_AT, direction: DESC}
    ) {
      totalCount
      nodes {
        name
        stargazerCount
        forkCount
        isPrivate
        isFork
        primaryLanguage {
          name
          color
        }
        languages(first: 20, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node {
              name
              color
            }
          }
        }
      }
    }
    pinnedItems(first: 6, types: [REPOSITORY]) {
      nodes {
        ... on Repository {
          name
          description
          stargazerCount
          forkCount
          primaryLanguage { name color }
          url
        }
      }
    }
    organizations(first: 10) {
      nodes {
        name
        login
        avatarUrl
        url
      }
    }
  }
}
"""


@dataclass
class ContributionDay:
    date: str  # YYYY-MM-DD
    count: int
    color: str
    weekday: int  # 0 = Sunday, 6 = Saturday


@dataclass
class ContributionWeek:
    days: List[ContributionDay] = field(default_factory=list)


@dataclass
class StreakInfo:
    current_streak: int
    current_start: Optional[str]
    current_end: Optional[str]
    longest_streak: int
    longest_start: Optional[str]
    longest_end: Optional[str]
    total_active_days: int
    total_days: int


@dataclass
class LanguageStat:
    name: str
    color: str
    bytes: int
    percentage: float


@dataclass
class PinnedRepo:
    name: str
    description: str
    stars: int
    forks: int
    language: str
    url: str


@dataclass
class OrgInfo:
    name: str
    login: str
    url: str


@dataclass
class GitHubUserData:
    username: str
    name: str
    bio: str
    location: str
    total_contributions: int
    total_commits: int
    total_issues: int
    total_prs: int
    total_reviews: int
    total_stars: int
    total_forks: int
    public_repos_count: int
    weeks: List[ContributionWeek]
    streak: StreakInfo
    languages: List[LanguageStat]
    from_date: str
    to_date: str
    pinned_repos: List[PinnedRepo] = field(default_factory=list)
    organizations: List[OrgInfo] = field(default_factory=list)


def get_deterministic_utc_window(days: int = 365) -> Tuple[datetime.datetime, datetime.datetime]:
    """
    Get normalized UTC datetime window for deterministic data fetching.
    start = midnight UTC (00:00:00)
    end   = end of UTC day (23:59:59)
    """
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    to_dt = datetime.datetime(
        now_utc.year, now_utc.month, now_utc.day, 23, 59, 59, tzinfo=datetime.timezone.utc
    )
    # Calculate days-1 back to encompass exact number of days
    from_dt = (to_dt - datetime.timedelta(days=days - 1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return from_dt, to_dt


def calculate_streak(all_days: List[ContributionDay]) -> StreakInfo:
    """
    Calculate current streak, longest streak, and active days.
    Input days should be ordered chronologically by date.
    """
    if not all_days:
        return StreakInfo(0, None, None, 0, None, None, 0, 0)

    # Sort days chronologically just in case
    sorted_days = sorted(all_days, key=lambda d: d.date)
    total_days = len(sorted_days)
    total_active_days = sum(1 for d in sorted_days if d.count > 0)

    longest_streak = 0
    longest_start = None
    longest_end = None
    
    current_run = 0
    current_run_start = None
    
    for day in sorted_days:
        if day.count > 0:
            if current_run == 0:
                current_run_start = day.date
            current_run += 1
            if current_run > longest_streak:
                longest_streak = current_run
                longest_start = current_run_start
                longest_end = day.date
        else:
            current_run = 0
            current_run_start = None

    # Calculate current streak ending today or yesterday
    # Determine the reference date (latest date in calendar)
    current_streak = 0
    current_start = None
    current_end = None
    
    if sorted_days:
        # Check backwards from the latest day
        idx = len(sorted_days) - 1
        latest_day = sorted_days[idx]
        
        # If latest day (today) has 0 contributions, check if yesterday was part of an active streak
        if latest_day.count == 0:
            idx -= 1

        while idx >= 0 and sorted_days[idx].count > 0:
            current_streak += 1
            if current_end is None:
                current_end = sorted_days[idx].date
            current_start = sorted_days[idx].date
            idx -= 1

    return StreakInfo(
        current_streak=current_streak,
        current_start=current_start,
        current_end=current_end,
        longest_streak=longest_streak,
        longest_start=longest_start,
        longest_end=longest_end,
        total_active_days=total_active_days,
        total_days=total_days
    )


def aggregate_languages(repositories: List[Dict[str, Any]]) -> List[LanguageStat]:
    """
    Deterministically aggregate byte-weighted language stats from public repos.
    Excludes forks and private repositories.
    """
    lang_bytes: Dict[str, int] = {}
    lang_colors: Dict[str, str] = {}
    
    default_colors = {
        "Python": "#3572A5",
        "Rust": "#dea584",
        "TypeScript": "#3178c6",
        "JavaScript": "#f1e05a",
        "Go": "#00ADD8",
        "C++": "#f34b7d",
        "C": "#555555",
        "Java": "#b07219",
        "HTML": "#e34c26",
        "CSS": "#563d7c",
        "Shell": "#89e051",
        "Dockerfile": "#384d54",
        "Swift": "#F05138",
        "Kotlin": "#A97BFF",
        "Ruby": "#701516",
        "Zig": "#ec915c",
        "Lua": "#000080"
    }

    for repo in repositories:
        if repo.get("isFork") or repo.get("isPrivate"):
            continue
            
        langs = repo.get("languages", {}).get("edges", [])
        for edge in langs:
            size = edge.get("size", 0)
            node = edge.get("node", {})
            name = node.get("name")
            color = node.get("color") or default_colors.get(name, "#8b949e")
            
            if name:
                lang_bytes[name] = lang_bytes.get(name, 0) + size
                lang_colors[name] = color

    total_bytes = sum(lang_bytes.values())
    if total_bytes == 0:
        return []

    # Sort deterministically: descending size, then alphabetically
    sorted_langs = sorted(
        lang_bytes.items(),
        key=lambda item: (-item[1], item[0])
    )

    result: List[LanguageStat] = []
    for name, b_count in sorted_langs:
        pct = (b_count / total_bytes) * 100.0
        result.append(
            LanguageStat(
                name=name,
                color=lang_colors.get(name, "#8b949e"),
                bytes=b_count,
                percentage=round(pct, 2)
            )
        )
        
    return result


def generate_mock_user_data(config: Config) -> GitHubUserData:
    """Generate high-quality, realistic deterministic mock data for local testing."""
    from_dt, to_dt = get_deterministic_utc_window(config.contribution_days)
    from_str = from_dt.strftime("%Y-%m-%dT00:00:00Z")
    to_str = to_dt.strftime("%Y-%m-%dT23:59:59Z")
    
    # Generate 52 weeks of deterministic activity
    weeks: List[ContributionWeek] = []
    all_days: List[ContributionDay] = []
    
    curr = from_dt
    # Align to start of week (Sunday)
    weekday_offset = (curr.weekday() + 1) % 7  # 0=Sunday
    curr = curr - datetime.timedelta(days=weekday_offset)
    
    total_contribs = 0
    import math
    
    day_idx = 0
    while curr <= to_dt or (curr.weekday() + 1) % 7 != 0:
        week = ContributionWeek()
        for _ in range(7):
            date_str = curr.strftime("%Y-%m-%d")
            # Deterministic wave pattern simulating realistic commits
            wave = math.sin(day_idx * 0.15) * 2 + math.cos(day_idx * 0.05) * 3
            day_of_week = (curr.weekday() + 1) % 7
            is_weekend = (day_of_week in (0, 6))
            
            base_count = int(max(0, wave + (2 if not is_weekend else 0)))
            if (day_idx % 19 == 0) or (day_idx % 37 == 0):
                count = base_count + 8
            elif is_weekend and (day_idx % 3 != 0):
                count = 0
            else:
                count = base_count
                
            total_contribs += count
            c_day = ContributionDay(
                date=date_str,
                count=count,
                color="#26a641" if count > 0 else "#161b22",
                weekday=day_of_week
            )
            week.days.append(c_day)
            all_days.append(c_day)
            curr += datetime.timedelta(days=1)
            day_idx += 1
            
        weeks.append(week)
        if curr > to_dt:
            break

    streak = calculate_streak(all_days)
    
    mock_repos = [
        {
            "name": "neural-engine",
            "stargazerCount": 248,
            "forkCount": 38,
            "isFork": False,
            "isPrivate": False,
            "languages": {
                "edges": [
                    {"size": 420000, "node": {"name": "Rust", "color": "#dea584"}},
                    {"size": 180000, "node": {"name": "C++", "color": "#f34b7d"}},
                    {"size": 65000, "node": {"name": "Python", "color": "#3572A5"}}
                ]
            }
        },
        {
            "name": "distributed-kv",
            "stargazerCount": 185,
            "forkCount": 24,
            "isFork": False,
            "isPrivate": False,
            "languages": {
                "edges": [
                    {"size": 310000, "node": {"name": "Go", "color": "#00ADD8"}},
                    {"size": 45000, "node": {"name": "Shell", "color": "#89e051"}}
                ]
            }
        },
        {
            "name": "terminal-ui",
            "stargazerCount": 92,
            "forkCount": 11,
            "isFork": False,
            "isPrivate": False,
            "languages": {
                "edges": [
                    {"size": 210000, "node": {"name": "TypeScript", "color": "#3178c6"}},
                    {"size": 85000, "node": {"name": "Python", "color": "#3572A5"}},
                    {"size": 30000, "node": {"name": "HTML", "color": "#e34c26"}}
                ]
            }
        }
    ]
    
    languages = aggregate_languages(mock_repos)
    
    return GitHubUserData(
        username=config.github_username,
        name=config.display_name,
        bio=config.bio,
        location=config.location,
        total_contributions=total_contribs,
        total_commits=int(total_contribs * 0.85),
        total_issues=int(total_contribs * 0.05),
        total_prs=int(total_contribs * 0.08),
        total_reviews=int(total_contribs * 0.02),
        total_stars=525,
        total_forks=73,
        public_repos_count=18,
        weeks=weeks,
        streak=streak,
        languages=languages,
        from_date=from_str,
        to_date=to_str
    )


class GitHubAPIClient:
    """GraphQL client for GitHub API."""
    
    def __init__(self, config: Config) -> None:
        self.config = config
        
    def fetch_user_data(self) -> GitHubUserData:
        """Fetch real data from GitHub GraphQL API or fall back to mock data."""
        if not self.config.github_token:
            logger.info("No GITHUB_TOKEN provided; using deterministic mock activity data.")
            return generate_mock_user_data(self.config)
            
        from_dt, to_dt = get_deterministic_utc_window(self.config.contribution_days)
        from_str = from_dt.strftime("%Y-%m-%dT00:00:00Z")
        to_str = to_dt.strftime("%Y-%m-%dT23:59:59Z")
        
        headers = {
            "Authorization": f"bearer {self.config.github_token}",
            "User-Agent": "GitHub-Profile-Generator/1.0",
            "Content-Type": "application/json"
        }
        
        payload = {
            "query": USER_DATA_QUERY,
            "variables": {
                "login": self.config.github_username,
                "from": from_str,
                "to": to_str
            }
        }
        
        try:
            logger.info(f"Querying GitHub GraphQL API for user '{self.config.github_username}'...")
            response = requests.post(
                self.config.github_api_url,
                json=payload,
                headers=headers,
                timeout=15.0
            )
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                error_msg = "; ".join(e.get("message", "Unknown error") for e in data["errors"])
                logger.error(f"GitHub GraphQL API errors: {error_msg}")
                raise ValueError(f"GitHub API Error: {error_msg}")
                
            user_data = data.get("data", {}).get("user")
            if not user_data:
                raise ValueError(f"User '{self.config.github_username}' not found on GitHub.")
                
            return self._parse_api_response(user_data, from_str, to_str)
            
        except Exception as e:
            logger.error(f"Failed to fetch data from GitHub API: {e}")
            logger.warning("Falling back to deterministic mock activity data.")
            return generate_mock_user_data(self.config)

    def _parse_api_response(
        self, user_dict: Dict[str, Any], from_date: str, to_date: str
    ) -> GitHubUserData:
        """Parse raw GraphQL dictionary into strongly typed GitHubUserData."""
        contribs_collection = user_dict.get("contributionsCollection", {})
        calendar = contribs_collection.get("contributionCalendar", {})
        total_contribs = calendar.get("totalContributions", 0)
        
        weeks: List[ContributionWeek] = []
        all_days: List[ContributionDay] = []
        
        for w in calendar.get("weeks", []):
            week = ContributionWeek()
            for d in w.get("contributionDays", []):
                c_day = ContributionDay(
                    date=d.get("date", ""),
                    count=d.get("contributionCount", 0),
                    color=d.get("color", ""),
                    weekday=d.get("weekday", 0)
                )
                week.days.append(c_day)
                all_days.append(c_day)
            weeks.append(week)

        streak = calculate_streak(all_days)
        
        repos_data = user_dict.get("repositories", {})
        repo_nodes = repos_data.get("nodes", [])
        public_repos_count = repos_data.get("totalCount", len(repo_nodes))
        
        total_stars = sum(r.get("stargazerCount", 0) for r in repo_nodes)
        total_forks = sum(r.get("forkCount", 0) for r in repo_nodes)
        
        languages = aggregate_languages(repo_nodes)

        # Parse pinned repos
        pinned_nodes = user_dict.get("pinnedItems", {}).get("nodes", [])
        pinned_repos = [
            PinnedRepo(
                name=r.get("name", ""),
                description=r.get("description") or "",
                stars=r.get("stargazerCount", 0),
                forks=r.get("forkCount", 0),
                language=(r.get("primaryLanguage") or {}).get("name", ""),
                url=r.get("url", "")
            )
            for r in pinned_nodes
        ]

        # Parse organizations
        org_nodes = user_dict.get("organizations", {}).get("nodes", [])
        organizations = [
            OrgInfo(
                name=o.get("name") or o.get("login", ""),
                login=o.get("login", ""),
                url=o.get("url", "")
            )
            for o in org_nodes
        ]

        return GitHubUserData(
            username=user_dict.get("login", self.config.github_username),
            name=user_dict.get("name") or self.config.display_name,
            bio=user_dict.get("bio") or self.config.bio,
            location=user_dict.get("location") or self.config.location,
            total_contributions=total_contribs,
            total_commits=contribs_collection.get("totalCommitContributions", 0),
            total_issues=contribs_collection.get("totalIssueContributions", 0),
            total_prs=contribs_collection.get("totalPullRequestContributions", 0),
            total_reviews=contribs_collection.get("totalPullRequestReviewContributions", 0),
            total_stars=total_stars,
            total_forks=total_forks,
            public_repos_count=public_repos_count,
            weeks=weeks,
            streak=streak,
            languages=languages,
            from_date=from_date,
            to_date=to_date,
            pinned_repos=pinned_repos,
            organizations=organizations,
        )
