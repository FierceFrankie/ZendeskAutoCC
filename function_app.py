import json
import logging
import os

import azure.functions as func
import requests


app = func.FunctionApp(
    http_auth_level=func.AuthLevel.FUNCTION
)


@app.route(route="zendesk-cc", methods=["POST"])
def zendesk_cc(req: func.HttpRequest) -> func.HttpResponse:

    logging.info("Zendesk Auto CC function started.")

    # ---------------------------------------------------------
    # Configuration
    # ---------------------------------------------------------

    subdomain = os.getenv("ZENDESK_SUBDOMAIN")
    client_id = os.getenv("ZENDESK_CLIENT_ID")
    client_secret = os.getenv("ZENDESK_CLIENT_SECRET")
    cc_user_id = os.getenv("ZENDESK_CC_USER_ID")

    required_settings = {
        "ZENDESK_SUBDOMAIN": subdomain,
        "ZENDESK_CLIENT_ID": client_id,
        "ZENDESK_CLIENT_SECRET": client_secret,
        "ZENDESK_CC_USER_ID": cc_user_id,
    }

    missing_settings = [
        name
        for name, value in required_settings.items()
        if not value
    ]

    if missing_settings:

        logging.error(
            "Missing required configuration: %s",
            ", ".join(missing_settings)
        )

        return json_response(
            {
                "success": False,
                "error": "Function configuration error."
            },
            500
        )

    # ---------------------------------------------------------
    # Validate Zendesk webhook request
    # ---------------------------------------------------------

    try:
        request_body = req.get_json()

    except ValueError:

        return json_response(
            {
                "success": False,
                "error": "Request body must be valid JSON."
            },
            400
        )

    ticket_id = request_body.get("ticket_id")

    try:
        ticket_id = int(ticket_id)

    except (TypeError, ValueError):

        return json_response(
            {
                "success": False,
                "error": "ticket_id must be numeric."
            },
            400
        )

    logging.info(
        "Processing Zendesk ticket %s.",
        ticket_id
    )

    # ---------------------------------------------------------
    # Obtain Zendesk OAuth token
    # ---------------------------------------------------------

    oauth_url = (
        f"https://{subdomain}.zendesk.com/oauth/tokens"
    )

    oauth_payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "tickets:write"
    }

    try:

        oauth_response = requests.post(
            oauth_url,
            json=oauth_payload,
            timeout=30
        )

        oauth_response.raise_for_status()

        oauth_data = oauth_response.json()

        access_token = oauth_data.get("access_token")

        if not access_token:
            raise ValueError(
                "OAuth response did not contain access_token."
            )

    except (
        requests.RequestException,
        ValueError
    ) as exc:

        logging.exception(
            "Zendesk OAuth request failed."
        )

        return json_response(
            {
                "success": False,
                "stage": "oauth",
                "ticket_id": ticket_id,
                "error": "Zendesk authentication failed."
            },
            502
        )

    logging.info(
        "Zendesk OAuth authentication succeeded."
    )

    # ---------------------------------------------------------
    # Add Amy as email CC
    # ---------------------------------------------------------

    ticket_url = (
        f"https://{subdomain}.zendesk.com/"
        f"api/v2/tickets/{ticket_id}.json"
    )

    ticket_payload = {
        "ticket": {
            "email_ccs": [
                {
                    "user_id": int(cc_user_id),
                    "action": "put"
                }
            ]
        }
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:

        ticket_response = requests.put(
            ticket_url,
            headers=headers,
            json=ticket_payload,
            timeout=30
        )

        if not ticket_response.ok:

            logging.error(
                "Zendesk ticket update failed. "
                "Ticket=%s Status=%s",
                ticket_id,
                ticket_response.status_code
            )

            return json_response(
                {
                    "success": False,
                    "stage": "ticket_update",
                    "ticket_id": ticket_id,
                    "zendesk_status":
                        ticket_response.status_code
                },
                502
            )

    except requests.RequestException:

        logging.exception(
            "Zendesk Ticket API request failed."
        )

        return json_response(
            {
                "success": False,
                "stage": "ticket_update",
                "ticket_id": ticket_id,
                "error":
                    "Unable to communicate with Zendesk."
            },
            502
        )

    # ---------------------------------------------------------
    # Success
    # ---------------------------------------------------------

    logging.info(
        "Successfully added configured CC user "
        "to Zendesk ticket %s.",
        ticket_id
    )

    return json_response(
        {
            "success": True,
            "ticket_id": ticket_id,
            "message": "Zendesk CC added successfully."
        },
        200
    )


def json_response(data, status_code):

    return func.HttpResponse(
        json.dumps(data),
        status_code=status_code,
        mimetype="application/json"
    )