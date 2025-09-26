def test_get_data_missing_params(client):
    """Test /get_data with missing required parameters."""
    response = client.get("/api/get_data")
    assert response.status_code == 400
    assert response.get_json() == {"error": "Missing required parameters"}


def test_get_global_sum_invalid_time_group(client):
    """Test /get_global_sum with an invalid time group."""
    response = client.get("/api/get_global_sum?model=test_model&time_group=invalid")
    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Invalid time_group, use year, month, or day"
    }
