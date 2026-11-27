import pytest


class FakeResponse:
    def __init__(self, status=200, json_body=None, content=b"", headers=None):
        self.status_code = status
        self._json = json_body
        self.content = content
        self.text = str(json_body) if json_body is not None else ""
        self.headers = headers or {}

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class FakeSession:
    """Records requests and answers from a route table."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def request(self, method, url, **kw):
        self.calls.append((method, url, kw))
        for (m, suffix), resp in self.routes.items():
            if m == method and url.split("?")[0].endswith(suffix):
                return resp(kw) if callable(resp) else resp
        return FakeResponse(404, {"detail": "no route"})

    def post(self, url, **kw):
        return self.request("POST", url, **kw)


PROFILES = [
    {"id": "me", "name": "My voice", "kind": "clone", "verified_own_voice": 1, "consent_recorded_at": 1.0},
    {"id": "robot", "name": "Robot", "kind": "design", "verified_own_voice": 0},
    {"id": "celeb", "name": "Someone else", "kind": "clone", "verified_own_voice": 0},
    {"id": "legacy", "name": "Legacy", "kind": None, "verified_own_voice": 0},
]


@pytest.fixture
def profiles():
    return [dict(p) for p in PROFILES]


@pytest.fixture(autouse=True)
def mischief_home(tmp_path, monkeypatch):
    monkeypatch.setenv("MISCHIEF_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("VOICESTUDIO_URL", raising=False)
    monkeypatch.delenv("VOICESTUDIO_API_KEY", raising=False)
    return tmp_path / "home"
