"""
AI-Powered Mobile Exchange Valuation Engine
Uses Scikit-Learn Regression model trained on depreciation factors, brand retention,
hardware wear, battery health, and cosmetic conditions to predict real-world resale value.
"""
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import joblib
import os

class MobileValuationEngine:
    _instance = None

    BRAND_TIERS = {
        'apple': 1.0,
        'samsung': 0.9,
        'oneplus': 0.82,
        'google': 0.80,
        'xiaomi': 0.70,
        'realme': 0.68,
        'vivo': 0.68,
        'oppo': 0.68,
        'motorola': 0.65,
        'other': 0.55
    }

    SCREEN_WEIGHTS = {
        'Flawless': 1.0,
        'Minor Scratches': 0.90,
        'Cracked Glass': 0.65,
        'Touch / Display Issues': 0.40
    }

    BODY_WEIGHTS = {
        'Mint': 1.0,
        'Good': 0.92,
        'Scratched': 0.82,
        'Dented / Bent': 0.65
    }

    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self._train_baseline_model()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _train_baseline_model(self):
        """Train baseline Random Forest model on 2,500 synthetic realistic device depreciation profiles."""
        np.random.seed(42)
        n_samples = 2500

        # Features:
        # 1. Original Price (₹8,000 to ₹160,000)
        # 2. Age in months (1 to 48)
        # 3. Brand tier (0.55 to 1.0)
        # 4. Storage tier in GB (32, 64, 128, 256, 512, 1024)
        # 5. Battery Health (60% to 100%)
        # 6. Screen condition factor (0.4 to 1.0)
        # 7. Body condition factor (0.65 to 1.0)
        # 8. Functional flags (Camera + Biometrics: 0, 1, 2)

        orig_prices = np.random.choice([12000, 18000, 25000, 35000, 48000, 65000, 85000, 125000, 145000], size=n_samples)
        ages = np.random.randint(1, 49, size=n_samples)
        brand_weights = np.random.choice([1.0, 0.9, 0.82, 0.80, 0.70, 0.68, 0.65, 0.55], size=n_samples)
        storages = np.random.choice([64, 128, 256, 512], size=n_samples)
        battery_healths = np.random.randint(65, 101, size=n_samples)
        screen_weights = np.random.choice([1.0, 0.90, 0.65, 0.40], size=n_samples)
        body_weights = np.random.choice([1.0, 0.92, 0.82, 0.65], size=n_samples)
        functional_scores = np.random.choice([1.0, 0.85, 0.70], size=n_samples)

        # Realistic valuation equation ground truth + random market noise
        # Age depreciation curve: e^(-0.03 * months)
        age_decay = np.exp(-0.028 * ages)
        storage_boost = 1.0 + (storages - 64) * 0.0004
        battery_factor = (battery_healths / 100.0) ** 0.5

        y_values = (
            orig_prices
            * age_decay
            * brand_weights
            * storage_boost
            * battery_factor
            * screen_weights
            * body_weights
            * functional_scores
        )
        # Add realistic market jitter +/- 5%
        noise = np.random.normal(1.0, 0.04, size=n_samples)
        y_values = np.clip(y_values * noise, a_min=800, a_max=None)

        X = np.column_stack([
            orig_prices,
            ages,
            brand_weights,
            storages,
            battery_healths,
            screen_weights,
            body_weights,
            functional_scores
        ])

        X_scaled = self.scaler.fit_transform(X)
        self.model = RandomForestRegressor(n_estimators=60, max_depth=10, random_state=42)
        self.model.fit(X_scaled, y_values)

    def evaluate_phone(self, brand, model_name, original_price, age_months, storage_str,
                       battery_health, screen_cond, body_cond, camera_ok=True, biometrics_ok=True):
        """
        Calculates AI estimated resale valuation and returns detailed breakdown.
        """
        brand_clean = str(brand).strip().lower()
        brand_weight = self.BRAND_TIERS.get(brand_clean, 0.65)
        
        # Parse storage
        storage_int = 128
        try:
            storage_int = int(''.join(filter(str.isdigit, str(storage_str))))
        except Exception:
            storage_int = 128

        screen_w = self.SCREEN_WEIGHTS.get(screen_cond, 0.90)
        body_w = self.BODY_WEIGHTS.get(body_cond, 0.90)
        
        func_score = 1.0
        if not camera_ok:
            func_score -= 0.15
        if not biometrics_ok:
            func_score -= 0.15
        func_score = max(0.5, func_score)

        orig_price_float = float(original_price or 25000.0)
        age_months_int = max(1, int(age_months or 12))
        battery_int = max(50, min(100, int(battery_health or 85)))

        features = np.array([[
            orig_price_float,
            age_months_int,
            brand_weight,
            storage_int,
            battery_int,
            screen_w,
            body_w,
            func_score
        ]])

        scaled_feat = self.scaler.transform(features)
        predicted_market_val = float(self.model.predict(scaled_feat)[0])

        # Floor cap: old phone should not be lower than ₹500 or higher than 85% original price
        predicted_market_val = max(500.0, min(orig_price_float * 0.85, predicted_market_val))
        
        # Shop Exchange Offer = ~88% of AI Market Value (allows store margin on resale)
        offered_exchange_val = round(predicted_market_val * 0.88, -1) # rounded to nearest 10
        predicted_market_val = round(predicted_market_val, -1)

        # Condition summary
        overall_grade = "A (Excellent)"
        if screen_w < 0.7 or body_w < 0.7 or func_score < 0.85:
            overall_grade = "C (Fair/Damaged)"
        elif screen_w < 0.95 or body_w < 0.95 or battery_int < 80:
            overall_grade = "B (Good)"

        return {
            'brand': brand,
            'model': model_name,
            'ai_estimated_market_value': predicted_market_val,
            'offered_exchange_value': offered_exchange_val,
            'condition_grade': overall_grade,
            'depreciation_percentage': round(((orig_price_float - predicted_market_val) / orig_price_float) * 100, 1),
            'factors': {
                'brand_retention': f"{int(brand_weight * 100)}%",
                'screen_condition': screen_cond,
                'body_condition': body_cond,
                'battery_health': f"{battery_int}%",
                'camera_ok': camera_ok,
                'biometrics_ok': biometrics_ok
            }
        }

valuation_engine = MobileValuationEngine.get_instance()
