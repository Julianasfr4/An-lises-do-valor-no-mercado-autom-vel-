#!/usr/bin/env python3
"""
olx_car_scraper.py
---------------------------------------------------------------------
Scraper unificado de anúncios de carros do OLX Portugal.
Suporta extração rápida e detalhada (imagens, potência, cilindrada, cor, etc.).
Garante limpeza e normalização robusta de marcas e modelos para o motor de IA.
---------------------------------------------------------------------
"""

import argparse
import json
import os
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm

# -- Importação do driver ----------------------------------------------
try:
    import undetected_chromedriver as uc
    DRIVER_MODE = "undetected"
except ImportError:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    DRIVER_MODE = "selenium"
    print("[AVISO] undetected-chromedriver nao instalado. A usar selenium padrao.")
    print("        Para melhor fiabilidade: pip install undetected-chromedriver\n")

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# -- Configuração ------------------------------------------------------
BASE_URL = "https://www.olx.pt/carros-motos-e-barcos/carros/"
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

# Map of known brands to solve messy titles
BRAND_MAP = {
    "mercedes-benz": "Mercedes-Benz", "mercedes": "Mercedes-Benz", "marcedes": "Mercedes-Benz",
    "bmw": "BMW", "audi": "Audi", "peugeot": "Peugeot", "renault": "Renault",
    "volkswagen": "Volkswagen", "vw": "Volkswagen", "toyota": "Toyota", "citroen": "Citroen",
    "citroën": "Citroen", "porsche": "Porsche", "ford": "Ford", "opel": "Opel",
    "tesla": "Tesla", "volvo": "Volvo", "fiat": "Fiat", "nissan": "Nissan",
    "mini": "Mini", "hyundai": "Hyundai", "byd": "BYD", "honda": "Honda",
    "smart": "Smart", "seat": "Seat", "alfa romeo": "Alfa Romeo", "alfa": "Alfa Romeo",
    "land rover": "Land Rover", "land": "Land Rover", "range rover": "Land Rover",
    "range": "Land Rover", "mazda": "Mazda", "cupra": "Cupra", "polestar": "Polestar",
    "class": "Mercedes-Benz", "jaguar": "Jaguar", "dacia": "Dacia", "mitsubishi": "Mitsubishi",
    "kia": "Kia", "chevrolet": "Chevrolet", "chervolet": "Chevrolet", "bentley": "Bentley",
    "ds": "DS", "mg": "MG", "skoda": "Skoda", "saab": "Saab", "dodge": "Dodge",
    "ferrari": "Ferrari", "aston martin": "Aston Martin", "aston": "Aston Martin",
    "moke": "Moke", "jeep": "Jeep", "suzuki": "Suzuki", "microcar": "Microcar",
    "subaru": "Subaru", "lancia": "Lancia", "rover": "Rover"
}

MODEL_TO_BRAND = {
    "punto": ("Fiat", "Punto"), "laguna": ("Renault", "Laguna"), "defender": ("Land Rover", "Defender"),
    "clio": ("Renault", "Clio"), "megane": ("Renault", "Megane"), "golf": ("Volkswagen", "Golf"),
    "corsa": ("Opel", "Corsa"), "astra": ("Opel", "Astra"), "ibiza": ("Seat", "Ibiza"),
    "civic": ("Honda", "Civic")
}

def clean_title_make_model(titulo):
    """Clean title to extract standardized brand and model"""
    titulo_limpo = str(titulo).strip()
    titulo_lower = titulo_limpo.lower()
    
    # First check model_to_brand fallback if title starts with one of these
    partes_low = titulo_lower.split()
    first_word = partes_low[0] if partes_low else ""
    if first_word in MODEL_TO_BRAND:
        brand, model = MODEL_TO_BRAND[first_word]
        rest = titulo_limpo[len(first_word):].strip()
        model_details = (first_word + " " + " ".join(rest.split()[:2])).strip()
        return brand, model_details
        
    # Search for known brand in title
    for brand_key, brand_norm in BRAND_MAP.items():
        if brand_key in titulo_lower:
            idx = titulo_lower.find(brand_key)
            words_after = titulo_limpo[idx + len(brand_key):].strip().split()
            model = " ".join(words_after[:2]) if words_after else "Outro"
            return brand_norm, model
            
    # Fallback to splitting first words
    partes = titulo_limpo.split()
    if len(partes) >= 1:
        make = partes[0]
        make = re.sub(r'^[^\w]+', '', make)
        make = BRAND_MAP.get(make.lower(), make.title())
    else:
        make = "Desconhecido"
        
    model = " ".join(partes[1:3]) if len(partes) >= 2 else "Outro"
    return make, model

