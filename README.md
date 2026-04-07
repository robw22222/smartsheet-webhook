# Smartsheet Webhook

A Python Flask webhook that receives POST requests from Zapier containing email attachments (base64-encoded), decodes them, and uploads them directly to a specific Smartsheet row.

## How It Works

1. Zapier sends a POST request to `/webhook` with email metadata and base64-encoded attachments
2. The app decodes each attachment and uploads it to the specified Smartsheet row
3. Returns a JSON response with upload results

## Setup

### Environment Variables

| Variable | Description |
|---|---|
| `SMARTSHEET_API_KEY` | Your Smartsheet API key |

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run the App

```bash
python app.py
```

The server starts on port `5000` by default (set `PORT` env var to override).

## Endpoints

### `POST /webhook`

Receives the Zapier payload and uploads attachments to Smartsheet.

**Request body (JSON):**

```json
{
  "row_id": "123456789",
  "subject": "Email subject",
  "sender": "sender@example.com",
  "body": "Email body text",
  "attachments": [
    {
      "filename": "report.pdf",
      "data": "<base64-encoded file content>",
      "content_type": "application/pdf"
    }
  ]
}
```

- `row_id` — required. The Smartsheet row ID to attach files to.
- `attachments[].data` — base64-encoded file content. Also accepts `content` or `base64` as key names.
- `attachments[].content_type` — optional. Auto-detected from filename extension if omitted.

**Responses:**

| Status | Meaning |
|---|---|
| `200` | All attachments uploaded successfully |
| `200` with `partial_errors` | Some uploaded, some failed |
| `400` | Missing required fields |
| `502` | All attachment uploads failed |

### `GET /healthz`

Health check endpoint. Returns `{"status": "ok"}`.

## Smartsheet Configuration

- **Sheet ID**: `2653610878914436` (hardcoded in `app.py`)
- The `row_id` is passed dynamically in each Zapier request

## Zapier Setup

1. Add a **Webhooks by Zapier** action step
2. Set method to `POST`
3. Set URL to your webhook endpoint: `https://<your-domain>/webhook`
4. Set payload type to `JSON`
5. Map fields:
   - `row_id` → the Smartsheet row ID
   - `subject` → email subject
   - `sender` → sender email
   - `body` → email body
   - `attachments` → array of `{filename, data}` objects

## UptimeRobot (Keep-Alive)

Register `https://<your-domain>/healthz` on [uptimerobot.com](https://uptimerobot.com) with a 5-minute ping interval to keep the app alive.
