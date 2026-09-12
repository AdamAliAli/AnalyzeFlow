import pytest


@pytest.fixture
def bad_html() -> str:
    return """<!doctype html><html><head><title>Damascus Restaurant</title></head>
    <body><h1>Welcome</h1><h1>Our Food</h1><p>We serve food.</p>
    <img src="/a.jpg"><img src="/b.jpg"></body></html>"""


@pytest.fixture
def good_html() -> str:
    return """<!doctype html><html lang="en"><head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Damascus Restaurant - Levantine Home Cooking</title>
    <meta name="description" content="Authentic Levantine food delivered hot.">
    <meta property="og:title" content="Damascus Restaurant">
    <meta property="og:description" content="Levantine home cooking.">
    <link rel="icon" href="/favicon.ico">
    <script src="https://www.googletagmanager.com/gtag/js?id=G-X"></script>
    <script type="application/ld+json">{"@type":"Restaurant"}</script>
    </head><body>
    <h1>Authentic Levantine home cooking, delivered hot to your door</h1>
    <a class="btn" href="/order">Order now</a>
    <h2>Menu</h2><h2>Delivery</h2>
    <p>Call +60 3 1234 5678 or email orders@damascus.example to order today.</p>
    <img src="/dish.jpg" alt="A plate of mezze">
    <form action="/subscribe" method="post"><input type="email" name="email"></form>
    <a href="https://instagram.com/damascus">Instagram</a>
    </body></html>"""
