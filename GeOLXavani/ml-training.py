# =============================================================
# Avaliador Inteligente de Carros — Versão Atualizada
# Modelos: Reg. Linear | Reg. Exponencial | Reg. Logarítmica |
#          Random Forest | XGBoost | LightGBM
# =============================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import warnings
import sys
import os
import re
import pickle
warnings.filterwarnings("ignore")

from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    console = Console()
except ImportError:
    class Console:
        def clear(self): pass
        def print(self, *args, **kwargs): print(*args)
    console = Console()

# =============================================================
# 1. CONFIGURAÇÃO CENTRAL
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

    CORES = {
        "Regressão Linear" : "#4A90D9",
        "Reg. Exponencial" : "#E8744A",
        "Reg. Logarítmica" : "#64B5F6",
        "Random Forest"    : "#2EAB7B",
        "XGBoost"          : "#E53935",
        "LightGBM"         : "#AB47BC",
    }

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
# 2. ENGENHARIA DE FEATURES E LIMPEZA
# =============================================================

class FeatureEngineer:
    def __init__(self):
        self.colunas_treino = None
        self.modelos_frequentes = None

    def fit_modelos(self, models_series):
        # Group models with count < 3 into "Outro"
        counts = models_series.value_counts()
        self.modelos_frequentes = counts[counts >= 3].index.tolist()

    def preparar(self, df: pd.DataFrame, fit_mode=False) -> pd.DataFrame:
        df_copy = df.copy()
        
        # Apply simplified model grouping
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
        if self.colunas_treino is None:
            raise RuntimeError("Chame fit() primeiro.")
        # Ensure all columns from training are present
        for col in self.colunas_treino:
            if col not in X.columns:
                X[col] = 0
        return X[self.colunas_treino]

# =============================================================
# 3. MODELOS
# =============================================================

class ModeloBase:
    def __init__(self, nome, cor, nota=""):
        self.nome   = nome
        self.cor    = cor
        self.nota   = nota
        self._m     = None
        self.metricas = {}
        self.y_pred_teste = None

    def treinar(self, X, y): raise NotImplementedError
    def prever(self, X):     raise NotImplementedError

    def avaliar(self, X_teste, y_teste):
        y_pred = self.prever(X_teste)
        self.y_pred_teste = y_pred
        self.metricas = dict(
            mae  = mean_absolute_error(y_teste, y_pred),
            rmse = np.sqrt(mean_squared_error(y_teste, y_pred)),
            r2   = r2_score(y_teste, y_pred),
            mape = np.mean(np.abs((y_teste - y_pred) / np.where(y_teste == 0, 1, y_teste))) * 100,
        )
        return self.metricas

class RegLinear(ModeloBase):
    def __init__(self):
        super().__init__("Regressão Linear", Config.CORES["Regressão Linear"])
        self.scaler = StandardScaler()

    def treinar(self, X, y):
        self._m = LinearRegression()
        X_scaled = X.copy()
        # Scale numeric features (first 5 columns)
        X_scaled[:, :5] = self.scaler.fit_transform(X[:, :5])
        self._m.fit(X_scaled, y)

    def prever(self, X):
        X_scaled = X.copy()
        X_scaled[:, :5] = self.scaler.transform(X[:, :5])
        return self._m.predict(X_scaled)

class RegExponencial(ModeloBase):
    def __init__(self):
        super().__init__("Reg. Exponencial", Config.CORES["Reg. Exponencial"], "(log target)")
        self.scaler = StandardScaler()

    def treinar(self, X, y):
        # Use Ridge regression for stability
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
        super().__init__("Reg. Logarítmica", Config.CORES["Reg. Logarítmica"], "(log features)")
        self.scaler = StandardScaler()

    def _transformar(self, X: np.ndarray) -> np.ndarray:
        Xl = X.astype(np.float64)
        # Apply log transform to mileage (idx 0), hp (idx 1), km_per_year (idx 4)
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
    def __init__(self):
        super().__init__("Random Forest", Config.CORES["Random Forest"])

    def treinar(self, X, y):
        self._m = RandomForestRegressor(
            n_estimators=150, max_depth=15,
            min_samples_leaf=2, n_jobs=-1, random_state=Config.RANDOM_STATE)
        self._m.fit(X, y)

    def prever(self, X):
        return self._m.predict(X)

