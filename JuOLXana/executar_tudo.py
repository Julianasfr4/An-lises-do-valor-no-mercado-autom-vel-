import subprocess
import sys
import time
import os

def correr_comando(comando, descricao):
    print(f"\n{'='*65}")
    print(f"🚀 A INICIAR: {descricao}")
    print(f"Comando: {' '.join(comando)}")
    print(f"{'='*65}\n")
    
    try:
        # Corre o comando e mostra o output no terminal em tempo real
        resultado = subprocess.run(comando, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ ERRO: O processo '{descricao}' falhou com o código {e.returncode}.")
        return False
    except FileNotFoundError:
        print(f"\n❌ ERRO: Não foi possível encontrar o comando '{comando[0]}'.")
        return False

def main():
    print("\n🤖 BEM-VINDO AO AUTOMERCADO (Sistema Unificado) 🤖")
    print("Este script vai extrair dados do OLX e exportar o JSON inteligente para o portal JuOLXana.\n")
    
    # =========================================================
    # ⚙️ CONFIGURAÇÃO DO SCRAPER
    # =========================================================
    paginas = "1"             
    marca = ""    # Em branco extrai de forma aleatória as várias marcas
    
    comando_scraper = [sys.executable, "olx_car_scraper.py", "--pages", paginas]
    
    if marca:
        comando_scraper.extend(["--marca", marca])
    
    # Detalhe ligado!
    comando_scraper.append("--detalhe") 
    
    # =========================================================
    
    if not os.path.exists("olx_car_scraper.py"):
        print("❌ ERRO: Não encontro o ficheiro 'olx_car_scraper.py' nesta pasta.")
        return
    if not os.path.exists("gerar_previsoes_ia.py"):
        print("❌ ERRO: Não encontro o ficheiro 'gerar_previsoes_ia.py' nesta pasta.")
        return

    # 1. Correr o Scraper
    sucesso_scraper = correr_comando(comando_scraper, "Extração de Dados do OLX")
    
    if not sucesso_scraper:
        print("\n⚠️ O processo parou porque o scraper encontrou um erro.")
        sys.exit(1)
        
    print("\n⏳ Extração concluída com sucesso! A iniciar a IA...")
    time.sleep(2)
    
    # 2. Correr a IA (Agora automatizada e sem menus!)
    comando_ia = [sys.executable, "gerar_previsoes_ia.py", "olx_carros.csv", "olx_carros.json"]
    correr_comando(comando_ia, "Gerar Previsões de IA para o portal JuOLXana")
    
    print("\n✅ Processo unificado concluído! Podes abrir o teu automarket.html")

if __name__ == "__main__":
    main()