# SEO Farm Orchestrator - Project Overview

## 🚫 KRITICKÁ PRAVIDLA
- **ZAKÁZANÉ FALLBACKY:** Žádné fallback mechanismy! Když selže API nebo chybí data, asistent musí hodit exception a workflow selhat.
- **ZAKÁZANÁ MOCK DATA:** Žádné hardcoded/mock data! Všechno se načítá z databáze nebo external API.
- **POUZE DATABÁZOVÉ PROMPTY:** Používají se výhradně prompty uložené ručně přes frontend, žádné default prompty v kódu.
- **STRICT VALIDATION:** Pokud system_prompt není v databázi, workflow selže s chybou.

## 🌐 FRONTEND KONFIGURACE
- **URL:** http://localhost:3001 (VŽDY a POUZE tento port)
- **Spuštění:** `cd web-frontend && npm run dev`
- **Next.js:** Automaticky používá port 3001 pokud je 3000 obsazený

## SSH Připojení na Hetzner Production Server

### Server Details
- **IP adresa**: 91.99.210.104
- **Hostname**: Petrs-farm
- **OS**: Ubuntu 24.04.2 LTS
- **Username**: root

### SSH Klíč Konfigurace ✅
Používáme SSH klíč pro bezpečné připojení. Klíč je uložen v `~/.ssh/id_ed25519`.

### Postup připojení

```bash
# PRIMÁRNÍ způsob připojení (s SSH klíčem)
ssh -i ~/.ssh/id_ed25519 root@91.99.210.104

# FALLBACK způsob (bez explicitního klíče - pokud je nastavený v SSH config)
ssh root@91.99.210.104
```

**Výstup při úspěšném připojení:**
```
Welcome to Ubuntu 24.04.2 LTS (GNU/Linux 6.8.0-60-generic x86_64)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com
 * Support:        https://ubuntu.com/pro

 System information as of Sat Aug  2 07:51:58 PM UTC 2025

  System load:  0.0                Processes:             147
  Usage of /:   2.4% of 149.92GB   Users logged in:       1
  Memory usage: 3%                 IPv4 address for eth0: 91.99.210.104
  Swap usage:   0%                 IPv6 address for eth0: 2a01:4f8:c17:d7f0::1

Last login: Sat Aug  2 19:31:23 2025 from 46.13.215.141
root@Petrs-farm:~#
```

### Ověření připojení
```bash
whoami  # výstup: root
hostname  # výstup: Petrs-farm
pwd  # výstup: /root
```

## 🔧 IMPLEMENTOVANÉ BEZPEČNOSTNÍ OPATŘENÍ

### ✅ Odstraněné Fallbacky (2025-08-03)
- **Všechny activities:** Odstraněn fallback `assistant.system_prompt or default_params["system_prompt"]`
- **safe_assistant_activities.py:** Přidána strict validace pro system_prompt z databáze
- **Hardcoded prompty:** Odstraněny ze všech default_params v activities
- **Worker restart:** Implementován s čistým kódem bez fallbacků

### 🎯 Chování při chybějících datech
```python
# PŘED (špatně - s fallback):
system_prompt = assistant.system_prompt or default_params["system_prompt"]

# PO (správně - strict):
system_prompt = assistant.system_prompt
if not system_prompt or not system_prompt.strip():
    raise Exception("❌ ŽÁDNÝ SYSTEM PROMPT v databázi!")
```

## 🚨 CRITICAL: Temporal Worker Management

### ⚠️ KRITICKÉ PRAVIDLO - POUZE JEDEN WORKER!

**NIKDY nevytvářej více worker procesů současně!** Temporal rozděluje úkoly mezi všechny dostupné workery náhodně, což způsobuje:
- ❌ API_BASE_URL konflikty (některé workery bez env variable)
- ❌ Nekonzistentní chování pipeline
- ❌ Náhodné selhání asistentů
- ❌ previous_outputs nejsou předávány správně

### ✅ NOVÝ BEZPEČNÝ POSTUP - MANAGEMENT SCRIPT! 🛡️

🚀 **VŽDY používej `manage_worker.sh` script místo manuálních příkazů!**

#### 1. Základní používání
```bash
# 📊 Kontrola stavu (DOPORUČENO jako první)
./manage_worker.sh status

# 🔄 Bezpečný restart (NEJBEZPEČNĚJŠÍ)
./manage_worker.sh restart

# 🚀 Spuštění (pouze pokud žádný neběží)
./manage_worker.sh start

# 🛑 Zastavení všech workerů
./manage_worker.sh stop
```

