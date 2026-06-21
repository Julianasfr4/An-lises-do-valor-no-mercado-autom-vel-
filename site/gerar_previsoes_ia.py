#!/usr/bin/env python3
"""
gerar_previsoes_ia.py
====================================================
Treina os modelos e escreve a previsão de preço justo 
diretamente no ficheiro JSON consumido pelo site.
Salva o melhor modelo calibrado no ficheiro modelo_ia.pkl para persistência.
====================================================
"""

import sys
import json
import warnings
import os
import re
import pickle
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")

from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor

# =============================================================
# 1. CONFIGURAÇÃO
# =============================================================
class Config:
    CAMPOS_NUMERICOS   = ["mileage", "hp", "year", "age", "km_per_year"]
    CAMPOS_CATEGORICOS = ["make", "model", "fuel", "gear"]

    PRECO_MIN  =       500
    PRECO_MAX  =   600_000
    KM_MAX     = 1_000_000
    HP_MAX     =     1_000

    TEST_SIZE    = 0.20
    RANDOM_STATE = 42

    @classmethod
    def campos_treino(cls):
        return cls.CAMPOS_NUMERICOS + cls.CAMPOS_CATEGORICOS

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

# =============================================================
# 2. ENGENHARIA DE FEATURES
# =============================================================
class FeatureEngineer:
    def __init__(self):
        self.colunas_treino = None
        self.modelos_frequentes = None

    def fit_modelos(self, models_series):
        counts = models_series.value_counts()
        self.modelos_frequentes = counts[counts >= 3].index.tolist()

    def preparar(self, df: pd.DataFrame, fit_mode=False) -> pd.DataFrame:
        df_copy = df.copy()
        if fit_mode:
            self.fit_modelos(df_copy["model"])
        if self.modelos_frequentes is not None:
            df_copy["model"] = df_copy["model"].apply(lambda x: x if x in self.modelos_frequentes else "Outro")
        
        X = df_copy[Config.campos_treino()].copy()
        X = pd.get_dummies(X, columns=Config.CAMPOS_CATEGORICOS)
        return X

    def fit(self, X: pd.DataFrame):
        self.colunas_treino = X.columns.tolist()

    def alinhar(self, X: pd.DataFrame) -> pd.DataFrame:
        for col in self.colunas_treino:
            if col not in X.columns:
                X[col] = 0
        return X[self.colunas_treino]

# =============================================================
# 3. MODELOS
# =============================================================
class ModeloBase:
    def __init__(self, nome, nota=""):
        self.nome = nome
        self.nota = nota
        self._m = None
        self.metricas = {}

    def treinar(self, X, y): raise NotImplementedError
    def prever(self, X):     raise NotImplementedError

    def avaliar(self, X_teste, y_teste):
        y_pred = self.prever(X_teste)
        self.metricas = dict(
            mae  = mean_absolute_error(y_teste, y_pred),
            rmse = np.sqrt(mean_squared_error(y_teste, y_pred)),
            r2   = r2_score(y_teste, y_pred),
            mape = np.mean(np.abs((y_teste - y_pred) / np.where(y_teste == 0, 1, y_teste))) * 100,
        )
        return self.metricas

class RegLinear(ModeloBase):
    def __init__(self):
        super().__init__("Regressão Linear")
        self.scaler = StandardScaler()
    def treinar(self, X, y):
        self._m = LinearRegression()
        X_scaled = X.copy()
        X_scaled[:, :5] = self.scaler.fit_transform(X[:, :5])
        self._m.fit(X_scaled, y)
    def prever(self, X):
        X_scaled = X.copy()
        X_scaled[:, :5] = self.scaler.transform(X[:, :5])
        return self._m.predict(X_scaled)

class RegExponencial(ModeloBase):
    def __init__(self):
        super().__init__("Reg. Exponencial", "(log target)")
        self.scaler = StandardScaler()
    def treinar(self, X, y):
        self._m = Ridge(alpha=1.0)
        X_scaled = X.copy()
        X_scaled[:, :5] = self.scaler.fit_transform(X[:, :5])
        self._m.fit(X_scaled, np.log1p(y))
    def prever(self, X):
        X_scaled = X.copy()
        X_scaled[:, :5] = self.scaler.transform(X[:, :5])
        return np.expm1(self._m.predict(X_scaled))

class RegLogaritmica(ModeloBase):
    def __init__(self):
        super().__init__("Reg. Logarítmica", "(log features)")
        self.scaler = StandardScaler()
    def _transformar(self, X: np.ndarray) -> np.ndarray:
        Xl = X.astype(np.float64)
        Xl[:, 0] = np.log1p(np.maximum(0, Xl[:, 0]))
        Xl[:, 1] = np.log1p(np.maximum(0, Xl[:, 1]))
        Xl[:, 4] = np.log1p(np.maximum(0, Xl[:, 4]))
        return Xl
    def treinar(self, X, y):
        self._m = LinearRegression()
        Xt = self._transformar(X)
        Xt[:, :5] = self.scaler.fit_transform(Xt[:, :5])
        self._m.fit(Xt, y)
    def prever(self, X):
        Xt = self._transformar(X)
        Xt[:, :5] = self.scaler.transform(Xt[:, :5])
        return self._m.predict(Xt)

