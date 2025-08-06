#!/usr/bin/env python3
"""
🧪 TEST INTEGRACE PUBLISH SCRIPTU
================================

Test napojení publish_activity do pipeline
"""

import sys
import os
from datetime import datetime

# Přidání cest
sys.path.append(os.path.join(os.path.dirname(__file__), 'activities'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'helpers'))

from activities.publish_activity import test_publish_activity_locally
from helpers.transformers import transform_to_PublishInput


def create_mock_pipeline_data():
    """Vytvoří mock data ze simulované pipeline"""
    
    return {
        "seo_assistant_output": """
        {
            "title": "Vyplatí se auto na benzín v roce 2025? Analýza nákladů a výhod",
            "description": "Zjistěte, zda je benzínový vůz v roce 2025 stále výhodnou volbou. Analyzujeme náklady, výhody a legislativní rizika.",
            "keywords": ["auto na benzín", "benzínové vozy", "náklady na benzínové auto", "Euro 7 norma", "srovnání benzín a elektro", "výhody benzínového auta", "TCO benzínového vozu"],
            "canonical": "https://seofarm.ai/auto-na-benzin-2025-analyza-nakladu-vyhod"
        }
        """,
        
        "draft_assistant_output": """<article>
<h1>Vyplatí se ještě v roce 2025 auto na benzín? Kompletní analýza nákladů, výhod a rizik</h1>

<p class="lead">Rozhodování o koupi automobilu v roce 2025 přináší více komplikací než kdykoli předtím. Zatímco před pěti lety představovala volba mezi benzínem a naftou relativně přímočarou záležitost, současnost nabízí široké spektrum alternativ: elektromobily s rostoucí dostupností, přísnější emisní normy, nepředvídatelné ceny paliv a otázky kolem budoucí hodnoty vozů se spalovacími motory.</p>

<h2>Klíčové faktory rozhodování: Co se změnilo do roku 2025</h2>

<p>Nová emisní norma Euro 7, kterou schválila Rada EU v dubnu 2024, vstoupí v platnost pro nové typy osobních automobilů přibližně na přelomu let 2026/2027. Pro kupce benzínového vozu to znamená dvě věci: vozy splňující pouze Euro 6d budou pravděpodobně ztrácet hodnotu rychleji než modely certifikované dle Euro 7.</p>

<h2>Rostoucí nabídka a klesající ceny elektromobilů a hybridů</h2>

<p>V prvním pololetí roku 2024 tvořily benzínové motory dominantních 65,84 % registrací nových osobních automobilů v ČR, zatímco registrace čistě elektrických vozů (BEV) dosáhly 3,67 % a plug-in hybridů (PHEV) 2,75 %. Tyto podíly zatím nejsou dramatické, ale cenový rozdíl se postupně snižuje.</p>

<h2>Nejistota ohledně cen paliv a energií</h2>

<p>Průměrná cena benzínu Natural 95 v České republice byla v červenci 2024 přibližně 39,40 Kč/l. Pro srovnání, cena silové elektřiny pro domácnosti se pohybovala okolo 3-4 Kč/kWh, zatímco nabíjení na veřejných DC stanicích stálo 13-15 Kč/kWh pro neregistrované zákazníky.</p>

<h2>Srovnání celkových nákladů na vlastnictví (TCO): Benzín vs. Hybrid vs. Elektro</h2>

<p>Největší výhodou benzínových vozů zůstává dostupnost napříč všemi cenovými kategoriemi. Mediánová cena ojetého vozu s benzínovým motorem v síti AAA AUTO v prvním čtvrtletí 2024 byla 220 000 Kč, což umožňuje vstup do motorizace i s omezeným rozpočtem.</p>

<h2>Praktické výhody a nevýhody benzínového pohonu dnes</h2>

<p>Doba "tankování" benzínového vozu na plnou nádrž (600-800 km dojezdu) je přibližně 5 minut, zatímco rychlé nabití elektromobilu na 80 % kapacity (250-350 km dojezdu) trvá 25-40 minut. Pro řidiče často cestující na dlouhé vzdálenosti nebo s nepravidelným režimem jízd zůstává benzínový pohon praktičtější volbou.</p>

<h2>Pro koho je benzínové auto stále ideální volbou?</h2>

<h2>Náklady na palivo a energii: Modelový příklad</h2>

<p>Pro modelový příklad použijeme průměrný roční nájezd 15 000 km a reálné spotřeby. Benzínový vůz se spotřebou 7,5 l/100 km má roční spotřebu 1 125 litrů, což při ceně 39,40 Kč/l představuje roční náklady 44 325 Kč. Plug-in hybrid s kombinovaným provozem 2,5 l/100 km plus elektřina má roční náklady přibližně 25 000-30 000 Kč při 50% elektrickém provozu. Elektromobil se spotřebou 18 kWh/100 km stojí při domácím nabíjení 9 720 Kč ročně (při ceně 3,6 Kč/kWh), ale při veřejném nabíjení až 37 800 Kč ročně (při ceně 14 Kč/kWh).</p>

<h2>Servis a údržba: Kde jsou rozdíly</h2>

<p>Servisní náklady na elektromobil jsou v horizontu 5 let a 150 000 km přibližně o 35 % nižší než u srovnatelného vozu se spalovacím motorem. Elektromobily nepotřebují výměny oleje, filtrů, zapalovacích svíček ani složité opravy rozvodů. Moderní benzínové vozy však vyžadují pravidelné výměny oleje (typicky po 15 000 km), filtrů a zapalovacích svíček. Nákladnou položkou může být výměna rozvodového řetězu nebo řemenu (typicky mezi 120 000-240 000 km), která u elektromobilů zcela odpadá.</p>

<h2>Výhoda: Široký výběr a prověřená technika</h2>

<p>Benzínové motory představují zralou technologii s desetiletími vývoje. Moderní jednotky často využívají technologii mild-hybrid (MHEV), kde malý elektromotor pomáhá při akceleraci a snižuje spotřebu paliva o 5-10 %. Výběr benzínových vozů je nejširší ze všech pohonů – od malých městských aut za 300 000 Kč po luxusní limuzíny. Na trhu ojetých vozů je situace ještě výraznější, kde benzínové vozy dominují ve všech cenových kategoriích.</p>

<h2>Nevýhoda: Hluk a vibrace vs. ticho elektřiny</h2>

<p>Hluková zátěž v městském prostředí je u elektromobilů při nízkých rychlostech výrazně nižší než u vozů se spalovacím motorem. Teprve při rychlostech nad 50 km/h se dominantním zdrojem hluku stává valivý odpor pneumatik u obou typů pohonů. Pro řidiče zvyklé na ticho a plynulost elektrického pohonu může přechod zpět na benzínový motor působit rušivě, zejména při jízdě ve městě nebo při čekání na semaforech.</p>

<h2>Scénář 1: Řidič s nízkým ročním nájezdem převážně mimo město</h2>

<p>U vozů s ročním nájezdem pod 10 000 km jsou celkové náklady na vlastnictví (TCO) u benzínového vozu zpravidla nižší než u srovnatelného elektromobilu či plug-in hybridu kvůli vysoké pořizovací ceně alternativ. Úspora na palivu jednoduše nestačí kompenzovat vyšší pořizovací náklady. Navíc při převážně mimostředním provozu odpadají výhody elektromobilu (tichý chod, nulové lokální emise) a zůstávají nevýhody (omezený dojezd, nutnost plánování nabíjení).</p>

<h2>Scénář 2: Uživatel bez možnosti domácího nabíjení</h2>

<p>Bez možnosti domácího nabíjení se náklady na provoz elektromobilu dramaticky zvyšují. Nabíjení na veřejných stanicích za 13-15 Kč/kWh činí roční náklady na elektřinu srovnatelné s benzínem, ale přidává komplikace s dostupností a časovou náročností nabíjení. Pro tyto uživatele zůstává benzínový pohon praktičtější a často i ekonomičtější volbou, zejména pokud kombinují městskou a mimostředskou jízdu.</p>

<h2>Scénář 3: Kupující s omezeným rozpočtem na ojetý vůz</h2>

<p>Na trhu ojetých vozů do 300 000 Kč dominují benzínové motory. Ojeté elektromobily v této cenové kategorii jsou vzácné a často mají opotřebované baterie s omezeným dojezdem. Ojeté plug-in hybridy mohou mít problémy s bateriovým systémem, jehož oprava je nákladná. Kvalitní ojetý benzínový vůz představuje pro tuto skupinu nejbezpečnější a nejdostupnější volbu s předvídatelnými provozními náklady.</p>

<h2>Budoucí výhled: Co čekat v následujících letech</h2>

<p>Bezpečnostní a emisní standardy budou v následujících letech nadále zpřísňovány. Evropská unie plánuje postupné zavádění nízkoemisních zón ve všech městech nad 100 000 obyvatel do roku 2030. Benzínové vozy splňující normu Euro 6d-ISC-FCM by měly mít zaručený přístup do těchto zón minimálně do roku 2035, ale situace se může měnit v závislosti na lokální politice jednotlivých měst.</p>

<h2>Technologické inovace v benzínových motorech</h2>

<p>Výrobci automobilů nadále investují do vývoje benzínových motorů s vyšší účinností. Moderní technologie jako variabilní časování ventilů, přímé vstřikování paliva s vysokým tlakem, turbodmychadla s variabilní geometrií a pokročilé systémy řízení motoru umožňují dosáhnout výrazně nižší spotřeby než u vozů starších deseti let. Některé nejmodernější benzínové jednotky dosahují kombinované spotřeby pod 5 litrů na 100 kilometrů i u vozů vyšší střední třídy.</p>

<h2>Finanční aspekty a dostupnost úvěrů</h2>

<p>Financování nákupu automobilu představuje pro většinu kupujících klíčový faktor. Benzínové vozy mají obecně nižší pořizovací cenu, což se pozitivně odráží ve výši splátek úvěru nebo leasingu. Zatímco leasing na elektromobil za 800 000 Kč může znamenat měsíční splátku 15 000-20 000 Kč, srovnatelný benzínový vůz za 500 000 Kč vyjde na 10 000-13 000 Kč měsíčně. Tento rozdíl může rozhodovat především u rodin se středními příjmy.</p>

<h2>Regionální dostupnost a servisní síť</h2>

<p>Jedna z často opomíjených výhod benzínových vozů je rozsáhlá servisní síť. Zatímco autorizované servisy pro elektromobily jsou koncentrovány především ve větších městech, benzínové vozy lze nechat opravit prakticky kdekoliv. To je zvláště důležité pro uživatele žijící na venkově nebo často cestující do méně rozvinutých regionů. Navíc náhradní díly pro benzínové motory jsou obecně dostupnější a levnější než komponenty elektrických pohonů.</p>

<p>Rozsáhlá analýza ukazuje, že benzínové vozy mají stále své místo na trhu, zejména pro specifické skupiny uživatelů. Klíčovým faktorem je poměr mezi pořizovacími náklady, způsobem využití a dostupností alternativní infrastruktury. Ekonomická racionalita při nízkém nájezdu, flexibilita mobility a široký výběr na trhu jsou hlavní důvody, proč si v roce 2025 koupit benzínové auto. Na druhou stranu je třeba uvážit dlouhodobé environmentální omezení, vyšší provozní náklady v městském provozu a klesající zůstatkovou hodnotu. Závěrem lze říci, že rozhodnutí o koupi benzínového vozu v roce 2025 by mělo být založeno na pečlivé analýze individuálních potřeb, finančních možností a očekávaného způsobu využití vozidla. Trend směřuje k elektromobilitě, ale benzínové vozy mají stále své opodstatnění v určitých scénářích použití. Vždy je důležité zvážit všechny aspekty před finálním rozhodnutím.</p>

</article>""",
        
        "humanizer_assistant_output": "",  # Prázdný - použije se draft
        
        "qa_assistant_output": """
        [
            {
                "question": "Je výhodné koupit benzínové auto v roce 2025?",
                "answer": "Ano, zejména pokud máte nízký roční nájezd (pod 12 000 km) a nemáte možnost domácího nabíjení elektromobilu. Pro tyto uživatele benzínový vůz nabízí lepší ekonomickou návratnost."
            },
            {
                "question": "Jaké jsou hlavní výhody benzínového auta oproti elektromobilu?",
                "answer": "Rychlé tankování (5 minut vs. 25-40 minut), široká dostupnost čerpacích stanic, nižší pořizovací cena a žádná závislost na nabíjecí infrastruktuře."
            },
            {
                "question": "Proč může být nevýhodné pořídit benzínový vůz?",
                "answer": "Kvůli možným budoucím omezením vjezdu do nízkoemisních zón, vyšším provozním nákladům v městském provozu a rychlejšímu poklesu zůstatkové hodnoty ve srovnání s elektromobily."
            },
            {
                "question": "Jak ovlivní norma Euro 7 hodnotu benzínových vozů?",
                "answer": "Vozy splňující pouze normu Euro 6d budou pravděpodobně ztrácet hodnotu rychleji než modely certifikované podle Euro 7, která vstupuje v platnost v letech 2026/2027."
            }
        ]
        """,
        
        "multimedia_assistant_output": "Generováno: 2 obrázky pro článek o benzínových vozech",
        
        "image_renderer_assistant_output": """
        [
            {
                "url": "https://cdn.seofarm.ai/images/cityscape-2025-gasoline-electric.webp",
                "prompt": "A futuristic cityscape in 2025 with both gasoline and electric vehicles on the roads",
                "alt": "Srovnání benzínových a elektrických vozů v městské krajině roku 2025"
            },
            {
                "url": "https://cdn.seofarm.ai/images/tco-comparison-chart.webp", 
                "prompt": "A detailed vector chart comparing total cost of ownership between gasoline, hybrid, and electric cars",
                "alt": "Graf porovnávající celkové náklady na vlastnictví benzínového, hybridního a elektrického auta"
            }
        ]
        """,
        
        "fact_validator_assistant_output": "Fakta ověřena a validována",
        "brief_assistant_output": "Brief vytvořen pro téma benzínové vozy 2025"
    }


