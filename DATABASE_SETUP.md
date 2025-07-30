# 🗄️ Database Setup - SEO Farm Orchestrator

## **📋 Přehled databázové struktury**

### **🏗️ Modely:**
- **Project** - Správa projektů (obsahuje asistenty a workflow běhy)
- **Assistant** - Konfigurace asistentů pro každý projekt 
- **WorkflowRun** - Log všech běhů workflow s výsledky

---

## **⚙️ Setup Instructions**

### **1️⃣ Instalace závislostí**
```bash
# Instalace Prisma CLI a klienta
npm install

# Nebo globálně
npm install -g prisma
```

### **2️⃣ Vytvoření a migrace databáze**
```bash
# Vytvoření první migrace
npm run db:migrate

# Generování Prisma klienta (pro Python)
npm run db:generate
```

### **3️⃣ Spuštění serveru s databází**
```bash
# Start backend + frontend
make dev

# Nebo manuálně
./run-dev.sh
```

---

## **🔧 Dostupné příkazy**

| Příkaz | Funkce |
|--------|--------|
| `npm run db:migrate` | Vytvoří novou migraci a aplikuje ji |
| `npm run db:generate` | Vygeneruje Prisma klienta |
| `npm run db:studio` | Spustí Prisma Studio (GUI prohlížeč) |
| `npm run db:reset` | Smaže a znovu vytvoří databázi |
| `npm run db:seed` | Naplní databázi testovacími daty |

---

## **📊 API Endpointy**

### **🏢 Projects**
```bash
GET    /api/projects           # Seznam všech projektů
POST   /api/project            # Vytvoření nového projektu
GET    /api/project/{id}       # Detail projektu s asistenty
PUT    /api/project/{id}       # Úprava projektu
DELETE /api/project/{id}       # Smazání projektu
```

### **🤖 Assistants**
```bash
GET    /api/assistant-functions       # Dostupné funkce
POST   /api/assistant                 # Vytvoření asistenta
GET    /api/assistants/{project_id}   # Asistenti pro projekt
GET    /api/assistant/{id}            # Detail asistenta
PUT    /api/assistant/{id}            # Úprava asistenta
DELETE /api/assistant/{id}            # Smazání asistenta
POST   /api/assistant/reorder         # Přeřazení pořadí
POST   /api/assistant/bulk-create/{project_id}  # Výchozí asistenti
```

### **🏃‍♂️ Workflow Runs**
```bash
GET    /api/workflow-runs                    # Seznam běhů (filtrovatelný)
POST   /api/workflow-run                     # Vytvoření nového běhu
GET    /api/workflow-run/{id}                # Detail běhu
PUT    /api/workflow-run/{id}                # Aktualizace běhu
DELETE /api/workflow-run/{id}                # Smazání běhu
GET    /api/workflow-run/temporal/{wf_id}/{run_id}  # Detail dle Temporal ID
PUT    /api/workflow-run/temporal/{wf_id}/{run_id}  # Update dle Temporal ID
GET    /api/workflow-runs/project/{id}/stats        # Statistiky projektu
```

---

## **🧪 Testování API**

### **Vytvoření nového projektu:**
```bash
curl -X POST http://localhost:8000/api/project \
  -H "Content-Type: application/json" \
  -d '{"name": "SEO Blog Generator", "language": "cs", "description": "AI nástroj pro generování blog článků"}'
```

### **Přidání výchozích asistentů:**
```bash
curl -X POST http://localhost:8000/api/assistant/bulk-create/{PROJECT_ID}
```

### **Seznam projektů:**
```bash
curl http://localhost:8000/api/projects
```

---

## **🔍 Database Schema**

### **Project** 
```sql
CREATE TABLE projects (
  id          TEXT PRIMARY KEY,
  name        TEXT NOT NULL,
  slug        TEXT UNIQUE NOT NULL,
  language    TEXT DEFAULT 'cs',
  description TEXT,
  createdAt   DATETIME DEFAULT CURRENT_TIMESTAMP,
  updatedAt   DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### **Assistant**
```sql
CREATE TABLE assistants (
  id          TEXT PRIMARY KEY,
  projectId   TEXT NOT NULL,
  name        TEXT NOT NULL,
  functionKey TEXT NOT NULL,
  inputType   TEXT DEFAULT 'string',
  outputType  TEXT DEFAULT 'string',
  order       INTEGER NOT NULL,
  timeout     INTEGER DEFAULT 60,
  heartbeat   INTEGER DEFAULT 15,
  active      BOOLEAN DEFAULT true,
  description TEXT,
  createdAt   DATETIME DEFAULT CURRENT_TIMESTAMP,
  updatedAt   DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (projectId) REFERENCES projects(id) ON DELETE CASCADE,
  UNIQUE(projectId, order)
);
```

### **WorkflowRun**
```sql
CREATE TABLE workflow_runs (
  id             TEXT PRIMARY KEY,
  projectId      TEXT NOT NULL,
  runId          TEXT NOT NULL,
  workflowId     TEXT NOT NULL,
  topic          TEXT NOT NULL,
  status         TEXT NOT NULL,
  startedAt      DATETIME DEFAULT CURRENT_TIMESTAMP,
  finishedAt     DATETIME,
  outputPath     TEXT,
  resultJson     TEXT,
  errorMessage   TEXT,
  elapsedSeconds INTEGER,
  stageCount     INTEGER,
  totalStages    INTEGER,
  createdAt      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updatedAt      DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (projectId) REFERENCES projects(id) ON DELETE CASCADE,
  UNIQUE(workflowId, runId)
);
```

---

## **🚀 Produkční deployment**

1. **Změna databáze na PostgreSQL** (v `prisma/schema.prisma`):
```prisma
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}
```

2. **Environment variables:**
```bash
DATABASE_URL="postgresql://user:password@localhost:5432/seoFarm"
```

3. **Deploy migrace:**
```bash
npm run db:deploy
``` 