#### 2. Bezpečnostní mechanismy scriptu
- ✅ **Automatická kontrola** - script zabezpečuje pouze 1 worker
- ✅ **PID file tracking** - sledování běžícího procesu  
- ✅ **Environment validation** - kontrola API_BASE_URL
- ✅ **Fallback protection** - zastavení všech před spuštěním nového
- ✅ **Error handling** - validace každého kroku

#### 3. Příklad správného výstupu
```bash
$ ./manage_worker.sh status

📊 STAV WORKER PROCESŮ:
======================
🔍 Kontroluji běžící workery...
📊 Nalezeno workerů: 1
✅ Správně - POUZE JEDEN worker:
petrliesner      42887   0,0  0,2 34840060  79900 s125  SN    6:46od   0:01.13
```

### 🔧 Současný Správný Worker (PID 42887)
- **Management:** Spravován přes `./manage_worker.sh`
- **Status:** ✅ Běžící s bezpečnostními kontrolami
- **API_BASE_URL:** http://localhost:8000 (automaticky validována)
- **PID file:** `worker.pid` (automaticky spravován)
- **Created:** 2025-08-03 18:46:00

### 🚫 ZAKÁZANÉ POSTUPY (NIKDY NEPOUŽÍVEJ!):
```bash
# ❌ NIKDY toto nepoužívaj:
python production_worker.py &                    # Bez ochrany
API_BASE_URL=... python production_worker.py &   # Manuální spuštění  
pkill -f "production_worker"                     # Manuální zastavování
export API_BASE_URL=... && python...             # Nebezpečné

# ✅ VŽDY místo toho:
./manage_worker.sh restart                       # Bezpečný způsob
```

### 🔍 Řešení problémů
```bash
# Pokud máš více workerů:
./manage_worker.sh restart

# Pokud worker nejede:
./manage_worker.sh start

# Pokud něco nejde:
./manage_worker.sh status  # Diagnostika
```

### ✅ WORKFLOW OPRAVY:
1. **previous_outputs FIX**: Workflow nyní správně předává `{k: v for k, v in pipeline_data.items() if k.endswith("_output")}` místo prázdného `{}`
2. **PublishAssistant FIX**: Dostává nyní všechna data z předchozích asistentů
3. **Single Worker**: Pouze jeden proces s API_BASE_URL

---

## PostgreSQL Databáze - Production Server ✅ DOKONČENO

### Konfigurace databáze
- **Server**: 91.99.210.104:5432
- **Databáze**: `seo_farm`
- **Uživatel**: `seo_user`
- **Heslo**: `silne-heslo`
- **Vzdálený přístup**: ✅ Povolený z jakékoli IP

### Connection String
```
DATABASE_URL="postgresql://seo_user:silne-heslo@91.99.210.104:5432/seo_farm"
```

### 1. Dokončená instalace PostgreSQL
```bash
apt update && apt install -y postgresql postgresql-contrib
systemctl enable postgresql
systemctl start postgresql
```

### 2. Databáze a uživatel vytvořen ✅
```sql
CREATE DATABASE seo_farm;
CREATE USER seo_user WITH PASSWORD 'silne-heslo';
GRANT ALL PRIVILEGES ON DATABASE seo_farm TO seo_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO seo_user;
GRANT CREATE ON SCHEMA public TO seo_user;
ALTER SCHEMA public OWNER TO seo_user;
```

### 3. Povolený vzdálený přístup ✅
```bash
# /etc/postgresql/16/main/postgresql.conf
  listen_addresses = '*'

# /etc/postgresql/16/main/pg_hba.conf  
  host    seo_farm    seo_user    0.0.0.0/0    md5
  ```

## Lokální Vývojové Prostředí

### .env Konfigurace ✅
Lokální projekt nyní používá vzdálenou PostgreSQL databázi:

```bash
# .env soubor v root adresáři
DATABASE_URL="postgresql://seo_user:silne-heslo@91.99.210.104:5432/seo_farm"
TEMPORAL_HOST=localhost:7233
TEMPORAL_NAMESPACE=default
API_BASE_URL=http://localhost:8000
LOG_LEVEL=INFO
```

### Migrace z SQLite na PostgreSQL ✅
- **Backup vytvořen**: ✅ `backup_20250803_140401/`
- **Schema změněno**: ✅ SQLite → PostgreSQL 
- **Prisma client regenerován**: ✅
- **Data migrována**: ✅ Základní projekty importovány

### Spuštění lokálních serverů
```bash
# Spuštění všech služeb
./start_servers.sh

# Kontrola stavu
lsof -i :8000 -i :3001 -i :7233
```

## Production Deployment Status

### PM2 Procesy na serveru
```bash
# Kontrola statusu
pm2 status

# Logy
pm2 logs seo-backend
pm2 logs seo-frontend

# Restart
pm2 restart seo-backend
pm2 restart seo-frontend
```