# -- Driver ------------------------------------------------------------
def criar_driver(headless: bool = True):
    if DRIVER_MODE == "undetected":
        opts = uc.ChromeOptions()
        if headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument(f"--user-agent={random.choice(USER_AGENTS)}")
        opts.add_argument("--lang=pt-PT")
        opts.add_argument("--window-size=1440,900")
        opts.add_argument('--ignore-certificate-errors')
        opts.add_argument('--log-level=3')
        opts.add_argument('--disable-popup-blocking')
        driver = uc.Chrome(options=opts, version_main=149)
    else:
        opts = Options()
        if headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        driver = webdriver.Chrome(options=opts)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    driver.implicitly_wait(8)
    return driver

# -- Filtro de ano e preco ---------------------------------------------
def passa_filtros(dados: dict, ano_min, ano_max, preco_min, preco_max) -> tuple[bool, str]:
    ano    = dados.get("ano")
    preco  = dados.get("preco_eur")

    if ano is not None:
        if ano_min is not None and ano < ano_min:
            return False, f"ano {ano} < minimo {ano_min}"
        if ano_max is not None and ano > ano_max:
            return False, f"ano {ano} > maximo {ano_max}"

    if preco is not None:
        if preco_min is not None and preco < preco_min:
            return False, f"preco {preco}E < minimo {preco_min}E"
        if preco_max is not None and preco > preco_max:
            return False, f"preco {preco}E > maximo {preco_max}E"

    return True, ""

