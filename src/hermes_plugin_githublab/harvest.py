import logging
from typing import Tuple, Dict, Optional
import gitlab
import requests
from urllib.parse import urlparse

from hermes.utils import hermes_user_agent
from hermes.commands.harvest.base import HermesHarvestPlugin, HermesHarvestCommand
from hermes.commands.harvest.util.token import load_token_from_toml
from hermes_plugin_git.util.github_utils import CodeMetaBuilder
from hermes_plugin_git.util.gitlab_utils import (
    get_gitlab_project,
    extract_gitlab_license,
    get_gitlab_contributors
)

logger = logging.getLogger(__name__)

SPDX_URL = 'https://raw.githubusercontent.com/spdx/license-list-data/master/json/licenses.json'


def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": hermes_user_agent})
    return session


class GitHubLabHarvestPlugin(HermesHarvestPlugin):
    def __init__(self):
        self.session = create_session()
        self.spdx_licenses = self._load_spdx_licenses()
        self.token = None

    def _load_spdx_licenses(self) -> Dict[str, str]:
        try:
            response = self.session.get(SPDX_URL)
            response.raise_for_status()
            licenses = {
                lic['name'].upper(): lic['licenseId']
                for lic in response.json().get('licenses', [])
            }
            return licenses
        except requests.RequestException as e:
            logger.error(f"Failed to load SPDX licenses: {e}")
            return {}

    def __call__(self, command: HermesHarvestCommand):
        self.token = self._load_token()

        path = str(getattr(command.args, "path", "")).replace("\\", "/")
        path = self._normalize_url(path)

        platform, metadata = self._fetch_repo_metadata(path)
        if platform == 'github' and metadata:
            codemeta = CodeMetaBuilder(metadata, token=self.token).build()
            return codemeta, {}
        return metadata, {}

    def _normalize_url(self, path: str) -> str:
        if not path.startswith(("http", "git@")):
            raise ValueError("Provided path is not a valid URL.")
        if path.startswith("https:/") and not path.startswith("https://"):
            path = "https://" + path[7:]
        return path

    def _load_token(self) -> Optional[str]:
        try:
            return load_token_from_toml('hermes.toml')
        except Exception as e:
            logger.warning(f"Failed to load token: {e}")
            return None

    def _fetch_repo_metadata(self, url: str) -> Tuple[str, dict]:
        parsed_url = urlparse(url)
        host = parsed_url.netloc.lower()

        if 'github.com' in host:
            return 'github', self._fetch_github_metadata(url)
        elif 'gitlab.com' in host:
            return 'gitlab', self._fetch_gitlab_metadata(url)
        else:
            raise ValueError("Unsupported repository host.")

    def _fetch_github_metadata(self, repo_url: str) -> dict:
        parsed = urlparse(repo_url)
        owner, repo = parsed.path.strip("/").split("/")[:2]
        api_url = f"https://api.github.com/repos/{owner}/{repo}"

        headers = {"Authorization": f"token {self.token}"} if self.token else {}

        response = self.session.get(api_url, headers=headers)
        response.raise_for_status()

        data = response.json()
        license_key = data.get("license", {}).get("key")

        if license_key:
            data["license"] = {"url": f"https://spdx.org/licenses/{license_key.upper()}"}
        return data

    def _fetch_gitlab_metadata(self, repo_url: str) -> dict:
        parsed = urlparse(repo_url)
        host = f"{parsed.scheme}://{parsed.netloc}"
        path = parsed.path.strip("/")

        if not self.token:
            raise ValueError("GitLab access requires a token.")
        gl = gitlab.Gitlab(host, private_token=self.token)

        project = get_gitlab_project(gl, path)
        license_url = extract_gitlab_license(gl, project.id, self.spdx_licenses)
        contributors = get_gitlab_contributors(project)

        metadata = {
            "@context": "https://doi.org/10.5063/schema/codemeta-2.0",
            "@type": "SoftwareSourceCode",
            "name": project.name,
            "description": project.description,
            "codeRepository": project.http_url_to_repo,
            "url": project.web_url,
            "issueTracker": f"{project.web_url}/-/issues",
            "license": license_url,
            "dateCreated": self._parse_date(project.created_at),
            "dateModified": self._parse_date(project.last_activity_at),
            "keywords": project.topics or [],
            "programmingLanguage": list(project.languages().keys()),
            "downloadUrl": project.http_url_to_repo,
            "author": [{"@type": "Person", "name": project.namespace.get('name', ''), "email": ""}],
            "contributor": contributors,
            "readme": project.readme_url,
        }
        return metadata

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[str]:
        return date_str.split('T')[0] if date_str else None
