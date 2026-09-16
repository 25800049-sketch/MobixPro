/**
 * MOBIX AI-Powered Phone Valuation & Exchange Predictor
 * Interactively calls Scikit-Learn regression engine to estimate resale value
 */

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('aiValuationForm');
  const batterySlider = document.getElementById('batteryHealthSlider');
  const batteryDisplay = document.getElementById('batteryHealthDisplay');
  const ageSlider = document.getElementById('ageMonthsSlider');
  const ageDisplay = document.getElementById('ageMonthsDisplay');

  // Update slider displays
  if (batterySlider && batteryDisplay) {
    batterySlider.addEventListener('input', () => {
      batteryDisplay.textContent = `${batterySlider.value}%`;
      triggerEvaluation();
    });
  }

  if (ageSlider && ageDisplay) {
    ageSlider.addEventListener('input', () => {
      ageDisplay.textContent = `${ageSlider.value} Months`;
      triggerEvaluation();
    });
  }

  // Bind change events to all inputs for real-time recalculation
  if (form) {
    form.querySelectorAll('input, select').forEach(input => {
      input.addEventListener('change', triggerEvaluation);
    });
  }

  let debounceTimer;
  function triggerEvaluation() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      evaluateDevice();
    }, 200);
  }

  window.evaluateDevice = function() {
    if (!form) return;

    const brand = document.getElementById('exBrand')?.value || 'Samsung';
    const model = document.getElementById('exModel')?.value || 'Galaxy Phone';
    const originalPrice = parseFloat(document.getElementById('exOrigPrice')?.value || 25000);
    const ageMonths = parseInt(document.getElementById('ageMonthsSlider')?.value || 12);
    const storage = document.getElementById('exStorage')?.value || '128GB';
    const batteryHealth = parseInt(document.getElementById('batteryHealthSlider')?.value || 85);
    const screenCondition = document.getElementById('exScreenCond')?.value || 'Good';
    const bodyCondition = document.getElementById('exBodyCond')?.value || 'Good';
    const cameraOk = document.getElementById('exCameraOk')?.checked ?? true;
    const biometricsOk = document.getElementById('exBiometricsOk')?.checked ?? true;

    const payload = {
      brand,
      model,
      original_price: originalPrice,
      age_months: ageMonths,
      storage,
      battery_health: batteryHealth,
      screen_condition: screenCondition,
      body_condition: bodyCondition,
      camera_ok: cameraOk,
      biometrics_ok: biometricsOk
    };

    fetch('/exchange/api/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(res => {
      if (res.success) {
        updateValuationUI(res.data);
      }
    })
    .catch(err => console.error("Evaluation error:", err));
  };

  function updateValuationUI(data) {
    const aiMarketValEl = document.getElementById('aiMarketValue');
    const offeredValEl = document.getElementById('aiOfferedValue');
    const gradeBadgeEl = document.getElementById('aiGradeBadge');
    const depMeterEl = document.getElementById('aiDepreciationMeter');
    const depTextEl = document.getElementById('aiDepreciationText');

    if (aiMarketValEl) aiMarketValEl.textContent = `₹${data.ai_estimated_market_value.toLocaleString()}`;
    if (offeredValEl) offeredValEl.textContent = `₹${data.offered_exchange_value.toLocaleString()}`;
    
    if (gradeBadgeEl) {
      gradeBadgeEl.textContent = data.condition_grade;
      if (data.condition_grade.startsWith('A')) {
        gradeBadgeEl.className = 'badge badge-success';
      } else if (data.condition_grade.startsWith('B')) {
        gradeBadgeEl.className = 'badge badge-primary';
      } else {
        gradeBadgeEl.className = 'badge badge-warning';
      }
    }

    if (depMeterEl) {
      depMeterEl.style.width = `${Math.min(100, data.depreciation_percentage)}%`;
    }
    if (depTextEl) {
      depTextEl.textContent = `${data.depreciation_percentage}% Depreciation from launch`;
    }

    // Hidden inputs for form submission if saving to DB
    const hidMarket = document.getElementById('hidAiMarketValue');
    const hidOffered = document.getElementById('hidOfferedValue');
    if (hidMarket) hidMarket.value = data.ai_estimated_market_value;
    if (hidOffered) hidOffered.value = data.offered_exchange_value;

    // Store globally for POS billing if loaded inside POS modal
    window.lastEvaluationData = data;
  }

  // Initial trigger on load
  if (form) {
    evaluateDevice();
  }
});
