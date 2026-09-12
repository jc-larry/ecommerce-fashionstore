import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_filter_options_endpoint():
    """Valida que el endpoint /filter-options devuelva la estructura de filtros facetados."""
    response = client.get("/api/v1/catalog/filter-options")
    assert response.status_code == 200, response.text
    data = response.json()
    assert "min_price" in data
    assert "max_price" in data
    assert "categories" in data
    assert "sizes" in data
    assert "colors" in data
    assert "branches" in data
    assert isinstance(data["categories"], list)
    assert isinstance(data["branches"], list)

def test_product_search_basic():
    """Valida la búsqueda paginada y facetada en /products/search."""
    response = client.get("/api/v1/catalog/products/search?page=1&limit=6")
    assert response.status_code == 200, response.text
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "limit" in data
    assert "total_pages" in data
    assert data["page"] == 1
    assert data["limit"] == 6

def test_product_search_with_filters():
    """Valida que la búsqueda acepte filtros combinados."""
    # Búsqueda por rango de precio
    response = client.get("/api/v1/catalog/products/search?min_price=10&max_price=500&sort_by=price_asc")
    assert response.status_code == 200, response.text
    data = response.json()
    items = data["items"]
    # Verificar que los items cumplan con el rango o estén ordenados
    for item in items:
        assert item["base_price"] >= 10
        assert item["base_price"] <= 500

def test_branch_availability_not_found():
    """Valida error 404 para prenda inexistente en /branch-availability."""
    response = client.get("/api/v1/catalog/products/999999/branch-availability")
    assert response.status_code == 404