class XGB(ModeloBase):
    def __init__(self):
        super().__init__("XGBoost", Config.CORES["XGBoost"])

    def treinar(self, X, y):
        self._m = XGBRegressor(
            n_estimators=200, max_depth=5, learning_rate=0.06,
            subsample=0.8, colsample_bytree=0.8,
            random_state=Config.RANDOM_STATE, verbosity=0)
        self._m.fit(X, y)

    def prever(self, X):
        return self._m.predict(X)

class LGBM(ModeloBase):
    def __init__(self):
        super().__init__("LightGBM", Config.CORES["LightGBM"])

    def treinar(self, X, y):
        self._m = LGBMRegressor(
            n_estimators=200, max_depth=5, learning_rate=0.06,
            subsample=0.8, colsample_bytree=0.8,
            random_state=Config.RANDOM_STATE, verbose=-1)
        self._m.fit(X, y)

    def prever(self, X):
        return self._m.predict(X)

# =============================================================
# 4. GESTOR DE MODELOS
# =============================================================

class ModelManager:
    MODELOS_DISPONIVEIS = [RegLinear, RegExponencial, RegLogaritmica, RndForest, XGB, LGBM]

    def __init__(self, fe: FeatureEngineer):
        self.fe      = fe
        self.modelos = [cls() for cls in self.MODELOS_DISPONIVEIS]
        self.melhor  = None
        self.y_teste = None

    def treinar_e_avaliar(self, X_enc: pd.DataFrame, y: np.ndarray):
        X_tr, X_te, y_tr, y_te = train_test_split(
            X_enc.values.astype(np.float64), y,
            test_size=Config.TEST_SIZE, random_state=Config.RANDOM_STATE)

        self.y_teste = y_te
        print(f"\n   Treino : {len(X_tr):,} amostras")
        print(f"   Teste  : {len(X_te):,} amostras\n")

        for m in self.modelos:
            print(f"   -> {m.nome} {m.nota}...".ljust(44), end=" ", flush=True)
            m.treinar(X_tr, y_tr)
            met = m.avaliar(X_te, y_te)
            print(f"R2={met['r2']:.3f} | MAE={met['mae']:,.0f}€ | MAPE={met['mape']:.1f}%")

        self.melhor = min(self.modelos, key=lambda m: m.metricas["mape"])

    def prever_carro(self, df_carro: pd.DataFrame) -> dict:
        X = self.fe.preparar(df_carro)
        X = self.fe.alinhar(X)
        Xv = X.values.astype(np.float64)
        return {m.nome: max(float(m.prever(Xv)[0]), Config.PRECO_MIN) for m in self.modelos}

# =============================================================
# 5. GRÁFICOS
# =============================================================

