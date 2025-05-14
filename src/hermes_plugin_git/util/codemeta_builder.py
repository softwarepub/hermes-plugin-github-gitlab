import requests
import re


def get_contributors_from_repo(url: str):
    
    github_token = ''
    headers = {"Authorization": f"token {github_token}"} if github_token else {}
    
    # Convert GitHub HTML URL to GitHub API URL
    if url.startswith("https://github.com/"):
        parts = url.replace("https://github.com/", "").strip("/").split("/")
        if len(parts) >= 2:
            owner, repo = parts[0], parts[1]
        else:
            print("Invalid GitHub URL.")
            return []
    else:
        print("Invalid GitHub URL format.")
        return []

    api_url_commits = f"https://api.github.com/repos/{owner}/{repo}/commits"
        
    all_commits = []
    page = 1
    
    while True:
        response = requests.get(f"{api_url_commits}?per_page=100&page={page}", headers=headers)
        
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

    
def fetch_readme(url: str):
    url = url.replace("https://github.com/", "")
    base_url = f"https://api.github.com/repos/{url}/contents"
    response = requests.get(base_url)
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch contents for repo {url}: {response.status_code}")
    
    contents = response.json()
    readme_file = next(
        (item for item in contents if item['name'].lower().startswith('readme')),
        None
    )
    
    if not readme_file:
        return None

    readme_url = readme_file['download_url']
    return readme_url


class CodeMetaBuilder:
    def __init__(self, repo_data: dict):
        self.repo_data = repo_data

    def build(self) -> dict:

        github_token = ''
        headers = {"Authorization": f"token {github_token}"} if github_token else {}
        
        # Fetch language data from the languages_url
        languages_url = self.repo_data['languages_url']
        if languages_url:
            languages_response = requests.get(languages_url, headers=headers)
            languages_response.raise_for_status()
            languages_data = languages_response.json()
            programming_languages = list(languages_data.keys())
        else:
            print(f"Error: 'languages_url' not found in the API response.")
            return None

        repo_url = self.repo_data.get("html_url")
        readme_url = fetch_readme(repo_url)
        contributors = get_contributors_from_repo(repo_url) if repo_url else []
        
        issueTracker = repo_url + '/issues'
        
        metadata_dict = {
            "@context": "https://doi.org/10.5063/schema/codemeta-2.0",
            "@type": "SoftwareSourceCode",
            "name": self.repo_data.get("name"),
            "identifier": self.repo_data.get("id"),
            "description": self.repo_data.get("description"),
            "codeRepository": self.repo_data.get("html_url"),
            "issueTracker": issueTracker,
            "license": self.repo_data.get("license", {}).get("url") if self.repo_data.get("license") else None,
            "programmingLanguage": programming_languages,
            "copyrightHolder": {"@type": "Person", "name": ""},
            "dateCreated": self.repo_data.get("created_at", "")[:10],
            "dateModified": self.repo_data.get("updated_at", "")[:10],
            "datePublished": self.repo_data.get("pushed_at", "")[:10],
            "keywords": self.repo_data.get("topics"),
            "downloadUrl": self.repo_data.get("archive_url"),
            "contributor": contributors,
            "readme": readme_url,
            "author": [{"@type": "Person",
                    "givenName": "",
                    "familyName": "",
                    "email":""
                    }],
        }
        
        return metadata_dict