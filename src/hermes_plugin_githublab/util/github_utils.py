import requests
import re
from urllib.parse import urlparse 


def parse_repo_url(url: str):
    """
    Parses a GitHub repository URL and extracts the owner and repository name.

    Args:
        url (str): The GitHub repository URL. Expected format: 'https://github.com/owner/repo'.

    Returns:
        tuple: A tuple containing the owner and repository name as strings.

    Raises:
        ValueError: If the URL does not match the expected GitHub repository format.
    """
    parsed = urlparse(url)
    parts = parsed.path.strip('/').split('/')
    if len(parts) >= 2:
        return parts[0], parts[1]
    raise ValueError("Invalid GitHub URL. Expected format: https://github.com/owner/repo")


def get_contributors_from_repo(url: str, token: str = None):
    """
    Fetch a list of contributors from a GitHub repository.

    Args:
        url (str): The GitHub repository URL.
        token (str, optional): GitHub API token for authenticated requests. Defaults to None.

    Returns:
        list: A sorted list of contributors with givenName, familyName, and email.
    """
    
    headers = {"Authorization": f"token {token}"} if token else {}
    owner, repo = parse_repo_url(url)
    
    api_url_commits = f"https://api.github.com/repos/{owner}/{repo}/commits"
        
    all_commits = []
    page = 1
    max_pages = 10
    
    while page <= max_pages:
        response = requests.get(f"{api_url_commits}?per_page=100&page={page}", headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"Failed to retrieve commit history: {response.status_code}")
            print(response.text)
            return []
        
        try:
            commit_data = response.json()
        except ValueError:
            print("Could not decode JSON")
            print(response.text)
            return []

        if not commit_data:
            break

        all_commits.extend(commit_data)
        page += 1

    metadata = []
    seen_emails = set()

    for commit in all_commits:
        if "commit" in commit and "author" in commit["commit"]:
            contributor_name = commit["commit"]["author"].get("name")
            contributor_email = commit["commit"]["author"].get("email")

            if contributor_name and contributor_email:
                contributor_email = contributor_email.lower()
                if contributor_email not in seen_emails:
                    cleaned_name = re.sub(r'[^a-zA-Z\s]', '', contributor_name)
                    name_parts = cleaned_name.split()
                    given_name = name_parts[0]
                    family_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

                    metadata.append({
                        "@type": "Person",
                        "givenName": given_name,
                        "familyName": family_name,
                        "email": contributor_email
                    })
                    seen_emails.add(contributor_email)
                    
    contributors = sorted(metadata, key=lambda x: x['givenName'].lower())
    return contributors

    
def fetch_readme(url: str, token: str = None) -> str | None:
    """
    Fetch the README file download URL from a GitHub repository.

    Args:
        url (str): The GitHub repository URL.
        token (str, optional): GitHub personal access token.

    Returns:
        str or None: The download URL of the README file if found, otherwise None.
    """

    owner, repo = parse_repo_url(url)
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents"
    
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token is None:
        token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    
    response = requests.get(api_url, headers=headers, timeout=10)
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch contents for repo {url}: {response.status_code} - {response.text}")
    
    for item in response.json():
        if item["name"].lower().startswith("readme"):
            return item["download_url"]
    return None


def generate_github_download_url(url: str, token: str = None) -> str:
    """
    Generate a download URL for a GitHub repository's default branch using the GitHub API.
    Falls back to unauthenticated access if no token is provided.

    Args:
        url (str): GitHub repository URL (e.g., https://github.com/owner/repo)
        token (str, optional): GitHub personal access token (PAT). Defaults to None.

    Returns:
        str: Direct ZIP download URL for the default branch.
    """
    # Clean the URL
    url = url.rstrip('/')
    if url.endswith('.git'):
        url = url[:-4]

    parsed = urlparse(url)
    path_parts = parsed.path.strip('/').split('/')

    if len(path_parts) < 2:
        raise ValueError("Invalid GitHub URL. Expected format: https://github.com/owner/repo")

    owner, repo = parse_repo_url(url)
    
    # Preparing headers with or without token
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    # Calling GitHub API
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    response = requests.get(api_url, headers=headers, timeout=10)

    if response.status_code == 200:
        repo_info = response.json()
        default_branch = repo_info.get("default_branch", "main")
    elif response.status_code == 403 and "X-RateLimit-Remaining" in response.headers and response.headers["X-RateLimit-Remaining"] == "0":
        raise RuntimeError("Rate limit exceeded. Provide a GitHub token to increase limits.")
    elif response.status_code == 404:
        raise RuntimeError("Repository not found or it's private. Provide a valid GitHub token.")
    else:
        raise RuntimeError(f"GitHub API error: {response.status_code} - {response.text}")

    # Building and returning the ZIP download URL
    download_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{default_branch}.zip"
    return download_url


class CodeMetaBuilder:
    """
    Class to build a CodeMeta-based metadata dictionary for a GitHub repository.

    Attributes:
        repo_data (dict): The repository metadata from the GitHub API.
        token (str, optional): GitHub API token for authenticated requests.
    """
    def __init__(self, repo_data: dict, token: str = None):
        self.repo_data = repo_data
        self.token = token

    def build(self) -> dict:
        """
        Build the CodeMeta metadata dictionary.

        Fetches languages, README file, and contributors, and organizes
        them into a dictionary following the CodeMeta.

        Returns:
            dict: A dictionary containing CodeMeta-based metadata, or None if an error occurs.
        """
        headers = {"Authorization": f"token {self.token}"} if self.token else {}
        
        # Fetch language data from the languages_url
        languages_url = self.repo_data['languages_url']
        if languages_url:
            languages_response = requests.get(languages_url, headers=headers, timeout=10)
            languages_response.raise_for_status()
            languages_data = languages_response.json()
            programming_languages = list(languages_data.keys())
        else:
            print(f"Error: 'languages_url' not found in the API response.")
            return None

        repo_url = self.repo_data.get("html_url")
        readme_url = fetch_readme(repo_url, self.token)
        contributors = get_contributors_from_repo(repo_url, self.token) if repo_url else []
        downloadUrl = generate_github_download_url(repo_url, self.token)
        issueTracker = repo_url + '/issues'
        
        metadata_dict = {
            "@context": "https://w3id.org/codemeta/3.0",
            "@type": "SoftwareSourceCode",
            "name": self.repo_data.get("name"),
            "identifier": self.repo_data.get("id"),
            "description": self.repo_data.get("description"),
            "codeRepository": self.repo_data.get("html_url"),
            "url": self.repo_data.get("html_url"),
            "issueTracker": issueTracker,
            "license": self.repo_data.get("license", {}).get("url") if self.repo_data.get("license") else None,
            "programmingLanguage": programming_languages,
            "copyrightHolder": {"@type": "Person", "name": ""},
            "dateCreated": self.repo_data.get("created_at", "")[:10],
            "dateModified": self.repo_data.get("updated_at", "")[:10],
            "datePublished": self.repo_data.get("pushed_at", "")[:10],
            "keywords": self.repo_data.get("topics"),
            "downloadUrl": downloadUrl,
            "contributor": contributors,
            "readme": readme_url,
        }
        
        return metadata_dict
