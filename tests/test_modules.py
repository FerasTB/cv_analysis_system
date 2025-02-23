import sys
import os

# Add the project root directory to the sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from flask import Flask
from modules.chatbot import chat_bp


@pytest.fixture
def client():
    """
    Pytest fixture to create a Flask test client.
    """
    app = Flask(__name__)
    # Secret key for session usage
    app.secret_key = "test_secret_key"
    app.register_blueprint(chat_bp)

    with app.test_client() as test_client:
        yield test_client


def test_chatbot_get(client):
    """
    Test that the /chatbot route loads correctly.
    """
    response = client.get("/chatbot")
    assert response.status_code == 200
    assert b"Chatbot & CV Upload Interface" in response.data


def test_send_message_empty(client):
    """
    Test sending an empty message returns error 400.
    """
    response = client.post("/send_message", json={"message": ""})
    assert response.status_code == 400
    assert b"Empty message" in response.data


def test_upload_cv_no_file(client):
    """
    Test uploading a CV with no file provided returns error 400.
    """
    response = client.post("/upload_cv", data={})
    assert response.status_code == 400
    assert b"No file uploaded" in response.data
