#!/usr/bin/env python3
"""
🧪 TEST PUBLISH SCRIPTU
=======================

Test funkcionality publish_script.py s reálnými daty
"""

import json
import sys
import os
from datetime import datetime

# Přidání activities do path
sys.path.append(os.path.join(os.path.dirname(__file__), 'activities'))

from activities.publish_script import publish_script


def create_test_data():
    """Vytvoří testovací data ve formátu očekávaném scriptem"""
    
    test_data = {
        "title": "Vyplatí se auto na benzín v roce 2025? Analýza nákladů a výhod",
        "meta": {
            "description": "Zjistěte, zda je benzínový vůz v roce 2025 stále výhodnou volbou. Analyzujeme náklady, výhody a legislativní rizika.",
            "keywords": [
                "auto na benzín",
                "benzínové vozy", 
                "náklady na benzínové auto",
                "Euro 7 norma",
                "srovnání benzín a elektro",
                "výhody benzínového auta",
                "TCO benzínového vozu"
            ],
            "canonical": "https://seofarm.ai/auto-na-benzin-2025-analyza-nakladu-vyhod"
        },
        "content_html": """<article>
<h1>Vyplatí se ještě v roce 2025 auto na benzín? Kompletní analýza nákladů, výhod a rizik</h1>

<p class="lead">Rozhodování o koupi automobilu v roce 2025 přináší více komplikací než kdykoli předtím. Zatímco před pěti lety představovala volba mezi benzínem a naftou relativně přímočarou záležitost, současnost nabízí široké spektrum alternativ: elektromobily s rostoucí dostupností, přísnější emisní normy, nepředvídatelné ceny paliv a otázky kolem budoucí hodnoty vozů se spalovacími motory.</p>

<h2>Klíčové faktory rozhodování: Co se změnilo do roku 2025</h2>

<h3>Vliv normy Euro 7 a tlaku na emise</h3>
<p>Nová emisní norma Euro 7, kterou schválila Rada EU v dubnu 2024, vstoupí v platnost pro nové typy osobních automobilů přibližně na přelomu let 2026/2027. Na rozdíl od původních obav Euro 7 pro osobní vozy zachovává stávající limitní hodnoty výfukových emisí jako Euro 6, ale nově zavádí limity pro emise pevných částic z brzd a otěr pneumatik. Pro kupce benzínového vozu to znamená dvě věci: vozy splňující pouze Euro 6d budou pravděpodobně ztrácet hodnotu rychleji než modely certifikované dle Euro 7. Moderní benzínové motory s přímým vstřikováním jsou již povinně vybaveny filtrem pevných částic (GPF), který výrazně snižuje emise karcinogenních sazí.</p>

<h2>Rostoucí nabídka a klesající ceny elektromobilů a hybridů</h2>
<p>V prvním pololetí roku 2024 tvořily benzínové motory dominantních 65,84 % registrací nových osobních automobilů v ČR, zatímco registrace čistě elektrických vozů (BEV) dosáhly 3,67 % a plug-in hybridů (PHEV) 2,75 %. Tyto podíly zatím nejsou dramatické, ale cenový rozdíl se postupně snižuje. Například nová Škoda Octavia 1.5 TSI v červnu 2024 začínala na 719 900 Kč, zatímco plug-in hybridní verze Octavia iV na 969 900 Kč – rozdíl 250 000 Kč. U elektromobilu Škoda Enyaq 85 byla startovní cena 1 324 900 Kč, tedy o 605 000 Kč více než u benzínové Octavie.</p>

<h2>Nejistota ohledně cen paliv a energií</h2>
<p>Průměrná cena benzínu Natural 95 v České republice byla v červenci 2024 přibližně 39,40 Kč/l. Pro srovnání, cena silové elektřiny pro domácnosti se pohybovala okolo 3-4 Kč/kWh, zatímco nabíjení na veřejných DC stanicích stálo 13-15 Kč/kWh pro neregistrované zákazníky. Volatilita cen energií však zůstává vysoká a dlouhodobé prognózy jsou nejisté, což komplikuje kalkulace celkových nákladů na vlastnictví.</p>

<h2>Srovnání celkových nákladů na vlastnictví (TCO): Benzín vs. Hybrid vs. Elektro</h2>

<h3>Pořizovací cena: Nový vs. ojetý vůz</h3>
<p>Největší výhodou benzínových vozů zůstává dostupnost napříč všemi cenovými kategoriemi. Mediánová cena ojetého vozu s benzínovým motorem v síti AAA AUTO v prvním čtvrtletí 2024 byla 220 000 Kč, což umožňuje vstup do motorizace i s omezeným rozpočtem. U nových vozů je cenový rozdíl stále významný. Zatímco základní benzínové vozy začínají pod 400 000 Kč, nejlevnější nové elektromobily startují kolem 600 000 Kč a kvalitní plug-in hybridy nad 800 000 Kč.</p>

<h3>Náklady na palivo a energii: Modelový příklad</h3>
<p>Pro modelový příklad použijeme průměrný roční nájezd 15 000 km a reálné spotřeby. Benzínový vůz se spotřebou 7,5 l/100 km má roční spotřebu 1 125 litrů, což při ceně 39,40 Kč/l představuje roční náklady 44 325 Kč. Plug-in hybrid s kombinovaným provozem 2,5 l/100 km plus elektřina má roční náklady přibližně 25 000-30 000 Kč při 50% elektrickém provozu. Elektromobil se spotřebou 18 kWh/100 km stojí při domácím nabíjení 9 720 Kč ročně (při ceně 3,6 Kč/kWh), ale při veřejném nabíjení až 37 800 Kč ročně (při ceně 14 Kč/kWh).</p>

<h3>Servis a údržba: Kde jsou rozdíly</h3>
<p>Servisní náklady na elektromobil jsou v horizontu 5 let a 150 000 km přibližně o 35 % nižší než u srovnatelného vozu se spalovacím motorem. Elektromobily nepotřebují výměny oleje, filtrů, zapalovacích svíček ani složité opravy rozvodů. Moderní benzínové vozy však vyžadují pravidelné výměny oleje (typicky po 15 000 km), filtrů a zapalovacích svíček. Nákladnou položkou může být výměna rozvodového řetězu nebo řemenu (typicky mezi 120 000-240 000 km), která u elektromobilů zcela odpadá.</p>

<h2>Praktické výhody a nevýhody benzínového pohonu dnes</h2>

<h3>Výhoda: Neomezený dojezd a rychlost tankování</h3>
<p>Doba "tankování" benzínového vozu na plnou nádrž (600-800 km dojezdu) je přibližně 5 minut, zatímco rychlé nabití elektromobilu na 80 % kapacity (250-350 km dojezdu) trvá 25-40 minut. Pro řidiče často cestující na dlouhé vzdálenosti nebo s nepravidelným režimem jízd zůstává benzínový pohon praktičtější volbou. Síť čerpacích stanic je v ČR hustá a dostupná 24/7, zatímco počet veřejných dobíjecích bodů k 30. 6. 2024 činil 5 628, což je stále nedostatečné pro bezproblémové cestování elektromobilem po celé republice.</p>

<h3>Výhoda: Široký výběr a prověřená technika</h3>
<p>Benzínové motory představují zralou technologii s desetiletími vývoje. Moderní jednotky často využívají technologii mild-hybrid (MHEV), kde malý elektromotor pomáhá při akceleraci a snižuje spotřebu paliva o 5-10 %. Výběr benzínových vozů je nejširší ze všech pohonů – od malých městských aut za 300 000 Kč po luxusní limuzíny. Na trhu ojetých vozů je situace ještě výraznější, kde benzínové vozy dominují ve všech cenových kategoriích.</p>

<h3>Nevýhoda: Hluk a vibrace vs. ticho elektřiny</h3>
<p>Hluková zátěž v městském prostředí je u elektromobilů při nízkých rychlostech výrazně nižší než u vozů se spalovacím motorem. Teprve při rychlostech nad 50 km/h se dominantním zdrojem hluku stává valivý odpor pneumatik u obou typů pohonů. Pro řidiče zvyklé na ticho a plynulost elektrického pohonu může přechod zpět na benzínový motor působit rušivě, zejména při jízdě ve městě nebo při čekání na semaforech.</p>

<h2>Pro koho je benzínové auto stále ideální volbou?</h2>

<h3>Scénář 1: Řidič s nízkým ročním nájezdem převážně mimo město</h3>
<p>U vozů s ročním nájezdem pod 10 000 km jsou celkové náklady na vlastnictví (TCO) u benzínového vozu zpravidla nižší než u srovnatelného elektromobilu či plug-in hybridu kvůli vysoké pořizovací ceně alternativ. Úspora na palivu jednoduše nestačí kompenzovat vyšší pořizovací náklady. Navíc při převážně mimostředním provozu odpadají výhody elektromobilu (tichý chod, nulové lokální emise) a zůstávají nevýhody (omezený dojezd, nutnost plánování nabíjení).</p>

<h3>Scénář 2: Uživatel bez možnosti domácího nabíjení</h3>
<p>Bez možnosti domácího nabíjení se náklady na provoz elektromobilu dramaticky zvyšují. Nabíjení na veřejných stanicích za 13-15 Kč/kWh činí roční náklady na elektřinu srovnatelné s benzínem, ale přidává komplikace s dostupností a časovou náročností nabíjení. Pro tyto uživatele zůstává benzínový pohon praktičtější a často i ekonomičtější volbou, zejména pokud kombinují městskou a mimostředskou jízdu.</p>

<h3>Scénář 3: Kupující s omezeným rozpočtem na ojetý vůz</h3>
<p>Na trhu ojetých vozů do 300 000 Kč dominují benzínové motory. Ojeté elektromobily v této cenové kategorii jsou vzácné a často mají opotřebované baterie s omezeným dojezdem. Ojeté plug-in hybridy mohou mít problémy s bateriovým systémem, jehož oprava je nákladná. Kvalitní ojetý benzínový vůz představuje pro tuto skupinu nejbezpečnější a nejdostupnější volbu s předvídatelnými provozními náklady.</p>

<p>Rozsáhlá analýza ukazuje, že benzínové vozy mají stále své místo na trhu, zejména pro specifické skupiny uživatelů. Klíčovým faktorem je poměr mezi pořizovacími náklady, způsobem využití a dostupností alternativní infrastruktury. Ekonomická racionalita při nízkém nájezdu, flexibilita mobility a široký výběr na trhu jsou hlavní důvody, proč si v roce 2025 koupit benzínové auto.</p>

<p>Na druhou stranu je třeba uvážit dlouhodobé environmentální omezení, vyšší provozní náklady v městském provozu a klesající zůstatkovou hodnotu. Závěrem lze říci, že rozhodnutí o koupi benzínového vozu v roce 2025 by mělo být založeno na pečlivé analýze individuálních potřeb, finančních možností a očekávaného způsobu využití vozidla. Trend směřuje k elektromobilitě, ale benzínové vozy mají stále své opodstatnění v určitých scénářích použití. Vždy je důležité zvážit všechny aspekty před finálním rozhodnutím.</p>

</article>""",
        "faq": [
            {
                "question": "Je výhodné koupit benzínové auto v roce 2025?",
                "answer_html": "<p>Ano, zejména pokud máte nízký roční nájezd (pod 12 000 km) a nemáte možnost domácího nabíjení elektromobilu. Pro tyto uživatele benzínový vůz nabízí lepší ekonomickou návratnost.</p>"
            },
            {
                "question": "Jaké jsou hlavní výhody benzínového auta oproti elektromobilu?",
                "answer_html": "<p>Rychlé tankování (5 minut vs. 25-40 minut), široká dostupnost čerpacích stanic, nižší pořizovací cena a žádná závislost na nabíjecí infrastruktuře.</p>"
            },
            {
                "question": "Proč může být nevýhodné pořídit benzínový vůz?",
                "answer_html": "<p>Kvůli možným budoucím omezením vjezdu do nízkoemisních zón, vyšším provozním nákladům v městském provozu a rychlejšímu poklesu zůstatkové hodnoty ve srovnání s elektromobily.</p>"
            },
            {
                "question": "Jak ovlivní norma Euro 7 hodnotu benzínových vozů?",
                "answer_html": "<p>Vozy splňující pouze normu Euro 6d budou pravděpodobně ztrácet hodnotu rychleji než modely certifikované podle Euro 7, která vstupuje v platnost v letech 2026/2027.</p>"
            }
        ],
        "visuals": [
            {
                "image_url": "https://cdn.seofarm.ai/images/cityscape-2025-gasoline-electric.webp",
                "prompt": "A futuristic cityscape in 2025 with both gasoline and electric vehicles on the roads",
                "alt": "Srovnání benzínových a elektrických vozů v městské krajině roku 2025",
                "position": "top",
                "width": 1200,
                "height": 675
            },
            {
                "image_url": "https://cdn.seofarm.ai/images/tco-comparison-chart.webp", 
                "prompt": "A detailed vector chart comparing total cost of ownership between gasoline, hybrid, and electric cars",
                "alt": "Graf porovnávající celkové náklady na vlastnictví benzínového, hybridního a elektrického auta",
                "position": "bottom",
                "width": 800,
                "height": 600
            }
        ],
        "schema_org": {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "Vyplatí se auto na benzín v roce 2025? Analýza nákladů a výhod",
            "author": {
                "@type": "Person",
                "name": "SEO Farm Editorial"
            },
            "publisher": {
                "@type": "Organization",
                "name": "SEO Farm",
                "logo": {
                    "@type": "ImageObject",
                    "url": "https://seofarm.ai/logo.png"
                }
            },
            "datePublished": "2025-08-04T10:00:00Z",
            "dateModified": "2025-08-04T10:00:00Z",
            "image": "https://cdn.seofarm.ai/images/cityscape-2025-gasoline-electric.webp",
            "articleBody": "Rozhodování o koupi automobilu v roce 2025..."
        },
        "format": "html",
        "language": "cs",
        "date_published": "2025-08-04T10:00:00Z"
    }
    
    return test_data


