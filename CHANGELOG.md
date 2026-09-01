# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-09-01

### Added

- Three-agent pipeline: Researcher, Summarizer, and Critic over AWS Bedrock Converse API
- Local `search_documents` tool backed by a sample corpus in `data/`
- Mocked pytest suite (no AWS credentials required for CI)
- uv-based dependency management with locked installs
- GitHub Actions CI matrix on Python 3.10–3.12 (lint + test)
- Project documentation, contributing guide, and security policy

[0.1.0]: https://github.com/manasaranjanbehera/agentic-research-assistant/releases/tag/v0.1.0
