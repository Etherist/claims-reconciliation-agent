# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-04-27

### Added
- Initial release of Claims Reconciliation Agent
- 5 autonomous agents (File Ingestor, Data Cleaner, Fuzzy Matcher, Discrepancy Detector, Report Generator)
- Streamlit interactive dashboard
- Command-line interface (CLI)
- Jupyter notebook demo
- Fuzzy matching with configurable thresholds
- Underpayment/overpayment detection
- Duplicate claim/payment detection
- Multi-format report generation (CSV, JSON, PDF)
- Australian healthcare insurer support (Medicare, Bupa, Medibank, HBF, nib)
- Unit and integration test suite
- GitHub Actions CI/CD (linting, type-checking, testing, security scan)
- Comprehensive documentation (README, architecture docs, data format spec, demo guide)
- Makefile for common tasks
- Pre-commit hooks configuration
- Docker support (optional)

### Features
- Name fuzzy matching (token_set_ratio)
- Date tolerance (±N days)
- Amount tolerance (absolute + percentage)
- High-priority discrepancy flagging
- Interactive visualizations (pie charts, bar charts)
- Sample data generation script
- Configuration via environment variables

### Documentation
- Full README with badges, screenshots, usage examples
- Architecture diagrams (Mermaid)
- Agent workflow specification
- Data format specifications
- Demo guide with step-by-step instructions
- Contributing guidelines
- Code of conduct

### Security
- No real patient data in demo
- File size and type validation
- Environment variable config
- PII sanitization in sample data

## [Planned] - Future Releases

### v1.1.0 (Q3 2026)
- Full EDI 837/835 parsing support
- Medicare Online API integration (mock)
- PostgreSQL backend for reconciliation history
- Batch processing for large files
- Improved matching algorithm (ML-based)

### v1.2.0 (Q4 2026)
- Xero/MYOB integration for accounting export
- Real-time dashboard with WebSocket updates
- Multi-tenant SaaS architecture
- Role-based access control (RBAC)
- Email/Slack notifications for discrepancies

### v2.0.0 (2027)
- Cloud-native deployment (AWS/GCP/Azure)
- Microservice architecture (Kubernetes)
- Advanced analytics (trends, forecasting)
- Machine learning for anomaly detection
- Predictive payment modeling