def test_html_export():
    """Test HTML exportu"""
    print("🧪 TEST HTML EXPORT")
    
    test_data = create_test_data()
    test_data["format"] = "html"
    
    try:
        result = publish_script(test_data)
        
        print("✅ HTML export úspěšný")
        print(f"📄 Délka HTML: {len(result['output'])} znaků")
        print(f"🏷️ Title: {result['title']}")
        print(f"🔗 Slug: {result['slug']}")
        
        # Uložení pro kontrolu
        with open("test_output.html", "w", encoding="utf-8") as f:
            f.write(result["output"])
        print("💾 HTML uložen do test_output.html")
        
        return True
        
    except Exception as e:
        print(f"❌ HTML export selhal: {e}")
        return False


def test_json_export():
    """Test JSON exportu"""
    print("\n🧪 TEST JSON EXPORT")
    
    test_data = create_test_data()
    test_data["format"] = "json"
    
    try:
        result = publish_script(test_data)
        
        print("✅ JSON export úspěšný")
        print(f"📊 JSON keys: {list(result['output'].keys())}")
        print(f"🏷️ Title: {result['title']}")
        print(f"🔗 Slug: {result['slug']}")
        
        # Uložení pro kontrolu  
        with open("test_output.json", "w", encoding="utf-8") as f:
            json.dump(result["output"], f, ensure_ascii=False, indent=2)
        print("💾 JSON uložen do test_output.json")
        
        return True
        
    except Exception as e:
        print(f"❌ JSON export selhal: {e}")
        return False


