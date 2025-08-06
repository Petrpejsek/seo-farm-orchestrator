#!/usr/bin/env python3
"""
🔧 STANDALONE TEST PUBLISH SCRIPTU
Testuje pouze publish_script.py bez spouštění celé pipeline
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add project root to Python path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from helpers.transformers import transform_to_PublishInput, create_project_config
from activities.publish_script import publish_script as publish_script_run
from logger import get_logger

logger = get_logger(__name__)

def create_mock_pipeline_data():
    """Vytvoří mock data pro testování"""
    return {
        "seo_assistant_output": """
Title: Vyplatí se auto na benzín v roce 2025? Analýza nákladů a výhod
Description: Zjistěte, zda je benzínový vůz v roce 2025 stále výhodnou volbou. Analyzujeme náklady, výhody a legislativní rizika.
Keywords: ["auto na benzín", "benzínové vozy", "náklady na benzínové auto", "Euro 7 norma", "srovnání benzín a elektro", "výhody benzínového auta", "TCO benzínového vozu"]
Canonical: https://seofarm.ai/auto-na-benzin-2025-analyza-nakladu-vyhod
Slug: vyplati-se-auto-na-benzin-v-roce-2025-analyza-nakladu-a-vyhod
""",
        "draft_assistant_output": """<article>
<h1>Vyplatí se auto na benzín v roce 2025? Analýza nákladů a výhod</h1>

<p class="lead">Benzínové automobily zůstávají významnou součástí automobilového trhu i v době elektromobility. Zjistěte, zda je nákup benzínového vozu v roce 2025 stále rozumným rozhodnutím.</p>

<h2>Náklady na provoz benzínového vozidla</h2>
<p>Provozní náklady benzínového automobilu zahrnují několik klíčových komponent. Cena paliva představuje obvykle největší část nákladů, přičemž v roce 2025 se pohybuje kolem 35-40 Kč za litr. Při průměrné spotřebě 7 litrů na 100 km to znamená náklady přibližně 2,5-3 Kč na kilometr pouze za palivo.</p>

<h3>Servisní náklady a údržba</h3>
<p>Benzínové motory vyžadují pravidelnou údržbu včetně výměny oleje, filtrů a zapalovacích svíček. Roční náklady na servis se pohybují mezi 15 000-25 000 Kč v závislosti na značce a stáří vozidla. Oproti elektromobilům jsou tyto náklady vyšší kvůli složitější konstrukci spalovacího motoru.</p>

<h2>Výhody benzínových automobilů</h2>
<p>Benzínové vozy nabízejí řadu praktických výhod. Hustá síť čerpacích stanic umožňuje doplnění paliva prakticky kdekoli během několika minut. Pořizovací cena je stále nižší než u elektromobilů srovnatelné kategorie, což činí benzínové vozy dostupnějšími pro širší spektrum kupujících.</p>

<h3>Dojezd a flexibilita</h3>
<p>Moderní benzínové automobily dosahují dojezdu 600-800 kilometrů na jednu nádrž, což převyšuje většinu současných elektromobilů. Tato vlastnost je zvláště cenná pro dlouhé cesty a oblasti s omezenou nabíjecí infrastrukturou.</p>

<h2>Legislativní změny a budoucnost</h2>
<p>Evropská unie plánuje ukončení prodeje nových spalovacích motorů do roku 2035. Toto rozhodnutí však neovlivní vozidla již uvedená na trh. Norma Euro 7, která vstoupí v platnost v roce 2025, přinese přísnější emisní limity, ale nebude znamenat konec benzínových motorů.</p>

<h3>Hodnota při prodeji</h3>
<p>Zůstatková hodnota benzínových vozidel může být ovlivněna měnícími se preferencemi spotřebitelů a legislativními změnami. Kvalitní benzínové automobily však budou mít svou hodnotu i v následujících letech, zejména na sekundárním trhu.</p>

<h2>Srovnání s alternativami</h2>
<p>Při rozhodování mezi benzínovým a elektrickým vozidlem je třeba zvážit individuální potřeby. Elektromobily nabízejí nižší provozní náklady a ekologičnost, ale vyžadují vyšší počáteční investici a plánování nabíjení.</p>

<h3>Hybridní řešení</h3>
<p>Hybridní vozidla představují kompromis mezi tradičními a elektrickými automobily. Kombinují výhody obou technologií a mohou být vhodnou volbou pro přechodné období. Mild-hybridní systémy snižují spotřebu o 5-10%, zatímco plug-in hybridy nabízejí elektrický dojezd 50-80 kilometrů pro městské jízdy.</p>

<h2>Ekonomická analýza vlastnictví</h2>
<p>Celkové náklady vlastnictví (TCO) benzínového vozidla zahrnují pořizovací cenu, deprecaci, pojištění, palivo, servis a opravy. Při pětiletém vlastnictví se pohybují kolem 6-8 Kč na kilometr podle kategorie vozidla. Kompaktní benzínové vozy nabízejí nejlepší poměr cena/výkon pro běžné využití.</p>

