#!/usr/bin/env python3
"""
olx_carros_scraper.py
─────────────────────────────────────────────────────────────────────
Scraper de anúncios de carros do OLX Portugal (olx.pt)
Extrai: marca, modelo, ano, km, preço, combustível, transmissão,
        condição, localização, data, URL e descrição.

INSTALAÇÃO (uma vez):
    pip install selenium undetected-chromedriver beautifulsoup4 lxml pandas tqdm

UTILIZAÇÃO:
    python webcar.py                                        # 5 páginas, exporta CSV + JSON
    python webcar.py --pages 20                             # 20 páginas
    python webcar.py --marca BMW                            # filtra por marca
    python webcar.py --marca BMW --ano-min 2018             # BMW a partir de 2018
    python webcar.py --marca BMW --ano-min 2015 --ano-max 2020   # BMW entre 2015 e 2020
    python webcar.py --preco-min 5000 --preco-max 20000     # preço entre 5000€ e 20000€
    python webcar.py --marca BMW --ano-min 2018 --preco-max 30000 --detalhe
    python webcar.py --output resultados --formato csv
─────────────────────────────────────────────────────────────────────
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


# ── Importação do driver ──────────────────────────────────────────────
try:
    import undetected_chromedriver as uc
    DRIVER_MODE = "undetected"
except ImportError:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    DRIVER_MODE = "selenium"
    print("[AVISO] undetected-chromedriver não instalado. A usar selenium padrão.")
    print("        Para melhor fiabilidade: pip install undetected-chromedriver\n")

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ── Configuração ──────────────────────────────────────────────────────
BASE_URL = "https://www.olx.pt/carros-motos-e-barcos/carros/"
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]


# ── Driver ────────────────────────────────────────────────────────────
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
        driver = uc.Chrome(options=opts, version_main=148)
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


# ── Filtro de ano e preço ─────────────────────────────────────────────
def passa_filtros(dados: dict, ano_min, ano_max, preco_min, preco_max) -> tuple[bool, str]:
    """
    Verifica se um anúncio passa nos filtros de ano e preço.
    Devolve (True, "") se passa, ou (False, "motivo") se não passa.

    Lógica:
    - Se o campo é None (não extraído), deixa passar — não queremos
      descartar anúncios só porque ainda não temos o valor (ex: ano
      só disponível na página de detalhe).
    - Se o campo existe, verifica os limites.
    """
    ano    = dados.get("ano")
    preco  = dados.get("preco_eur")

    if ano is not None:
        if ano_min is not None and ano < ano_min:
            return False, f"ano {ano} < mínimo {ano_min}"
        if ano_max is not None and ano > ano_max:
            return False, f"ano {ano} > máximo {ano_max}"

    if preco is not None:
        if preco_min is not None and preco < preco_min:
            return False, f"preço {preco}€ < mínimo {preco_min}€"
        if preco_max is not None and preco > preco_max:
            return False, f"preço {preco}€ > máximo {preco_max}€"

    return True, ""


# ── Parsing do cartão de listagem ─────────────────────────────────────
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
    }

    # ── Título ────────────────────────────────────────────────────────
    titulo_el = (
        card_soup.find("h4") or
        card_soup.find("h6") or
        card_soup.find(attrs={"data-cy": "ad-card-title"}) or
        card_soup.find(class_=re.compile(r"title|Title"))
    )
    if titulo_el:
        dados["titulo"] = titulo_el.get_text(strip=True)
        partes = dados["titulo"].split()
        if len(partes) >= 2:
            dados["marca"]  = partes[0]
            dados["modelo"] = " ".join(partes[1:3])

        # Tenta extrair ano do título (ex: "BMW 320d 2019 Diesel")
        m_ano = re.search(r'\b(19[89]\d|20[012]\d)\b', dados["titulo"])
        if m_ano:
            dados["ano"] = int(m_ano.group())

    # ── URL ───────────────────────────────────────────────────────────
    link = card_soup.find("a", href=re.compile(r"/anuncio/"))
    if not link:
        link = card_soup.find("a", href=re.compile(r"olx\.pt"))
    if link:
        href = link.get("href", "")
        dados["url"] = href if href.startswith("http") else f"https://www.olx.pt{href}"

    # ── Preço ─────────────────────────────────────────────────────────
    preco_el = (
        card_soup.find(attrs={"data-testid": "ad-price"}) or
        card_soup.find(class_=re.compile(r"[Pp]rice|[Pp]reco|[Vv]alor")) or
        card_soup.find("strong", string=re.compile(r"€|\d"))
    )
    if preco_el:
        txt = preco_el.get_text(strip=True)
        numeros = re.sub(r"[^\d]", "", txt.replace(".", "").replace(",", ""))
        if numeros:
            dados["preco_eur"] = int(numeros)

    # ── Localização + Data ────────────────────────────────────────────
    loc_date_el = card_soup.find(attrs={"data-testid": "location-date"})
    if loc_date_el:
        txt = loc_date_el.get_text(" ", strip=True)
        partes = txt.split(" - ", 1)
        if len(partes) == 2:
            dados["localizacao"]  = partes[0].strip()
            dados["data_anuncio"] = partes[1].strip()
        else:
            dados["localizacao"] = txt.strip()

    # ── KM (ícone de quilometragem no cartão) ─────────────────────────
    km_icon = card_soup.find(attrs={"data-testid": "millage-card-param-icon"})
    if km_icon:
        km_span = km_icon.find_parent("span")
        if km_span:
            km_txt = km_span.get_text(strip=True)
            m = re.sub(r"[^\d]", "", km_txt)
            if m:
                dados["km"] = int(m)

    # ── Fallback para km se não encontrou pelo ícone ──────────────────
    if dados["km"] is None:
        spans = card_soup.find_all(["span", "li", "p"])
        for s in spans:
            txt_low = s.get_text(strip=True).lower()
            m = re.search(r'([\d\s\.]+)\s*km', txt_low)
            if m:
                val = re.sub(r'[\s\.]', '', m.group(1))
                if val.isdigit():
                    dados["km"] = int(val)
                    break

    # ── Combustível / Transmissão / Condição (se visíveis no cartão) ──
    param_textos = []
    for sel in ["[data-testid='param-value']", "span[class*='param']", "li[class*='param']"]:
        els = card_soup.select(sel)
        if els:
            param_textos = [e.get_text(strip=True) for e in els]
            break

    for txt in param_textos:
        txt_low = txt.lower()
        if dados["ano"] is None:
            m = re.search(r'\b(19[89]\d|20[012]\d)\b', txt)
            if m:
                dados["ano"] = int(m.group())
        if dados["combustivel"] is None:
            for c in ["gasolina", "diesel", "gasóleo", "gasoleo", "elétrico", "eletrico",
                      "híbrido", "hibrido", "gpl", "gnv", "plug-in"]:
                if c in txt_low:
                    dados["combustivel"] = txt.strip()
                    break
        if dados["transmissao"] is None:
            for t in ["manual", "automático", "automatico", "semi-automático"]:
                if t in txt_low:
                    dados["transmissao"] = txt.strip()
                    break
        if dados["condicao"] is None:
            for cond in ["usado", "novo", "recondicionado"]:
                if cond in txt_low:
                    dados["condicao"] = txt.strip()
                    break

    return dados


# ── Parsing da página de detalhe ──────────────────────────────────────
def parsear_detalhe(driver, url: str) -> dict:
    extra = {
        "descricao":     None,
        "potencia_cv":   None,
        "num_portas":    None,
        "cor":           None,
        "cilindrada_cc": None,
        "vendedor":      None,
        # Campos que podem completar os do cartão
        "ano":           None,
        "km":            None,
        "combustivel":   None,
        "transmissao":   None,
        "condicao":      None,
    }
    try:
        driver.get(url)
        esperar(driver, "[data-cy='ad_description'], .css-bgzo2k, h1", timeout=10)
        soup = BeautifulSoup(driver.page_source, "lxml")

        # Descrição
        desc_el = (
            soup.find(attrs={"data-cy": "ad_description"}) or
            soup.find(class_=re.compile(r"[Dd]esc"))
        )
        if desc_el:
            extra["descricao"] = desc_el.get_text(" ", strip=True)[:500]

        # Parâmetros detalhados — OLX usa uma tabela de parâmetros na página de detalhe
        # Tenta vários seletores comuns
        param_items = (
            soup.select("[data-testid='ad-detail-params'] li") or
            soup.select("[class*='params'] li") or
            soup.select("[class*='param'] li") or
            soup.find_all(["li", "div", "p"], class_=re.compile(r"[Pp]aram|[Dd]etail|[Ff]eature"))
        )

        for item in param_items:
            txt      = item.get_text(" ", strip=True)
            txt_low  = txt.lower()

            # Ano
            if extra["ano"] is None:
                m = re.search(r'\b(19[89]\d|20[012]\d)\b', txt)
                if m:
                    extra["ano"] = int(m.group())

            # KM
            if extra["km"] is None:
                m = re.search(r'([\d\s\.]+)\s*km', txt_low)
                if m:
                    val = re.sub(r'[\s\.]', '', m.group(1))
                    if val.isdigit():
                        extra["km"] = int(val)

            # Combustível
            if extra["combustivel"] is None:
                for c in ["gasolina", "diesel", "gasóleo", "gasoleo", "elétrico", "eletrico",
                          "híbrido", "hibrido", "gpl", "gnv", "plug-in"]:
                    if c in txt_low:
                        extra["combustivel"] = txt.strip()
                        break

            # Transmissão
            if extra["transmissao"] is None:
                for t in ["manual", "automático", "automatico", "semi-automático"]:
                    if t in txt_low:
                        extra["transmissao"] = txt.strip()
                        break

            # Condição
            if extra["condicao"] is None:
                for cond in ["usado", "novo", "recondicionado"]:
                    if cond in txt_low:
                        extra["condicao"] = txt.strip()
                        break

            # Potência
            if extra["potencia_cv"] is None:
                if "cv" in txt_low or "cavalos" in txt_low:
                    m = re.search(r'(\d+)\s*cv', txt_low)
                    if m:
                        extra["potencia_cv"] = int(m.group(1))

            # Portas
            if extra["num_portas"] is None:
                if "port" in txt_low:
                    m = re.search(r'(\d)\s*port', txt_low)
                    if m:
                        extra["num_portas"] = int(m.group(1))

            # Cor
            if extra["cor"] is None:
                if "cor" in txt_low or "color" in txt_low:
                    val = re.sub(r'cor[:\s]*', '', txt, flags=re.IGNORECASE).strip()
                    if val and len(val) < 30:
                        extra["cor"] = val

            # Cilindrada
            if extra["cilindrada_cc"] is None:
                if "cc" in txt_low or "cilindrada" in txt_low:
                    m = re.search(r'(\d{3,5})\s*cc', txt_low)
                    if m:
                        extra["cilindrada_cc"] = int(m.group(1))

        # Vendedor
        vend_el = soup.find(class_=re.compile(r"[Ss]eller|[Vv]endedor|[Uu]ser"))
        if vend_el:
            extra["vendedor"] = vend_el.get_text(strip=True)[:60]

    except Exception as e:
        print(f"  [AVISO] Falha ao ler detalhe: {e}")

    return extra


# ── Utilitários ───────────────────────────────────────────────────────
def esperar(driver, seletor_css, timeout=12):
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

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    exportados = []

    if formato in ("csv", "ambos"):
        f_csv = f"{caminho_base}_{timestamp}.csv"
        df.to_csv(f_csv, index=False, encoding="utf-8-sig")
        exportados.append(f_csv)

    if formato in ("json", "ambos"):
        f_json = f"{caminho_base}_{timestamp}.json"
        df.to_json(f_json, orient="records", force_ascii=False, indent=2)
        exportados.append(f_json)

    print(f"\n✓ {len(df)} anúncios exportados:")
    for f in exportados:
        print(f"  → {f}")

    print("\n── Resumo ──────────────────────────────────────")
    if df["preco_eur"].notna().any():
        print(f"  Preço   │ mediana {df['preco_eur'].median():,.0f} € │ mín {df['preco_eur'].min():,.0f} € │ máx {df['preco_eur'].max():,.0f} €")
    if df["km"].notna().any():
        print(f"  Km      │ mediana {df['km'].median():,.0f}  │ mín {df['km'].min():,.0f}  │ máx {df['km'].max():,.0f}")
    if df["ano"].notna().any():
        print(f"  Ano     │ {int(df['ano'].min())} – {int(df['ano'].max())}")
    if df["marca"].notna().any():
        top = df["marca"].value_counts().head(5)
        print(f"  Marcas  │ {', '.join(f'{m}({n})' for m, n in top.items())}")
    if df["combustivel"].notna().any():
        top_c = df["combustivel"].value_counts().head(4)
        print(f"  Combust.│ {', '.join(f'{c}({n})' for c, n in top_c.items())}")
    print("────────────────────────────────────────────────")

    return df


# ── Scraper principal ─────────────────────────────────────────────────
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
    # ── Linha de filtros activos para mostrar no cabeçalho ────────────
    filtros_ano   = (
        f"{ano_min or ''}–{ano_max or ''}" if (ano_min or ano_max)
        else "todos"
    )
    filtros_preco = (
        f"{preco_min or ''}–{preco_max or ''}€" if (preco_min or preco_max)
        else "todos"
    )

    print(f"""