# -- Parsing do cartão de listagem -------------------------------------
def parsear_card(card_soup) -> dict:
    dados = {
        "marca":        None,
        "modelo":       None,
        "ano":          None,
        "km":           None,
        "preco_eur":    None,
        "combustivel":  None,
        "transmissao":  None,
        "condicao":     None,
        "localizacao":  None,
        "data_anuncio": None,
        "url":          None,
        "titulo":       None,
        "imagem_url":   None,
    }

    # -- Titulo --------------------------------------------------------
    titulo_el = (
        card_soup.find("h4") or
        card_soup.find("h6") or
        card_soup.find(attrs={"data-cy": "ad-card-title"}) or
        card_soup.find(class_=re.compile(r"title|Title"))
    )
    if titulo_el:
        dados["titulo"] = titulo_el.get_text(" ", strip=True)
        # Standardize brand and model using title parser
        dados["marca"], dados["modelo"] = clean_title_make_model(dados["titulo"])

        m_ano = re.search(r'\b(19[89]\d|20[0-3]\d)\b', dados["titulo"])
        if m_ano:
            dados["ano"] = int(m_ano.group())

    # -- URL -----------------------------------------------------------
    link = card_soup.find("a", href=re.compile(r"/anuncio/"))
    if not link:
        link = card_soup.find("a", href=re.compile(r"olx\.pt"))
    if link:
        href = link.get("href", "")
        dados["url"] = href if href.startswith("http") else f"https://www.olx.pt{href}"

    # -- Imagem (OLX CDN) ----------------------------------------------
    img_el = card_soup.find("img", src=re.compile(r'apollo\.olxcdn\.com'))
    if not img_el:
        todas_imgs = card_soup.find_all("img")
        for img in todas_imgs:
            link_real = img.get("data-src") or img.get("srcset") or img.get("src")
            if link_real and "apollo.olxcdn.com" in link_real:
                img_el = img
                break
    if img_el:
        src = img_el.get("data-src") or img_el.get("srcset") or img_el.get("src") or ""
        if " " in src:
            src = src.split(" ")[0]
        dados["imagem_url"] = src

    # -- Preco ---------------------------------------------------------
    preco_el = (
        card_soup.find(attrs={"data-testid": "ad-price"}) or
        card_soup.find(class_=re.compile(r"[Pp]rice|[Pp]reco|[Vv]alor")) or
        card_soup.find("strong", string=re.compile(r"E|\d"))
    )
    if preco_el:
        txt = preco_el.get_text(strip=True)
        numeros = re.sub(r"[^\d]", "", txt.replace(".", "").replace(",", ""))
        if numeros:
            dados["preco_eur"] = int(numeros)

    # -- Localizacao + Data --------------------------------------------
    loc_date_el = card_soup.find(attrs={"data-testid": "location-date"})
    if loc_date_el:
        txt = loc_date_el.get_text(" ", strip=True)
        partes = txt.split(" - ", 1)
        if len(partes) == 2:
            dados["localizacao"]  = partes[0].strip()
            dados["data_anuncio"] = partes[1].strip()
        else:
            dados["localizacao"] = txt.strip()

    # -- KM (icone de quilometragem no cartao) -------------------------
    km_icon = card_soup.find(attrs={"data-testid": "millage-card-param-icon"})
    if km_icon:
        km_span = km_icon.find_parent("span")
        if km_span:
            km_txt = km_span.get_text(strip=True)
            m = re.sub(r"[^\d]", "", km_txt)
            if m:
                if len(m) >= 4 and 1980 <= int(m[:4]) <= 2026:
                    if dados["ano"] is None:
                        dados["ano"] = int(m[:4])
                    if len(m) > 4:
                        dados["km"] = int(m[4:])
                else:
                    dados["km"] = int(m)

    # -- Fallback para km se nao encontrou pelo icone ------------------
    if dados["km"] is None:
        spans = card_soup.find_all(["span", "li", "p"])
        for s in spans:
            txt_low = s.get_text(strip=True).lower()
            m = re.search(r'(\d[\d\s\.]*)\s*km', txt_low)
            if m:
                km_val = re.sub(r'[\s\.]', '', m.group(1))
                if km_val.isdigit():
                    dados["km"] = int(km_val)
                    break
            else:
                numbers = re.findall(r'\b\d{4,6}\b', txt_low)
                for num in numbers:
                    if len(num) == 4 and 1980 <= int(num) <= 2026:
                        continue
                    dados["km"] = int(num)
                    break

    # -- Combustivel / Transmissao / Condicao (se visiveis no cartao) --
    param_textos = []
    for sel in ["[data-testid='param-value']", "span[class*='param']", "li[class*='param']"]:
        els = card_soup.select(sel)
        if els:
            param_textos = [e.get_text(strip=True) for e in els]
            break

    for txt in param_textos:
        txt_low = txt.lower()
        if dados["ano"] is None:
            m = re.search(r'\b(19[89]\d|20[0-2]\d)\b', txt)
            if m:
                dados["ano"] = int(m.group())
        if dados["combustivel"] is None:
            for c in ["gasolina", "diesel", "gasoleo", "eletrico", "hibrido", "gpl", "gnv", "plug-in"]:
                if c in txt_low:
                    dados["combustivel"] = txt.strip()
                    break
        if dados["transmissao"] is None:
            for t in ["manual", "automatico", "semi-automatico"]:
                if t in txt_low:
                    dados["transmissao"] = txt.strip()
                    break
        if dados["condicao"] is None:
            for cond in ["usado", "novo", "recondicionado"]:
                if cond in txt_low:
                    dados["condicao"] = txt.strip()
                    break

    return dados

