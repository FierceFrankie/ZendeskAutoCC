# Zendesk Auto CC Azure Function

A Python Azure Function that automatically adds a configured Zendesk user as an email CC to qualifying Zendesk tickets.

This project was created as a proof of concept for handling an email CC workflow that could not be completed using Zendesk triggers alone.

## How It Works

When a qualifying ticket is created:

1. A Zendesk Trigger sends the ticket ID to the Azure Function through a webhook.
2. The Azure Function validates the incoming ticket ID.
3. The Function authenticates with Zendesk using OAuth client credentials.
4. Zendesk returns a short-lived OAuth access token.
5. The Function sends an authenticated API request to the Zendesk Ticket API.
6. The API request adds the configured Zendesk user as an email CC.
7. The Function returns a success or failure response.

The Function does not persist ticket data, customer data, or OAuth access tokens.

## Architecture

```text
Zendesk Ticket
      |
      v
Zendesk Trigger
      |
      | Webhook
      | {"ticket_id": "..."}
      v
Azure Function
      |
      | OAuth Client Credentials
      v
Zendesk OAuth
      |
      | Short-lived Access Token
      v
Azure Function
      |
      | Authenticated API Request
      v
Zendesk Ticket API
      |
      v
Configured User Added as Email CC
```

## Azure Function

The project uses the Python programming model for Azure Functions.

The HTTP endpoint accepts POST requests containing a Zendesk ticket ID.

Example request:

```json
{
  "ticket_id": "107202"
}
```

The Function uses the ticket ID to construct the appropriate Zendesk Ticket API request.

## Zendesk API Request

After obtaining an OAuth access token, the Function submits a ticket update similar to:

```json
{
  "ticket": {
    "email_ccs": [
      {
        "user_id": 123456789,
        "action": "put"
      }
    ]
  }
}
```

The actual Zendesk user ID is supplied through environment configuration and is not stored in the source code.

## Configuration

The Function expects the following environment variables:

| Setting | Description |
|---|---|
| `ZENDESK_SUBDOMAIN` | Zendesk account subdomain |
| `ZENDESK_CLIENT_ID` | Zendesk OAuth client ID |
| `ZENDESK_CLIENT_SECRET` | Zendesk OAuth client secret |
| `ZENDESK_CC_USER_ID` | Zendesk user ID to add as an email CC |

### Local Development

During local development, these values can be supplied through:

```text
local.settings.json
```

`local.settings.json` is intentionally excluded from source control because it can contain credentials.

Example structure:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "ZENDESK_SUBDOMAIN": "example",
    "ZENDESK_CLIENT_ID": "example-client-id",
    "ZENDESK_CLIENT_SECRET": "DO-NOT-COMMIT-REAL-SECRETS",
    "ZENDESK_CC_USER_ID": "123456789"
  }
}
```

Do not commit actual Zendesk credentials to the repository.

## Production Azure Deployment

For deployment in a company Azure environment, the Zendesk OAuth client secret should not be hardcoded in the application.

The intended production architecture is:

```text
Azure Key Vault
      |
      | Zendesk OAuth Client Secret
      v
Azure Function Configuration
      |
      v
Python Azure Function
      |
      | Request temporary OAuth token
      v
Zendesk OAuth
```

The Azure Function can use an Azure Managed Identity with permission to access the required secret in Azure Key Vault.

The Python application continues to retrieve its configuration through environment variables, keeping credentials separate from the application source code.

## Security

This proof of concept was designed with several security considerations:

- Zendesk credentials are not hardcoded in the Python source code.
- `local.settings.json` is excluded from Git.
- Python virtual environments and local artifacts are excluded from Git.
- OAuth access tokens are not logged.
- OAuth client secrets are not logged.
- OAuth access tokens are not persisted by the Function.
- The Function only receives the Zendesk ticket ID required to perform the update.
- Production secrets can be managed through Azure Key Vault.
- Azure Managed Identity can be used to control access to production secrets.

## Local Testing

Start the Azure Function locally with:

```powershell
func start
```

The Function runs locally on the Azure Functions development host, typically:

```text
http://localhost:7071
```

For local proof-of-concept testing, a tunneling service such as ngrok can expose the local HTTP endpoint so Zendesk can deliver webhook requests to it.

ngrok is only required for local testing and would not be part of the production Azure deployment.

## Project Structure

```text
ZendeskAutoCC/
├── .gitignore
├── function_app.py
├── host.json
├── README.md
├── requirements.txt
└── local.settings.json    # Local only - excluded from Git
```

## Requirements

The Python dependencies are defined in:

```text
requirements.txt
```

The primary dependencies are:

```text
azure-functions
requests
```

## Status

Proof of concept complete.

The workflow has been tested locally from the incoming Zendesk webhook through OAuth authentication and the resulting Zendesk ticket update.

The next step is deployment to a managed Azure Function App environment.
