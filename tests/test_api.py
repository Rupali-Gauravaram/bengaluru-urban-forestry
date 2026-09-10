from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_zones_returns_all8_bbmp_zones():
    '''There are only 8 zones in the BBMP dataset used, but a spelling difference caused the API to return 9 zones.
    This is a regression test to ensure the the bug was fixed and now API returns only 8 zones.'''

    # Act
    response = client.get("/zones")

    # Assert
    assert response.status_code == 200

    zones = response.json()
    assert len(zones) == 8

    # assert that every zone is accounted for, none double-counted
    assert sum(z["ward_count"] for z in zones) == 198

    # check that no zone carries stray whitespaces
    for z in zones:
        assert z['Zone'].strip() == z['Zone']

def test_health_status_okay():
    '''This test ensures that the health status is okay'''
    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"status":"ok"}

def test_top_0or51_wards_input_error():
    '''This is an edge case that tests whether the API generates error when input is less that 1 or greater than 50'''

    # ACt
    response1 = client.get("/wards/rankings/top?n=0")
    response2 = client.get("/wards/rankings/top?n=51")
    # Assert 
    assert response1.status_code == 422
    assert response2.status_code == 422

def test_top_3_wards():
    '''This is an edge case that tests whether the top three ranked wards are returned'''

    # ACt
    response = client.get("/wards/rankings/top?n=3")
    data = response.json()

    # Assert 
    assert response.status_code == 200
    assert len(data) == 3
    assert data[0]['city_rank'] == 1
    assert data[0]['Ward_Name'] == 'Halsoor'
    assert [d['city_rank'] for d in data] == [1,2,3]

def test_unreal_wards_404():
    '''This test ensures that the API returns 404 for wards that are not in the dataset'''
    # Act 
    response = client.get("/wards/NotARealWard")

    # Assert
    assert response.status_code == 404
    assert response.json()['detail'] == "Ward not found"

    

    