def gerar_graficos(modelos: list, y_teste: np.ndarray, ficheiro="comparacao_modelos.png"):
    print("\n   A gerar gráficos...")
    nomes  = [m.nome  for m in modelos]
    cores  = [m.cor   for m in modelos]
    mapes  = [m.metricas["mape"] for m in modelos]
    r2s    = [m.metricas["r2"]   for m in modelos]
    melhor = min(modelos, key=lambda m: m.metricas["mape"]).nome
    idx_m  = nomes.index(melhor)

    TEXTO, GRADE = "#E8E8E8", "#2A2A3A"

    def estilo(ax):
        ax.set_facecolor("#1A1B26")
        ax.tick_params(colors=TEXTO, labelsize=8)
        ax.xaxis.label.set_color(TEXTO)
        ax.yaxis.label.set_color(TEXTO)
        ax.title.set_color(TEXTO)
        for s in ax.spines.values(): s.set_edgecolor(GRADE)
        ax.grid(color=GRADE, linewidth=0.5)

    fig = plt.figure(figsize=(18, 16))
    fig.patch.set_facecolor("#0F1117")
    gs  = gridspec.GridSpec(3, 6, figure=fig, hspace=0.45, wspace=0.60)

    for i, m in enumerate(modelos):
        linha, col_idx = divmod(i, 3)
        if linha > 1: break
        ax = fig.add_subplot(gs[linha, col_idx * 2 : col_idx * 2 + 2])
        ax.scatter(y_teste, m.y_pred_teste, alpha=0.2, s=5, color=m.cor)
        lim = max(y_teste.max(), m.y_pred_teste.max())
        ax.plot([0, lim], [0, lim], "w--", linewidth=1, alpha=0.5)
        ax.set_xlabel("Real (€)", fontsize=8)
        ax.set_ylabel("Previsto (€)", fontsize=8)
        titulo = m.nome + (f" {m.nota}" if m.nota else "")
        ax.set_title(f"{titulo}\nR2={m.metricas['r2']:.3f}  MAE={m.metricas['mae']:,.0f}€", fontsize=9, fontweight="bold")
        estilo(ax)

    nomes_curtos = [n.replace("Regressão Linear", "Reg. Linear").replace("Random Forest", "Rnd. Forest") for n in nomes]

    ax1 = fig.add_subplot(gs[2, 0:3])
    bars1 = ax1.bar(nomes_curtos, mapes, color=cores, edgecolor="none", width=0.6)
    for b, v, n in zip(bars1, mapes, nomes):
        c = "#FFD700" if n == melhor else TEXTO
        ax1.text(b.get_x()+b.get_width()/2, v+0.3, f"{v:.1f}%", ha="center", va="bottom", color=c, fontsize=9, fontweight="bold")
    bars1[idx_m].set_edgecolor("#FFD700")
    bars1[idx_m].set_linewidth(2)
    ax1.set_ylabel("MAPE — Erro % médio", fontsize=10)
    ax1.set_title("Erro Percentual Médio (MAPE) <- menor é melhor", fontsize=11, fontweight="bold")
    ax1.tick_params(axis="x", labelsize=8, rotation=20)
    estilo(ax1)

    ax2 = fig.add_subplot(gs[2, 3:6])
    bars2 = ax2.bar(nomes_curtos, r2s, color=cores, edgecolor="none", width=0.6)
    for b, v, n in zip(bars2, r2s, nomes):
        c = "#FFD700" if n == melhor else TEXTO
        ax2.text(b.get_x()+b.get_width()/2, v+0.003, f"{v:.3f}", ha="center", va="bottom", color=c, fontsize=9, fontweight="bold")
    bars2[idx_m].set_edgecolor("#FFD700")
    bars2[idx_m].set_linewidth(2)
    ax2.set_ylabel("R2 — Variância explicada", fontsize=10)
    ax2.set_title("R2 por Modelo <- maior é melhor", fontsize=11, fontweight="bold")
    ax2.set_ylim(0, 1.08)
    ax2.tick_params(axis="x", labelsize=8, rotation=20)
    estilo(ax2)

    fig.suptitle("Comparação de 6 Modelos de ML — Previsão do Preço de Carros\nDataset Raspado Localmente", fontsize=14, fontweight="bold", color=TEXTO, y=0.96)
    plt.savefig(ficheiro, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.show()
    print(f"   Gráfico guardado: {ficheiro}")

# =============================================================
# 6. SISTEMA PRINCIPAL
# =============================================================

class AvaliadorCarros:
    def __init__(self):
        self.fe       = FeatureEngineer()
        self.mm       = ModelManager(self.fe)
        self.dados    = None
        self.treinado = False

    def clean_title_make_model(self, row):
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
        
        # Model mapping
        partes_low = titulo_lower.split()
        first_word = partes_low[0] if partes_low else ""
        if first_word in MODEL_TO_BRAND:
            brand, model = MODEL_TO_BRAND[first_word]
            rest = titulo_limpo[len(first_word):].strip()
            model_details = (first_word + " " + " ".join(rest.split()[:2])).strip()
            return pd.Series([brand, model_details])
            
        # Search known brands
        for brand_key, brand_norm in BRAND_MAP.items():
            if brand_key in titulo_lower:
                idx = titulo_lower.find(brand_key)
                words_after = titulo_limpo[idx + len(brand_key):].strip().split()
                model = " ".join(words_after[:2]) if words_after else "Outro"
                return pd.Series([brand_norm, model])
                
        # Split fallback
        partes = titulo_limpo.split()
        if len(partes) >= 1:
            make = partes[0]
            make = re.sub(r'^[^\w]+', '', make)
            make = BRAND_MAP.get(make.lower(), make.title())
        else:
            make = "Desconhecido"
            
        model = " ".join(partes[1:3]) if len(partes) >= 2 else "Outro"
        return pd.Series([make, model])

    def estimar_potencia(self, row):
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

    def carregar(self, default_ficheiro="JuOLXana/olx_carros.csv"):
        # Se Qt ou terminal passar caminho via argumento
        if len(sys.argv) > 2 and sys.argv[2].endswith('.csv'):
            ficheiro = sys.argv[2]
        elif len(sys.argv) > 1 and sys.argv[1].endswith('.csv'):
            ficheiro = sys.argv[1]
        else:
            # Fallback pathing relative to execution source dir
            possible_paths = [
                default_ficheiro,
                "../" + default_ficheiro,
                "JuOLXana/olx_carros.csv",
                "../JuOLXana/olx_carros.csv",
                "carros_scraped.csv"
            ]
            ficheiro = None
            for p in possible_paths:
                if os.path.exists(p):
                    ficheiro = p
                    break
            if not ficheiro:
                ficheiro = default_ficheiro

        print(f"\n   A carregar '{ficheiro}'...")
        try:
            df = pd.read_csv(ficheiro)
        except FileNotFoundError:
            print(f"   ERRO: ficheiro '{ficheiro}' não encontrado. Executa o Scraper primeiro.")
            sys.exit(1)

        print(f"   {len(df):,} registos encontrados no CSV")

        # Rename columns to ensure English format for the ML pipeline
        df = df.rename(columns={
            "preco_eur": "price", "preco": "price",
            "km": "mileage", "quilometros": "mileage",
            "ano": "year", "marca": "make", "modelo": "model",
            "combustivel": "fuel", "transmissao": "gear"
        })

        # Re-map/Clean brand and model names in-place
        df[["make", "model"]] = df.apply(self.clean_title_make_model, axis=1)

        # Drop invalid dirty rows
        invalid_brands = ['Vendo', 'Raro', 'Carrinha', 'Laguna', 'Punto', 'Defender', 'Desconhecido', '!!!Mercedes-Benz']
        df = df[~df['make'].isin(invalid_brands)]

        # Heuristic power estimation
        df["hp"] = df.apply(self.estimar_potencia, axis=1)

        # Sanitização numérica
        for col in ["price", "mileage", "hp", "year"]:
            if col in df.columns:
                if df[col].dtype == object or df[col].dtype == str:
                    df[col] = df[col].astype(str).str.replace(r'[^\d]', '', regex=True)
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Remover linhas inválidas
        df = df.dropna(subset=["price", "mileage", "hp", "year"])
        
        df["price"] = df["price"].astype(int)
        df["mileage"] = df["mileage"].astype(int)
        df["year"] = df["year"].astype(int)
        df["hp"] = df["hp"].astype(int)

        # Feature Engineering
        df['age'] = 2026 - df['year']
        df['km_per_year'] = df['mileage'] / (df['age'] + 1)

        # Filtros
        df = df[(df["price"]   >= Config.PRECO_MIN)  & (df["price"]   <= Config.PRECO_MAX)]
        df = df[(df["mileage"] >= 0)                 & (df["mileage"] <= Config.KM_MAX)]
        df = df[(df["hp"]      > 0)                  & (df["hp"]      <= Config.HP_MAX)]

        print(f"   {len(df):,} registos válidos após filtragem, limpeza e engenharia de features")

        # Campo de busca para interface interativa
        df["_busca"] = (
            df["make"].astype(str).str.lower() + " " +
            df["model"].astype(str).str.lower()
        )

        self.dados = df

    def treinar(self, model_file="JuOLXana/modelo_ia.pkl"):
        if len(self.dados) < 10:
            print("   ERRO: Dados insuficientes para treinar os modelos (mínimo 10 registos).")
            return
            
        print("\n" + "=" * 62)
        print("  A treinar os 6 modelos com dados do Scraper...")
        print("=" * 62)

        X_enc = self.fe.preparar(self.dados, fit_mode=True)
        self.fe.fit(X_enc)
        y = self.dados["price"].values

        self.mm.treinar_e_avaliar(X_enc, y)
        self.treinado = True

        print("\n" + "=" * 72)
        print(f"  {'MODELO':<22} {'NOTA':<14} {'MAE':>9} {'RMSE':>9} {'R2':>7} {'MAPE':>7}")
        print("  " + "-" * 68)
        melhor_nome = self.mm.melhor.nome
        for m in self.mm.modelos:
            flag = " <- MELHOR" if m.nome == melhor_nome else ""
            print(f"  {m.nome:<22} {m.nota:<14} {m.metricas['mae']:>8,.0f}€ {m.metricas['rmse']:>8,.0f}€ {m.metricas['r2']:>6.3f} {m.metricas['mape']:>6.1f}%{flag}")
        print("=" * 72)

        # Persistence: save state
        try:
            # Create directories if needed
            parent_dir = os.path.dirname(model_file)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            with open(model_file, "wb") as f:
                pickle.dump(self, f)
            print(f"\n   [PERSISTÊNCIA] Modelo calibrado e salvo com sucesso em '{model_file}'!")
        except Exception as e:
            # Try saving in fallback location (current folder)
            fallback = os.path.basename(model_file)
            try:
                with open(fallback, "wb") as f:
                    pickle.dump(self, f)
                print(f"\n   [PERSISTÊNCIA] Modelo salvo em local alternativo '{fallback}' devido a: {e}")
            except:
                print(f"\n   [AVISO] Falha ao persistir modelo: {e}")

    def buscar(self, termo: str) -> pd.DataFrame:
        return self.dados[self.dados["_busca"].str.contains(termo.lower(), na=False)].sort_values("price")

    def avaliar_carro(self, df_carro: pd.DataFrame):
        # Apply standard preprocessors
        df_copy = df_carro.copy()
        if "make" in df_copy.columns:
            df_copy["make"] = df_copy["make"].astype(str).str.strip().apply(lambda x: BRAND_MAP.get(x.lower(), x.title()))
        if "model" in df_copy.columns:
            df_copy["model"] = df_copy["model"].astype(str).str.strip().apply(lambda x: str(x).split()[0] if x else "Outro")
        
        # Calculate dynamic age and km_per_year
        if "year" in df_copy.columns:
            df_copy["age"] = 2026 - df_copy["year"].astype(int)
        else:
            df_copy["age"] = 10
            
        if "mileage" in df_copy.columns:
            df_copy["km_per_year"] = df_copy["mileage"].astype(float) / (df_copy["age"] + 1)
        else:
            df_copy["km_per_year"] = 15000.0

        if "hp" not in df_copy.columns or pd.isna(df_copy["hp"]).any():
            df_copy["hp"] = df_copy.apply(self.estimar_potencia, axis=1)

        previsoes  = self.mm.prever_carro(df_copy)
        preco_real = df_carro["price"].iloc[0] if "price" in df_carro.columns and pd.notna(df_carro["price"].iloc[0]) else None
        return previsoes, preco_real

    def mostrar_avaliacao(self, previsoes: dict, preco_real=None):
        print(f"\n{'=' * 60}\n      AVALIAÇÃO DO CARRO\n{'=' * 60}")
        if preco_real: print(f"\n  Preço do Anúncio: {preco_real:,.0f} €")
        print(f"\n  PREVISÕES DOS MODELOS:")
        menor_erro = float("inf")
        melhor_nome = melhor_prev = None

        # Best predicted value
        melhor_prev = previsoes.get(self.mm.melhor.nome, list(previsoes.values())[0])
        melhor_nome = self.mm.melhor.nome

        for nome, prev in previsoes.items():
            if preco_real:
                erro_abs  = abs(prev - preco_real)
                erro_perc = (erro_abs / preco_real) * 100
                status = f"  BARATO (economiza {prev - preco_real:,.0f} €)" if prev > preco_real else f"   CARO (paga {preco_real - prev:,.0f} € a mais)"
                print(f"   {nome:<22}: {prev:>10,.0f} € | {status} | Erro: {erro_perc:.1f}%")
                if erro_abs < menor_erro:
                    menor_erro = erro_abs; melhor_nome = nome; melhor_prev = prev
            else:
                print(f"   {nome:<22}: {prev:>10,.0f} €")

        print(f"\n{'=' * 60}")
        if preco_real and melhor_nome:
            print(f"  MODELO MAIS PRECISO: {melhor_nome}\n  Valor justo de mercado: {melhor_prev:,.0f} €")
            dif = melhor_prev - preco_real
            msg = "  EXCELENTE OPORTUNIDADE! COMPRE!" if dif/preco_real > 0.15 else "  BOM NEGÓCIO!" if dif > 0 else "  NEGÓCIO DESFAVORÁVEL — EVITE!" if abs(dif)/preco_real > 0.15 else "   Caro, tente negociar."
            print(f"\n{msg} ({'abaixo' if dif > 0 else 'acima'} do mercado por {abs(dif):,.0f} €)")
        else:
            print(f"  Valor estimado médio ({melhor_nome}): {melhor_prev:,.0f} €")
        print(f"{'=' * 60}\n")

    def criar_carro_manual(self) -> pd.DataFrame:
        print("\n" + "=" * 50 + "\n     CRIAR CARRO PERSONALIZADO\n" + "=" * 50)
        carro = {}
        for campo in ["mileage", "hp", "year"]:
            v = input(f"   {campo}: ").strip()
            carro[campo] = int(v) if v.isdigit() else (100 if campo == "hp" else (2015 if campo == "year" else 100000))
        for campo in ["make", "model", "fuel", "gear"]:
            carro[campo] = input(f"   {campo}: ").strip()
        v = input("   price (preço opcional — Enter para saltar): ").strip()
        carro["price"] = int(v) if v.isdigit() else None
        return pd.DataFrame([carro])


def main():
    console.clear()
    print("=" * 56 + "\n    AVALIADOR INTELIGENTE DE CARROS   \n    Treinado com dados Dinâmicos do Scraper\n" + "=" * 56)
    
    # Path settings
    model_paths = ["JuOLXana/modelo_ia.pkl", "../JuOLXana/modelo_ia.pkl", "modelo_ia.pkl"]
    loaded = False
    av = None
    
    for p in model_paths:
        if os.path.exists(p):
            try:
                with open(p, "rb") as f:
                    av = pickle.load(f)
                loaded = True
                print(f"\n   [OK] Modelo carregado a partir do ficheiro de persistência '{p}'!")
                break
            except Exception as e:
                print(f"   [AVISO] Erro ao ler '{p}': {e}")
                
    if not loaded:
        av = AvaliadorCarros()
        av.carregar()
        # Train and save to default JuOLXana/modelo_ia.pkl
        av.treinar()
    
    while True:
        print("\n[1] Buscar carros no dataset\n[2] Criar e avaliar carro personalizado\n[3] Gerar gráficos comparativos\n[4] Sair")
        opcao = input("\n Opção: ").strip()
        if opcao == "1":
            termo = input("\n Pesquisa (ex: 'bmw 320'): ").strip()
            res   = av.buscar(termo)
            if res.empty: print("    Nenhum resultado encontrado."); continue
            for idx, row in res.head(10).iterrows():
                print(f"    ID {idx:>6} | {row['make']} {row['model']} | {int(row['year'])} | {int(row['mileage']):>9,} km | {int(row['price']):>9,} €")
            id_str = input("\n  ID do carro para avaliar: ").strip()
            if id_str.isdigit() and int(id_str) in res.index:
                previsoes, preco_real = av.avaliar_carro(res.loc[[int(id_str)]])
                av.mostrar_avaliacao(previsoes, preco_real)
        elif opcao == "2":
            av.mostrar_avaliacao(*av.avaliar_carro(av.criar_carro_manual()))
        elif opcao == "3":
            gerar_graficos(av.mm.modelos, av.mm.y_teste)
        elif opcao == "4":
            break


if __name__ == "__main__":
    main()