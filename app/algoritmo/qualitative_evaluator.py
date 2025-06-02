"""
Evaluador cualitativo para el algoritmo de recomendación de motos.
Maneja todas las preguntas cualitativas (no numéricas) del test.
"""
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Any, Optional, Union

logger = logging.getLogger(__name__)

class QualitativeEvaluator:
    """
    Evaluador que procesa y puntúa criterios cualitativos del test de preferencias.
    Incluye todas las preguntas no numéricas: experiencia, uso, pasajeros, combustible, etc.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Mapeos de compatibilidad experiencia -> características de moto
        self.experiencia_compatibility = {
            'principiante': {
                'potencia_max': 50,  # CV máximos recomendados
                'cilindrada_max': 400,  # cc máximos
                'peso_min': 120,  # kg mínimos para estabilidad
                'tipos_recomendados': ['naked', 'scooter', 'custom'],
                'tipos_evitar': ['sport', 'supermoto'],
                'score_modifier': 1.0
            },
            'intermedio': {
                'potencia_max': 120,
                'cilindrada_max': 800,
                'peso_min': 100,
                'tipos_recomendados': ['naked', 'adventure', 'touring', 'sport'],
                'tipos_evitar': [],
                'score_modifier': 1.2
            },
            'experto': {
                'potencia_max': 999999,  # Sin límite
                'cilindrada_max': 999999,
                'peso_min': 80,
                'tipos_recomendados': ['sport', 'supermoto', 'naked', 'adventure'],
                'tipos_evitar': [],
                'score_modifier': 1.5
            }
        }
        
        # Mapeos uso previsto -> tipos de moto compatibles
        self.uso_compatibility = {
            'ciudad': {
                'tipos_ideales': ['naked', 'scooter'],
                'tipos_buenos': ['custom', 'street'],
                'tipos_malos': ['touring', 'adventure', 'enduro'],
                'potencia_ideal': (25, 80),
                'peso_ideal': (100, 200)
            },
            'carretera': {
                'tipos_ideales': ['touring', 'sport', 'naked'],
                'tipos_buenos': ['adventure'],
                'tipos_malos': ['scooter'],
                'potencia_ideal': (60, 150),
                'peso_ideal': (150, 300)
            },
            'mixto': {
                'tipos_ideales': ['naked', 'adventure'],
                'tipos_buenos': ['sport', 'touring', 'custom'],
                'tipos_malos': [],
                'potencia_ideal': (40, 120),
                'peso_ideal': (120, 250)
            },
            'aventura': {
                'tipos_ideales': ['adventure', 'enduro'],
                'tipos_buenos': ['naked'],
                'tipos_malos': ['scooter', 'sport', 'custom'],
                'potencia_ideal': (50, 130),
                'peso_ideal': (130, 280)
            }
        }
        
        # Mapeos pasajeros/carga -> características necesarias
        self.pasajeros_compatibility = {
            'solo': {
                'peso_max_bonus': 0,
                'tipos_permitidos': 'all',
                'score_bonus': 0
            },
            'ocasional': {
                'peso_max_bonus': 20,  # Prefiere motos hasta 20kg más pesadas
                'tipos_recomendados': ['naked', 'touring', 'adventure'],
                'tipos_evitar': ['sport'],
                'score_bonus': 1
            },
            'frecuente': {
                'peso_max_bonus': 40,
                'tipos_recomendados': ['touring', 'adventure', 'custom'],
                'tipos_evitar': ['sport', 'scooter'],
                'score_bonus': 2
            },
            'carga': {
                'peso_max_bonus': 60,
                'tipos_recomendados': ['touring', 'adventure'],
                'tipos_evitar': ['sport', 'scooter', 'naked'],
                'score_bonus': 3
            }
        }
        
        # Mapeos combustible vs potencia -> balances ideales
        self.combustible_compatibility = {
            'ahorro': {
                'potencia_max': 80,
                'cilindrada_max': 600,
                'tipos_recomendados': ['scooter', 'naked'],
                'penalizacion_potencia_alta': -2.0
            },
            'potencia': {
                'potencia_min': 60,
                'tipos_recomendados': ['sport', 'naked', 'adventure'],
                'bonus_potencia_alta': 2.0
            },
            'equilibrio': {
                'potencia_ideal': (40, 100),
                'tipos_recomendados': ['naked', 'adventure', 'touring'],
                'score_modifier': 1.0
            }
        }
        
        # Mapeos relación potencia/peso
        self.potencia_peso_compatibility = {
            'alta': {
                'ratio_min': 0.3,  # CV/kg mínimo
                'tipos_recomendados': ['sport', 'naked', 'supermoto'],
                'bonus_ratio_alto': 2.0
            },
            'media': {
                'ratio_ideal': (0.2, 0.4),
                'tipos_recomendados': ['naked', 'adventure', 'touring'],
                'score_modifier': 1.0
            },
            'baja': {
                'ratio_max': 0.25,
                'tipos_recomendados': ['custom', 'touring', 'scooter'],
                'penalizacion_ratio_alto': -1.5
            }
        }
        
        # Mapeos preferencia rendimiento vs economía
        self.rendimiento_compatibility = {
            'rendimiento': {
                'potencia_min': 70,
                'tipos_recomendados': ['sport', 'naked', 'supermoto'],
                'bonus_potencia': 1.5,
                'penalizacion_economia': -1.0
            },
            'economia': {
                'potencia_max': 60,
                'cilindrada_max': 500,
                'tipos_recomendados': ['scooter', 'naked'],
                'bonus_economia': 1.5,
                'penalizacion_potencia': -1.0
            },
            'balance': {
                'potencia_ideal': (40, 90),
                'tipos_recomendados': ['naked', 'adventure'],
                'score_modifier': 1.0
            }
        }

    def evaluate_moto_qualitative(self, user_preferences: Dict[str, Any], 
                                 moto: pd.Series) -> Tuple[float, List[str]]:
        """
        Evalúa una moto usando criterios cualitativos del test
        """
        total_score = 0.0
        reasons = []
        
        self.logger.info(f"[QUALITATIVE] Iniciando evaluación cualitativa de moto {moto.get('id')}")
        self.logger.info(f"[QUALITATIVE] Preferencias cualitativas: {user_preferences}")
        
        # Extraer características de la moto
        moto_potencia = float(moto.get('potencia', 0))
        moto_cilindrada = float(moto.get('cilindrada', 0))
        moto_peso = float(moto.get('peso', 0))
        moto_tipo = str(moto.get('tipo', '')).lower()
        
        # 1. EXPERIENCIA DEL USUARIO
        experiencia = user_preferences.get('experiencia', 'intermedio')
        if experiencia in self.experiencia_compatibility:
            exp_config = self.experiencia_compatibility[experiencia]
            
            # Verificar límites de potencia
            if moto_potencia <= exp_config['potencia_max']:
                score = 3.0 * exp_config['score_modifier']
                total_score += score
                reasons.append(f"✓ Potencia adecuada para {experiencia} ({moto_potencia}CV) [+{score:.1f}]")
            else:
                penalty = min(2.0, (moto_potencia - exp_config['potencia_max']) / 50)
                total_score -= penalty
                reasons.append(f"⚠ Potencia alta para {experiencia} ({moto_potencia}CV) [-{penalty:.1f}]")
            
            # Verificar tipos recomendados
            for tipo_recomendado in exp_config['tipos_recomendados']:
                if tipo_recomendado in moto_tipo:
                    bonus = 2.0 * exp_config['score_modifier']
                    total_score += bonus
                    reasons.append(f"✓ Tipo {moto_tipo} recomendado para {experiencia} [+{bonus:.1f}]")
                    break
            
            # Penalizar tipos a evitar
            for tipo_evitar in exp_config['tipos_evitar']:
                if tipo_evitar in moto_tipo:
                    penalty = 2.0
                    total_score -= penalty
                    reasons.append(f"⚠ Tipo {moto_tipo} no recomendado para {experiencia} [-{penalty:.1f}]")
                    break

        # 2. USO PREVISTO
        uso = user_preferences.get('tipo_uso', user_preferences.get('uso_previsto', 'mixto'))
        if uso in self.uso_compatibility:
            uso_config = self.uso_compatibility[uso]
            
            # Verificar tipos ideales
            for tipo_ideal in uso_config['tipos_ideales']:
                if tipo_ideal in moto_tipo:
                    bonus = 3.0
                    total_score += bonus
                    reasons.append(f"✓ Tipo {moto_tipo} ideal para uso {uso} [+{bonus:.1f}]")
                    break
            else:
                # Verificar tipos buenos
                for tipo_bueno in uso_config['tipos_buenos']:
                    if tipo_bueno in moto_tipo:
                        bonus = 1.5
                        total_score += bonus
                        reasons.append(f"✓ Tipo {moto_tipo} bueno para uso {uso} [+{bonus:.1f}]")
                        break
                else:
                    # Verificar tipos malos
                    for tipo_malo in uso_config['tipos_malos']:
                        if tipo_malo in moto_tipo:
                            penalty = 2.0
                            total_score -= penalty
                            reasons.append(f"⚠ Tipo {moto_tipo} no ideal para uso {uso} [-{penalty:.1f}]")
                            break
            
            # Verificar rango de potencia ideal para el uso
            potencia_min, potencia_max = uso_config['potencia_ideal']
            if potencia_min <= moto_potencia <= potencia_max:
                bonus = 2.0
                total_score += bonus
                reasons.append(f"✓ Potencia ideal para uso {uso} ({moto_potencia}CV) [+{bonus:.1f}]")
            elif moto_potencia < potencia_min:
                penalty = min(1.5, (potencia_min - moto_potencia) / 20)
                total_score -= penalty
                reasons.append(f"⚠ Potencia baja para uso {uso} [-{penalty:.1f}]")
            else:
                penalty = min(1.0, (moto_potencia - potencia_max) / 30)
                total_score -= penalty
                reasons.append(f"⚠ Potencia excesiva para uso {uso} [-{penalty:.1f}]")

        # 3. PASAJEROS Y CARGA
        pasajeros = user_preferences.get('pasajeros_carga', 'solo')
        if pasajeros in self.pasajeros_compatibility:
            pas_config = self.pasajeros_compatibility[pasajeros]
            
            if pasajeros != 'solo':
                # Verificar tipos recomendados para pasajeros
                if 'tipos_recomendados' in pas_config:
                    for tipo_rec in pas_config['tipos_recomendados']:
                        if tipo_rec in moto_tipo:
                            bonus = pas_config['score_bonus']
                            total_score += bonus
                            reasons.append(f"✓ Tipo {moto_tipo} adecuado para {pasajeros} [+{bonus:.1f}]")
                            break
                
                # Penalizar tipos a evitar
                if 'tipos_evitar' in pas_config:
                    for tipo_evitar in pas_config['tipos_evitar']:
                        if tipo_evitar in moto_tipo:
                            penalty = pas_config['score_bonus']
                            total_score -= penalty
                            reasons.append(f"⚠ Tipo {moto_tipo} no ideal para {pasajeros} [-{penalty:.1f}]")
                            break

        # 4. COMBUSTIBLE VS POTENCIA
        combustible_pref = user_preferences.get('combustible_potencia', 'equilibrio')
        if combustible_pref in self.combustible_compatibility:
            comb_config = self.combustible_compatibility[combustible_pref]
            
            if combustible_pref == 'ahorro':
                if moto_potencia <= comb_config['potencia_max']:
                    bonus = 2.0
                    total_score += bonus
                    reasons.append(f"✓ Potencia económica ({moto_potencia}CV) [+{bonus:.1f}]")
                else:
                    penalty = abs(comb_config['penalizacion_potencia_alta'])
                    total_score -= penalty
                    reasons.append(f"⚠ Alta potencia vs preferencia de ahorro [-{penalty:.1f}]")
                    
            elif combustible_pref == 'potencia':
                if moto_potencia >= comb_config['potencia_min']:
                    bonus = comb_config['bonus_potencia_alta']
                    total_score += bonus
                    reasons.append(f"✓ Buena potencia ({moto_potencia}CV) [+{bonus:.1f}]")
                else:
                    penalty = 1.5
                    total_score -= penalty
                    reasons.append(f"⚠ Potencia insuficiente vs preferencia [-{penalty:.1f}]")

        # 5. RELACIÓN POTENCIA/PESO
        potencia_peso_pref = user_preferences.get('preferencia_potencia_peso', 'media')
        if potencia_peso_pref in self.potencia_peso_compatibility and moto_peso > 0:
            pp_config = self.potencia_peso_compatibility[potencia_peso_pref]
            ratio_actual = moto_potencia / moto_peso
            
            if potencia_peso_pref == 'alta':
                if ratio_actual >= pp_config['ratio_min']:
                    bonus = pp_config['bonus_ratio_alto']
                    total_score += bonus
                    reasons.append(f"✓ Excelente relación potencia/peso ({ratio_actual:.2f} CV/kg) [+{bonus:.1f}]")
                else:
                    penalty = 1.5
                    total_score -= penalty
                    reasons.append(f"⚠ Relación potencia/peso baja [{penalty:.1f}]")
                    
            elif potencia_peso_pref == 'baja':
                if ratio_actual <= pp_config['ratio_max']:
                    bonus = 1.5
                    total_score += bonus
                    reasons.append(f"✓ Relación potencia/peso relajada [+{bonus:.1f}]")
                else:
                    penalty = abs(pp_config['penalizacion_ratio_alto'])
                    total_score -= penalty
                    reasons.append(f"⚠ Relación potencia/peso alta vs preferencia [-{penalty:.1f}]")

        # 6. PREFERENCIA RENDIMIENTO VS ECONOMÍA
        rendimiento_pref = user_preferences.get('preferencia_rendimiento', 'balance')
        if rendimiento_pref in self.rendimiento_compatibility:
            rend_config = self.rendimiento_compatibility[rendimiento_pref]
            
            if rendimiento_pref == 'rendimiento':
                if moto_potencia >= rend_config['potencia_min']:
                    bonus = rend_config['bonus_potencia']
                    total_score += bonus
                    reasons.append(f"✓ Potencia alta para rendimiento [+{bonus:.1f}]")
                else:
                    penalty = abs(rend_config['penalizacion_economia'])
                    total_score -= penalty
                    reasons.append(f"⚠ Potencia baja vs preferencia de rendimiento [-{penalty:.1f}]")
                    
            elif rendimiento_pref == 'economia':
                if moto_potencia <= rend_config['potencia_max']:
                    bonus = rend_config['bonus_economia']
                    total_score += bonus
                    reasons.append(f"✓ Potencia económica [+{bonus:.1f}]")
                else:
                    penalty = abs(rend_config['penalizacion_potencia'])
                    total_score -= penalty
                    reasons.append(f"⚠ Potencia alta vs preferencia de economía [-{penalty:.1f}]")

        self.logger.info(f"[QUALITATIVE] Moto {moto.get('id')} - Score cualitativo FINAL: {total_score}")
        
        return total_score, reasons

    def get_qualitative_weight_factor(self, user_preferences: Dict[str, Any]) -> float:
        """
        Calcula un factor de peso para la evaluación cualitativa basado en las preferencias del usuario
        """
        # Los usuarios más experimentados dan más peso a criterios cualitativos
        experiencia = user_preferences.get('experiencia', 'intermedio')
        
        weight_factors = {
            'principiante': 1.2,  # Los principiantes necesitan más guía cualitativa
            'intermedio': 1.0,
            'experto': 0.8  # Los expertos se basan más en especificaciones técnicas
        }
        
        return weight_factors.get(experiencia, 1.0)
