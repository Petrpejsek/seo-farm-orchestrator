# SEO Farm Orchestrator

🎯 **AI-powered SEO content orchestrace pomocí Temporal.io + OpenAI Assistant API**

## ✨ Nové funkcie

### 1️⃣ **Bulk Processing z CSV súborov**
```bash
# Spracuje všetky témy z CSV súboru
python scripts/test_cli.py --csv input/topics.csv
```

### 2️⃣ **Export do PostgreSQL databázy**
```bash
# Nastavenie v .env súbore
SAVE_TO_DB=true
DATABASE_URL=postgresql://user:password@localhost:5432/seo_farm

# Automaticky sa vytvorí tabuľka seo_outputs s kompletným obsahom
```

### 3️⃣ **CLI nástroj pre produkčné použitie**
```bash
# Inštalácia balíčka
pip install -e .

# Použitie
python scripts/test_cli.py pipeline "Téma"
python scripts/test_cli.py --csv input/topics.csv
```

## 🚀 Rýchly štart

### 1. Inštalácia
```bash
git clone <your-repo>
cd seo-farm-orchestrator

# Python 3.11 virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Konfigurácia (.env súbor)
```ini
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_ASSISTANT_ID=asst_xxxxxxxxxxxxxxxxxx

# Voliteľné - databázový export
SAVE_TO_DB=false
DATABASE_URL=postgresql://user:password@localhost:5432/seo_farm
```

### 3. Spustenie Temporal serveru (Docker)
```bash
docker-compose up -d
```

### 4. Spustenie workera
```bash
source .venv/bin/activate
PYTHONPATH=$(pwd) python3 worker.py
```

### 5. Testovanie

#### Jednotlivé téma:
```bash
python scripts/test_cli.py pipeline "AI nástroje pre content marketing"
```

#### Bulk processing z CSV:
```bash
# Vytvor CSV súbor s témami
echo "AI nástroje pre marketing
Moderní SEO strategie 2025
Automatizace social media" > input/topics.csv

# Spusti bulk processing
python scripts/test_cli.py --csv input/topics.csv
```

## 📊 Výstup

### JSON súbory
```
outputs/seo_output_20250728_123456_cli_AI_n.json
```

### PostgreSQL tabuľka (voliteľné)
```sql
CREATE TABLE seo_outputs (
    id SERIAL PRIMARY KEY,
    topic VARCHAR(500),
    generated TEXT,
    structured TEXT,
    enriched TEXT,
    faq_final TEXT,
    workflow_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 🔄 Temporal Workflow (5 kroků)

1. **generate_llm_friendly_content** - OpenAI Assistant API
2. **inject_structured_markup** - JSON-LD schema
3. **enrich_with_entities** - Entity linking
4. **add_conversational_faq** - FAQ sekcia
5. **save_output** - JSON súbor + voliteľne PostgreSQL

## 🛠️ Vývoj

### CLI testovanie bez Temporal
```bash
python scripts/test_cli.py pipeline "Test téma"
```

### Temporal workflow
```bash
temporal workflow start --type SEOWorkflow --task-queue default --input '"Test téma"'
```

### Logs a monitoring
- Temporal UI: http://localhost:8081
- Worker logs: `tail -f worker.log`
- JSON výstupy: `ls outputs/`

## 📦 Dependencies

### Core
- `temporalio==1.4.0` - Workflow orchestrace
- `openai==1.58.1` - OpenAI Assistant API
- `python-dotenv==1.0.0` - Environment konfigurácia

### Voliteľné
- `sqlalchemy>=2.0.23` - PostgreSQL export
- `psycopg2-binary>=2.9.9` - PostgreSQL driver

## 🐛 Troubleshooting

### Python 3.13 problémy
```bash
# Použij Python 3.11
brew install python@3.11
python3.11 -m venv .venv
```

### Temporal sandbox chyby
```bash
# Uisti sa, že používaš Python 3.11
python3 --version
# Python 3.11.13
```

### Import chyby
```bash
# Nastav PYTHONPATH
export PYTHONPATH=$(pwd)
python3 worker.py
```

## 📈 Produkčné nasadenie

1. **Docker setup** s PostgreSQL
2. **Environment variables** v produkčnom prostredí
3. **Temporal cluster** konfigurácia
4. **Rate limiting** pre OpenAI API
5. **Monitoring** Temporal workflows

## 🔗 API Integration

- **OpenAI Assistant API** - Pokročilé content generation
- **Temporal.io** - Reliable workflow orchestrace  
- **PostgreSQL** - Persistent data storage
- **JSON-LD Schema** - Structured markup
- **CSV Import** - Bulk topic processing 