import pytest
from django.urls import reverse

@pytest.mark.django_db
def test_example_view(client):
    response = client.get(reverse('example_view'))
    assert response.status_code == 200
    assert 'Example' in response.content.decode()