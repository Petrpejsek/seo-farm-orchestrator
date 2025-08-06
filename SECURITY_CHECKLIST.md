# 🔒 SECURITY CHECKLIST PRO PRODUKČNÍ NASAZENÍ

## ❌ KRITICKÉ BEZPEČNOSTNÍ PROBLÉMY

### 1. **API KLÍČE V REPOSITORY**
- ❌ `backend/api_keys.json` - obsahuje šifrované API klíče
- ❌ `backend/encryption_key.txt` - encryption key je v plaintextu
- **Řešení**: Přesunout do environment variables nebo AWS Secrets Manager

### 2. **DATABÁZE SOUBORY V GIT**
- ❌ `backend/dev.db` - SQLite databáze
- ❌ `prisma/dev.db` - Prisma databáze
- **Řešení**: Přidat do .gitignore, použít externí databázi

### 3. **LOG SOUBORY OBSAHUJÍ CITLIVÁ DATA**
- ⚠️ Worker logy mohou obsahovat parts of prompts/responses
- **Řešení**: Sanitizace logů, log rotation

## ✅ DOPORUČENÁ OPATŘENÍ

### Environment Variables
```bash
# Kritické proměnné pro produkci
export OPENAI_API_KEY="sk-..."
export CLAUDE_API_KEY="sk-ant-..."
export GEMINI_API_KEY="AIza..."
export DATABASE_URL="postgresql://..."
export ENCRYPTION_KEY="$(openssl rand -base64 32)"
export JWT_SECRET="$(openssl rand -base64 64)"
```

### Firewall pravidla
```bash
# Pouze potřebné porty
ufw allow 8000/tcp  # Backend API
ufw allow 3000/tcp  # Frontend
ufw allow 7233/tcp  # Temporal (pouze local)
ufw allow 8233/tcp  # Temporal UI (pouze local)
ufw deny 9090/tcp   # Prometheus (pouze monitoring)
```

### Docker Security
```dockerfile
# Non-root user
RUN adduser --disabled-password --gecos '' seouser
USER seouser

# Read-only filesystem
--read-only --tmpfs /tmp
```

### SSL/TLS
- ✅ HTTPS pro všechny external endpointy
- ✅ TLS pro databázové spojení
- ✅ Certificate management (Let's Encrypt)

## 🛡️ IMPLEMENTOVANÉ BEZPEČNOSTNÍ FUNKCE

### Input Validation
✅ Všechny API endpointy mají validaci
✅ SQL injection protection (Prisma ORM)
✅ XSS protection v frontend

### Error Handling
✅ Structured error responses
✅ No sensitive data in error messages
✅ Graceful shutdown handling

### Rate Limiting
⚠️ **CHYBÍ** - implementovat rate limiting pro API

### Authentication & Authorization
⚠️ **ZÁKLADNÍ** - pouze API key auth
🔧 **UPGRADE**: JWT tokens, role-based access

## 📋 AKČNÍ PLÁN

### 1. Okamžitá opatření
- [ ] Odstranit sensitive soubory z git history
- [ ] Přesunout API klíče do env variables
- [ ] Aktualizovat .gitignore
- [ ] Změnit všechny API klíče

### 2. Krátkodobá (týden)
- [ ] Implementovat HashiCorp Vault / AWS Secrets Manager
- [ ] Přidat rate limiting
- [ ] Setup SSL certifikátů
- [ ] Database encryption at rest

### 3. Dlouhodobá (měsíc)
- [ ] JWT authentication
- [ ] Role-based access control
- [ ] Security audit logging
- [ ] Penetration testing

## 🚨 EMERGENCY RESPONSE

### V případě kompromitace:
1. **Okamžitě rotovat všechny API klíče**
2. Zkontrolovat access logy
3. Restartovat všechny služby
4. Notify stakeholders
5. Post-incident review