# Security Policy

## Supported versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | Yes       |

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security-sensitive reports.

Email **manasabehera5901@gmail.com** with:

- A description of the issue
- Steps to reproduce (if applicable)
- Impact assessment

You should receive a response within a reasonable timeframe. If the report is
accepted, a fix will be coordinated before public disclosure when appropriate.

## Scope notes

This project calls AWS Bedrock with credentials from your environment. Keep
`.env` and AWS keys out of version control and restrict Bedrock model access
to least-privilege IAM policies in production deployments.
