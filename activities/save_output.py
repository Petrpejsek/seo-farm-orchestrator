import json
import os
from datetime import datetime
from temporalio import activity
from dotenv import load_dotenv

# Načtení environment variables
load_dotenv()

# Optional PostgreSQL dependencies
try:
    from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, MetaData, Table
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False

@activity.defn
async def save_output_to_json(result: dict) -> str:
    """
    Uloží výstup workflow jako JSON soubor do složky outputs/.
    """
    return await save_output(result)

@activity.defn
async def save_output(result: dict) -> str:
    """
    Uloží výstup workflow jako JSON soubor a volitelně do PostgreSQL databáze.
    """
    try:
        # 1️⃣ Vždy uložit do JSON
        json_path = await _save_to_json(result)
        activity.logger.info(f"✅ JSON výstup uložen: {json_path}")
        
        # 2️⃣ Volitelně uložit do databáze
        if os.getenv("SAVE_TO_DB", "false").lower() == "true":
            db_saved = await _save_to_database(result)
            if db_saved:
                activity.logger.info(f"✅ Výstup uložen i do databáze")
            else:
                activity.logger.warning(f"⚠️ Uložení do databáze se nezdařilo")
        
        return json_path
        
    except Exception as e:
        activity.logger.error(f"❌ Chyba při ukládání výstupu: {str(e)}")
        raise

async def _save_to_json(result: dict) -> str:
    """Uloží výstup jako JSON soubor"""
    
    # Vytvoření složky pokud neexistuje
    output_path = "outputs"
    os.makedirs(output_path, exist_ok=True)
    
    # Vytvoření názvu souboru s timestampem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    workflow_id = result.get("workflow_id", "unknown")
    filename = f"seo_output_{timestamp}_{workflow_id[:8]}.json"
    filepath = os.path.join(output_path, filename)
    
    # Uložení do JSON souboru
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    return filepath

async def _save_to_database(result: dict) -> bool:
    """Uloží výstup do PostgreSQL databáze"""
    
    if not SQLALCHEMY_AVAILABLE:
        activity.logger.error("❌ SQLAlchemy není nainstalováno. Spusťte: pip install sqlalchemy psycopg2-binary")
        return False
    
    try:
        # Načtení DB connection stringu
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            activity.logger.warning("⚠️ DATABASE_URL není nastaveno. Přeskakuji ukládání do DB.")
            return False
        
        # Vytvoření engine a session
        engine = create_engine(db_url)
        
        # Definice tabulky
        metadata = MetaData()
        seo_outputs = Table(
            'seo_outputs', metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('topic', String(500), nullable=False),
            Column('generated', Text, nullable=True),
            Column('structured', Text, nullable=True),
            Column('enriched', Text, nullable=True),
            Column('faq_final', Text, nullable=True),
            Column('workflow_id', String(100), nullable=True),
            Column('created_at', DateTime, default=datetime.utcnow),
        )
        
        # Vytvoření tabulky pokud neexistuje
        metadata.create_all(engine)
        
        # Uložení dat
        with engine.connect() as conn:
            insert_data = {
                'topic': result.get('topic', ''),
                'generated': result.get('generated', ''),
                'structured': result.get('structured', ''),
                'enriched': result.get('enriched', ''),
                'faq_final': result.get('faq_final', ''),
                'workflow_id': result.get('workflow_id', ''),
                'created_at': datetime.utcnow()
            }
            
            conn.execute(seo_outputs.insert().values(**insert_data))
            conn.commit()
        
        return True
        
    except Exception as e:
        activity.logger.error(f"❌ Chyba při ukládání do databáze: {str(e)}")
        return False 