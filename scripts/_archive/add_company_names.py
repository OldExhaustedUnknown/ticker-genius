#!/usr/bin/env python
"""
Add company_name field to all enriched JSON records.

This script adds a company_name field based on a ticker -> company name mapping.
For unknown tickers, it uses the ticker itself as a fallback.
"""

import json
from pathlib import Path
from datetime import datetime

# Comprehensive ticker -> company name mapping (100+ companies)
TICKER_TO_COMPANY = {
    # Major Pharma (Big Pharma)
    "PFE": "Pfizer",
    "MRK": "Merck & Co.",
    "JNJ": "Johnson & Johnson",
    "NVS": "Novartis",
    "LLY": "Eli Lilly",
    "AZN": "AstraZeneca",
    "GSK": "GlaxoSmithKline",
    "BMY": "Bristol-Myers Squibb",
    "ABBV": "AbbVie",
    "SNY": "Sanofi",
    "GILD": "Gilead Sciences",
    "AMGN": "Amgen",
    "REGN": "Regeneron Pharmaceuticals",
    "VRTX": "Vertex Pharmaceuticals",
    "BIIB": "Biogen",
    "TAK": "Takeda Pharmaceutical",
    "NVO": "Novo Nordisk",
    "TEVA": "Teva Pharmaceutical",
    "BAX": "Baxter International",
    "GEHC": "GE HealthCare",

    # Large Biotech
    "ALNY": "Alnylam Pharmaceuticals",
    "SGEN": "Seagen",
    "BMRN": "BioMarin Pharmaceutical",
    "INCY": "Incyte Corporation",
    "JAZZ": "Jazz Pharmaceuticals",
    "EXEL": "Exelixis",
    "NBIX": "Neurocrine Biosciences",
    "SRPT": "Sarepta Therapeutics",
    "UTHR": "United Therapeutics",
    "ALXN": "Alexion Pharmaceuticals",
    "IONS": "Ionis Pharmaceuticals",
    "BGNE": "BeiGene",
    "LEGN": "Legend Biotech",
    "MRNA": "Moderna",
    "NVAX": "Novavax",

    # Mid-Cap Biotech
    "ACAD": "ACADIA Pharmaceuticals",
    "AGIO": "Agios Pharmaceuticals",
    "AKBA": "Akebia Therapeutics",
    "ALKS": "Alkermes",
    "APLS": "Apellis Pharmaceuticals",
    "ARDX": "Ardelyx",
    "ARGX": "argenx",
    "ARWR": "Arrowhead Pharmaceuticals",
    "AXSM": "Axsome Therapeutics",
    "BCRX": "BioCryst Pharmaceuticals",
    "BHVN": "Biohaven Pharmaceutical",
    "BLUE": "bluebird bio",
    "BPMC": "Blueprint Medicines",
    "CORT": "Corcept Therapeutics",
    "CPRX": "Catalyst Pharmaceuticals",
    "CYTK": "Cytokinetics",
    "DCPH": "Deciphera Pharmaceuticals",
    "DNLI": "Denali Therapeutics",
    "DVAX": "Dynavax Technologies",
    "ESPR": "Esperion Therapeutics",
    "FGEN": "FibroGen",
    "FOLD": "Amicus Therapeutics",
    "GERN": "Geron Corporation",
    "HZNP": "Horizon Therapeutics",
    "ICPT": "Intercept Pharmaceuticals",
    "IMMU": "Immunomedics",
    "IMGN": "ImmunoGen",
    "INSM": "Insmed",
    "IOVA": "Iovance Biotherapeutics",
    "IRWD": "Ironwood Pharmaceuticals",
    "ITCI": "Intra-Cellular Therapies",
    "KRYS": "Krystal Biotech",
    "MDGL": "Madrigal Pharmaceuticals",
    "MGNX": "MacroGenics",
    "MIRM": "Mirum Pharmaceuticals",
    "MRTX": "Mirati Therapeutics",
    "MRUS": "Merus",
    "OCUL": "Ocular Therapeutix",
    "PCYC": "Pharmacyclics",
    "PGEN": "Precigen",
    "PTCT": "PTC Therapeutics",
    "QURE": "uniQure",
    "RARE": "Ultragenyx Pharmaceutical",
    "RETA": "Reata Pharmaceuticals",
    "SAGE": "Sage Therapeutics",
    "SNDX": "Syndax Pharmaceuticals",
    "SRRK": "Scholar Rock",
    "TGTX": "TG Therapeutics",
    "ZGNX": "Zogenix",

    # Small-Cap Biotech / Specialty Pharma
    "ABEO": "Abeona Therapeutics",
    "ACER": "Acer Therapeutics",
    "ACOG": "Acabar Therapeutics",
    "ADAP": "Adaptimmune Therapeutics",
    "ADMP": "Adamis Pharmaceuticals",
    "AGRX": "Agile Therapeutics",
    "AIR": "Air Industries Group",
    "ALDX": "Aldeyra Therapeutics",
    "ALVO": "Alvotech",
    "AMLX": "Amylyx Pharmaceuticals",
    "AMPH": "Amphastar Pharmaceuticals",
    "AMRX": "Amneal Pharmaceuticals",
    "AMYT": "Amryt Pharma",
    "APLT": "Applied Therapeutics",
    "AQST": "Aquestive Therapeutics",
    "ARQT": "Arcus Biosciences",
    "ASND": "Ascendis Pharma",
    "ATEK": "Athira Pharma",
    "ATNX": "Athenex",
    "ATRA": "Atara Biotherapeutics",
    "ATXI": "Avenue Therapeutics",
    "AUTL": "Autolus Therapeutics",
    "AVDL": "Avadel Pharmaceuticals",
    "AXGN": "AxoGen",
    "BBIO": "BridgeBio Pharma",
    "BCDF": "BC Discovery Pharma",
    "BCYC": "Bicycle Therapeutics",
    "BFRI": "Biofrontera",
    "BHC": "Bausch Health",
    "BLCO": "Bausch + Lomb",
    "BLRX": "BioLineRx",
    "BSX": "Boston Scientific",
    "BTAI": "BioXcel Therapeutics",
    "BXRXQ": "Baudax Bio",
    "BYSI": "BeyondSpring",
    "CALT": "Calliditas Therapeutics",
    "CAPR": "Capricor Therapeutics",
    "CCXI": "ChemoCentryx",
    "CDTX": "Cidara Therapeutics",
    "CHRS": "Coherus BioSciences",
    "CKPT": "Checkpoint Therapeutics",
    "CLSD": "Clearside Biomedical",
    "CLVS": "Clovis Oncology",
    "CMRX": "Chimerix",
    "CRMD": "Cormedix",
    "CRNX": "Crinetics Pharmaceuticals",
    "CTIC": "CTI BioPharma",
    "CTXR": "Citius Pharmaceuticals",
    "CXDO": "Crexendo",
    "DARE": "Dare Bioscience",
    "DAWN": "Day One Biopharmaceuticals",
    "DCTH": "Delcath Systems",
    "DERM": "Journey Medical",
    "EBS": "Emergent BioSolutions",
    "EGRX": "Eagle Pharmaceuticals",
    "EPZM": "Epizyme",
    "ETON": "Eton Pharmaceuticals",
    "EVFM": "Evofem Biosciences",
    "EVOK": "Evoke Pharma",
    "EXP": "Eagle Materials",
    "EYEN": "Eyenovia",
    "FBIO": "Fortress Biotech",
    "FBYD": "Falcone Technology",
    "FENC": "Fennec Pharmaceuticals",
    "FHN": "First Horizon",
    "GKOS": "Glaukos Corporation",
    "GMAB": "Genmab",
    "GMDA": "Gamida Cell",
    "GNFT": "Genfit",
    "GRTX": "Galera Therapeutics",
    "HCM": "HUTCHMED",
    "HRMY": "Harmony Biosciences",
    "HRTX": "Heron Therapeutics",
    "HUMA": "Humacyte",
    "IBRX": "ImmunityBio",
    "IMCR": "Immunocore",
    "IMPL": "Impel Pharmaceuticals",
    "INVA": "Innoviva",
    "ISEE": "IVERIC bio",
    "ITRM": "Iterum Therapeutics",
    "KALV": "KalVista Pharmaceuticals",
    "KURA": "Kura Oncology",
    "LENZ": "Lenz Therapeutics",
    "LPCN": "Lipocine",
    "LQDA": "Liquidia Technologies",
    "LXRX": "Lexicon Pharmaceuticals",
    "MCRB": "Seres Therapeutics",
    "MDWD": "MediWound",
    "MESO": "Mesoblast",
    "MIST": "Milestone Pharmaceuticals",
    "MLTC": "MLT Pharmaceuticals",
    "MNK": "Mallinckrodt",
    "MRNS": "Marinus Pharmaceuticals",
    "MYOV": "Myovant Sciences",
    "NBRV": "Nabriva Therapeutics",
    "NERV": "Minerva Neurosciences",
    "NOVN": "Novan",
    "NUVB": "Nuvation Bio",
    "OGN": "Organon",
    "OMER": "Omeros Corporation",
    "OPK": "OPKO Health",
    "OPTN": "OptiNose",
    "ORTX": "Orchard Therapeutics",
    "OTLK": "Outlook Therapeutics",
    "OYST": "Oyster Point Pharma",
    "PCRX": "Pacira BioSciences",
    "PHAR": "Pharming Group",
    "PHAT": "Phathom Pharmaceuticals",
    "PLX": "Protalix BioTherapeutics",
    "PRGO": "Perrigo Company",
    "PRVB": "Provention Bio",
    "RCKT": "Rocket Pharmaceuticals",
    "RDY": "Dr. Reddy's Laboratories",
    "REPL": "Replimune Group",
    "RGNX": "REGENXBIO",
    "RIGL": "Rigel Pharmaceuticals",
    "RMTI": "Rockwell Medical",
    "RNA": "Avidity Biosciences",
    "ROIV": "Roivant Sciences",
    "RVLPQ": "Revlon",
    "RVNC": "Revance Therapeutics",
    "RYTM": "Rhythm Pharmaceuticals",
    "SBBP": "Strongbridge Biopharma",
    "SCLX": "Scilex Holding",
    "SCPH": "scPharmaceuticals",
    "SCYX": "SCYNEXIS",
    "SDZ": "Sandoz",
    "SESN": "Sesen Bio",
    "SLNO": "Soleno Therapeutics",
    "SPPI": "Spectrum Pharmaceuticals",
    "SPRO": "Spero Therapeutics",
    "SPRY": "ARS Pharmaceuticals",
    "STSA": "Satsuma Pharmaceuticals",
    "SUPN": "Supernus Pharmaceuticals",
    "SWTX": "SpringWorks Therapeutics",
    "TARS": "Tarsus Pharmaceuticals",
    "TCDA": "Tricida",
    "THTX": "Theratechnologies",
    "TNXP": "Tonix Pharmaceuticals",
    "TRVN": "Trevena",
    "TSVT": "2seventy bio",
    "TVTX": "Travere Therapeutics",
    "TXMD": "TherapeuticsMD",
    "UCB": "UCB",
    "UHS": "Universal Health Services",
    "UNCY": "Unicycive Therapeutics",
    "URGN": "UroGen Pharma",
    "VALN": "Valneva",
    "VBIV": "VBI Vaccines",
    "VCEL": "Vericel Corporation",
    "VNDA": "Vanda Pharmaceuticals",
    "VRCA": "Verrica Pharmaceuticals",
    "VRDN": "Viridian Therapeutics",
    "VRNA": "Verona Pharma",
    "VSTM": "Verastem",
    "VTRS": "Viatris",
    "XERS": "Xeris Biopharma",
    "XFOR": "X4 Pharmaceuticals",
    "YMAB": "Y-mAbs Therapeutics",
    "ZEAL": "Zealand Pharma",
    "ZVRA": "Zevra Therapeutics",
}


