#!/usr/bin/env python3
"""
evaluate_car.py
====================================================
Lê os dados de um carro a partir da linha de comandos, 
carrega o melhor modelo persistido em modelo_ia.pkl
e calcula a previsão de valor justo de mercado.
====================================================
"""

import argparse
import sys
import os
import re
import pickle
import numpy as np
import pandas as pd

# Mappings for standardization (must match training exactly)
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

def estimar_potencia(row):
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

def main():
    parser = argparse.ArgumentParser(description="Avaliador pontual de carro")
    parser.add_argument("--brand", type=str, required=True)
    parser.add_argument("--model", type=str, required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--price", type=int, default=0)
    parser.add_argument("--km", type=int, required=True)
    parser.add_argument("--fuel", type=str, default="Gasolina")
    parser.add_argument("--transmission", type=str, default="Manual")
    args = parser.parse_args()

    # Find the pickled model
    possible_paths = [
        "../JuOLXana/modelo_ia.pkl",
        "JuOLXana/modelo_ia.pkl",
        "modelo_ia.pkl",
        "../../JuOLXana/modelo_ia.pkl"
    ]
    model_path = None
    for p in possible_paths:
        if os.path.exists(p):
            model_path = p
            break

    if not model_path:
        print("Preço Estimado: ERROR - Modelo calibrado (modelo_ia.pkl) nao foi encontrado. Treine o modelo primeiro.")
        sys.exit(1)

    try:
        with open(model_path, "rb") as f:
            state = pickle.load(f)
    except Exception as e:
        print(f"Preço Estimado: ERROR - Falha ao carregar o modelo persistido: {e}")
        sys.exit(1)

    # Reconstruct input dataframe
    # Clean brand
    make_clean = BRAND_MAP.get(args.brand.strip().lower(), args.brand.strip().title())
    
    # Clean model
    model_word = args.model.strip().split()[0] if args.model.strip() else "Outro"
    modelos_frequentes = state.get("modelos_frequentes", [])
    model_clean = model_word if model_word in modelos_frequentes else "Outro"

    df_carro = pd.DataFrame([{
        "make": make_clean,
        "model": model_clean,
        "year": args.year,
        "price": args.price,
        "mileage": args.km,
        "fuel": args.fuel.strip(),
        "gear": args.transmission.strip()
    }])

    # Estimate HP
    df_carro["hp"] = df_carro.apply(estimar_potencia, axis=1)

    # Feature Engineering
    df_carro["age"] = 2026 - df_carro["year"]
    df_carro["km_per_year"] = df_carro["mileage"] / (df_carro["age"] + 1)

    # Prepare features
    CAMPOS_NUMERICOS = ["mileage", "hp", "year", "age", "km_per_year"]
    CAMPOS_CATEGORICOS = ["make", "model", "fuel", "gear"]

    X = df_carro[CAMPOS_NUMERICOS + CAMPOS_CATEGORICOS].copy()
    X = pd.get_dummies(X, columns=CAMPOS_CATEGORICOS)

    # Align columns
    colunas_treino = state["colunas_treino"]
    for col in colunas_treino:
        if col not in X.columns:
            X[col] = 0
    X = X[colunas_treino]
    X_val = X.values.astype(np.float64)

    # Apply scaling if linear model
    scaler = state.get("scaler")
    if scaler is not None:
        X_val[:, :5] = scaler.transform(X_val[:, :5])

    # Apply log features if RegLogaritmica
    if state.get("is_log_features"):
        X_val[:, 0] = np.log1p(np.maximum(0, X_val[:, 0]))
        X_val[:, 1] = np.log1p(np.maximum(0, X_val[:, 1]))
        X_val[:, 4] = np.log1p(np.maximum(0, X_val[:, 4]))

    # Predict
    model = state["melhor_modelo"]
    y_pred = model.predict(X_val)[0]

    # Apply exponential transform if RegExponencial
    if state.get("is_log"):
        y_pred = np.expm1(y_pred)

    preco_final = max(int(round(y_pred, 0)), 500)
    
    # Print the expected outputs for Qt
    print(f"Preço Estimado: {preco_final} €")
    print(f"Modelo IA Utilizado: {state['melhor_modelo_nome']}")
    if args.price > 0:
        dif = preco_final - args.price
        status = f"BARATO (economiza {dif} €)" if dif > 0 else f"CARO (paga {abs(dif)} € a mais)"
        print(f"Estatuto: {status}")

if __name__ == "__main__":
    main()
