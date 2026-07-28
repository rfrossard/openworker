import base64
from types import SimpleNamespace

from coworker.tools.image_generation import make_generate_image_tool


PNG = b"\x89PNG\r\n\x1a\n" + b"test-payload"


class _Images:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


class _Client:
    def __init__(self, images):
        self.images = images


class _Secrets:
    def get(self, _key):
        return {}


def _response(payload=PNG):
    return SimpleNamespace(
        data=[SimpleNamespace(b64_json=base64.b64encode(payload).decode())],
        usage=SimpleNamespace(input_tokens=12, output_tokens=34),
    )


def test_generate_image_writes_png_atomically_inside_workspace(tmp_path):
    images = _Images(_response())
    tool = make_generate_image_tool(
        _Secrets(), workspace=tmp_path, client=_Client(images)
    )

    result = tool(
        prompt="An editorial illustration of a secure research workflow",
        path="reports/assets/workflow.png",
        size="1536x1024",
        quality="medium",
    )

    assert result["ok"] is True
    assert (tmp_path / result["path"]).read_bytes() == PNG
    assert result["operation_usage"]["type"] == "image"
    assert result["operation_usage"]["units"] == 1
    assert images.calls[0]["model"] == "gpt-image-1.5"


def test_generate_image_rejects_escape_and_invalid_output(tmp_path):
    valid = make_generate_image_tool(
        _Secrets(), workspace=tmp_path, client=_Client(_Images(_response()))
    )
    assert valid(prompt="x", path="../outside.png")["ok"] is False
    assert valid(prompt="x", path="/tmp/outside.png")["ok"] is False

    invalid = make_generate_image_tool(
        _Secrets(),
        workspace=tmp_path,
        client=_Client(_Images(_response(b"not a png"))),
    )
    result = invalid(prompt="x", path="reports/assets/bad.png")
    assert result == {"ok": False, "error": "The image provider did not return a PNG."}
    assert not (tmp_path / "reports/assets/bad.png").exists()


def test_generate_image_redacts_provider_error_details(tmp_path):
    tool = make_generate_image_tool(
        _Secrets(),
        workspace=tmp_path,
        client=_Client(_Images(error=RuntimeError("Authorization: Bearer secret"))),
    )

    result = tool(prompt="x", path="reports/assets/fail.png")

    assert result == {
        "ok": False,
        "error": "Image generation failed (RuntimeError).",
    }
    assert "secret" not in str(result)