def get_company_name(ticker: str) -> str:
    """Get company name for a ticker, fallback to ticker if unknown."""
    return TICKER_TO_COMPANY.get(ticker, ticker)


def add_company_names_to_files():
    """Add company_name field to all enriched JSON files."""
    enriched_dir = Path("d:/ticker-genius/data/enriched")

    if not enriched_dir.exists():
        print(f"Error: Directory {enriched_dir} does not exist")
        return

    json_files = list(enriched_dir.glob("*.json"))
    print(f"Found {len(json_files)} JSON files to process")

    updated_count = 0
    skipped_count = 0
    error_count = 0
    unknown_tickers = set()

    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            ticker = data.get("ticker")
            if not ticker:
                print(f"Warning: No ticker in {json_file.name}")
                skipped_count += 1
                continue

            company_name = get_company_name(ticker)

            # Track unknown tickers
            if company_name == ticker:
                unknown_tickers.add(ticker)

            # Add company_name field after ticker
            if "company_name" not in data or data["company_name"] != company_name:
                # Create new ordered dict with company_name after ticker
                new_data = {}
                for key, value in data.items():
                    new_data[key] = value
                    if key == "ticker":
                        new_data["company_name"] = company_name

                # If ticker wasn't found (shouldn't happen), add at end
                if "company_name" not in new_data:
                    new_data["company_name"] = company_name

                with open(json_file, "w", encoding="utf-8") as f:
                    json.dump(new_data, f, indent=2, ensure_ascii=False)

                updated_count += 1
            else:
                skipped_count += 1

        except json.JSONDecodeError as e:
            print(f"Error parsing {json_file.name}: {e}")
            error_count += 1
        except Exception as e:
            print(f"Error processing {json_file.name}: {e}")
            error_count += 1

    print(f"\n{'='*50}")
    print(f"Results:")
    print(f"  Updated: {updated_count}")
    print(f"  Skipped (already has company_name): {skipped_count}")
    print(f"  Errors: {error_count}")
    print(f"  Total: {len(json_files)}")

    if unknown_tickers:
        print(f"\nUnknown tickers (using ticker as company name):")
        for ticker in sorted(unknown_tickers):
            print(f"  - {ticker}")

    print(f"\nMapping coverage: {len(TICKER_TO_COMPANY)} companies in dictionary")


if __name__ == "__main__":
    print(f"Add Company Names Script")
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"{'='*50}\n")

    add_company_names_to_files()

    print(f"\nCompleted at: {datetime.now().isoformat()}")
