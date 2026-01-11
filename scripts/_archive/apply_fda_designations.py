"""FDA Designations 적용 스크립트"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 알려진 FDA designations
fda_data = {
    # Gene therapies
    'ZYNTEGLO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'LYFGENIA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'SKYSONA': {'btd': True, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'CASGEVY': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ZOLGENSMA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'LUXTURNA': {'btd': True, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'HEMGENIX': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ROCTAVIAN': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'ELEVIDYS': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    
    # CAR-T
    'KYMRIAH': {'btd': True, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'YESCARTA': {'btd': True, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'TECARTUS': {'btd': True, 'ft': False, 'pr': True, 'od': True, 'aa': True},
    'BREYANZI': {'btd': True, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'ABECMA': {'btd': True, 'ft': False, 'pr': True, 'od': True, 'aa': True},
    'CARVYKTI': {'btd': True, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'AUCATZYL': {'btd': True, 'ft': False, 'pr': True, 'od': True, 'aa': True},
    
    # Rare disease
    'SPINRAZA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'EVRYSDI': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'DAYBUE': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'trofinetide': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'PALYNZIQ': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'NEXVIAZYME': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'GALAFOLD': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'GIVLAARI': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'OXLUMO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'IMCIVREE': {'btd': True, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'LIVMARLI': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'BYLVAY': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    
    # Oncology IO
    'KEYTRUDA': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'OPDIVO': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'TECENTRIQ': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'IMFINZI': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'LIBTAYO': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    
    # Oncology targeted
    'ENHERTU': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'PADCEV': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'TRODELVY': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'LUMAKRAS': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'KRAZATI': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'RETEVMO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'GAVRETO': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'TABRECTA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'AYVAKIT': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'QINLOCK': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'TIBSOVO': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'WELIREG': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'JAYPIRCA': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    'VORANIGO': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'DARZALEX': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': True},
    
    # Hematology
    'REBLOZYL': {'btd': False, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'PYRUKYND': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'EMPAVELI': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    
    # Neurology
    'LEQEMBI': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'lecanemab': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': True},
    'KISUNLA': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'donanemab': {'btd': True, 'ft': True, 'pr': True, 'od': False, 'aa': False},
    'NUPLAZID': {'btd': True, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'INGREZZA': {'btd': False, 'ft': False, 'pr': True, 'od': False, 'aa': False},
    'AUSTEDO': {'btd': False, 'ft': False, 'pr': True, 'od': True, 'aa': False},
    'VYVGART': {'btd': True, 'ft': True, 'pr': True, 'od': True, 'aa': False},
    'RYSTIGGO': {'btd