def test_wordpress_export():
    """Test WordPress exportu"""
    print("\n🧪 TEST WORDPRESS EXPORT")
    
    test_data = create_test_data()
    test_data["format"] = "wordpress"
    
    try:
        result = publish_script(test_data)
        
        print("✅ WordPress export úspěšný")
        print(f"📋 WP fields: {list(result['output'].keys())}")
        print(f"🏷️ Post title: {result['output']['post_title']}")
        print(f"🔗 Post name: {result['output']['post_name']}")
        
        # Uložení pro kontrolu
        with open("test_output_wordpress.json", "w", encoding="utf-8") as f:
            json.dump(result["output"], f, ensure_ascii=False, indent=2)
        print("💾 WordPress JSON uložen do test_output_wordpress.json")
        
        return True
        
    except Exception as e:
        print(f"❌ WordPress export selhal: {e}")
        return False


def test_validation_errors():
    """Test validačních chyb"""
    print("\n🧪 TEST VALIDAČNÍCH CHYB")
    
    # Test 1: Příliš krátký title
    test_data = create_test_data()
    test_data["title"] = ""
    
    try:
        publish_script(test_data)
        print("❌ Validace prázdného titulu selhala")
    except ValueError as e:
        print(f"✅ Správně zachycena chyba prázdného titulu: {e}")
    
    # Test 2: Málo FAQ
    test_data = create_test_data()
    test_data["faq"] = test_data["faq"][:2]  # Pouze 2 FAQ místo 3+
    
    try:
        publish_script(test_data)
        print("❌ Validace počtu FAQ selhala")
    except ValueError as e:
        print(f"✅ Správně zachycena chyba počtu FAQ: {e}")
    
    # Test 3: Špatný počet visuals
    test_data = create_test_data()
    test_data["visuals"] = test_data["visuals"][:1]  # Pouze 1 visual místo 2
    
    try:
        publish_script(test_data)
        print("❌ Validace počtu visuals selhala")
    except ValueError as e:
        print(f"✅ Správně zachycena chyba počtu visuals: {e}")


def main():
    """Hlavní test funkce"""
    print("🚀 SPOUŠTÍM TESTY PUBLISH SCRIPTU")
    print("=" * 50)
    
    tests_passed = 0
    
    # HTML test
    if test_html_export():
        tests_passed += 1
    
    # JSON test
    if test_json_export():
        tests_passed += 1
    
    # WordPress test
    if test_wordpress_export():
        tests_passed += 1
    
    # Validační testy
    test_validation_errors()
    
    print(f"\n🎯 VÝSLEDKY: {tests_passed}/3 exportních testů prošlo")
    
    if tests_passed == 3:
        print("🎉 VŠECHNY TESTY ÚSPĚŠNÉ! Publish script je funkční.")
    else:
        print("⚠️ Některé testy selhaly, zkontrolujte chyby výše.")


if __name__ == "__main__":
    main()