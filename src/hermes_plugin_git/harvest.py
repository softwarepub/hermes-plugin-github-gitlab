import logging
import os
import pathlib
import typing as t

from pydantic import BaseModel
import subprocess
import shutil

from hermes.commands.harvest.base import HermesHarvestCommand, HermesHarvestPlugin

from hermes_plugin_git.util.git_contributor_data import ContributorData
from hermes_plugin_git.util.git_node_register import NodeRegister


# TODO: can and should we get this somehow?
SHELL_ENCODING = 'utf-8'

_GIT_SEP = '|'
_GIT_FORMAT = ['%aN', '%aE', '%aI', '%cN', '%cE', '%cI']
_GIT_ARGS = []


# TODO The following code contains a lot of duplicate implementation that can be found in hermes.model
#      (In fact, it was kind of the prototype for lots of stuff there.)
#      Clean up and refactor to use hermes.model instead

class GitHarvestSettings(BaseModel):
    from_branch: str = 'HEAD'


class GitHarvestPlugin(HermesHarvestPlugin):
    settings_class = GitHarvestSettings

    def __init__(self):
        self.git_exe = shutil.which('git')
        if not self.git_exe:
            raise RuntimeError('Git not available!')

    def _run_git(self, subcommand: str, *args: str) -> t.TextIO:
        proc = subprocess.run([self.git_exe, subcommand, *args, *_GIT_ARGS], capture_output=True)
        if proc.returncode != 0:
            # TODO better suited exception with stdout / stderr output
            raise RuntimeError(f"`git {subcommand}` command failed with code {proc.returncode}")
        return proc.stdout

    def __call__(self, command: HermesHarvestCommand):
        """Implementation of a harvester that provides autor data from Git."""

        git_authors = NodeRegister(ContributorData, 'email', 'name', email=str.upper)
        git_committers = NodeRegister(ContributorData, 'email', 'name', email=str.upper)

        path = command.args.path
        old_path = pathlib.Path.cwd()
        if path != old_path:
            os.chdir(path)

        stdout = self._run_git("rev-parse", "--abbrev-ref", command.settings.git.from_branch)
        git_branch = stdout.decode(SHELL_ENCODING).strip()

        # TODO: should we warn or error if the HEAD is detached?

        stdout = self._run_git("log", f"--pretty={_GIT_SEP.join(_GIT_FORMAT)}")
        git_log = stdout.decode(SHELL_ENCODING).split('\n')

        for line in git_log:
            try:
                # a = author, c = committer
                a_name, a_email, a_timestamp, c_name, c_email, c_timestamp = line.split(_GIT_SEP)
            except ValueError:
                continue

            git_authors.update(email=a_email, name=a_name, timestamp=a_timestamp, role=None)
            git_committers.update(email=c_email, name=c_name, timestamp=c_timestamp, role=None)

        git_contributors = self._merge_contributors(git_authors, git_committers)
        self._audit_contributors(git_contributors, logging.getLogger('audit.git'))

        data = dict()
        data.update({"contributor": [contributor.to_codemeta() for contributor in git_contributors._all]})
        data.update({"hermes:gitBranch": git_branch})

        return data, {"gitBranch": git_branch}

    def _audit_contributors(self, contributors, audit_log: logging.Logger):
        # Collect all authors that have ambiguous data
        unmapped_contributors = [a for a in contributors._all if len(a.email) > 1 or len(a.name) > 1]

        if unmapped_contributors:
            # Report to the audit about our findings
            audit_log.warning('!!! warning "You have unmapped contributors in your Git history."')
            for contributor in unmapped_contributors:
                if len(contributor.email) > 1:
                    audit_log.info("    - %s has alternate email: %s", str(contributor),
                                   ', '.join(contributor.email[1:]))
                if len(contributor.name) > 1:
                    audit_log.info("    - %s has alternate names: %s", str(contributor),
                                   ', '.join(contributor.name[1:]))
            audit_log.warning('')

            audit_log.info(
                "Please consider adding a `.maillog` file to your repository to disambiguate these contributors.")
            audit_log.info('')
            audit_log.info('``` .mailmap')

            audit_log.info('```')

    def _merge_contributors(self, git_authors: NodeRegister, git_committers: NodeRegister) -> NodeRegister:
        """
        Merges the git authors and git committers :py:class:`NodeRegister` and assign the respective roles for each node.
        """
        git_contributors = NodeRegister(ContributorData, 'email', 'name', email=str.upper)
        for author in git_authors._all:
            git_contributors.update(email=author.email[0], name=author.name[0], timestamp=author.timestamp,
                                    role='git author')

        for committer in git_committers._all:
            git_contributors.update(email=committer.email[0], name=committer.name[0], timestamp=committer.timestamp,
                                    role='git committer')

        return git_contributors