# -- Parsing da pagina de detalhe --------------------------------------
def parsear_detalhe(driver, url: str) -> dict:
    extra = {
        "descricao":     None,
        "potencia_cv":   None,
        "num_portas":    None,
        "cor":           None,
        "cilindrada_cc": None,
        "vendedor":      None,
        "ano":           None,
        "km":            None,
        "combustivel":   None,
        "transmissao":   None,
        "condicao":      None,
        "imagem_url":    None,
    }
    try:
        driver.get(url)
        esperar(driver, "[data-cy='ad_description'], .css-bgzo2k, h1", timeout=8)
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Descricao
        desc_el = (
            soup.find(attrs={"data-cy": "ad_description"}) or
            soup.find(class_=re.compile(r"[Dd]esc"))
        )
        if desc_el:
            extra["descricao"] = desc_el.get_text(" ", strip=True)[:500]

        # Imagem real fallback
        img_tag = soup.find("img", src=re.compile(r'apollo\.olxcdn\.com'))
        if img_tag and img_tag.get("src"):
            extra["imagem_url"] = img_tag.get("src")

        param_items = (
            soup.select("[data-testid='ad-detail-params'] li") or
            soup.select("[class*='params'] li") or
            soup.select("[class*='param'] li") or
            soup.find_all(["li", "div", "p"], class_=re.compile(r"[Pp]aram|[Dd]etail|[Ff]eature"))
        )

        for item in param_items:
            txt      = item.get_text(" ", strip=True)
            txt_low  = txt.lower()

            if extra["ano"] is None:
                m = re.search(r'\b(19[89]\d|20[0-2]\d)\b', txt)
                if m:
                    extra["ano"] = int(m.group())

            if extra["km"] is None:
                m = re.search(r'([\d\s\.]+)\s*km', txt_low)
                if m:
                    val = re.sub(r'[\s\.]', '', m.group(1))
                    if val.isdigit():
                        extra["km"] = int(val)

            if extra["combustivel"] is None:
                for c in ["gasolina", "diesel", "gasoleo", "eletrico", "hibrido", "gpl", "gnv", "plug-in"]:
                    if c in txt_low:
                        extra["combustivel"] = txt.strip()
                        break

            if extra["transmissao"] is None:
                for t in ["manual", "automatico", "semi-automatico"]:
                    if t in txt_low:
                        extra["transmissao"] = txt.strip()
                        break

            if extra["condicao"] is None:
                for cond in ["usado", "novo", "recondicionado"]:
                    if cond in txt_low:
                        extra["condicao"] = txt.strip()
                        break

            if extra["potencia_cv"] is None:
                if "cv" in txt_low or "cavalos" in txt_low or "potência" in txt_low or "potencia" in txt_low:
                    m = re.search(r'(\d+)\s*(?:cv|cavalos)', txt_low)
                    if m:
                        extra["potencia_cv"] = int(m.group(1))
                    else:
                        m_val = re.search(r'\b(\d{2,3})\b', txt_low)
                        if m_val:
                            extra["potencia_cv"] = int(m_val.group(1))

            if extra["num_portas"] is None:
                if "port" in txt_low:
                    m = re.search(r'(\d)\s*port', txt_low)
                    if m:
                        extra["num_portas"] = int(m.group(1))

            if extra["cor"] is None:
                if "cor" in txt_low or "color" in txt_low:
                    val = re.sub(r'cor[:\s]*', '', txt, flags=re.IGNORECASE).strip()
                    if val and len(val) < 30:
                        extra["cor"] = val

            if extra["cilindrada_cc"] is None:
                if "cc" in txt_low or "cilindrada" in txt_low:
                    m = re.search(r'(\d{3,5})\s*(?:cc|cm3)', txt_low)
                    if m:
                        extra["cilindrada_cc"] = int(m.group(1))

        vend_el = soup.find(class_=re.compile(r"[Ss]eller|[Vv]endedor|[Uu]ser"))
        if vend_el:
            extra["vendedor"] = vend_el.get_text(strip=True)[:60]

    except Exception as e:
        print(f"  [AVISO] Falha ao ler detalhe: {e}")

    return extra

# -- Utilitarios -------------------------------------------------------
def esperar(driver, seletor_css, timeout=10):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, seletor_css))
        )
    except Exception:
        pass

def fechar_cookies(driver):
    seletores = [
        "[id*='onetrust-accept']",
        "[class*='cookie'] button",
        "button[id*='accept']",
        "#didomi-notice-agree-button",
    ]
    for sel in seletores:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, sel)
            btn.click()
            time.sleep(0.5)
            return
        except Exception:
            continue

def pausa():
    time.sleep(random.uniform(1.8, 4.2))

def construir_url(pagina: int, marca: str = None) -> str:
    if marca:
        url = f"https://www.olx.pt/carros-motos-e-barcos/carros/{marca.lower()}/"
    else:
        url = BASE_URL
    return url + f"?page={pagina}"

