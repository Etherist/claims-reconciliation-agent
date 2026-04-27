# Security Policy

## Reporting a Vulnerability

We take the security of the Claims Reconciliation Agent seriously. If you believe you have found a security vulnerability, please report it responsibly.

**Please do not** disclose the vulnerability publicly until we have had a chance to address it.

### How to Report

- **Email:** security@claims-reconciliation-agent.dev (example)
- **GitHub:** [Private security advisory](https://github.com/your-username/claims-reconciliation-agent/security/advisories)

Please include:
- Description of the vulnerability
- Steps to reproduce
- Affected versions
- Potential impact

We will respond within 48 hours and aim to resolve within 90 days.

---

## Security Best Practices (For Users)

### 1. Data Privacy

The tool processes healthcare claim data which may contain **Personally Identifiable Information (PII)**.

**Recommendations:**
- Use only synthetic or properly de-identified data in demo environments
- Enable log sanitization: set `LOG_SANITIZE_PII=true` in `.env` to redact patient names from logs
- Store reports in encrypted directories if they contain real data
- Follow Australian Privacy Principles (APPs) under the *Privacy Act 1988*

### 2. Input Validation

The tool validates:
- File size (max 10MB by default)
- File extensions (.csv, .json, .edi)
- Required column headers
- Data types (amounts, dates)

**Note:** Do not increase `MAX_FILE_SIZE_MB` beyond what your system can safely handle.

### 3. Dependency Security

We use automated dependency scanning via GitHub Actions (`safety check`). To monitor locally:

```bash
pip install safety
safety check --full-report
```

We recommend enabling **GitHub Dependabot** on your repository to receive automatic PRs for vulnerable dependencies.

### 4. CSV Injection Prevention

All CSV reports are generated with `quoting=csv.QUOTE_ALL` and sanitized to prevent Excel formula injection. This is enabled by default.

**If you modify report generation**, ensure you maintain these protections:
- Use `sanitize_csv_value()` on all string fields
- Use `csv.QUOTE_ALL` when calling `DataFrame.to_csv()`

### 5. File System Security

- Reports are written to `REPORT_DIR` (default: `reports/`)
- The directory is validated to be within the project root (prevents path traversal)
- Do not set `REPORT_DIR` to a system directory (e.g., `/etc`, `C:\Windows`)
- Ensure file permissions restrict access to the user running the tool (`chmod 700` on Unix)

### 6. Environment Variables

- Never commit `.env` to version control (already in `.gitignore`)
- Use strong, unique values for any future API keys
- Rotate keys periodically

### 7. Logging

By default, logs contain patient names and amounts for debugging. To redact:

```bash
# .env
LOG_SANITIZE_PII=true
```

This replaces patient names with `[REDACTED]` and masks amounts.

### 8. Network Security

Current version is **offline only** – no external API calls are made. Future EDI/API integrations will:

- Use HTTPS with certificate validation
- Implement API key rotation
- Support mutual TLS (mTLS) for insurer connections

### 9. Access Control

This is a **single-user** CLI/demo tool. For multi-user deployment:

- Implement authentication (OAuth2, LDAP)
- Use role-based access control (RBAC)
- Audit all user actions
- Encrypt data at rest (AES-256)

### 10. Secure Deployment

- **Local:** Run in a virtual environment (already recommended)
- **Streamlit Cloud:** Enable authentication and set `authentication=true` in secrets
- **Docker:** Run as non-root user, use read-only filesystem where possible

---

## Known Security Limitations

| Limitation | Severity | Mitigation |
|------------|----------|------------|
| No built-in encryption for stored reports | Medium | Use OS-level encryption (BitLocker, FileVault) or encrypt reports manually |
| Logs may contain PII by default | Medium | Set `LOG_SANITIZE_PII=true` |
| No integrity verification (HMAC) of output files | Low | Generate checksums manually if needed |
| Sample data is not truly anonymous (uses realistic names) | Low | Use only in non-production environments |

---

## Security Audit Checklist (For Production)

Before deploying to a production environment:

- [ ] Run `safety check` and update all dependencies
- [ ] Enable `LOG_SANITIZE_PII=true`
- [ ] Set `MAX_FILE_SIZE_MB` to appropriate limit
- [ ] Ensure `REPORT_DIR` is on an encrypted volume
- [ ] Configure file system permissions (700 for directories, 600 for files)
- [ ] Enable audit logging (track who ran reconciliation and when)
- [ ] Review and minimize retained data (implement retention policy)
- [ ] If using EDI: validate EDI signatures and use secure transport (AS2)
- [ ] If using APIs: store credentials in a secrets manager (AWS Secrets Manager, HashiCorp Vault)
- [ ] Conduct penetration testing if handling real patient data

---

## Security Contact

For security issues, please use GitHub Security Advisories or email:
**security@claims-reconciliation-agent.dev** (example)

We respond within 48 hours and aim to patch within 90 days.

---

**Last updated:** 2026-04-27  
**Reviewer:** Kilo (Senior Agent Engineer)