class RndForest(ModeloBase):
    def __init__(self): super().__init__("Random Forest")
    def treinar(self, X, y):
        self._m = RandomForestRegressor(
            n_estimators=150, max_depth=15, min_samples_leaf=2,
            n_jobs=-1, random_state=Config.RANDOM_STATE)
        self._m.fit(X, y)
    def prever(self, X): return self._m.predict(X)

class XGB(ModeloBase):
    def __init__(self): super().__init__("XGBoost")
    def treinar(self, X, y):
        self._m = XGBRegressor(
            n_estimators=200, max_depth=5, learning_rate=0.06,
            subsample=0.8, colsample_bytree=0.8,
            random_state=Config.RANDOM_STATE, verbosity=0)
        self._m.fit(X, y)
    def prever(self, X): return self._m.predict(X)

class LGBM(ModeloBase):
    def __init__(self): super().__init__("LightGBM")
    def treinar(self, X, y):
        self._m = LGBMRegressor(
            n_estimators=200, max_depth=5, learning_rate=0.06,
            subsample=0.8, colsample_bytree=0.8,
            random_state=Config.RANDOM_STATE, verbose=-1)
        self._m.fit(X, y)
    def prever(self, X): return self._m.predict(X)

MODELOS_DISPONIVEIS = [RegLinear, RegExponencial, RegLogaritmica, RndForest, XGB, LGBM]

# =============================================================
# 4. CARREGAMENTO E LIMPEZA
# =============================================================
def clean_title_make_model(row):
    titulo_limpo = ""
    if "titulo" in row and pd.notna(row["titulo"]):
        titulo_limpo = str(row["titulo"]).strip()
    elif "title" in row and pd.notna(row["title"]):
        titulo_limpo = str(row["title"]).strip()
        
    if not titulo_limpo:
        make_val = row.get("marca") or row.get("make") or ""
        model_val = row.get("modelo") or row.get("model") or ""
        titulo_limpo = (str(make_val) + " " + str(model_val)).strip()
        
    titulo_lower = titulo_limpo.lower()
    
    first_word = titulo_lower.split()[0] if titulo_lower.split() else ""
    if first_word in MODEL_TO_BRAND:
        brand, model = MODEL_TO_BRAND[first_word]
        rest = titulo_limpo[len(first_word):].strip()
        model_details = (first_word + " " + " ".join(rest.split()[:2])).strip()
        return pd.Series([brand, model_details])
        
    for brand_key, brand_norm in BRAND_MAP.items():
        if brand_key in titulo_lower:
            idx = titulo_lower.find(brand_key)
            words_after = titulo_limpo[idx + len(brand_key):].strip().split()
            model = " ".join(words_after[:2]) if words_after else "Outro"
            return pd.Series([brand_norm, model])
            
    partes = titulo_limpo.split()
    if len(partes) >= 1:
        make = partes[0]
        make = re.sub(r'^[^\w]+', '', make)
        make = BRAND_MAP.get(make.lower(), make.title())
    else:
        make = "Desconhecido"
    model = " ".join(partes[1:3]) if len(partes) >= 2 else "Outro"
    return pd.Series([make, model])

def estimar_potencia(row):
    if "potencia_cv" in row and pd.notna(row["potencia_cv"]):
        try:
            val = float(row["potencia_cv"])
            if 10 <= val <= 1000:
                return val
        except:
            pass
    if "hp" in row and pd.notna(row["hp"]):
        try:
            val = float(row["hp"])
            if 10 <= val <= 1000 and val != 100:
                return val
        except:
            pass
            
    title = (str(row.get("make", "")) + " " + str(row.get("model", ""))).lower()
    m = re.search(r'(\d+)\s*cv', title)
    if m:
        return int(m.group(1))
    m = re.search(r'(\d\.\d)\s*(?:gasolina|diesel|hdi|tdi|dci|d|i)', title)
    if m:
        liters = float(m.group(1))
        if liters >= 3.0: return 250
        elif liters >= 2.5: return 190
        elif liters >= 2.0: return 150
        elif liters >= 1.6: return 115
        elif liters >= 1.4: return 90
        else: return 75
        
    if "tesla" in title or "porsche" in title or "ferrari" in title or "amg" in title or "m5" in title:
        return 300
    if "mustang" in title or "camaro" in title:
        return 300
    if "320d" in title or "220d" in title or "a4" in title or "a5" in title or "passat" in title or "520d" in title:
        return 150
    if "corsa" in title or "clio" in title or "yaris" in title or "fiesta" in title or "c3" in title or "punto" in title or "micra" in title:
        return 75
    if "smart" in title:
        return 71
    if "zoe" in title:
        return 90
        
    make = str(row.get("make", "")).lower()
    if make in ["porsche", "tesla", "jaguar", "bentley", "maserati", "ferrari", "aston"]:
        return 280
    if make in ["bmw", "audi", "mercedes-benz", "mercedes"]:
        return 150
    if make in ["volvo", "alfa", "cupra", "byd"]:
        return 140
    if make in ["volkswagen", "toyota", "nissan", "hyundai", "honda", "kia", "ford", "skoda", "mazda"]:
        return 110
    if make in ["peugeot", "renault", "opel", "citroen", "fiat", "dacia", "seat", "smart"]:
        return 85
    return 100

