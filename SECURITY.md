# Security Policy

## Supported versions

AI Infra Console is pre-release software. Security updates currently target the latest branch only.

## Reporting a vulnerability

Do not disclose suspected vulnerabilities in a public issue. Contact the repository maintainers privately through the security reporting channel configured on the hosting platform.

Include the affected component, reproduction steps, impact, and any suggested mitigation. Avoid including real credentials, registration tokens, server addresses, or model provider tokens in the report.

## Security boundaries

The project follows these baseline rules:

- Agent operations must use an explicit allowlist.
- Arbitrary remote shell, SSH terminal, `/exec`, `/shell`, and `/command` endpoints are out of scope.
- Registration tokens must be hashed at rest when the Agent phase is implemented.
- Model deletion must be restricted to configured model directories and require confirmation.
- Local server records and secrets must never be committed to the public repository.
