import unittest

from gmail_daemon.tasks import resolve_tasklist_id


class _Execute:
    def __init__(self, response):
        self.response = response

    def execute(self):
        return self.response


class _TaskLists:
    def __init__(self, list_response):
        self.list_response = list_response

    def list(self, maxResults):
        return _Execute(self.list_response)

    def insert(self, body):
        return _Execute({"id": "created-list-id", "title": body["title"]})


class _Service:
    def __init__(self, list_response):
        self.list_response = list_response

    def tasklists(self):
        return _TaskLists(self.list_response)


class TasksTests(unittest.TestCase):
    def test_uses_configured_tasklist_id(self) -> None:
        tasklist_id = resolve_tasklist_id(_Service({"items": []}), "custom-list")

        self.assertEqual("custom-list", tasklist_id)

    def test_resolves_default_to_first_tasklist(self) -> None:
        tasklist_id = resolve_tasklist_id(_Service({"items": [{"id": "first-list"}]}), "@default")

        self.assertEqual("first-list", tasklist_id)

    def test_creates_tasklist_if_none_exist(self) -> None:
        tasklist_id = resolve_tasklist_id(_Service({"items": []}), "@default")

        self.assertEqual("created-list-id", tasklist_id)


if __name__ == "__main__":
    unittest.main()
