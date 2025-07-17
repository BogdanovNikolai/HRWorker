import pytest
from unittest.mock import patch, MagicMock
from api.hh.main import HHApiClient
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def mock_hh_response(items):
    return {"found": len(items), "items": items}

@pytest.fixture
def hh_client():
    return HHApiClient()

def test_search_phrase_in_quotes(hh_client):
    with patch.object(hh_client, 'get_all_resumes') as mock_search:
        mock_search.return_value = mock_hh_response([
            {"id": "1", "title": "Калибровка пищевых весов", "description": "Калибровка Пищевые весы"},
        ])
        result = hh_client.get_all_resumes('Калибровка AND "Пищевые весы"', region=["1"])
        assert result["found"] == 1
        assert any("Пищевые весы" in r["description"] for r in result["items"])

def test_search_minus_word(hh_client):
    with patch.object(hh_client, 'get_all_resumes') as mock_search:
        mock_search.return_value = mock_hh_response([
            {"id": "2", "title": "Калибровка весов", "description": "Калибровка весов"},
        ])
        result = hh_client.get_all_resumes('Калибровка -электронные', region=["1"])
        assert result["found"] == 1
        assert all("электронные" not in r["description"] for r in result["items"])

def test_search_and_or(hh_client):
    with patch.object(hh_client, 'get_all_resumes') as mock_search:
        mock_search.return_value = mock_hh_response([
            {"id": "3", "title": "Калибровка весов", "description": "Калибровка весов"},
            {"id": "4", "title": "Пищевые весы", "description": "Пищевые весы"},
        ])
        result = hh_client.get_all_resumes('Калибровка OR "Пищевые весы"', region=["1"])
        assert result["found"] == 2
        titles = [r["title"] for r in result["items"]]
        assert "Калибровка весов" in titles
        assert "Пищевые весы" in titles 