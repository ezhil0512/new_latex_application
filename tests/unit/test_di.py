"""Unit tests for the DI container and adapter caching."""

from new_latex_app.infrastructure.di import Container
from new_latex_app.infrastructure.adapters.paddle_ocr import PaddleOcrTextRecognizer
from new_latex_app.infrastructure.adapters.pix2text_math_ocr import Pix2TextMathOcrRecognizer


def test_di_container_reuses_recognizers() -> None:
    """The DI container should cache and reuse PaddleOCR and Pix2Text recognizer instances."""
    container = Container.bootstrap()
    pipeline_1 = container.document_pipeline()
    pipeline_2 = container.document_pipeline()

    # Extract routers
    router_1 = pipeline_1.model_router
    router_2 = pipeline_2.model_router

    # Retrieve list of recognizers
    recognizers_1 = router_1._recognizers
    recognizers_2 = router_2._recognizers

    # Find the PaddleOCR instances
    paddle_1 = next(r for r in recognizers_1 if isinstance(r, PaddleOcrTextRecognizer))
    paddle_2 = next(r for r in recognizers_2 if isinstance(r, PaddleOcrTextRecognizer))

    # Find the Pix2Text instances
    pix_1 = next(r for r in recognizers_1 if isinstance(r, Pix2TextMathOcrRecognizer))
    pix_2 = next(r for r in recognizers_2 if isinstance(r, Pix2TextMathOcrRecognizer))

    assert paddle_1 is paddle_2, "PaddleOCR recognizer instance was not cached/reused"
    assert pix_1 is pix_2, "Pix2Text recognizer instance was not cached/reused"