def carregar_csv(caminho: str) -> pd.DataFrame:
    print(f"   A carregar '{caminho}'...")
    try:
        df = pd.read_csv(caminho)
    except FileNotFoundError:
        print(f"   ERRO: ficheiro '{caminho}' não encontrado.")
        sys.exit(1)

    # Rename columns to ensure English format for the ML pipeline first
    df = df.rename(columns={
        "preco_eur": "price", "preco": "price",
        "km": "mileage", "quilometros": "mileage",
        "ano": "year", "marca": "make", "modelo": "model",
        "combustivel": "fuel", "transmissao": "gear"
    })

    # Re-map/Clean brand and model names in-place
    df[["make", "model"]] = df.apply(clean_title_make_model, axis=1)

    # Drop invalid dirty rows
    invalid_brands = ['Vendo', 'Raro', 'Carrinha', 'Laguna', 'Punto', 'Defender', 'Desconhecido', '!!!Mercedes-Benz']
    df = df[~df['make'].isin(invalid_brands)]

    df["hp"] = df.apply(estimar_potencia, axis=1)

    for col in ["price", "mileage", "hp", "year"]:
        if col in df.columns:
            if df[col].dtype == object or df[col].dtype == str:
                df[col] = df[col].astype(str).str.replace(r'[^\d]', '', regex=True)
            df[col] = pd.to_numeric(df[col], errors='coerce')

    df = df.dropna(subset=["price", "mileage", "hp", "year"])

    df["price"]   = df["price"].astype(int)
    df["mileage"] = df["mileage"].astype(int)
    df["year"]    = df["year"].astype(int)
    df["hp"]      = df["hp"].astype(int)

    # Feature Engineering
    df['age'] = 2026 - df['year']
    df['km_per_year'] = df['mileage'] / (df['age'] + 1)

    df = df[(df["price"]   >= Config.PRECO_MIN)  & (df["price"]   <= Config.PRECO_MAX)]
    df = df[(df["mileage"] >= 0)                 & (df["mileage"] <= Config.KM_MAX)]
    df = df[(df["hp"]      > 0)                  & (df["hp"]      <= Config.HP_MAX)]

    print(f"   {len(df):,} registos válidos após limpeza")
    return df

# =============================================================
# 5. TREINO + PREVISÃO EM LOTE
# =============================================================
def treinar_e_escolher_melhor(df: pd.DataFrame):
    fe = FeatureEngineer()
    X_enc = fe.preparar(df, fit_mode=True)
    fe.fit(X_enc)
    y = df["price"].values

    X_tr, X_te, y_tr, y_te = train_test_split(
        X_enc.values.astype(np.float64), y,
        test_size=Config.TEST_SIZE, random_state=Config.RANDOM_STATE)

    modelos = [cls() for cls in MODELOS_DISPONIVEIS]
    print(f"\n   Treino: {len(X_tr):,} amostras | Teste: {len(X_te):,} amostras\n")
    for m in modelos:
        m.treinar(X_tr, y_tr)
        met = m.avaliar(X_te, y_te)
        print(f"   -> {m.nome:<20} R2={met['r2']:.3f} | MAE={met['mae']:,.0f}€ | MAPE={met['mape']:.1f}%")

    melhor = min(modelos, key=lambda m: m.metricas["mape"])
    print(f"\n   Melhor modelo: {melhor.nome} (MAPE={melhor.metricas['mape']:.1f}%)\n")
    return melhor, fe

def prever_para_todos(df: pd.DataFrame, melhor: ModeloBase, fe: FeatureEngineer) -> dict:
    X_enc = fe.preparar(df)
    X_enc = fe.alinhar(X_enc)
    previsoes = melhor.prever(X_enc.values.astype(np.float64))
    previsoes = np.maximum(previsoes, Config.PRECO_MIN)
    if "url" not in df.columns:
        return {}
    return dict(zip(df["url"], previsoes))

