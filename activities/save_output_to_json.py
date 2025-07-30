import json
import os
from datetime import datetime
from temporalio import activity

@activity.defn
async def save_output_to_json(result: dict) -> str:
    """
    Uloží výstup workflow jako JSON soubor do složky outputs/.
    """
    try:
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
        
        activity.logger.info(f"✅ Výstup workflow uložen: {filepath}")
        return filepath
        
    except Exception as e:
        activity.logger.error(f"❌ Chyba při ukládání JSON: {str(e)}")
        raise 