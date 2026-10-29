# AI Banking Agent setup

The customer Help desk calls `POST /assistant/ask`. It requires an authenticated Customer token. The agent uses verified help topics from `backend/app/agents/banking_agent.py` and can use an OpenAI-compatible chat-completions provider when configured.

Set these environment variables in the same environment that launches Uvicorn:

- `BANKING_AI_API_KEY` — provider API key. Keep it private; do not put it in frontend code or commit it.
- `BANKING_AI_MODEL` — optional model name; defaults to `gpt-4o-mini`.
- `BANKING_AI_BASE_URL` — optional API base URL; defaults to `https://api.openai.com/v1`. Must use HTTPS unless it points to localhost.

Without `BANKING_AI_API_KEY`, the endpoint returns the best matching verified help-center answer. If the provider is unavailable, it also falls back to help-center guidance when a topic matches. The UI indicates which response mode was used.

Only the submitted question and matching, non-customer-specific help guidance are sent to the configured AI provider. The service does not send account profile data, transaction data, or conversation history. Do not enter passwords, card/account numbers, PINs, or one-time codes. Ticket creation is not implemented, so the agent always reports `ticket_created: false`.
