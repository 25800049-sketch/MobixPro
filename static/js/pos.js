/**
 * MOBIX POS & Billing Interactive Terminal
 * Manages cart state, real-time totals, tax, discounts, exchange trade-ins, and EMI calculator
 */

let cart = [];
let exchangePhoneData = null;

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const searchInput = document.getElementById('posSearchInput');
  const searchResults = document.getElementById('posSearchResults');
  const cartItemsContainer = document.getElementById('posCartItems');
  const emptyCartPlaceholder = document.getElementById('emptyCartPlaceholder');
  
  const subtotalEl = document.getElementById('posSubtotal');
  const taxRateInput = document.getElementById('posTaxRate');
  const taxAmountEl = document.getElementById('posTaxAmount');
  const discountInput = document.getElementById('posDiscount');
  const discountModeInput = document.getElementById('posDiscountMode');
  const btnDiscountAmt = document.getElementById('btnDiscountAmt');
  const btnDiscountPct = document.getElementById('btnDiscountPct');
  const discountAmountEl = document.getElementById('posDiscountAmount');
  const discountUnitSymbolEl = document.getElementById('posDiscountUnitSymbol');
  const exchangeDiscountEl = document.getElementById('posExchangeDiscount');
  const exchangeRowEl = document.getElementById('posExchangeRow');
  const finalTotalEl = document.getElementById('posFinalTotal');
  
  const paymentModeSelect = document.getElementById('paymentModeSelect');
  const emiOptionsBox = document.getElementById('emiOptionsBox');
  const emiDownPaymentInput = document.getElementById('emiDownPayment');
  const emiTenureSelect = document.getElementById('emiTenureSelect');
  const emiMonthlyEstimateEl = document.getElementById('emiMonthlyEstimate');

  const customerSelect = document.getElementById('customerSelect');
  const newCustomerFields = document.getElementById('newCustomerFields');
  const checkoutBtn = document.getElementById('checkoutBtn');

  // 1. Customer Mode Switching & Management
  const selectedCustomerInfo = document.getElementById('selectedCustomerInfo');
  const selectedCustName = document.getElementById('selectedCustName');
  const selectedCustPhone = document.getElementById('selectedCustPhone');
  const selectedCustEmailInput = document.getElementById('selectedCustEmailInput');

  function updateSelectedCustomerCard() {
    if (!customerSelect) return;
    if (customerSelect.value === 'new') {
      if (newCustomerFields) newCustomerFields.style.display = 'block';
      if (selectedCustomerInfo) selectedCustomerInfo.style.display = 'none';
    } else {
      if (newCustomerFields) newCustomerFields.style.display = 'none';
      if (selectedCustomerInfo) {
        selectedCustomerInfo.style.display = 'block';
        const selectedOpt = customerSelect.options[customerSelect.selectedIndex];
        if (selectedOpt) {
          if (selectedCustName) selectedCustName.textContent = selectedOpt.getAttribute('data-name') || selectedOpt.textContent;
          if (selectedCustPhone) selectedCustPhone.textContent = selectedOpt.getAttribute('data-phone') || '';
          if (selectedCustEmailInput) selectedCustEmailInput.value = selectedOpt.getAttribute('data-email') || '';
        }
      }
    }
  }

  function selectCustomerInDropdown(cust) {
    if (!customerSelect) return;
    let opt = Array.from(customerSelect.options).find(o => o.value == cust.id);
    if (!opt) {
      opt = document.createElement('option');
      opt.value = cust.id;
      opt.setAttribute('data-name', cust.name);
      opt.setAttribute('data-phone', cust.phone);
      opt.setAttribute('data-email', cust.email || '');
      opt.textContent = `${cust.name} (${cust.phone})`;
      customerSelect.appendChild(opt);
    } else {
      opt.setAttribute('data-name', cust.name);
      opt.setAttribute('data-phone', cust.phone);
      opt.setAttribute('data-email', cust.email || '');
      opt.textContent = `${cust.name} (${cust.phone})`;
    }
    customerSelect.value = cust.id;
    updateSelectedCustomerCard();
    fetchAndRenderCustomerCredit();
  }

  if (customerSelect) {
    customerSelect.addEventListener('change', () => {
      updateSelectedCustomerCard();
      fetchAndRenderCustomerCredit();
    });
  }

  // Save inline customer button
  const btnSaveInlineCustomer = document.getElementById('btnSaveInlineCustomer');
  const custNameInput = document.getElementById('custNameInput');
  const custPhoneInput = document.getElementById('custPhoneInput');
  const custEmailInput = document.getElementById('custEmailInput');
  const custAddressInput = document.getElementById('custAddressInput');
  const inlineCustMsg = document.getElementById('inlineCustMsg');
  const custLookupIndicator = document.getElementById('custLookupIndicator');

  if (btnSaveInlineCustomer) {
    btnSaveInlineCustomer.addEventListener('click', () => {
      const name = custNameInput ? custNameInput.value.trim() : '';
      const phone = custPhoneInput ? custPhoneInput.value.trim() : '';
      const email = custEmailInput ? custEmailInput.value.trim() : '';
      const address = custAddressInput ? custAddressInput.value.trim() : '';

      if (!name) {
        alert("Please enter customer's full name.");
        custNameInput?.focus();
        return;
      }
      if (!phone || phone.length < 5) {
        alert("Please enter customer's contact phone number.");
        custPhoneInput?.focus();
        return;
      }

      btnSaveInlineCustomer.disabled = true;
      btnSaveInlineCustomer.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

      fetch('/customers/api/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, phone, email, address })
      })
      .then(res => res.json())
      .then(data => {
        btnSaveInlineCustomer.disabled = false;
        btnSaveInlineCustomer.innerHTML = '<i class="fas fa-save"></i> Save Customer';
        if (data.success) {
          selectCustomerInDropdown(data.customer);
          if (inlineCustMsg) {
            inlineCustMsg.textContent = data.message;
            inlineCustMsg.style.display = 'inline';
            setTimeout(() => { inlineCustMsg.style.display = 'none'; }, 4000);
          }
        } else {
          alert(data.message || "Failed to register customer.");
        }
      })
      .catch(err => {
        btnSaveInlineCustomer.disabled = false;
        btnSaveInlineCustomer.innerHTML = '<i class="fas fa-save"></i> Save Customer';
        alert("Error saving customer: " + err);
      });
    });
  }

  // Quick Add Customer Modal Submission
  const quickAddCustForm = document.getElementById('posQuickAddCustomerForm');
  const modalCustAlert = document.getElementById('modalCustAlert');
  if (quickAddCustForm) {
    quickAddCustForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const name = document.getElementById('modalCustName')?.value.trim();
      const phone = document.getElementById('modalCustPhone')?.value.trim();
      const email = document.getElementById('modalCustEmail')?.value.trim();
      const address = document.getElementById('modalCustAddress')?.value.trim();

      if (!name || !phone) {
        alert("Name and phone number are required.");
        return;
      }

      const submitBtn = document.getElementById('btnSubmitModalCustomer');
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
      }

      fetch('/customers/api/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, phone, email, address })
      })
      .then(res => res.json())
      .then(data => {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = '<i class="fas fa-check"></i> Register & Select';
        }
        if (data.success) {
          selectCustomerInDropdown(data.customer);
          closeModal('posQuickAddCustomerModal');
          quickAddCustForm.reset();
        } else {
          if (modalCustAlert) {
            modalCustAlert.textContent = data.message;
            modalCustAlert.style.display = 'block';
            modalCustAlert.style.background = 'rgba(244, 63, 94, 0.15)';
            modalCustAlert.style.color = '#fb7185';
          } else {
            alert(data.message);
          }
        }
      })
      .catch(err => {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = '<i class="fas fa-check"></i> Register & Select';
        }
        alert("Error: " + err);
      });
    });
  }

  // Auto-lookup by phone
  if (custPhoneInput) {
    let phoneLookupTimer;
    custPhoneInput.addEventListener('input', () => {
      clearTimeout(phoneLookupTimer);
      const phone = custPhoneInput.value.trim();
      if (phone.length >= 7) {
        phoneLookupTimer = setTimeout(() => {
          fetch(`/customers/api/lookup?phone=${encodeURIComponent(phone)}`)
            .then(res => res.json())
            .then(res => {
              if (res.found && res.customer) {
                if (custNameInput && !custNameInput.value) custNameInput.value = res.customer.name;
                if (custEmailInput && !custEmailInput.value) custEmailInput.value = res.customer.email;
                if (custAddressInput && !custAddressInput.value) custAddressInput.value = res.customer.address;
                if (custLookupIndicator) {
                  custLookupIndicator.textContent = `✓ Found: ${res.customer.name}`;
                  custLookupIndicator.style.color = '#10b981';
                }
              } else {
                if (custLookupIndicator) custLookupIndicator.textContent = '';
              }
            });
        }, 400);
      } else {
        if (custLookupIndicator) custLookupIndicator.textContent = '';
      }
    });
  }

  // Customer Credit Scoring for Smart Store EMI
  const posCreditScoreWidget = document.getElementById('posCreditScoreWidget');
  const posCreditTierBadge = document.getElementById('posCreditTierBadge');
  const posCreditScoreNum = document.getElementById('posCreditScoreNum');
  const posCreditMinDp = document.getElementById('posCreditMinDp');
  const posCreditRiskWarning = document.getElementById('posCreditRiskWarning');

  function fetchAndRenderCustomerCredit() {
    if (!paymentModeSelect || paymentModeSelect.value !== 'EMI') return;
    const custId = customerSelect ? customerSelect.value : '';
    if (!custId || custId === 'new' || custId === '') {
      if (posCreditScoreWidget) posCreditScoreWidget.style.display = 'none';
      if (posCreditTierBadge) posCreditTierBadge.style.display = 'none';
      return;
    }

    fetch(`/emi/api/customer-credit/${custId}`)
      .then(res => res.json())
      .then(data => {
        if (data.success && data.profile) {
          const p = data.profile;
          if (posCreditScoreWidget) posCreditScoreWidget.style.display = 'block';
          if (posCreditTierBadge) {
            posCreditTierBadge.style.display = 'inline-block';
            posCreditTierBadge.className = `badge ${p.badge_class}`;
            posCreditTierBadge.textContent = `${p.tier} (${p.score})`;
          }
          if (posCreditScoreNum) posCreditScoreNum.textContent = p.score;
          if (posCreditMinDp) posCreditMinDp.textContent = `${p.down_payment_min_pct}%`;

          // If high risk or severe overdue
          if (posCreditRiskWarning) {
            if (p.tier === 'Tier-C' || p.severe_overdue_count > 0) {
              posCreditRiskWarning.style.display = 'block';
              posCreditRiskWarning.innerHTML = `<i class="fas fa-triangle-exclamation"></i> <strong>High Default Risk:</strong> Customer credit score is ${p.score}/900. Minimum mandatory down payment is ${p.down_payment_min_pct}%.`;
            } else {
              posCreditRiskWarning.style.display = 'none';
            }
          }

          // Suggest minimum down payment if current down payment is default/low
          const finalTotal = calculateFinalTotal();
          const recommendedDp = Math.round(finalTotal * (p.down_payment_min_pct / 100));
          if (emiDownPaymentInput && (parseFloat(emiDownPaymentInput.value || 0) < recommendedDp || emiDownPaymentInput.value === '5000')) {
            if (recommendedDp > 0) {
              emiDownPaymentInput.value = recommendedDp;
              updateEmiCalculation();
            }
          }
        }
      })
      .catch(err => console.error("Error fetching credit score:", err));
  }

  // 2. Payment Mode Switching (Show/Hide EMI options)
  if (paymentModeSelect) {
    paymentModeSelect.addEventListener('change', () => {
      if (paymentModeSelect.value === 'EMI') {
        emiOptionsBox.style.display = 'block';
        updateEmiCalculation();
        fetchAndRenderCustomerCredit();
      } else {
        emiOptionsBox.style.display = 'none';
      }
    });
  }

  if (emiDownPaymentInput) {
    emiDownPaymentInput.addEventListener('input', updateEmiCalculation);
  }
  if (emiTenureSelect) {
    emiTenureSelect.addEventListener('change', updateEmiCalculation);
  }

  function updateEmiCalculation() {
    const finalTotal = calculateFinalTotal();
    const downPayment = parseFloat(emiDownPaymentInput.value || 0);
    const tenure = parseInt(emiTenureSelect.value || 6);

    const remaining = Math.max(0, finalTotal - downPayment);
    const monthly = tenure > 0 ? (remaining / tenure).toFixed(2) : '0.00';
    if (emiMonthlyEstimateEl) {
      emiMonthlyEstimateEl.textContent = `₹${parseFloat(monthly).toLocaleString()} / mo`;
    }
  }

  // 3. Product Search API
  if (searchInput) {
    let debounceTimer;
    searchInput.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      const query = searchInput.value.trim();
      if (!query) {
        searchResults.style.display = 'none';
        return;
      }

      debounceTimer = setTimeout(() => {
        fetch(`/inventory/api/search?q=${encodeURIComponent(query)}`)
          .then(res => res.json())
          .then(items => {
            searchResults.innerHTML = '';
            if (items.length === 0) {
              searchResults.innerHTML = '<div style="padding: 12px; color: var(--text-muted);">No products found in stock.</div>';
            } else {
              items.forEach(item => {
                const itemDiv = document.createElement('div');
                itemDiv.className = 'search-result-item';
                itemDiv.style.cssText = 'padding: 10px 14px; border-bottom: 1px solid var(--border-color); cursor: pointer; display: flex; justify-content: space-between; align-items: center;';
                itemDiv.innerHTML = `
                  <div>
                    <strong style="color: var(--text-main);">${item.name}</strong>
                    <div style="font-size: 11px; color: var(--text-muted);">${item.type === 'mobile' ? 'IMEI: ' + item.imei : 'Warranty: ' + item.warranty} | Stock: ${item.stock}</div>
                  </div>
                  <div style="font-weight: 700; color: var(--primary);">₹${item.price.toLocaleString()}</div>
                `;
                itemDiv.addEventListener('click', () => {
                  addToCart(item);
                  searchInput.value = '';
                  searchResults.style.display = 'none';
                });
                searchResults.appendChild(itemDiv);
              });
            }
            searchResults.style.display = 'block';
          });
      }, 250);
    });

    document.addEventListener('click', (e) => {
      if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
        searchResults.style.display = 'none';
      }
    });
  }

  // 4. Cart Operations
  window.addToCart = function(product) {
    const existingIndex = cart.findIndex(i => i.id === product.id && i.type === product.type);
    if (existingIndex > -1) {
      if (product.type === 'mobile') {
        alert("Mobile phones have unique IMEIs and are added as single units.");
        return;
      }
      if (cart[existingIndex].qty < product.stock) {
        cart[existingIndex].qty += 1;
      } else {
        alert("Maximum available stock reached for this accessory.");
        return;
      }
    } else {
      cart.push({
        id: product.id,
        type: product.type,
        name: product.name,
        price: product.price,
        qty: 1,
        imei: product.imei || '',
        stock: product.stock
      });
    }
    renderCart();
  };

  window.removeFromCart = function(index) {
    cart.splice(index, 1);
    renderCart();
  };

  window.updateQty = function(index, delta) {
    const item = cart[index];
    if (item.type === 'mobile') return;
    const newQty = item.qty + delta;
    if (newQty > 0 && newQty <= item.stock) {
      item.qty = newQty;
      renderCart();
    }
  };

  let discountMode = 'amount'; // 'amount' (₹) or 'percent' (%)

  function setDiscountMode(mode) {
    discountMode = mode;
    if (discountModeInput) discountModeInput.value = mode;

    if (mode === 'amount') {
      if (btnDiscountAmt) {
        btnDiscountAmt.style.background = 'var(--primary)';
        btnDiscountAmt.style.color = '#ffffff';
      }
      if (btnDiscountPct) {
        btnDiscountPct.style.background = 'transparent';
        btnDiscountPct.style.color = 'var(--text-muted)';
      }
      if (discountUnitSymbolEl) discountUnitSymbolEl.textContent = '₹';
      if (discountInput) {
        discountInput.placeholder = '0';
        discountInput.removeAttribute('max');
      }
    } else {
      if (btnDiscountPct) {
        btnDiscountPct.style.background = 'var(--primary)';
        btnDiscountPct.style.color = '#ffffff';
      }
      if (btnDiscountAmt) {
        btnDiscountAmt.style.background = 'transparent';
        btnDiscountAmt.style.color = 'var(--text-muted)';
      }
      if (discountUnitSymbolEl) discountUnitSymbolEl.textContent = '%';
      if (discountInput) {
        discountInput.placeholder = '0-100';
        discountInput.setAttribute('max', '100');
      }
    }
    renderCart();
  }

  if (btnDiscountAmt) {
    btnDiscountAmt.addEventListener('click', () => setDiscountMode('amount'));
  }
  if (btnDiscountPct) {
    btnDiscountPct.addEventListener('click', () => setDiscountMode('percent'));
  }

  function calculateSubtotal() {
    return cart.reduce((sum, item) => sum + (item.price * item.qty), 0);
  }

  function calculateDiscountAmount(subtotal) {
    const rawVal = parseFloat(discountInput ? discountInput.value : 0) || 0;
    if (rawVal <= 0) return 0;

    if (discountMode === 'percent') {
      const pct = Math.min(100, Math.max(0, rawVal));
      return (subtotal * pct) / 100.0;
    } else {
      return Math.min(subtotal, Math.max(0, rawVal));
    }
  }

  function calculateFinalTotal() {
    const subtotal = calculateSubtotal();
    const taxRate = parseFloat(taxRateInput ? taxRateInput.value : 18) || 0;
    const taxAmount = (subtotal * taxRate) / 100.0;
    const discountAmount = calculateDiscountAmount(subtotal);
    const exchangeDiscount = exchangePhoneData ? parseFloat(exchangePhoneData.offered_exchange_value || 0) : 0;

    const total = Math.max(0, subtotal + taxAmount - discountAmount - exchangeDiscount);
    const preorderAdvEl = document.getElementById('posPreorderAdvanceVal');
    const preorderAdvance = preorderAdvEl ? (parseFloat(preorderAdvEl.value) || 0) : 0;
    return Math.max(0, total - preorderAdvance);
  }

  function renderCart() {
    if (!cartItemsContainer) return;
    cartItemsContainer.innerHTML = '';

    if (cart.length === 0) {
      if (emptyCartPlaceholder) emptyCartPlaceholder.style.display = 'block';
    } else {
      if (emptyCartPlaceholder) emptyCartPlaceholder.style.display = 'none';
      cart.forEach((item, index) => {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'cart-item-card';
        itemDiv.innerHTML = `
          <div style="flex: 1;">
            <div style="font-weight: 600; font-size: 13px; color: var(--text-main);">${item.name}</div>
            <div style="font-size: 11px; color: var(--text-muted);">
              ${item.type === 'mobile' ? 'IMEI: ' + item.imei : 'Unit Price: ₹' + item.price.toLocaleString()}
            </div>
          </div>
          
          <div style="display: flex; align-items: center; gap: 8px;">
            ${item.type === 'accessory' ? `
              <button class="btn btn-secondary btn-sm" onclick="updateQty(${index}, -1)" style="padding: 2px 7px;">-</button>
              <span style="font-weight: 700; font-size: 13px;">${item.qty}</span>
              <button class="btn btn-secondary btn-sm" onclick="updateQty(${index}, 1)" style="padding: 2px 7px;">+</button>
            ` : `<span class="badge badge-primary">x1</span>`}
          </div>

          <div style="text-align: right; min-width: 80px;">
            <div style="font-weight: 700; color: var(--text-main);">₹${(item.price * item.qty).toLocaleString()}</div>
            <button onclick="removeFromCart(${index})" style="background: none; border: none; color: var(--danger); font-size: 11px; cursor: pointer; text-decoration: underline;">Remove</button>
          </div>
        `;
        cartItemsContainer.appendChild(itemDiv);
      });
    }

    // Update Totals
    const subtotal = calculateSubtotal();
    const taxRate = parseFloat(taxRateInput ? taxRateInput.value : 18) || 0;
    const taxAmount = (subtotal * taxRate) / 100.0;
    const discountAmount = calculateDiscountAmount(subtotal);
    const exchangeVal = exchangePhoneData ? parseFloat(exchangePhoneData.offered_exchange_value || 0) : 0;
    const grandTotal = calculateFinalTotal();

    if (subtotalEl) subtotalEl.textContent = `₹${subtotal.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
    if (taxAmountEl) taxAmountEl.textContent = `₹${taxAmount.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;

    // Update Discount Display Value
    if (discountAmountEl) {
      if (discountMode === 'percent' && (parseFloat(discountInput?.value) || 0) > 0) {
        const pctVal = parseFloat(discountInput.value);
        discountAmountEl.textContent = `- ₹${discountAmount.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
      } else {
        discountAmountEl.textContent = `- ₹${discountAmount.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
      }
    }

    // Update Trade-In Exchange Row
    if (exchangeRowEl) {
      exchangeRowEl.style.display = exchangeVal > 0 ? 'flex' : 'none';
    }
    if (exchangeDiscountEl) {
      exchangeDiscountEl.textContent = `- ₹${exchangeVal.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
    }

    if (finalTotalEl) finalTotalEl.textContent = `₹${grandTotal.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;

    updateEmiCalculation();
  }

  window.renderCart = renderCart;
  window.setDiscountMode = setDiscountMode;

  if (taxRateInput) taxRateInput.addEventListener('input', renderCart);
  if (discountInput) discountInput.addEventListener('input', renderCart);

  // 5. Phone Exchange Integration into Cart
  window.applyExchangeToBill = function(valuationData) {
    exchangePhoneData = valuationData;
    const tradeinBox = document.getElementById('tradeinActiveBanner');
    if (tradeinBox) {
      tradeinBox.style.display = 'flex';
      tradeinBox.innerHTML = `
        <div>
          <strong>Trade-In Applied:</strong> ${valuationData.brand} ${valuationData.model}
          <div style="font-size: 11px; opacity: 0.8;">Offered Credit: ₹${valuationData.offered_exchange_value.toLocaleString()}</div>
        </div>
        <button onclick="cancelExchangeCredit()" class="btn btn-danger btn-sm" style="padding: 2px 8px;">Cancel</button>
      `;
    }
    renderCart();
  };

  window.cancelExchangeCredit = function() {
    exchangePhoneData = null;
    const tradeinBox = document.getElementById('tradeinActiveBanner');
    if (tradeinBox) tradeinBox.style.display = 'none';
    renderCart();
  };

  // 6. Complete POS Checkout Submission
  if (checkoutBtn) {
    checkoutBtn.addEventListener('click', () => {
      if (cart.length === 0) {
        alert("Please add at least one item to cart before checkout.");
        return;
      }

      let customerId = customerSelect ? customerSelect.value : 'new';
      let custName = document.getElementById('custNameInput')?.value;
      let custPhone = document.getElementById('custPhoneInput')?.value;
      let custEmail = document.getElementById('custEmailInput')?.value;
      let custAddress = document.getElementById('custAddressInput')?.value;

      if (customerId !== 'new') {
        const selectedOpt = customerSelect.options[customerSelect.selectedIndex];
        custName = selectedOpt?.getAttribute('data-name') || custName;
        custPhone = selectedOpt?.getAttribute('data-phone') || custPhone;
        // Priority: user-edited email in existing customer box, or data-email
        const existingEmailInput = document.getElementById('selectedCustEmailInput');
        custEmail = (existingEmailInput && existingEmailInput.value.trim()) ? existingEmailInput.value.trim() : (selectedOpt?.getAttribute('data-email') || '');
      }

      if (customerId === 'new' && (!custPhone || custPhone.trim() === '')) {
        alert("Please enter customer's contact phone number.");
        return;
      }

      const paymentMode = paymentModeSelect ? paymentModeSelect.value : 'Cash';
      let emiPlan = null;
      if (paymentMode === 'EMI') {
        const dp = parseFloat(emiDownPaymentInput?.value || 0);
        const tenure = parseInt(emiTenureSelect?.value || 6);
        const finalTot = calculateFinalTotal();
        if (dp >= finalTot) {
          alert("Down payment cannot be equal to or greater than the total amount for an EMI sale.");
          return;
        }
        emiPlan = {
          down_payment: dp,
          tenure_months: tenure,
          fine_per_cycle: 200.0
        };
      }

      checkoutBtn.disabled = true;
      checkoutBtn.textContent = "Processing Transaction...";

      const subtotal = calculateSubtotal();
      const calculatedDiscount = calculateDiscountAmount(subtotal);
      const autoEmail = document.getElementById('autoEmailCheck') ? document.getElementById('autoEmailCheck').checked : true;

      const rawTaxRate = parseFloat(taxRateInput ? taxRateInput.value : 18);
      const safeTaxRate = isNaN(rawTaxRate) ? 18.0 : rawTaxRate;

      const safeDiscountAmount = isNaN(calculatedDiscount) ? 0.0 : parseFloat(calculatedDiscount.toFixed(2));
      const rawDiscountRate = parseFloat(discountInput ? discountInput.value : 0);
      const safeDiscountRate = isNaN(rawDiscountRate) ? 0.0 : rawDiscountRate;

      const safeExchangeDiscount = (exchangePhoneData && !isNaN(parseFloat(exchangePhoneData.offered_exchange_value))) ? parseFloat(exchangePhoneData.offered_exchange_value) : 0.0;

      const cleanItems = cart.map(item => ({
        id: parseInt(item.id),
        type: item.type,
        name: item.name,
        price: isNaN(parseFloat(item.price)) ? 0.0 : parseFloat(item.price),
        qty: isNaN(parseInt(item.qty)) ? 1 : parseInt(item.qty),
        imei: item.imei || null
      }));

      const payload = {
        customer_id: customerId,
        customer_name: custName,
        customer_phone: custPhone,
        customer_email: custEmail,
        customer_address: custAddress,
        send_email: autoEmail,
        payment_mode: paymentMode,
        tax_rate: safeTaxRate,
        discount_amount: safeDiscountAmount,
        discount_type: discountMode || 'amount',
        discount_rate: safeDiscountRate,
        exchange_discount: safeExchangeDiscount,
        exchange_details: exchangePhoneData,
        emi_plan: emiPlan,
        preorder_id: document.getElementById('posPreorderId') && document.getElementById('posPreorderId').value ? parseInt(document.getElementById('posPreorderId').value) : null,
        items: cleanItems
      };

      fetch('/pos/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      .then(res => res.json())
      .then(res => {
        if (res.success) {
          // Open invoice success modal or redirect
          showCheckoutSuccessModal(res);
        } else {
          alert("Checkout Error: " + res.message);
          checkoutBtn.disabled = false;
          checkoutBtn.textContent = "Complete Sale & Print Bill";
        }
      })
      .catch(err => {
        alert("Transaction failed: " + err);
        checkoutBtn.disabled = false;
        checkoutBtn.textContent = "Complete Sale & Print Bill";
      });
    });
  }

  function showCheckoutSuccessModal(data) {
    const modal = document.getElementById('checkoutSuccessModal');
    if (modal) {
      const invNoEl = document.getElementById('successInvoiceNo');
      if (invNoEl) invNoEl.textContent = '#' + data.invoice_number;

      const custNameEl = document.getElementById('successCustName');
      if (custNameEl) custNameEl.textContent = data.customer_name || 'Walk-in Customer';

      const custPhoneEl = document.getElementById('successCustPhone');
      if (custPhoneEl) custPhoneEl.textContent = data.customer_phone || 'N/A';

      const custEmailEl = document.getElementById('successCustEmail');
      if (custEmailEl) {
        if (data.email_sent && data.recipient_email) {
          custEmailEl.innerHTML = `<i class="fas fa-check-circle" style="color: #0284c7;"></i> Sent to ${data.recipient_email}`;
        } else {
          custEmailEl.innerHTML = `<span style="color: var(--text-muted);">Not dispatched</span>`;
        }
      }

      const modalEmailStatusText = document.getElementById('modalEmailStatusText');
      if (modalEmailStatusText) {
        if (data.email_sent && data.recipient_email) {
          modalEmailStatusText.textContent = `Bill & PDF emailed to ${data.recipient_email}`;
        } else {
          modalEmailStatusText.textContent = 'Email bill not dispatched';
        }
      }

      // Email resend setup
      const btnToggleEmailEdit = document.getElementById('btnToggleEmailEdit');
      const emailResendContainer = document.getElementById('emailResendContainer');
      const modalResendEmailInput = document.getElementById('modalResendEmailInput');
      const btnSendModalEmail = document.getElementById('btnSendModalEmail');
      const modalEmailFeedback = document.getElementById('modalEmailFeedback');

      if (modalResendEmailInput) {
        modalResendEmailInput.value = data.recipient_email || data.customer_email || '';
      }

      if (btnToggleEmailEdit && emailResendContainer) {
        emailResendContainer.style.display = 'none';
        btnToggleEmailEdit.onclick = function() {
          emailResendContainer.style.display = emailResendContainer.style.display === 'none' ? 'block' : 'none';
          if (emailResendContainer.style.display === 'block' && modalResendEmailInput) {
            modalResendEmailInput.focus();
          }
        };
      }

      if (btnSendModalEmail && modalResendEmailInput) {
        btnSendModalEmail.onclick = function() {
          const target = modalResendEmailInput.value.trim();
          if (!target) {
            alert("Please enter a valid recipient email address.");
            return;
          }
          btnSendModalEmail.disabled = true;
          btnSendModalEmail.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';
          if (modalEmailFeedback) modalEmailFeedback.style.display = 'none';

          fetch(`/pos/invoices/${data.invoice_id}/send-email`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: target })
          })
          .then(r => r.json())
          .then(res => {
            btnSendModalEmail.disabled = false;
            btnSendModalEmail.textContent = 'Send Now';
            if (modalEmailFeedback) {
              modalEmailFeedback.style.display = 'block';
              if (res.success) {
                modalEmailFeedback.innerHTML = `<span style="color: #059669; font-weight: 700;"><i class="fas fa-check-circle"></i> ${res.message}</span>`;
                if (custEmailEl) custEmailEl.innerHTML = `<i class="fas fa-check-circle" style="color: #0284c7;"></i> Sent to ${target}`;
                if (modalEmailStatusText) modalEmailStatusText.textContent = `Bill & PDF emailed to ${target}`;
              } else {
                modalEmailFeedback.innerHTML = `<span style="color: #e11d48;"><i class="fas fa-circle-exclamation"></i> ${res.message}</span>`;
              }
            }
          })
          .catch(err => {
            btnSendModalEmail.disabled = false;
            btnSendModalEmail.textContent = 'Send Now';
            if (modalEmailFeedback) {
              modalEmailFeedback.style.display = 'block';
              modalEmailFeedback.innerHTML = `<span style="color: #e11d48;"><i class="fas fa-circle-exclamation"></i> Error sending: ${err}</span>`;
            }
          });
        };
      }

      const amountEl = document.getElementById('successFinalAmount');
      if (amountEl) amountEl.textContent = '₹' + Number(data.final_total || 0).toLocaleString('en-IN', {minimumFractionDigits: 2});

      const receiptBtn = document.getElementById('btnViewReceipt');
      if (receiptBtn) receiptBtn.href = data.redirect_url;

      const pdfBtn = document.getElementById('btnDownloadPdf');
      const pdfDownloadUrl = data.pdf_url || `${data.redirect_url}/pdf`;
      if (pdfBtn) {
        pdfBtn.href = pdfDownloadUrl;
        pdfBtn.setAttribute('download', `${data.invoice_number}.pdf`);
      }

      const waBtn = document.getElementById('btnSendWhatsapp');
      if (waBtn && data.whatsapp_url) {
        waBtn.href = data.whatsapp_url;
        waBtn.target = '_blank';

        waBtn.onclick = function() {
          const tempLink = document.createElement('a');
          tempLink.href = pdfDownloadUrl;
          tempLink.download = `${data.invoice_number}.pdf`;
          document.body.appendChild(tempLink);
          tempLink.click();
          document.body.removeChild(tempLink);
        };
      }

      // Check if Web Share API with file attachment is supported (Mobile / Chrome / Safari)
      const sharePdfBtn = document.getElementById('btnSharePdfDirect');
      if (sharePdfBtn) {
        if (navigator.share) {
          sharePdfBtn.style.display = 'inline-flex';
          sharePdfBtn.onclick = async function() {
            sharePdfBtn.disabled = true;
            sharePdfBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Preparing PDF...';
            try {
              const response = await fetch(pdfDownloadUrl);
              const blob = await response.blob();
              const pdfFile = new File([blob], `${data.invoice_number}.pdf`, { type: 'application/pdf' });
              
              if (navigator.canShare && navigator.canShare({ files: [pdfFile] })) {
                await navigator.share({
                  files: [pdfFile],
                  title: `Tax Invoice #${data.invoice_number}`,
                  text: `Official Tax Invoice & Warranty Slip #${data.invoice_number} from MOBIXPRO`
                });
              } else {
                await navigator.share({
                  title: `Tax Invoice #${data.invoice_number}`,
                  text: data.whatsapp_message || `Tax Invoice #${data.invoice_number}`,
                  url: pdfDownloadUrl
                });
              }
            } catch (err) {
              if (err.name !== 'AbortError') {
                console.warn('Share aborted or failed:', err);
                const tempLink = document.createElement('a');
                tempLink.href = pdfDownloadUrl;
                tempLink.download = `${data.invoice_number}.pdf`;
                document.body.appendChild(tempLink);
                tempLink.click();
                document.body.removeChild(tempLink);
                window.open(data.whatsapp_url, '_blank');
              }
            } finally {
              sharePdfBtn.disabled = false;
              sharePdfBtn.innerHTML = '<i class="fas fa-share-nodes"></i> <span>Share PDF Document File Directly</span>';
            }
          };
        } else {
          sharePdfBtn.style.display = 'none';
        }
      }

      openModal('checkoutSuccessModal');

      // Check if auto-send to WhatsApp is enabled
      const autoWhatsapp = document.getElementById('autoWhatsappCheck')?.checked;
      if (autoWhatsapp && data.whatsapp_url) {
        setTimeout(() => {
          const tempLink = document.createElement('a');
          tempLink.href = pdfDownloadUrl;
          tempLink.download = `${data.invoice_number}.pdf`;
          document.body.appendChild(tempLink);
          tempLink.click();
          document.body.removeChild(tempLink);

          window.open(data.whatsapp_url, '_blank');
        }, 500);
      }
    } else {
      window.location.href = data.redirect_url;
    }
  }
});
