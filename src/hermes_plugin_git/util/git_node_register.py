import typing as t


class NodeRegister:
    """
    Helper class to unify Git commit authors and committers.

    This class keeps track of all registered instances and merges two :py:class:`ContributorData` instances if some
    attributes match.
    """

    def __init__(self, cls, *order, **mapping):
        """
        Initalize a new register.

        :param cls: Type of objects to store.
        :param order: The order of attributes to compare.
        :param mapping: A mapping to convert attributes (will be applied for comparison).
        """
        self.cls = cls
        self.order = order
        self.mapping = mapping
        self._all = []
        self._node_by = {key: {} for key in self.order}

    def add(self, node: t.Any):
        """
        Add (or merge) a new node to the register.
        :param node: The node that should be added.
        """
        self._all.append(node)

        for key in self.order:
            mapping = self.mapping.get(key, lambda x: x)
            attr = getattr(node, key, None)
            match attr:
                case None:
                    continue
                case list():
                    for value in attr:
                        self._node_by[key][mapping(value)] = node

    def update(self, **kwargs):
        """
        Add (or merge) a new item to the register with the given attribute values.

        :fixme: This is not a good implementation strategy at all.

        :param kwargs: The attribute values to be stored.
        """
        missing = []
        tail = list(self.order)
        while tail:
            key, *tail = tail
            if key not in kwargs:
                continue

            arg = kwargs[key]
            node = self._node_by[key].get(arg, None)
            if node is None:
                missing.append((key, arg))
                continue

            node.update(**kwargs)
            break
        else:
            node = self.cls(**kwargs)
            self._all.append(node)

        for key in tail:
            if key not in kwargs:
                continue

            arg = kwargs[key]
            alt_node = self._node_by[key].get(arg, None)
            if alt_node is None:
                missing.append((key, arg))

            elif alt_node != node:
                node.merge(alt_node)
                self._all.remove(alt_node)
                self._node_by[key][arg] = node

        for key, arg in missing:
            self._node_by[key][arg] = node
