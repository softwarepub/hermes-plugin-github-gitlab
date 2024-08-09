import typing as t


class ContributorData:
    """
    Stores contributor data information from Git history.
    """

    def __init__(self, name: str | t.List[str], email: str | t.List[str], timestamp: str | t.List[str],
                 role: str | t.List[str]):
        """
        Initialize a new contributor dataset.

        :param name: Name as returned by the `git log` command (i.e., with `.mailmap` applied).
        :param email: Email address as returned by the `git log` command (also with `.mailmap` applied).
        :param timestamp: Timestamp when the respective commit was done.
        :param role: Role that the contributor fulfills for the respective commit.
        """
        self.name = []
        self.email = []
        self.timestamp = []
        self.role = []

        self.update(name=name, email=email, timestamp=timestamp, role=role)

    def __str__(self):
        parts = []
        if self.name:
            parts.append(self.name[0])
        if self.email:
            parts.append(f'<{self.email[0]}>')
        return f'"{" ".join(parts)}"'

    def _update_attr(self, target, value, unique=True):
        match value:
            case list():
                target.extend([v for v in value if not unique or v not in target])
            case str() if not unique or value not in target:
                target.append(value)

    def update(self, name=None, email=None, timestamp=None, role=None):
        """
        Update the current contributor with the given data.

        :param name: New name to assign (addtionally).
        :param email: New email to assign (additionally).
        :param timestamp: New timestamp to adapt time range.
        """
        self._update_attr(self.name, name)
        self._update_attr(self.email, email)
        self._update_attr(self.timestamp, timestamp, unique=False)
        self._update_attr(self.role, role)

    def merge(self, other: 'ContributorData'):
        """
        Merge another :py:class:`ContributorData` instance into this one.

        All attributes will be merged yet kept unique if required.

        :param other: The other instance that should contribute to this.
        """
        self.name += [n for n in other.name if n not in self.name]
        self.email += [e for e in other.email if e not in self.email]
        self.timestamp += other.timestamp
        self.role += [r for r in other.role if r not in self.role]

    def to_codemeta(self) -> dict:
        """
        Return the current dataset as CodeMeta.

        :return: The CodeMeta representation of this dataset.
        """
        # Person as type is fine even for bots, as they need to have emails,
        # and the Person type can be a fictional person in schema.org.
        res = {
            '@type': 'Person',
        }

        if self.name:
            res['name'] = self.name.pop()
        if self.name:
            res['alternateName'] = list(self.name)

        if self.email:
            res['email'] = self.email.pop(0)
        if self.email:
            res['contactPoint'] = [{'@type': 'ContactPoint', 'email': email} for email in self.email]

        if self.role:
            if self.timestamp:
                timestamp_start, *_, timestamp_end = sorted(self.timestamp + [self.timestamp[0]])
                res['hermes:contributionRole'] = [
                    {'@type': 'Role', 'roleName': role, 'startTime': timestamp_start, 'endTime': timestamp_end}
                    for role in self.role]
            else:
                res['hermes:contributionRole'] = [{'@type': 'Role', 'roleName': role} for role in self.role]

        return res