### ✅ AKTUÁLNÍ STAV - VŠE FUNKČNÍ (6.8.2025 - KRITICKÉ OPRAVY)

**🚨 KRITICKÉ OPRAVY DOKONČENY:**
- ✅ **PublishAssistant OBNOVEN**: Smazaný soubor `activities/publish_assistant.py` obnoven s nejnovějšími opravami
- ✅ **Worker Management OBNOVEN**: Smazaný `manage_worker.sh` script obnoven
- ✅ **DataClass chyby OPRAVENY**: Opraveny chyby v `publish_script.py` (non-default po default argumentech)
- ✅ **QA Assistant FUNKČNÍ**: Správně dostává vstupy z předchozích asistentů
- ✅ **Worker RESTARTOVÁN**: PID 66111 - načetl všechny opravy:
 
1 of 5 unhandled errors
Next.js (14.0.0) is outdated (learn more)

Unhandled Runtime Error
TypeError: Failed to fetch

Source
app/workflows/page.tsx (45:29) @ fetch

  43 | console.log('🌐 DEBUG: Full API URL:', apiUrl);
  44 | 
> 45 | const response = await fetch(apiUrl)
     |                       ^
  46 | console.log('📡 DEBUG: Response status:', response.status, response.statusText);
  47 | 
  48 | if (!response.ok) {
    

**🌐 SLUŽBY A PORTY:**
- ✅ **Frontend (Next.js)**: http://localhost:3001 ← SPRÁVNÝ PORT!
- ✅ **Backend (FastAPI)**: http://localhost:8000
- ✅ **Temporal Server**: localhost:7233
- ✅ **Temporal UI**: http://localhost:8233
- ✅ **Temporal Worker**: Jeden bezpečný worker (PID 66111) ← NOVÝ!
- ✅ **Database**: PostgreSQL na 91.99.210.104:5432

**🧪 TESTOVACÍ PIPELINE SPUŠTĚNA:**
- Workflow ID: `assistant_pipeline_test_publish_assistant_opravy_1754510937`
- Frontend: http://localhost:3001/workflows/assistant_pipeline_test_publish_assistant_opravy_1754510937/db305aef-9843-460d-b882-760aefd6a70b

**🔧 RYCHLÁ KONTROLA:**
```bash
# Všechny služby:
./manage_worker.sh status                    # Worker stav
curl http://localhost:8000/health            # Backend
curl http://localhost:3001                   # Frontend
ps aux | grep "temporal server" | head -1   # Temporal server
```

---

## Kritické Opravy (7.8.2025)

### 🔧 Oprava TypeError undefined.substring v workflows
**Problém**: Production frontend házal TypeError na `/workflows` stránce kvůli `undefined.substring()`.

**Řešení**: ✅ Opravena `truncateHash` funkce pro zpracování `undefined` hodnot.

**Commit**: `9f923b9` - "🔧 Oprava TypeError undefined.substring v workflows stránce"

**Soubor**: `web-frontend/app/workflows/page.tsx`

### 🔧 Rozšíření API klíče modal o všechny LLM
**Problém**: Submit button nefungoval pro Claude a Gemini API klíče.

**Řešení**: ✅ Přidána podpora pro všechny 4 LLM providery s korektní validací.

**Commit**: `0b7d459` - "🔧 Oprava API klíče modal - funkční submit button"

**Soubor**: `web-frontend/app/components/ApiKeyModal.tsx`

---

## Kritické Opravy (3.8.2025)

### 🔧 Oprava pořadí asistentů v UI
**Problém**: Funkce "📋 Zobrazit výstupy 1-8" používala hardcoded mapping místo chronologického pořadí.

**Řešení**: ✅ Změněno na dynamické řazení podle timestamp (stejné jako pipeline display).

**Soubor**: `web-frontend/app/workflows/[workflow_id]/[run_id]/page.tsx`

---

## 🔗 LOKÁLNÍ SERVERY

### Frontend (Next.js)
```bash
cd web-frontend && npm run dev
# ✅ http://localhost:3001
```

### Backend API
```bash
cd backend && python3 main.py
# ✅ http://localhost:8000
```

### Temporal Server
```bash
temporal server start-dev
# ✅ http://localhost:8233 (UI)
# ✅ localhost:7233 (gRPC)
```

## Server Informace

- **IPv4**: 91.99.210.104
- **IPv6**: 2a01:4f8:c17:d7f0::1  
- **Disk**: 149.92GB (2.4% využito)
- **RAM**: 3% využití
- **OS**: Ubuntu 24.04.2 LTS