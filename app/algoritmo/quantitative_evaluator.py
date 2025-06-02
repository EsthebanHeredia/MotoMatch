"""
Evaluador cuantitativo para el algoritmo de recomendación de motos.
Compatible con inputs cuantitativos (rangos) y cualitativos (preguntas no numéricas).
VERSIÓN CORREGIDA Y LISTA PARA PRODUCCIÓN.
"""
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Any, Optional, Union
from .qualitative_evaluator import QualitativeEvaluator

logger = logging.getLogger(__name__)

class QuantitativeEvaluator:
    """
    Evaluador que combina criterios cuantitativos (rangos numéricos) 
    con criterios cualitativos (ponderaciones).
    
    COMPATIBLE CON:
    - Solo inputs cuantitativos (dual-thumb range sliders)
    - Solo inputs cualitativos (preguntas no numéricas)
    - Combinación de ambos tipos
    - Datos parciales o faltantes
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.qualitative_evaluator = QualitativeEvaluator()
        
        # Configurar parámetros por defecto
        self.default_weights = {
            'presupuesto': 3.0,
            'potencia': 3.0,
            'cilindrada': 2.0,
            'peso': 2.0,
            'marca': 5.0,
            'estilo': 6.0,
            'ano': 2.0,
            'torque': 2.0
        }
        
        # Configurar proporción de combinación
        self.quantitative_weight = 0.7  # 70% cuantitativo
        self.qualitative_weight = 0.3   # 30% cualitativo
    
    def evaluate_moto_quantitative(self, user_preferences: Dict[str, Any], 
                                 moto: pd.Series) -> Tuple[float, List[str]]:
        """
        Evalúa una moto combinando criterios cuantitativos y cualitativos.
        
        Args:
            user_preferences: Diccionario con preferencias del usuario
            moto: Serie de pandas con datos de la moto
            
        Returns:
            Tuple con (score_final, lista_de_razones)
        """
        total_score = 0.0
        reasons = []
        
        self.logger.info(f"[EVALUATOR] Iniciando evaluación de moto {moto.get('id', 'unknown')}")
        self.logger.info(f"[EVALUATOR] Preferencias recibidas: {list(user_preferences.keys())}")
        
        # VALIDAR TIPO DE INPUT
        has_quantitative = self._has_quantitative_inputs(user_preferences)
        has_qualitative = self._has_qualitative_inputs(user_preferences)
        
        self.logger.info(f"[INPUT_TYPE] Cuantitativo: {has_quantitative}, Cualitativo: {has_qualitative}")
        
        # === EVALUACIÓN CUANTITATIVA ===
        
        # 1. PRESUPUESTO
        total_score += self._evaluate_presupuesto(user_preferences, moto, reasons)
        
        # 2. POTENCIA
        total_score += self._evaluate_potencia(user_preferences, moto, reasons)
        
        # 3. CILINDRADA
        total_score += self._evaluate_cilindrada(user_preferences, moto, reasons)
        
        # 4. PESO
        total_score += self._evaluate_peso(user_preferences, moto, reasons)
        
        # 5. AÑO
        total_score += self._evaluate_ano(user_preferences, moto, reasons)
        
        # 6. TORQUE
        total_score += self._evaluate_torque(user_preferences, moto, reasons)
        
        # 7. MARCAS
        total_score += self._evaluate_marcas(user_preferences, moto, reasons)
        
        # 8. ESTILOS/TIPOS
        total_score += self._evaluate_estilos(user_preferences, moto, reasons)
        
        self.logger.info(f"[QUANTITATIVE] Score cuantitativo: {total_score:.2f}")
        
        # === EVALUACIÓN CUALITATIVA ===
        
        qualitative_score = 0.0
        qualitative_reasons = []
        
        if has_qualitative:
            try:
                qualitative_score, qualitative_reasons = self.qualitative_evaluator.evaluate_moto_qualitative(
                    user_preferences, moto
                )
                
                # Aplicar factor de peso cualitativo basado en experiencia
                qualitative_weight_factor = self.qualitative_evaluator.get_qualitative_weight_factor(user_preferences)
                qualitative_score *= qualitative_weight_factor
                
                self.logger.info(f"[QUALITATIVE] Score cualitativo: {qualitative_score:.2f}")
                
            except Exception as e:
                self.logger.warning(f"[QUALITATIVE] Error en evaluación cualitativa: {e}")
                qualitative_score = 0.0
                qualitative_reasons = []
        
        # === COMBINACIÓN FINAL ===
        
        if has_quantitative and has_qualitative:
            # Ambos tipos de input: combinar con pesos
            final_score = (total_score * self.quantitative_weight) + (qualitative_score * self.qualitative_weight)
            combination_type = "MIXTO"
        elif has_quantitative:
            # Solo cuantitativo: usar score cuantitativo completo
            final_score = total_score
            combination_type = "CUANTITATIVO"
        elif has_qualitative:
            # Solo cualitativo: usar score cualitativo completo
            final_score = qualitative_score
            combination_type = "CUALITATIVO"
        else:
            # Sin inputs válidos: score por defecto
            final_score = 5.0
            combination_type = "DEFECTO"
            reasons.append("⚠ Sin preferencias válidas - usando evaluación por defecto")
        
        # Combinar razones
        final_reasons = reasons.copy()
        if qualitative_reasons:
            final_reasons.append(f"--- Evaluación Cualitativa (peso: {self.qualitative_weight:.0%}) ---")
            final_reasons.extend(qualitative_reasons)
        
        # Agregar resumen final
        final_reasons.append(f"[{combination_type}] Score final: {final_score:.2f}")
        if has_quantitative and has_qualitative:
            final_reasons.append(f"[DETALLE] Cuantitativo: {total_score:.1f} | Cualitativo: {qualitative_score:.1f}")
        
        self.logger.info(f"[FINAL] Moto {moto.get('id', 'unknown')} - Score: {final_score:.2f} (Tipo: {combination_type})")
        
        return final_score, final_reasons
    
    def _has_quantitative_inputs(self, preferences: Dict[str, Any]) -> bool:
        """Verifica si hay inputs cuantitativos (rangos numéricos)."""
        quantitative_keys = [
            'presupuesto_min', 'presupuesto_max',
            'potencia_min', 'potencia_max',
            'cilindrada_min', 'cilindrada_max',
            'peso_min', 'peso_max',
            'ano_min', 'ano_max',
            'torque_min', 'torque_max'
        ]
        return any(key in preferences for key in quantitative_keys)
    
    def _has_qualitative_inputs(self, preferences: Dict[str, Any]) -> bool:
        """Verifica si hay inputs cualitativos (preguntas no numéricas)."""
        qualitative_keys = [
            'experiencia', 'tipo_uso', 'pasajeros_carga',
            'combustible_potencia', 'preferencia_potencia_peso',
            'preferencia_rendimiento'
        ]
        return any(key in preferences for key in qualitative_keys)
    
    def _evaluate_presupuesto(self, preferences: Dict[str, Any], moto: pd.Series, reasons: List[str]) -> float:
        """Evalúa el presupuesto con múltiples formatos de input."""
        precio_moto = float(moto.get('precio', 0))
        
        # Formato 1: rango min/max
        if 'presupuesto_min' in preferences and 'presupuesto_max' in preferences:
            min_precio = float(preferences['presupuesto_min'])
            max_precio = float(preferences['presupuesto_max'])
            
            if min_precio <= precio_moto <= max_precio:
                points = self.default_weights['presupuesto']
                reasons.append(f"✓ Precio dentro del presupuesto ({precio_moto}€) [+{points:.1f}]")
                return points
            else:
                mid_price = (min_precio + max_precio) / 2
                penalty = min(2.0, abs(precio_moto - mid_price) / 1000)
                reasons.append(f"⚠ Precio fuera del presupuesto ({precio_moto}€) [-{penalty:.1f}]")
                return -penalty
        
        # Formato 2: presupuesto único
        elif 'presupuesto' in preferences:
            presupuesto = float(preferences['presupuesto'])
            if precio_moto <= presupuesto:
                points = self.default_weights['presupuesto']
                reasons.append(f"✓ Precio dentro del presupuesto ({precio_moto}€) [+{points:.1f}]")
                return points
            else:
                penalty = min(2.0, (precio_moto - presupuesto) / 1000)
                reasons.append(f"⚠ Precio sobre el presupuesto ({precio_moto}€) [-{penalty:.1f}]")
                return -penalty
        
        return 0.0
    
    def _evaluate_potencia(self, preferences: Dict[str, Any], moto: pd.Series, reasons: List[str]) -> float:
        """Evalúa la potencia."""
        if 'potencia_min' not in preferences or 'potencia_max' not in preferences:
            return 0.0
            
        potencia_moto = float(moto.get('potencia', 0))
        potencia_min = float(preferences['potencia_min'])
        potencia_max = float(preferences['potencia_max'])
        
        if potencia_min <= potencia_moto <= potencia_max:
            points = self.default_weights['potencia']
            reasons.append(f"✓ Potencia ideal ({potencia_moto}CV) [+{points:.1f}]")
            return points
        else:
            mid_power = (potencia_min + potencia_max) / 2
            penalty = min(2.0, abs(potencia_moto - mid_power) / 30)
            reasons.append(f"⚠ Potencia fuera del rango ({potencia_moto}CV) [-{penalty:.1f}]")
            return -penalty
    
    def _evaluate_cilindrada(self, preferences: Dict[str, Any], moto: pd.Series, reasons: List[str]) -> float:
        """Evalúa la cilindrada."""
        if 'cilindrada_min' not in preferences or 'cilindrada_max' not in preferences:
            return 0.0
            
        cilindrada_moto = float(moto.get('cilindrada', 0))
        cilindrada_min = float(preferences['cilindrada_min'])
        cilindrada_max = float(preferences['cilindrada_max'])
        
        if cilindrada_min <= cilindrada_moto <= cilindrada_max:
            points = self.default_weights['cilindrada']
            reasons.append(f"✓ Cilindrada ideal ({cilindrada_moto}cc) [+{points:.1f}]")
            return points
        else:
            mid_displacement = (cilindrada_min + cilindrada_max) / 2
            penalty = min(1.5, abs(cilindrada_moto - mid_displacement) / 200)
            reasons.append(f"⚠ Cilindrada fuera del rango ({cilindrada_moto}cc) [-{penalty:.1f}]")
            return -penalty
    
    def _evaluate_peso(self, preferences: Dict[str, Any], moto: pd.Series, reasons: List[str]) -> float:
        """Evalúa el peso."""
        if 'peso_min' not in preferences or 'peso_max' not in preferences:
            return 0.0
            
        peso_moto = float(moto.get('peso', 0))
        peso_min = float(preferences['peso_min'])
        peso_max = float(preferences['peso_max'])
        
        if peso_min <= peso_moto <= peso_max:
            points = self.default_weights['peso']
            reasons.append(f"✓ Peso ideal ({peso_moto}kg) [+{points:.1f}]")
            return points
        else:
            mid_weight = (peso_min + peso_max) / 2
            penalty = min(1.0, abs(peso_moto - mid_weight) / 50)
            reasons.append(f"⚠ Peso fuera del rango ({peso_moto}kg) [-{penalty:.1f}]")
            return -penalty
    
    def _evaluate_ano(self, preferences: Dict[str, Any], moto: pd.Series, reasons: List[str]) -> float:
        """Evalúa el año."""
        if 'ano_min' not in preferences or 'ano_max' not in preferences:
            return 0.0
            
        ano_moto = int(moto.get('ano', 2020))
        ano_min = int(preferences['ano_min'])
        ano_max = int(preferences['ano_max'])
        
        if ano_min <= ano_moto <= ano_max:
            points = self.default_weights['ano']
            reasons.append(f"✓ Año ideal ({ano_moto}) [+{points:.1f}]")
            return points
        else:
            mid_year = (ano_min + ano_max) / 2
            penalty = min(1.5, abs(ano_moto - mid_year) / 5)
            reasons.append(f"⚠ Año fuera del rango ({ano_moto}) [-{penalty:.1f}]")
            return -penalty
    
    def _evaluate_torque(self, preferences: Dict[str, Any], moto: pd.Series, reasons: List[str]) -> float:
        """Evalúa el torque."""
        if 'torque_min' not in preferences or 'torque_max' not in preferences:
            return 0.0
            
        torque_moto = float(moto.get('torque', 0))
        torque_min = float(preferences['torque_min'])
        torque_max = float(preferences['torque_max'])
        
        if torque_min <= torque_moto <= torque_max:
            points = self.default_weights['torque']
            reasons.append(f"✓ Torque ideal ({torque_moto}Nm) [+{points:.1f}]")
            return points
        else:
            mid_torque = (torque_min + torque_max) / 2
            penalty = min(1.0, abs(torque_moto - mid_torque) / 20)
            reasons.append(f"⚠ Torque fuera del rango ({torque_moto}Nm) [-{penalty:.1f}]")
            return -penalty
    
    def _evaluate_marcas(self, preferences: Dict[str, Any], moto: pd.Series, reasons: List[str]) -> float:
        """Evalúa las marcas preferidas."""
        if 'marcas' not in preferences:
            return 0.0
            
        marca_moto = str(moto.get('marca', '')).lower()
        total_points = 0.0
        
        for marca, peso_marca in preferences['marcas'].items():
            if marca.lower() in marca_moto:
                points = float(peso_marca) * self.default_weights['marca']
                total_points += points
                reasons.append(f"✓ Marca preferida: {marca} [+{points:.1f}]")
                self.logger.info(f"[MARCA] {marca} coincide: +{points:.1f} puntos")
        
        return total_points
    
    def _evaluate_estilos(self, preferences: Dict[str, Any], moto: pd.Series, reasons: List[str]) -> float:
        """Evalúa los estilos/tipos preferidos."""
        if 'estilos' not in preferences:
            return 0.0
            
        tipo_moto = str(moto.get('tipo', '')).lower()
        total_points = 0.0
        
        for estilo, peso_estilo in preferences['estilos'].items():
            if estilo.lower() in tipo_moto:
                points = float(peso_estilo) * self.default_weights['estilo']
                total_points += points
                reasons.append(f"✓ Estilo preferido: {estilo} [+{points:.1f}]")
                self.logger.info(f"[ESTILO] {estilo} coincide: +{points:.1f} puntos")
        
        return total_points
