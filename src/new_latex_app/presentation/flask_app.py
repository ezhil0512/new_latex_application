"""Flask presentation layer for the Image-to-LaTeX Generator."""

from pathlib import Path
from tempfile import mkdtemp
from typing import Any
from uuid import UUID
import logging
import shutil

from flask import Flask, request, send_file, jsonify, after_this_request, render_template, Response
from werkzeug.datastructures import FileStorage

from new_latex_app.application.dto import ProcessDocumentCommand
from new_latex_app.domain.exceptions import NewLatexAppError, UnsupportedInputError
from new_latex_app.infrastructure.di import Container

logger: logging.Logger = logging.getLogger(__name__)


def create_app(container: Container | None = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB max file size

    if container is None:
        container = Container.bootstrap()

    @app.route("/", methods=["GET"])
    def home() -> tuple[Response, int] | str | Response | tuple[str, int]:
        """Return home page information or render the web interface."""
        logger.info("Home page requested")

        # Content negotiation: if text/html is preferred over application/json, render HTML.
        # Otherwise (or if Accept header is missing/unspecified), default to JSON.
        if request.accept_mimetypes:
            best = request.accept_mimetypes.best_match(["application/json", "text/html"])
            if best == "text/html":
                try:
                    return render_template("index.html")
                except Exception as e:
                    logger.error(f"Failed to render index.html template: {e}")
                    return "Failed to load index.html template", 500

        return jsonify({
            "service": "Image-to-LaTeX Generator",
            "version": "1.0",
            "endpoints": {
                "POST /process": "Upload document for processing",
                "GET /download/<session_id>": "Download export package",
                "GET /preview/<session_id>": "Get preview information",
            },
        }), 200

    @app.route("/process", methods=["POST"])
    def process_document() -> tuple[Response, int]:
        """Process an uploaded document."""
        logger.info("Document processing request received")

        if "file" not in request.files:
            logger.warning("No file part in request")
            return jsonify({"error": "No file provided"}), 400

        file: FileStorage = request.files["file"]
        if not file.filename or file.filename == "":
            logger.warning("Empty filename in request")
            return jsonify({"error": "Empty filename"}), 400

        if not _is_supported_format(file.filename):
            logger.warning(f"Unsupported file format: {file.filename}")
            return jsonify({"error": "Unsupported file format. Supported: pdf, png, jpg, jpeg"}), 400

        with container.workspace_manager().create() as upload_session:
            upload_path = upload_session.workspace_path / file.filename
            try:
                file.save(upload_path)
                service = container.document_processing_service()
                command = ProcessDocumentCommand(
                    input_path=upload_path,
                    original_filename=file.filename,
                )
                result = service.process(command)

                session_id_str = str(result.session_id)
                logger.info(f"Processing completed with session_id: {session_id_str}")
                return jsonify({
                    "session_id": session_id_str,
                    "download_url": f"/download/{session_id_str}",
                    "preview_url": f"/preview/{session_id_str}",
                    "status": "completed",
                }), 200
            except UnsupportedInputError as error:
                logger.warning(f"Unsupported input: {error}")
                return jsonify({"error": str(error)}), 400
            except NewLatexAppError as error:
                logger.exception(f"Pipeline error: {error}")
                return jsonify({"error": f"Processing failed: {str(error)}"}), 500
            except Exception as error:
                logger.exception(f"Unexpected error during processing: {error}")
                return jsonify({"error": "Internal server error"}), 500

    @app.route("/download/<session_id>", methods=["GET"])
    def download_export(session_id: str) -> Response | tuple[Response, int]:
        """Download the export package for a session."""
        logger.info(f"Download requested for session: {session_id}")

        try:
            UUID(session_id)
        except ValueError:
            logger.warning(f"Invalid session ID format: {session_id}")
            return jsonify({"error": "Invalid session ID format"}), 400

        service = container.document_processing_service()
        export_path = service.get_export_path(UUID(session_id))

        if export_path is None:
            logger.warning(f"Session not found: {session_id}")
            return jsonify({"error": "Export package not found"}), 404

        if not export_path.exists() or not export_path.is_dir():
            logger.warning(f"Export path not found for session: {session_id}")
            return jsonify({"error": "Export package not found"}), 404

        exam_tex = export_path / "exam.tex"
        if not exam_tex.exists():
            logger.warning(f"exam.tex not found in export package for session: {session_id}")
            return jsonify({"error": "Export package incomplete"}), 500

        try:
            archive_dir = Path(mkdtemp(prefix=f"flask_export_{session_id}_"))
            archive_base = archive_dir / f"export_{session_id}"
            archive_path = Path(shutil.make_archive(str(archive_base), "zip", root_dir=export_path))

            @after_this_request
            def cleanup(response: Response) -> Response:
                try:
                    archive_path.unlink()
                except OSError:
                    pass
                try:
                    shutil.rmtree(archive_dir, ignore_errors=True)
                except OSError:
                    pass
                return response

            return send_file(
                str(archive_path),
                as_attachment=True,
                download_name=f"export_{session_id}.zip",
            ), 200
        except Exception as error:
            logger.exception(f"Download error: {error}")
            return jsonify({"error": "Download failed"}), 500

    @app.route("/preview/<session_id>", methods=["GET"])
    def preview_session(session_id: str) -> tuple[Response, int]:
        """Get preview information for a session."""
        logger.info(f"Preview requested for session: {session_id}")

        try:
            UUID(session_id)
        except ValueError:
            logger.warning(f"Invalid session ID format: {session_id}")
            return jsonify({"error": "Invalid session ID format"}), 400

        service = container.document_processing_service()
        export_path = service.get_export_path(UUID(session_id))

        if export_path is None:
            logger.warning(f"Session not found: {session_id}")
            return jsonify({"error": "Export package not found"}), 404

        if not export_path.exists() or not export_path.is_dir():
            logger.warning(f"Export path not found for session: {session_id}")
            return jsonify({"error": "Export package not found"}), 404

        exam_tex = export_path / "exam.tex"

        preview_data: dict[str, Any] = {
            "session_id": session_id,
            "has_export": exam_tex.exists(),
            "download_url": f"/download/{session_id}",
            "status": "available" if exam_tex.exists() else "missing",
        }

        if exam_tex.exists():
            try:
                with exam_tex.open("r", encoding="utf-8") as f:
                    content = f.read()
                    preview_data["latex_preview"] = content[:1000]
                    preview_data["latex_size"] = len(content)
            except Exception as e:
                logger.warning(f"Failed to read LaTeX preview: {e}")

            # Extract LaTeX document body (between \begin{document} and \end{document}).
            # Use a local regex import to keep changes scoped to this function.
            try:
                import re

                begin_match = re.search(r"\\begin\s*\{\s*document\s*\}", content, re.IGNORECASE)
                end_match = re.search(r"\\end\s*\{\s*document\s*\}", content, re.IGNORECASE)
                if begin_match and end_match and begin_match.end() < end_match.start():
                    latex_body = content[begin_match.end(): end_match.start()].strip()
                else:
                    # Fallback to full content if markers not found or malformed
                    latex_body = content
            except Exception:
                latex_body = content

            preview_data["latex_body"] = latex_body

        assets_dir = export_path / "assets"
        if assets_dir.exists():
            asset_files = list(assets_dir.iterdir())
            preview_data["asset_count"] = len(asset_files)
            preview_data["asset_names"] = [f.name for f in asset_files[:10]]

        return jsonify(preview_data), 200

    @app.route("/preview/<session_id>/assets/<asset_name>", methods=["GET"])
    def get_session_asset(session_id: str, asset_name: str) -> Response | tuple[Response, int]:
        """Get an individual diagram/asset file from a session's workspace."""
        logger.info(f"Asset preview requested: {asset_name} for session: {session_id}")

        try:
            UUID(session_id)
        except ValueError:
            logger.warning(f"Invalid session ID format: {session_id}")
            return jsonify({"error": "Invalid session ID format"}), 400

        # Prevent path traversal
        clean_name = Path(asset_name).name
        if clean_name != asset_name or ".." in asset_name or "/" in asset_name or "\\" in asset_name:
            logger.warning(f"Potential path traversal blocked: {asset_name}")
            return jsonify({"error": "Invalid asset name"}), 400

        service = container.document_processing_service()
        export_path = service.get_export_path(UUID(session_id))

        if export_path is None or not export_path.exists() or not export_path.is_dir():
            logger.warning(f"Export path not found for session: {session_id}")
            return jsonify({"error": "Export package not found"}), 404

        assets_dir = export_path / "assets"
        resolved_path = (assets_dir / clean_name).resolve()
        resolved_assets_dir = assets_dir.resolve()

        # Strict relative check to prevent path traversal
        if not resolved_path.is_relative_to(resolved_assets_dir):
            logger.warning(f"Path traversal detected and blocked: {asset_name}")
            return jsonify({"error": "Access denied"}), 403

        if not resolved_path.exists() or not resolved_path.is_file():
            logger.warning(f"Asset file not found: {resolved_path}")
            return jsonify({"error": "Asset not found"}), 404

        return send_file(str(resolved_path)), 200

    @app.errorhandler(400)
    def bad_request(error: Any) -> tuple[Response, int]:
        """Handle 400 Bad Request errors."""
        return jsonify({"error": "Bad request"}), 400

    @app.errorhandler(404)
    def not_found(error: Any) -> tuple[Response, int]:
        """Handle 404 Not Found errors."""
        return jsonify({"error": "Endpoint not found"}), 404

    @app.errorhandler(500)
    def internal_error(error: Any) -> tuple[Response, int]:
        """Handle 500 Internal Server Error."""
        logger.exception(f"Internal server error: {error}")
        return jsonify({"error": "Internal server error"}), 500

    return app


def _is_supported_format(filename: str) -> bool:
    """Check if the filename has a supported extension."""
    supported = {".pdf", ".png", ".jpg", ".jpeg"}
    suffix = Path(filename).suffix.lower()
    return suffix in supported