def exportar(registos: list, caminho_base: str, formato: str):
    if not registos:
        print("Nenhum registo para exportar.")
        return

    df = pd.DataFrame(registos)
    df = df.drop_duplicates(subset=["url"]).reset_index(drop=True)
    
    exportados = []

    # Clean the path to avoid double extensions
    p = Path(caminho_base)
    parent_dir = p.parent
    base_name = p.stem
    if base_name.endswith(".csv") or base_name.endswith(".json"):
        base_name = Path(base_name).stem
        
    caminho_sem_ext = str(parent_dir / base_name)

    if formato in ("csv", "ambos"):
        f_csv = f"{caminho_sem_ext}.csv"
        df.to_csv(f_csv, index=False, encoding='utf-8-sig')
        exportados.append(f_csv)

    if formato in ("json", "ambos"):
        f_json = f"{caminho_sem_ext}.json"
        df.to_json(f_json, orient="records", force_ascii=False, indent=2)
        exportados.append(f_json)

    print(f"\n[OK] {len(df)} anuncios exportados:")
    for f in exportados:
        print(f"   -> {f}")

    print("\n-- Resumo --------------------------------------")
    if df["preco_eur"].notna().any():
        print(f"  Preco    | mediana {df['preco_eur'].median():,.0f} E | min {df['preco_eur'].min():,.0f} E | max {df['preco_eur'].max():,.0f} E")
    if df["km"].notna().any():
        print(f"  Km       | mediana {df['km'].median():,.0f}  | min {df['km'].min():,.0f}  | max {df['km'].max():,.0f}")
    if df["ano"].notna().any():
        print(f"  Ano      | {int(df['ano'].min())} - {int(df['ano'].max())}")
    if df["marca"].notna().any():
        top = df["marca"].value_counts().head(5)
        print(f"  Marcas   | {', '.join(f'{m}({n})' for m, n in top.items())}")
    if df["combustivel"].notna().any():
        top_c = df["combustivel"].value_counts().head(4)
        print(f"  Combust. | {', '.join(f'{c}({n})' for c, n in top_c.items())}")
    print("------------------------------------------------")

    return df