# =============================================================
# 6. JUNTAR AS PREVISÕES AO JSON DO SITE
# =============================================================
def atualizar_json(caminho_json: str, previsoes_por_url: dict, nome_modelo: str, mape_modelo: float, output_json="site/olx_carros_ia.json"):
    try:
        with open(caminho_json, "r", encoding="utf-8") as f:
            carros = json.load(f)
    except FileNotFoundError:
        print(f"   ERRO: ficheiro '{caminho_json}' não encontrado.")
        sys.exit(1)

    atualizados = 0
    MARGEM_MEDIA = 0.05 

    for carro in carros:
        url = carro.get("url")
        if url in previsoes_por_url:
            preco_previsto = int(round(float(previsoes_por_url[url]), 0))
            preco_real = carro.get("price") or carro.get("preco_eur") or carro.get("preco")

            status_ia = "Desconhecido"
            if preco_real and preco_previsto > 0:
                diferenca_perc = (preco_real - preco_previsto) / preco_previsto
                if diferenca_perc < -MARGEM_MEDIA:
                    status_ia = "Abaixo da média"
                elif diferenca_perc > MARGEM_MEDIA:
                    status_ia = "Acima da média"
                else:
                    status_ia = "Na média"

            carro["preco_ia"]  = preco_previsto
            carro["modelo_ia"] = nome_modelo
            carro["mape_ia"]   = round(float(mape_modelo), 1)
            carro["status_ia"] = status_ia
            atualizados += 1

    # Save to the target output JSON
    try:
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(carros, f, ensure_ascii=False, indent=4)
        print(f"   [OK] {atualizados}/{len(carros)} anúncios atualizados em '{output_json}'")
    except Exception as e:
        # Fallback to local name
        local_out = "olx_carros_ia.json"
        with open(local_out, "w", encoding="utf-8") as f:
            json.dump(carros, f, ensure_ascii=False, indent=4)
        print(f"   [OK] {atualizados}/{len(carros)} anúncios salvos no fallback '{local_out}' due to: {e}")

# =============================================================
# 7. PRINCIPAL
# =============================================================
def main():
    caminho_csv  = sys.argv[1] if len(sys.argv) > 1 else "site/olx_carros.csv"
    caminho_json = sys.argv[2] if len(sys.argv) > 2 else "site/olx_carros.json"

    # Fallbacks for paths if run from wrong directory
    if not os.path.exists(caminho_csv) and os.path.exists("olx_carros.csv"):
        caminho_csv = "olx_carros.csv"
    if not os.path.exists(caminho_json) and os.path.exists("olx_carros.json"):
        caminho_json = "olx_carros.json"

    print("=" * 60)
    print("  GERADOR DE PREVISÕES DE IA — AutoMercado")
    print("=" * 60)

    df = carregar_csv(caminho_csv)

    if len(df) < 10:
        print("\n   [AVISO] Dados insuficientes para treinar. JSON não foi alterado.")
        sys.exit(0)

    melhor, fe = treinar_e_escolher_melhor(df)
    previsoes_por_url = prever_para_todos(df, melhor, fe)

    if not previsoes_por_url:
        print("\n   [AVISO] Não foi possível ligar previsões ao JSON.")
        sys.exit(0)

    # Determine outputs based on inputs
    parent_json = os.path.dirname(caminho_json)
    output_json = os.path.join(parent_json, "olx_carros_ia.json") if parent_json else "olx_carros_ia.json"

    atualizar_json(caminho_json, previsoes_por_url, melhor.nome, melhor.metricas["mape"], output_json=output_json)

    # Persist the model state
    model_state = {
        "melhor_modelo_nome": melhor.nome,
        "melhor_modelo": melhor._m,
        "colunas_treino": fe.colunas_treino,
        "modelos_frequentes": fe.modelos_frequentes,
        "scaler": melhor.scaler if hasattr(melhor, "scaler") else None,
        "is_log": isinstance(melhor, RegExponencial),
        "is_log_features": isinstance(melhor, RegLogaritmica),
    }

    model_file = os.path.join(os.path.dirname(caminho_csv), "modelo_ia.pkl") if os.path.dirname(caminho_csv) else "modelo_ia.pkl"
    try:
        with open(model_file, "wb") as f:
            pickle.dump(model_state, f)
        print(f"   [PERSISTÊNCIA] Melhor modelo persistido com sucesso em '{model_file}'")
    except Exception as e:
        with open("modelo_ia.pkl", "wb") as f:
            pickle.dump(model_state, f)
        print(f"   [PERSISTÊNCIA] Modelo persistido no fallback local 'modelo_ia.pkl' due to: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n   [AVISO] Execução interrompida.")
        sys.exit(0)
    except Exception as e:
        print(f"\n   [ERRO CRÍTICO] Ocorreu um problema na execução: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
