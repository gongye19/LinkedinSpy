from fastapi.testclient import TestClient

from app.db import create_session_factory, init_db
from app.main import create_app


def test_keyword_settings_can_be_saved_and_loaded(tmp_path):
    session_factory = create_session_factory(f"sqlite:///{tmp_path / 'jobs.db'}")
    init_db(session_factory.engine)
    app = create_app(session_factory=session_factory)
    client = TestClient(app)

    update_response = client.put(
        "/api/settings/keywords",
        json={"keywords": ["ai engineer", "llm", "rag", "data scientist"]},
    )
    assert update_response.status_code == 200
    assert update_response.json()["keywords"] == ["ai engineer", "llm", "rag", "data scientist"]

    get_response = client.get("/api/settings/keywords")
    assert get_response.status_code == 200
    assert get_response.json()["keywords"] == ["ai engineer", "llm", "rag", "data scientist"]


def test_keyword_settings_reject_more_than_four(tmp_path):
    session_factory = create_session_factory(f"sqlite:///{tmp_path / 'jobs.db'}")
    init_db(session_factory.engine)
    app = create_app(session_factory=session_factory)
    client = TestClient(app)

    response = client.put(
        "/api/settings/keywords",
        json={"keywords": ["a", "b", "c", "d", "e"]},
    )
    assert response.status_code == 400
