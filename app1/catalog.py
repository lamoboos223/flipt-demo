from typing import Any

PRODUCTS = [
    {
        "id": 1,
        "name": "Wireless Earbuds Pro",
        "description": "Noise-cancelling earbuds with 30h battery life",
        "price": 79.99,
        "rating": 4.5,
        "image_url": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=400",
        "category": "Electronics",
    },
    {
        "id": 2,
        "name": "Smart Watch Series X",
        "description": "Fitness tracking, heart rate, GPS built-in",
        "price": 199.99,
        "rating": 4.7,
        "image_url": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400",
        "category": "Electronics",
    },
    {
        "id": 3,
        "name": "Organic Coffee Beans",
        "description": "Single-origin medium roast, 2lb bag",
        "price": 18.49,
        "rating": 4.8,
        "image_url": "https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=400",
        "category": "Grocery",
    },
]


def get_product(product_id: int) -> dict[str, Any] | None:
    return next((p for p in PRODUCTS if p["id"] == product_id), None)