def test_transformer():
    """Test transformačních funkcí"""
    print("🔄 TESTING TRANSFORMER FUNCTIONS")
    print("=" * 40)
    
    pipeline_data = create_mock_pipeline_data()
    pipeline_data["current_date"] = datetime.now().isoformat() + "Z"
    
    try:
        publish_input = transform_to_PublishInput(pipeline_data)
        
        print("✅ Transformace úspěšná")
        print(f"📋 Title: {publish_input['title']}")
        print(f"🏷️ Keywords: {len(publish_input['meta']['keywords'])}")
        print(f"📄 Content length: {len(publish_input['content_html'])} chars")
        print(f"❓ FAQ items: {len(publish_input['faq'])}")
        print(f"🖼️ Visuals: {len(publish_input['visuals'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Transformace selhala: {e}")
        return False


def test_activity():
    """Test publish_activity lokálně"""
    print("\n🔧 TESTING PUBLISH ACTIVITY")
    print("=" * 40)
    
    pipeline_data = create_mock_pipeline_data()
    
    try:
        result = test_publish_activity_locally(pipeline_data)
        
        print("✅ Publish Activity úspěšná")
        print(f"📋 Title: {result['title']}")
        print(f"📄 HTML length: {result['html_length']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Publish Activity selhala: {e}")
        return False


def main():
    """Hlavní test funkce"""
    print("🚀 TESTING PUBLISH INTEGRATION")
    print("=" * 50)
    
    tests_passed = 0
    
    # Test transformace
    if test_transformer():
        tests_passed += 1
    
    # Test activity
    if test_activity():
        tests_passed += 1
    
    print(f"\n🎯 VÝSLEDKY: {tests_passed}/2 testů prošlo")
    
    if tests_passed == 2:
        print("🎉 VŠECHNY TESTY ÚSPĚŠNÉ! Integrace je připravena.")
        print("🚀 Připraveno pro restart systému a testování pipeline.")
    else:
        print("⚠️ Některé testy selhaly, zkontrolujte chyby výše.")


if __name__ == "__main__":
    main()