<h3>Financování a leasing</h3>
<p>Benzínová vozidla nabízejí širokou škálu financování díky stabilní zůstatkové hodnotě. Operativní leasing často zahrnuje servis a pojištění, což zjednodušuje rozpočtování. Úrokové sazby jsou obvykle nižší než u elektromobilů kvůli menšímu riziku pro poskytovatele.</p>

<h2>Technologické inovace v benzínových motorech</h2>
<p>Moderní benzínové motory využívají pokročilé technologie jako přímé vstřikování, turbodmychadla a systémy start-stop. Tyto inovace snižují spotřebu a emise při zachování výkonu a spolehlivosti. Mild-hybridní systémy dále optimalizují efektivitu bez složitosti plných hybridů.</p>

<h3>Ekologické aspekty</h3>
<p>Nové benzínové motory splňují přísné emisní normy Euro 6d-ISC-FCM a připravují se na Euro 7. Moderna katalyzátory a filtry částic snižují emise NOx a jemných částic. Použití biopaliv může dále snížit uhlíkovou stopu bez úprav motoru.</p>

<p>Rozhodnutí o nákupu benzínového automobilu v roce 2025 závisí na individuálních potřebách, rozpočtu a očekávané době vlastnictví. Pro mnoho řidičů zůstává benzínový vůz praktickou a ekonomicky rozumnou volbou v přechodném období k elektromobilitě.</p>
</article>""",
        "humanizer_assistant_output": "",
        "qa_assistant_output": """[
            {"question": "Jaké jsou hlavní náklady na benzínové auto?", "answer": "Hlavní náklady zahrnují palivo (2,5-3 Kč/km), servis (15-25 tisíc Kč ročně) a pojištění."},
            {"question": "Budou benzínová auta zakázána?", "answer": "EU plánuje ukončit prodej nových spalovacích motorů do 2035, stávající vozy však budou moci jezdit dál."},
            {"question": "Je benzínové auto levnější než elektromobil?", "answer": "Ano, pořizovací cena je obvykle nižší, ale provozní náklady mohou být vyšší."},
            {"question": "Jaký je dojezd benzínového auta?", "answer": "Moderní benzínové vozy dosahují dojezdu 600-800 km na jednu nádrž."}
        ]""",
        "multimedia_assistant_output": """{
            "visuals": [
                {"image_url": "benzin_auto_2025_1.jpg", "prompt": "Graf nákladů na benzínové auto", "alt": "Srovnání nákladů benzín vs elektro", "position": "top"},
                {"image_url": "benzin_auto_2025_2.jpg", "prompt": "Moderní benzínové auto na čerpací stanici", "alt": "Tankování benzínového automobilu", "position": "bottom"}
            ]
        }""",
        "image_renderer_assistant_output": "",
        "fact_validator_assistant_output": "",
        "brief_assistant_output": ""
    }

async def test_publish_script():
    """Testuje publish script samostatně"""
    print("🚀 STANDALONE TEST PUBLISH SCRIPTU")
    print("=" * 50)
    
    try:
        # Mock data
        mock_pipeline_data = create_mock_pipeline_data()
        mock_current_date = datetime.now().isoformat()
        
        print(f"📊 Pipeline data klíče: {list(mock_pipeline_data.keys())}")
        
        # Transformace
        publish_input = transform_to_PublishInput(mock_pipeline_data)
        
        print(f"✅ PublishInput připraven:")
        print(f"   📋 Title: {publish_input['title']}")
        print(f"   📄 Content length: {len(publish_input['content_html'])} chars")
        print(f"   🏷️ Keywords: {len(publish_input['meta']['keywords'])}")
        print(f"   ❓ FAQ items: {len(publish_input['faq'])}")
        print(f"   🖼️ Visuals: {len(publish_input['visuals'])}")
        
        # Spuštění scriptu
        print("\n🔧 SPOUŠTÍM PUBLISH SCRIPT...")
        html_input = {**publish_input, "format": "html"}
        output_paths = publish_script_run(html_input)
        
        print(f"\n🎉 PUBLISH SCRIPT ÚSPĚŠNÝ!")
        print(f"📁 Výsledek:")
        print(f"   📋 Title: {output_paths.get('title', 'N/A')}")
        print(f"   🏷️ Slug: {output_paths.get('slug', 'N/A')}")
        print(f"   📄 Format: {output_paths.get('format', 'N/A')}")
        print(f"   📊 Output length: {len(str(output_paths.get('output', '')))} znaků")
        print(f"   ✅ Validation: {output_paths.get('validation_passed', False)}")
        
        # Uložení výstupu pro kontrolu
        if 'output' in output_paths:
            test_output_file = f"test_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            with open(test_output_file, 'w', encoding='utf-8') as f:
                f.write(output_paths['output'])
            print(f"   💾 Test výstup uložen: {test_output_file}")
                
    except Exception as e:
        print(f"❌ TEST SELHAL: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    asyncio.run(test_publish_script())