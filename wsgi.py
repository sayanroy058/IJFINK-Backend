import os

from app import create_app
from config import ProductionConfig


if not os.getenv("SECRET_KEY"):
    raise RuntimeError(
        "SECRET_KEY environment variable must be set before starting the "
        "production server. Refusing to start with an insecure default."
    )


app = create_app(ProductionConfig)
