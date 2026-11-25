"""Putanje i opis izvora podataka."""
from pathlib import Path

KORIJEN = Path(__file__).resolve().parents[1]
SIROVO = KORIJEN / "data" / "raw"
PODACI = KORIJEN / "podaci"
PREDMEMORIJA = PODACI / "slike_384"
REZULTATI = KORIJEN / "rezultati"
MODELI = KORIJEN / "modeli"

SJEME = 42
VELICINA = 224
SERIJA = 64
TEZINSKO_SLABLJENJE = 1e-4
UDIO_RASTA = 0.15
RAZREDI = ["zdrava", "nezdrava"]  # indeks 1 = nezdrava (pozitivan razred)
Z, N = "zdrava", "nezdrava"

IZVORI = {
    "indoor_plant_disease": {
        "mapa": "indoor_plant_disease_7wbstnfpjy/raw_dataset", "uloga": "skup",
        "razredi": {
            "Money_Plant_Healthy": ("zlatni puzavac", Z),
            "Money_Plant_Bacterial_wilt_disease": ("zlatni puzavac", N),
            "Money_Plant_Manganese_Toxicity": ("zlatni puzavac", N),
            "Snake_Plant_Healthy": ("sansevierija", Z),
            "Snake_Plant_Anthracnose": ("sansevierija", N),
            "Snake_Plant_Leaf_Withering": ("sansevierija", N),
            "Spider_Plant_Healthy": ("zelenčica", Z),
            "Spider_Plant_Fungal_leaf_spot": ("zelenčica", N),
            "Spider_Plant_Leaf_Tip_Necrosis": ("zelenčica", N),
        },
    },
    "money_plant_atlas": {
        "mapa": "money_plant_atlas_rzjww3vdxt/MoneyPlant", "uloga": "skup",
        "razredi": {
            "Healthy": ("zlatni puzavac", Z),
            "Bacterial wilt disease": ("zlatni puzavac", N),
            "Manganese Toxicity": ("zlatni puzavac", N),
        },
    },
    "epipremnum_aureum": {
        "mapa": "epipremnum_aureum_kd8hs7ch6t/Money Plant(Dr. D Y Patil Institute of Technology)",
        "uloga": "skup",
        "razredi": {
            "Healthy": ("zlatni puzavac", Z),
            "Un-Healthy": ("zlatni puzavac", N),
            "Yellow Leaf": ("zlatni puzavac", N),
        },
    },
    "aloe_vera_diseases": {
        "mapa": "aloe_vera_diseases_cksmdjw8gy/Aole Vera Quality Grading Dataset/Original Alo Vera Dataset",
        "uloga": "skup",
        "razredi": {
            "Fresh Aloe Vera": ("aloja", Z),
            "Rust Aloe Vera": ("aloja", N),
            "Rot Aloe Vera": ("aloja", N),
        },
    },
    "aloe_vera_leaf_disease": {
        "mapa": "aloe_vera_leaf_disease_7w6t4zx33n/Aloe vera leaf disease detection dataset/final",
        "uloga": "skup",
        "razredi": {
            "Healthy": ("aloja", Z),
            "Aloe Rust": ("aloja", N),
            "Anthracnose": ("aloja", N),
            "Leaf Spot": ("aloja", N),
            "Sunburn": ("aloja", N),
        },
    },
    "plantvita_aloevera": {
        "mapa": "kaggle_plantvita_aloevera_gursimranjit/Aloevera", "uloga": "skup",
        "razredi": {
            "Healthy": ("aloja", Z),
            "Infected": ("aloja", N),
            "Wilting": ("aloja", N),
        },
    },
    "healthy_wilted": {
        "mapa": "kaggle_healthy_wilted_russellchan/houseplant_images", "uloga": "skup",
        "razredi": {"healthy": ("razne", Z), "wilted": ("razne", N)},
    },
    "indoor_leaf_health": {
        "mapa": "kaggle_indoor_leaf_health_gauravsaklani00/indoor-plant-dataset", "uloga": "skup",
        "razredi": {"healthy": ("razne", Z), "unhealthy": ("razne", N)},
    },
    "medicinal_leaf_health": {
        "mapa": "medicinal_leaf_health_89rfgtxbdc/Original Image Dataset", "uloga": "skup",
        "razredi": {
            "Aloe Vera Young Healthy": ("aloja", Z),
            "Aloe Vera Mature Healthy": ("aloja", Z),
            "Aloe Vera Disease": ("aloja", N),
            "Aloe Vera Dried": ("aloja", N),
            "Kalanchoe Pinnata Healthy": ("kalanhoja", Z),
            "Kalanchoe Pinnata Disease": ("kalanhoja", N),
            "Kalanchoe Pinnata Chlorotic": ("kalanhoja", N),
            "Hibiscus Rosa Sinensis Healthy": ("hibiskus", Z),
            "Hibiscus Rosa Sinensis Disease": ("hibiskus", N),
            "Hibiscus Rosa Sinensis Chlorotic": ("hibiskus", N),
        },
    },
    "medicinal_leaf_disease": {
        "mapa": "medicinal_leaf_disease_ncg7kk3gwx/Medicinal_leaf_dataset", "uloga": "skup",
        "razredi": {
            "Kalanchoe_Healthy": ("kalanhoja", Z),
            "Kalanchoe_Web_Blight": ("kalanhoja", N),
            "Kalanchoe_Yellow": ("kalanhoja", N),
            "Kalanchoe_Yellow_Blight": ("kalanhoja", N),
        },
    },
    "multiclass_medicinal": {
        "mapa": "multiclass_medicinal_fmf2s22ntd/Medicinal", "uloga": "skup",
        "razredi": {
            "Kalancho Asymptomatic": ("kalanhoja", Z),
            "Kalanchoe Symptomatic": ("kalanhoja", N),
            "Kalancho Complex Foliar Damage": ("kalanhoja", N),
        },
    },
    "combined_medicinal": {
        "mapa": "combined_medicinal_3kzjdcz97w/Combined Medicial Leaf Original Dataset", "uloga": "skup",
        "razredi": {
            "Kalancho Asymptomatic": ("kalanhoja", Z),
            "Kalancho Chewing insect damage": ("kalanhoja", N),
            "Kalancho Complex Foliar Damage": ("kalanhoja", N),
        },
    },
    "houseplant_health": {
        "mapa": "kaggle_houseplant_health_tarieretimitimi/data_raw", "uloga": "vanjski_stvarni",
        "razredi": {"Healthy": ("razne", Z), "Unhealthy": ("razne", N)},
    },
}

LICENCE = {
    "aloe_vera_diseases": "CC BY 4.0",
    "aloe_vera_leaf_disease": "CC BY 4.0",
    "combined_medicinal": "CC BY 4.0",
    "epipremnum_aureum": "CC BY 4.0",
    "healthy_wilted": "Data files © Original Authors",
    "indoor_leaf_health": "CC BY-SA 4.0",
    "indoor_plant_disease": "CC BY 4.0",
    "medicinal_leaf_disease": "CC BY 4.0",
    "medicinal_leaf_health": "CC BY 4.0",
    "money_plant_atlas": "CC BY 4.0",
    "multiclass_medicinal": "CC BY 4.0",
    "plantvita_aloevera": "nije navedena",
    "houseplant_health": "CC BY-SA 4.0",
    "plantdoc": "CC BY 4.0",
}

PLANTDOC_MAPA = "plantdoc"
PLANTDOC_ZDRAVI = {
    "Apple leaf", "Bell_pepper leaf", "Blueberry leaf", "Cherry leaf", "Peach leaf",
    "Raspberry leaf", "Soyabean leaf", "Strawberry leaf", "Tomato leaf", "grape leaf",
}

NASTAVCI = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".jfif"}
