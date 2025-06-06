import re
import base64
import logging
from typing import Optional, List, Dict, Tuple
import gitlab

logger = logging.getLogger(__name__)


def get_gitlab_project(gl: gitlab.Gitlab, path: str):
    """
    Retrieve a GitLab project by its path.

    Args:
        gl (gitlab.Gitlab): Authenticated GitLab client instance.
        path (str): Path of the project (e.g., 'group/project').

    Returns:
        Project object if found.

    Raises:
        ValueError: If the project is not found or access is denied.
    """
    try:
        return gl.projects.get(path)
    except Exception as e:
        raise ValueError(f"Project not found or access denied: {e}")


def extract_gitlab_license(gl_client: gitlab.Gitlab, project_id: int, spdx_licenses: Dict[str, str]) -> Optional[str]:
    """
    Extract and match the license of a GitLab project to an SPDX license.

    Args:
        gl_client (gitlab.Gitlab): Authenticated GitLab client instance.
        project_id (int): ID of the GitLab project.
        spdx_licenses (Dict[str, str]): Mapping of license names to SPDX identifiers.

    Returns:
        Optional[str]: SPDX license URL if a match is found, otherwise None.
    """
    try:
        project = gl_client.projects.get(project_id)
        default_branch = project.default_branch
        license_file = find_license_file(project, default_branch)

        if not license_file:
            logger.warning("No license file found in repo.")
            return None

        file_obj = project.files.get(file_path=license_file, ref=default_branch)
        decoded_content = base64.b64decode(file_obj.content).decode('utf-8')
        license_name = get_license_name(decoded_content)

        return match_spdx_license(license_name, spdx_licenses)
    except Exception as e:
        logger.error(f"Failed to fetch license: {e}")
        return None


def find_license_file(project, branch: str) -> Optional[str]:
    """
    Search for a license file in the root directory of a project's repository.

    Args:
        project: GitLab project object.
        branch (str): Branch name to search in.

    Returns:
        Optional[str]: Path to the license file if found, otherwise None.
    """
    license_patterns = re.compile(r'^(LICENSE|COPYING|UNLICENSE|EULA|COPYRIGHT)(\..+)?$', re.IGNORECASE)
    page = 1
    while True:
        files = project.repository_tree(path='', ref=branch, per_page=100, page=page)
        if not files:
            break
        for file_info in files:
            if file_info['type'] == 'blob' and license_patterns.match(file_info['name']):
                return file_info['path']
        page += 1
    return None


def get_license_name(content: str) -> str:
    """
    Extract the license name from the first non-empty line of a license file.

    Args:
        content (str): Decoded content of the license file.

    Returns:
        str: license name or empty string if not found.
    """
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    return lines[0].upper() if lines else ""


def match_spdx_license(license_name: str, spdx_licenses: Dict[str, str]) -> Optional[str]:
    """
    Match a license name to an SPDX identifier.

    Args:
        license_name (str): Name of the license extracted from the file.
        spdx_licenses (Dict[str, str]): Mapping of license names to SPDX identifiers.

    Returns:
        Optional[str]: SPDX license URL if a match is found, otherwise None.
    """
    for spdx_name, license_id in spdx_licenses.items():
        if license_name in spdx_name or spdx_name in license_name:
            return f"https://spdx.org/licenses/{license_id}.html"
    logger.warning(f"No matching SPDX license found for: {license_name}")
    return None


def get_gitlab_contributors(project) -> List[Dict]:
    """
    Retrieve the list of contributors for a GitLab project.

    Args:
        project: GitLab project object.

    Returns:
        List[Dict]: List of contributors formatted with type, given name, family name, and email.
    """
    contributors = []
    try:
        for contributor in project.repository_contributors(all=True):
            full_name = contributor.get('name', '')
            email = contributor.get('email', '')
            given_name, family_name = split_name(full_name)
            contributors.append({
                "@type": "Person",
                "givenName": given_name,
                "familyName": family_name,
                "email": email
            })
    except Exception as e:
        logger.error(f"Failed to fetch contributors: {e}")
    return contributors


def split_name(name: str) -> Tuple[str, str]:
    """
    Split a full name into given name and family name.

    Args:
        name (str): Full name.

    Returns:
        Tuple[str, str]: Given name and family name. If the name has no spaces, family name is empty.
    """
    if ' ' in name:
        parts = name.rsplit(' ', 1)
        return parts[0], parts[1]
    return name, ""