# -- Scraper principal -------------------------------------------------
def scrape(
    paginas:    int  = 5,
    marca:      str  = None,
    com_detalhe:bool = False,
    headless:   bool = True,
    output:     str  = "olx_carros",
    formato:    str  = "ambos",
    ano_min:    int  = None,
    ano_max:    int  = None,
    preco_min:  int  = None,
    preco_max:  int  = None,
):
    filtros_ano   = (
        f"{ano_min or ''}-{ano_max or ''}" if (ano_min or ano_max)
        else "todos"
    )
    filtros_preco = (
        f"{preco_min or ''}-{preco_max or ''}E" if (preco_min or preco_max)
        else "todos"
    )

    print(f"""
--------------------------------------------------
        OLX Portugal - Scraper de Carros           
--------------------------------------------------
  Paginas : {paginas:<38}
  Marca   : {(marca or 'todas'):<38}
  Ano     : {filtros_ano:<38}
  Preco   : {filtros_preco:<38}
  Detalhe : {('sim (lento)' if com_detalhe else 'nao (rapido)'):<38}
  Headless: {('sim' if headless else 'nao (janela visivel)'):<38}
--------------------------------------------------
""")

    driver  = criar_driver(headless=headless)
    registos = []
    filtrados = 0

    try:
        print("[1/N] A abrir OLX e a aceitar cookies...")
        driver.get("https://www.olx.pt")
        time.sleep(2)
        fechar_cookies(driver)
        time.sleep(1)

        for pagina in tqdm(range(1, paginas + 1), desc="Paginas", unit="pag"):
            url_pag = construir_url(pagina, marca)
            driver.get(url_pag)
            esperar(driver, "[data-cy='l-card'], article, .offer-wrapper", timeout=12)
            time.sleep(random.uniform(1.0, 2.0))

            soup  = BeautifulSoup(driver.page_source, "html.parser")
            cards = (
                soup.select("[data-cy='l-card']") or
                soup.select("div[data-testid='listing-grid'] > div") or
                soup.select("article[class*='offer']") or
                soup.select("li[class*='offer']") or
                soup.select("div[class*='listing']")
            )

            if not cards:
                print(f"\n[AVISO] Pagina {pagina}: nenhum cartao encontrado. A parar.")
                break

            novos = 0
            for card in cards:
                dados = parsear_card(card)
                if not dados["url"]:
                    continue

                if dados["url"] in {r["url"] for r in registos}:
                    continue

                ok, motivo = passa_filtros(dados, ano_min, ano_max, preco_min, preco_max)
                if not ok:
                    filtrados += 1
                    tqdm.write(f"    [FILTRADO] ({motivo}): {dados.get('titulo','')[:50]}")
                    continue

                dados["pagina_origem"] = pagina
                dados["recolhido_em"]  = datetime.now().strftime("%Y-%m-%d %H:%M")
                registos.append(dados)
                novos += 1

            tqdm.write(
                f"  Pag {pagina:>2}: +{novos} anuncios aceites  "
                f"(total {len(registos)}, descartados {filtrados})"
            )

            sem_proxima = not soup.find(attrs={"data-testid": "pagination-forward"})
            if sem_proxima and pagina > 1:
                print(f"\n  Sem mais paginas apos pag {pagina}.")
                break

            pausa()

        # --- FASE 2: Modo Detalhe ---
        if com_detalhe and registos:
            print(f"\n🔍 MODO DETALHE: A visitar {len(registos)} anúncios individualmente para extrair dados técnicos...")
            for i in tqdm(range(len(registos)), desc="Fichas técnicas", unit="anuncio"):
                url_anuncio = registos[i]["url"]
                if url_anuncio:
                    extra = parsear_detalhe(driver, url_anuncio)

                    for campo, valor in extra.items():
                        if valor is not None:
                            # Prefer details value or update if None
                            if registos[i].get(campo) is None or campo in ["potencia_cv", "cilindrada_cc", "num_portas", "cor", "vendedor", "descricao"]:
                                registos[i][campo] = valor

                    pausa()

    except KeyboardInterrupt:
        print("\n\nInterrompido pelo utilizador.")
    except Exception as e:
        print(f"\nErro: {e}")
        import traceback; traceback.print_exc()
    finally:
        driver.quit()

    if filtrados:
        print(f"\n  [INFO] {filtrados} anuncios descartados pelos filtros de ano/preco.")

    return exportar(registos, output, formato)

# -- CLI ---------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Scraper de anuncios de carros do OLX Portugal",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--pages",     type=int, default=5,           help="Numero de paginas (default: 5)")
    parser.add_argument("--marca",     type=str, default=None,         help="Marca (ex: BMW, Volkswagen)")

    grupo_ano = parser.add_argument_group("Filtros de Ano")
    grupo_ano.add_argument("--ano-min",  type=int, default=None, help="Ano minimo")
    grupo_ano.add_argument("--ano-max",  type=int, default=None, help="Ano maximo")

    grupo_preco = parser.add_argument_group("Filtros de Preco")
    grupo_preco.add_argument("--preco-min", type=int, default=None, help="Preco minimo")
    grupo_preco.add_argument("--preco-max", type=int, default=None, help="Preco maximo")

    parser.add_argument("--detalhe",     action="store_true",               help="Visitar cada anuncio (potência, cilindrada...)")
    parser.add_argument("--no-headless", action="store_true",               help="Mostrar janela do browser")
    parser.add_argument("--output",      type=str, default="olx_carros",   help="Nome base do ficheiro de saida")
    parser.add_argument("--formato",     type=str, default="ambos", choices=["csv", "json", "ambos"], help="Formato (csv, json, ambos)")

    args = parser.parse_args()

    scrape(
        paginas=args.pages,
        marca=args.marca,
        com_detalhe=args.detalhe,
        headless=not args.no_headless,
        output=args.output,
        formato=args.formato,
        ano_min=args.ano_min,
        ano_max=args.ano_max,
        preco_min=args.preco_min,
        preco_max=args.preco_max,
    )

if __name__ == "__main__":
    main()