╔══════════════════════════════════════════════════╗
║      OLX Portugal · Scraper de Carros            ║
╠══════════════════════════════════════════════════╣
║  Páginas : {paginas:<38}║
║  Marca   : {(marca or 'todas'):<38}║
║  Ano     : {filtros_ano:<38}║
║  Preço   : {filtros_preco:<38}║
║  Detalhe : {('sim (lento)' if com_detalhe else 'não (rápido)'):<38}║
║  Headless: {('sim' if headless else 'não (janela visível)'):<38}║
╚══════════════════════════════════════════════════╝
""")

    driver  = criar_driver(headless=headless)
    registos = []
    filtrados = 0  # contador de anúncios descartados pelos filtros

    try:
        print("[1/N] A abrir OLX e a aceitar cookies...")
        driver.get(BASE_URL)
        time.sleep(2)
        fechar_cookies(driver)
        time.sleep(1)

        for pagina in tqdm(range(1, paginas + 1), desc="Páginas", unit="pág"):
            url_pag = construir_url(pagina, marca)
            driver.get(url_pag)
            esperar(driver, "[data-cy='l-card'], article, .offer-wrapper", timeout=15)
            time.sleep(random.uniform(1.0, 2.0))

            soup  = BeautifulSoup(driver.page_source, "lxml")
            cards = (
                soup.select("[data-cy='l-card']") or
                soup.select("div[data-testid='listing-grid'] > div") or
                soup.select("article[class*='offer']") or
                soup.select("li[class*='offer']") or
                soup.select("div[class*='listing']")
            )

            if not cards:
                print(f"\n[AVISO] Página {pagina}: nenhum cartão encontrado. A parar.")
                break

            novos = 0
            for card in cards:
                dados = parsear_card(card)
                if not dados["url"]:
                    continue

                # Evitar duplicados
                if dados["url"] in {r["url"] for r in registos}:
                    continue

                # ── Filtro rápido com dados do cartão ─────────────────
                # Se já temos ano e/ou preço do cartão, filtramos aqui
                # para evitar visitar a página de detalhe desnecessariamente.
                ok, motivo = passa_filtros(dados, ano_min, ano_max, preco_min, preco_max)
                if not ok:
                    filtrados += 1
                    tqdm.write(f"    ✗ Descartado ({motivo}): {dados.get('titulo','')[:50]}")
                    continue

                # ── Página de detalhe (opcional) ──────────────────────
                if com_detalhe and dados["url"]:
                    extra = parsear_detalhe(driver, dados["url"])

                    # Merge: só sobrescreve se o cartão não tinha o valor
                    for campo, valor in extra.items():
                        if valor is not None and dados.get(campo) is None:
                            dados[campo] = valor

                    # ── Filtro final com dados completos do detalhe ────
                    # Agora que temos mais campos (ex: ano da página de detalhe),
                    # filtramos de novo para garantir precisão.
                    ok, motivo = passa_filtros(dados, ano_min, ano_max, preco_min, preco_max)
                    if not ok:
                        filtrados += 1
                        tqdm.write(f"    ✗ Descartado após detalhe ({motivo}): {dados.get('titulo','')[:50]}")
                        pausa()
                        continue

                    pausa()

                dados["pagina_origem"] = pagina
                dados["recolhido_em"]  = datetime.now().strftime("%Y-%m-%d %H:%M")
                registos.append(dados)
                novos += 1

            tqdm.write(
                f"  Pág {pagina:>2}: +{novos} anúncios aceites  "
                f"(total {len(registos)}, descartados {filtrados})"
            )

            # Verificar se há página seguinte
            sem_proxima = not soup.find(attrs={"data-testid": "pagination-forward"})
            if sem_proxima and pagina > 1:
                print(f"\n  Sem mais páginas após pág {pagina}.")
                break

            pausa()

    except KeyboardInterrupt:
        print("\n\nInterrompido pelo utilizador.")
    except Exception as e:
        print(f"\nErro: {e}")
        import traceback; traceback.print_exc()
    finally:
        driver.quit()

    if filtrados:
        print(f"\n  ℹ️  {filtrados} anúncios descartados pelos filtros de ano/preço.")

    return exportar(registos, output, formato)


# ── CLI ───────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Scraper de anúncios de carros do OLX Portugal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python webcar.py
  python webcar.py --pages 10 --marca BMW
  python webcar.py --marca BMW --ano-min 2018
  python webcar.py --marca BMW --ano-min 2015 --ano-max 2020
  python webcar.py --preco-min 5000 --preco-max 20000
  python webcar.py --marca BMW --ano-min 2018 --preco-max 30000 --detalhe
  python webcar.py --pages 5 --detalhe --no-headless
  python webcar.py --output meus_carros --formato json
        """
    )

    # Pesquisa
    parser.add_argument("--pages",     type=int, default=5,           help="Número de páginas (default: 5)")
    parser.add_argument("--marca",     type=str, default=None,         help="Marca (ex: BMW, Volkswagen)")

    # ── Filtros de ano ────────────────────────────────────────────────
    grupo_ano = parser.add_argument_group("Filtros de Ano")
    grupo_ano.add_argument("--ano-min",  type=int, default=None,
                           help="Ano mínimo (inclusive). Ex: --ano-min 2015")
    grupo_ano.add_argument("--ano-max",  type=int, default=None,
                           help="Ano máximo (inclusive). Ex: --ano-max 2020")

    # ── Filtros de preço ──────────────────────────────────────────────
    grupo_preco = parser.add_argument_group("Filtros de Preço")
    grupo_preco.add_argument("--preco-min", type=int, default=None,
                             help="Preço mínimo em € (inclusive). Ex: --preco-min 5000")
    grupo_preco.add_argument("--preco-max", type=int, default=None,
                             help="Preço máximo em € (inclusive). Ex: --preco-max 20000")

    # Opções gerais
    parser.add_argument("--detalhe",     action="store_true",              help="Visitar cada anúncio (mais dados, mais lento)")
    parser.add_argument("--no-headless", action="store_true",              help="Mostrar janela do browser")
    parser.add_argument("--output",      type=str, default="olx_carros",   help="Nome base do ficheiro de saída")
    parser.add_argument("--formato",     type=str, default="ambos",
                        choices=["csv", "json", "ambos"],                  help="Formato de exportação (default: ambos)")

    args = parser.parse_args()

    # Validações básicas
    if args.ano_min and args.ano_max and args.ano_min > args.ano_max:
        parser.error(f"--ano-min ({args.ano_min}) não pode ser maior que --ano-max ({args.ano_max})")
    if args.preco_min and args.preco_max and args.preco_min > args.preco_max:
        parser.error(f"--preco-min ({args.preco_min}) não pode ser maior que --preco-max ({args.preco_max})")

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