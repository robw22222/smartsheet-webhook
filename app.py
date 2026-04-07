import base64
import io
import os
import logging

import requests
from flask import Flask, request, jsonify

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SMARTSHEET_API_KEY = os.environ.get("SMARTSHEET_API_KEY")
SMARTSHEET_SHEET_ID = "2653610878914436"
SMARTSHEET_BASE_URL = "https://api.smartsheet.com/2.0"


def upload_attachment_to_row(row_id, filename, file_bytes, content_type="application/octet-stream"):
    """Upload a single decoded file attachment to a Smartsheet row."""
    url = f"{SMARTSHEET_BASE_URL}/sheets/{SMARTSHEET_SHEET_ID}/rows/{row_id}/attachments"
    headers = {
        "Authorization": f"Bearer {SMARTSHEET_API_KEY}",
        "Content-Type": content_type,
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Length": str(len(file_bytes)),
    }
    response = requests.post(url, headers=headers, data=file_bytes)
    response.raise_for_status()
    return response.json()


def guess_content_type(filename):
    """Guess MIME type from filename extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    mime_map = {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "webp": "image/webp",
        "txt": "text/plain",
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xls": "application/vnd.ms-excel",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "doc": "application/msword",
        "zip": "application/zip",
        "json": "application/json",
        "xml": "application/xml",
        "mp4": "video/mp4",
        "mov": "video/quicktime",
    }
    return mime_map.get(ext, "application/octet-stream")


@app.route("/webhook", methods=["POST"])
def webhook():
    if not SMARTSHEET_API_KEY:
        logger.error("SMARTSHEET_API_KEY is not set")
        return jsonify({"success": False, "error": "Server configuration error: API key missing"}), 500

    data = request.get_json(force=True, silent=True)
    if data is None:
        return jsonify({"success": False, "error": "Invalid or missing JSON body"}), 400

    row_id = data.get("row_id")
    if not row_id:
        return jsonify({"success": False, "error": "Missing required field: row_id"}), 400

    attachments = data.get("attachments", [])
    if not attachments:
        return jsonify({"success": False, "error": "No attachments provided"}), 400

    subject = data.get("subject", "")
    sender = data.get("sender", "")
    body = data.get("body", "")

    logger.info("Received webhook — subject: %s, sender: %s, row_id: %s, attachments: %d",
                subject, sender, row_id, len(attachments))

    results = []
    errors = []

    for idx, attachment in enumerate(attachments):
        filename = attachment.get("filename") or f"attachment_{idx + 1}"
        b64_data = attachment.get("data") or attachment.get("content") or attachment.get("base64")

        if not b64_data:
            errors.append({"filename": filename, "error": "Missing base64 data"})
            continue

        try:
            padding = 4 - len(b64_data) % 4
            if padding != 4:
                b64_data += "=" * padding
            file_bytes = base64.b64decode(b64_data)
        except Exception as e:
            logger.warning("Failed to decode attachment %s: %s", filename, str(e))
            errors.append({"filename": filename, "error": f"Base64 decode error: {str(e)}"})
            continue

        content_type = attachment.get("content_type") or guess_content_type(filename)

        try:
            result = upload_attachment_to_row(row_id, filename, file_bytes, content_type)
            logger.info("Uploaded %s to row %s — result id: %s", filename, row_id, result.get("result", {}).get("id"))
            results.append({"filename": filename, "success": True, "attachment_id": result.get("result", {}).get("id")})
        except requests.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else "unknown"
            detail = ""
            try:
                detail = e.response.json()
            except Exception:
                detail = e.response.text if e.response is not None else str(e)
            logger.error("Smartsheet API error for %s: %s %s", filename, status_code, detail)
            errors.append({"filename": filename, "error": f"Smartsheet API error {status_code}: {detail}"})
        except Exception as e:
            logger.error("Unexpected error uploading %s: %s", filename, str(e))
            errors.append({"filename": filename, "error": str(e)})

    if errors and not results:
        return jsonify({"success": False, "errors": errors}), 502

    response_body = {
        "success": True,
        "uploaded": results,
    }
    if errors:
        response_body["partial_errors"] = errors

    return jsonify(response_body), 200


@app.route("/healthz", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
