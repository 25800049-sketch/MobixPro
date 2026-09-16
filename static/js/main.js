/**
 * MOBIX Management System - Main JS
 * Handles Dark/Light Mode, Mobile Navigation, Modals & Utility Actions
 */

// 1. Global Modal Opening and Closing Helper (available immediately)
window.openModal = function(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('active');
    modal.style.display = 'flex';
  } else {
    console.warn(`Modal with ID '${modalId}' not found.`);
  }
};

window.closeModal = function(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('active');
    modal.style.display = 'none';
  } else {
    console.warn(`Modal with ID '${modalId}' not found.`);
  }
};

// 2. Initialize Theme (Default to clean light theme) & Floating Mobile Theme
(function initTheme() {
  const savedTheme = localStorage.getItem('mobix_theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);
  
  const savedFloating = localStorage.getItem('mobix_floating_theme') || 'enabled';
  document.documentElement.setAttribute('data-floating-theme', savedFloating);
})();

document.addEventListener('DOMContentLoaded', () => {
  // Theme Toggle Button Setup
  const themeToggleBtn = document.getElementById('theme-toggle-btn');
  const themeToggleIcon = document.getElementById('theme-toggle-icon');

  function updateThemeIcon(theme) {
    if (!themeToggleBtn) return;
    const icon = themeToggleIcon || themeToggleBtn.querySelector('i');
    if (icon) {
      if (theme === 'dark') {
        icon.className = 'fas fa-sun';
        themeToggleBtn.setAttribute('title', 'Switch to Light Theme');
      } else {
        icon.className = 'fas fa-moon';
        themeToggleBtn.setAttribute('title', 'Switch to Dark Theme');
      }
    }
  }

  const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
  updateThemeIcon(currentTheme);

  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
      const activeTheme = document.documentElement.getAttribute('data-theme') || 'light';
      const newTheme = activeTheme === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('mobix_theme', newTheme);
      updateThemeIcon(newTheme);

      // Trigger event for charts re-render if present
      window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: newTheme } }));
    });
  }

  // Floating Mobile Theme Controls & Indicator
  const floatingToggleBtn = document.getElementById('floating-theme-toggle-btn');
  const floatingIndicator = document.getElementById('floatingThemeIndicator');
  const floatingUniverseInner = document.querySelector('.floating-universe-inner');

  function updateFloatingThemeUI(state) {
    if (floatingToggleBtn) {
      if (state === 'enabled') {
        floatingToggleBtn.setAttribute('title', 'Turn Off Floating Mobile Background');
        if (floatingIndicator) {
          floatingIndicator.style.background = '#10b981';
          floatingIndicator.style.boxShadow = '0 0 8px #10b981';
        }
      } else {
        floatingToggleBtn.setAttribute('title', 'Turn On Floating Mobile Background');
        if (floatingIndicator) {
          floatingIndicator.style.background = '#94a3b8';
          floatingIndicator.style.boxShadow = 'none';
        }
      }
    }
  }

  const initialFloatingState = document.documentElement.getAttribute('data-floating-theme') || 'enabled';
  updateFloatingThemeUI(initialFloatingState);

  if (floatingToggleBtn) {
    floatingToggleBtn.addEventListener('click', () => {
      const currentState = document.documentElement.getAttribute('data-floating-theme') || 'enabled';
      const nextState = currentState === 'enabled' ? 'disabled' : 'enabled';
      document.documentElement.setAttribute('data-floating-theme', nextState);
      localStorage.setItem('mobix_floating_theme', nextState);
      updateFloatingThemeUI(nextState);
    });
  }

  // Interactive 3D Mouse Parallax
  if (floatingUniverseInner && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    let targetX = 0, targetY = 0;
    let currentX = 0, currentY = 0;
    let rafId = null;

    window.addEventListener('mousemove', (e) => {
      const halfW = window.innerWidth / 2;
      const halfH = window.innerHeight / 2;
      targetX = (e.clientX - halfW) / halfW;
      targetY = (e.clientY - halfH) / halfH;

      if (!rafId) {
        rafId = requestAnimationFrame(renderParallax);
      }
    }, { passive: true });

    function renderParallax() {
      currentX += (targetX - currentX) * 0.05;
      currentY += (targetY - currentY) * 0.05;

      const rotY = currentX * 10;
      const rotX = -currentY * 10;
      const transX = currentX * 20;
      const transY = currentY * 18;

      floatingUniverseInner.style.transform = `translate3d(${transX.toFixed(2)}px, ${transY.toFixed(2)}px, 0) rotateX(${rotX.toFixed(2)}deg) rotateY(${rotY.toFixed(2)}deg)`;

      if (Math.abs(targetX - currentX) > 0.001 || Math.abs(targetY - currentY) > 0.001) {
        rafId = requestAnimationFrame(renderParallax);
      } else {
        rafId = null;
      }
    }
  }

  // 3. Mobile Sidebar Toggle
  const mobileToggle = document.getElementById('mobile-toggle-btn');
  const sidebar = document.querySelector('.app-sidebar');
  if (mobileToggle && sidebar) {
    mobileToggle.addEventListener('click', () => {
      sidebar.classList.toggle('open');
    });

    document.addEventListener('click', (e) => {
      if (sidebar.classList.contains('open') && !sidebar.contains(e.target) && !mobileToggle.contains(e.target)) {
        sidebar.classList.remove('open');
      }
    });
  }

  // 4. Close modals when clicking on overlay background
  document.querySelectorAll('.modal-overlay').forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.classList.remove('active');
      }
    });
  });

  // Close active modal on Escape key press
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const activeModal = document.querySelector('.modal-overlay.active');
      if (activeModal) {
        activeModal.classList.remove('active');
      }
    }
  });

  // 5. Auto-dismiss flash alerts after 5 seconds
  setTimeout(() => {
    document.querySelectorAll('.alert').forEach(alert => {
      alert.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
      alert.style.opacity = '0';
      alert.style.transform = 'translateY(-10px)';
      setTimeout(() => alert.remove(), 500);
    });
  }, 5000);
});

// ==========================================================================
// Floating Smart Phone Window (Mobix Smart Island) Controller
// ==========================================================================

let activeSmartGst = 18;

window.toggleFloatingPhoneWindow = function() {
  const win = document.getElementById('floatingPhoneWindow');
  const arrow = document.getElementById('dockArrowIcon');
  if (!win) return;
  
  win.classList.toggle('open');
  if (arrow) {
    if (win.classList.contains('open')) {
      arrow.className = 'fas fa-chevron-down dock-arrow';
    } else {
      arrow.className = 'fas fa-chevron-up dock-arrow';
    }
  }
};

window.switchPhoneTab = function(tabId, btn) {
  document.querySelectorAll('.phone-tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.phone-tab-btn').forEach(el => el.classList.remove('active'));
  
  const target = document.getElementById(tabId);
  if (target) target.classList.add('active');
  if (btn) btn.classList.add('active');
};

window.setSmartGst = function(rate, btn) {
  activeSmartGst = rate;
  if (btn && btn.parentElement) {
    btn.parentElement.querySelectorAll('button').forEach(b => {
      b.className = 'btn btn-secondary btn-sm';
    });
    btn.className = 'btn btn-primary btn-sm';
  }
  recalcSmartPhone();
};

window.recalcSmartPhone = function() {
  const baseEl = document.getElementById('smartCalcBase');
  const discEl = document.getElementById('smartCalcDiscount');
  if (!baseEl || !discEl) return;

  const base = parseFloat(baseEl.value) || 0;
  const discPct = parseFloat(discEl.value) || 0;

  const discAmt = base * (discPct / 100);
  const taxable = Math.max(0, base - discAmt);
  const gstAmt = taxable * (activeSmartGst / 100);
  const total = taxable + gstAmt;
  const emi6 = total / 6;

  const totalEl = document.getElementById('smartCalcTotal');
  const gstEl = document.getElementById('smartCalcGstAmount');
  const discAmtEl = document.getElementById('smartCalcDiscAmt');
  const emiEl = document.getElementById('smartCalcEmi');

  if (totalEl) totalEl.textContent = '₹' + Math.round(total).toLocaleString('en-IN');
  if (gstEl) gstEl.textContent = '₹' + Math.round(gstAmt).toLocaleString('en-IN');
  if (discAmtEl) discAmtEl.textContent = '-₹' + Math.round(discAmt).toLocaleString('en-IN');
  if (emiEl) emiEl.textContent = '₹' + Math.round(emi6).toLocaleString('en-IN') + ' /mo';
};

window.copySmartCalcResult = function() {
  const total = document.getElementById('smartCalcTotal')?.textContent || '0';
  const gst = document.getElementById('smartCalcGstAmount')?.textContent || '0';
  const disc = document.getElementById('smartCalcDiscAmt')?.textContent || '0';
  const emi = document.getElementById('smartCalcEmi')?.textContent || '0';

  const text = `MOBIX POS Estimate: Total ${total} (Incl. GST ${gst}, Disc ${disc}). 6-Mo No-Cost EMI: ${emi}`;
  navigator.clipboard.writeText(text).then(() => {
    const btnText = document.getElementById('copySmartCalcBtnText');
    if (btnText) {
      const orig = btnText.textContent;
      btnText.textContent = '✓ Copied to Clipboard!';
      setTimeout(() => { btnText.textContent = orig; }, 2000);
    }
  }).catch(() => {});
};

const PHONE_SPECS_DATABASE = {
  'iphone': {
    title: 'Apple iPhone 15 Pro Max',
    sub: 'Titanium • 256GB / 8GB RAM',
    chip: 'A17 Pro (3nm)',
    camera: '48MP + 12MP + 12MP 5x Zoom',
    battery: '4422 mAh (25W USB-C)',
    price: '₹1,34,900'
  },
  'samsung': {
    title: 'Samsung Galaxy S24 Ultra',
    sub: 'Titanium Gray • 512GB / 12GB RAM',
    chip: 'Snapdragon 8 Gen 3 for Galaxy',
    camera: '200MP + 50MP + 12MP + 10MP',
    battery: '5000 mAh (45W Fast)',
    price: '₹1,29,999'
  },
  'oneplus': {
    title: 'OnePlus 12 5G',
    sub: 'Emerald Green • 256GB / 16GB RAM',
    chip: 'Snapdragon 8 Gen 3',
    camera: '50MP Sony LYT-808 + 64MP Periscope',
    battery: '5400 mAh (100W SuperVOOC)',
    price: '₹64,999'
  },
  'pixel': {
    title: 'Google Pixel 8 Pro',
    sub: 'Bay Blue • 128GB / 12GB RAM',
    chip: 'Google Tensor G3 (Titan M2)',
    camera: '50MP + 48MP Ultrawide + 48MP Tele',
    battery: '5050 mAh (30W Fast)',
    price: '₹93,999'
  },
  'redmi': {
    title: 'Redmi Note 13 Pro+ 5G',
    sub: 'Fusion Purple • 256GB / 8GB RAM',
    chip: 'MediaTek Dimensity 7200-Ultra',
    camera: '200MP Samsung ISOCELL HP3 OIS',
    battery: '5000 mAh (120W HyperCharge)',
    price: '₹31,999'
  }
};

window.searchSmartPhoneSpecs = function(val) {
  const query = (val || '').toLowerCase().trim();
  let match = PHONE_SPECS_DATABASE['iphone'];

  for (const [key, spec] of Object.entries(PHONE_SPECS_DATABASE)) {
    if (query.includes(key)) {
      match = spec;
      break;
    }
  }

  const modelEl = document.getElementById('specModelTitle');
  const subEl = document.getElementById('specSubTitle');
  const chipEl = document.getElementById('specChipset');
  const camEl = document.getElementById('specCamera');
  const batEl = document.getElementById('specBattery');
  const priceEl = document.getElementById('specPrice');

  if (modelEl) modelEl.textContent = match.title;
  if (subEl) subEl.textContent = match.sub;
  if (chipEl) chipEl.textContent = match.chip;
  if (camEl) camEl.textContent = match.camera;
  if (batEl) batEl.textContent = match.battery;
  if (priceEl) priceEl.textContent = match.price;
};

window.setAndTrackRepair = function(ticketNo) {
  const idInput = document.getElementById('smartRepairInput');
  if (idInput) {
    idInput.value = ticketNo;
    window.trackSmartRepair();
  }
};

window.trackSmartRepair = async function() {
  const idInput = document.getElementById('smartRepairInput');
  const trackBtn = document.getElementById('smartRepairTrackBtn');
  const errBox = document.getElementById('smartRepairError');
  const detailsBox = document.getElementById('smartRepairDetails');

  let query = (idInput?.value || '').trim();

  // If user pasted something like REP-10REP-260910-EA46, clean it up
  if (query.includes('REP-') && query.lastIndexOf('REP-') > 0) {
    query = query.substring(query.lastIndexOf('REP-'));
    if (idInput) idInput.value = query;
  }

  if (!query) {
    if (errBox) {
      errBox.style.display = 'block';
      errBox.innerHTML = '<i class="fas fa-circle-info" style="color: var(--primary); font-size: 16px; margin-bottom: 6px; display: block;"></i> Please enter a Ticket Number (e.g. <strong>REP-260910-EA46</strong>) or IMEI.';
    }
    if (detailsBox) detailsBox.style.display = 'none';
    return;
  }

  // Visual loading feedback
  if (trackBtn) {
    trackBtn.disabled = true;
    trackBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
  }

  try {
    const res = await fetch(`/repairs/api/track?q=${encodeURIComponent(query)}`);
    const data = await res.json();

    if (data.success && data.ticket) {
      const t = data.ticket;
      if (errBox) errBox.style.display = 'none';
      if (detailsBox) detailsBox.style.display = 'block';

      // Update Header & Customer Info
      const titleEl = document.getElementById('smartRepairTitle');
      const subEl = document.getElementById('smartRepairSub');
      const badgeEl = document.getElementById('smartRepairBadge');
      const fillEl = document.getElementById('smartRepairProgressFill');
      const stepEl = document.getElementById('smartRepairStepText');
      const probEl = document.getElementById('smartRepairProblem');
      const techEl = document.getElementById('smartRepairTech');
      const costEl = document.getElementById('smartRepairCost');

      if (titleEl) titleEl.textContent = `${t.brand} ${t.model}`;
      if (subEl) subEl.textContent = `Ticket #${t.ticket_no} • Customer: ${t.customer_name || 'Walk-in'}`;
      
      if (badgeEl) {
        badgeEl.className = `badge ${t.badge_class || 'badge-primary'}`;
        badgeEl.textContent = (t.status || 'IN PROGRESS').toUpperCase();
      }

      if (fillEl) {
        fillEl.style.width = `${t.progress_percent || 50}%`;
      }

      if (stepEl) {
        stepEl.textContent = t.step_label || t.status;
      }

      if (probEl) {
        probEl.textContent = t.problem_description || 'General inspection';
      }

      if (techEl) {
        techEl.textContent = t.technician_name || 'Assigned Technician';
      }

      if (costEl) {
        const estOrFinal = t.final_cost > 0 ? t.final_cost : t.estimated_cost;
        costEl.textContent = `₹${Number(estOrFinal).toLocaleString('en-IN', {minimumFractionDigits: 2})} (Due: ₹${Number(t.balance_due).toLocaleString('en-IN', {minimumFractionDigits: 2})})`;
      }

      // Update Action Buttons
      const payBtn = document.getElementById('smartRepairPayBtn');
      const recLink = document.getElementById('smartRepairReceiptLink');
      if (payBtn) {
        if (t.balance_due > 0.01) {
          payBtn.style.display = 'inline-flex';
          payBtn.style.alignItems = 'center';
          payBtn.style.justifyContent = 'center';
          payBtn.href = '/repairs';
          payBtn.innerHTML = `<i class="fas fa-hand-holding-dollar" style="margin-right: 5px;"></i> Pay Balance (₹${Number(t.balance_due).toLocaleString('en-IN', {minimumFractionDigits: 2})})`;
        } else {
          payBtn.style.display = 'inline-flex';
          payBtn.style.alignItems = 'center';
          payBtn.style.justifyContent = 'center';
          payBtn.href = `/repairs/${t.id}/receipt`;
          payBtn.target = '_blank';
          payBtn.innerHTML = '<i class="fas fa-check-circle" style="margin-right: 5px;"></i> Fully Paid • View Receipt';
        }
      }
      if (recLink) {
        recLink.href = `/repairs/${t.id}/receipt`;
        recLink.style.display = 'inline-flex';
        recLink.style.alignItems = 'center';
        recLink.style.justifyContent = 'center';
      }
    } else {
      if (detailsBox) detailsBox.style.display = 'none';
      if (errBox) {
        errBox.style.display = 'block';
        errBox.innerHTML = `
          <i class="fas fa-triangle-exclamation" style="color: #e11d48; font-size: 20px; margin-bottom: 6px; display: block;"></i>
          <strong>${data.message || 'Ticket not found'}</strong>
          <div style="font-size: 9.5px; opacity: 0.8; margin-top: 6px;">
            Check your ticket code (e.g. <code>REP-260910-EA46</code>) or search with 15-digit IMEI.
          </div>
        `;
      }
    }
  } catch (err) {
    console.error('Error fetching repair status:', err);
    if (detailsBox) detailsBox.style.display = 'none';
    if (errBox) {
      errBox.style.display = 'block';
      errBox.innerHTML = '<i class="fas fa-circle-exclamation" style="color: #e11d48; margin-bottom: 6px; display: block;"></i> Network connection error while tracking ticket.';
    }
  } finally {
    if (trackBtn) {
      trackBtn.disabled = false;
      trackBtn.textContent = 'Track';
    }
  }
};

window.toggleFloatingUniverseFromPhone = function() {
  const toggleBtn = document.getElementById('floating-theme-toggle-btn');
  if (toggleBtn) {
    toggleBtn.click();
    const btnPhone = document.getElementById('smartThemeToggleBtn');
    const state = document.documentElement.getAttribute('data-floating-theme');
    if (btnPhone) {
      btnPhone.textContent = state === 'enabled' ? 'Active (ON)' : 'Disabled (OFF)';
      btnPhone.className = state === 'enabled' ? 'btn btn-primary btn-sm' : 'btn btn-secondary btn-sm';
    }
  }
};

window.adjustFloatingSpeed = function(val) {
  const num = parseFloat(val) || 1.0;
  const label = document.getElementById('smartFloatSpeedVal');
  if (label) label.textContent = num.toFixed(1) + 'x ' + (num > 1.4 ? '(Fast)' : (num < 0.8 ? '(Slow)' : '(Normal)'));

  const p1 = document.querySelector('.floating-phone-flagship');
  const p2 = document.querySelector('.floating-phone-holo');
  const p3 = document.querySelector('.floating-phone-orbit');

  if (p1) p1.style.animationDuration = `${(14 / num).toFixed(1)}s`;
  if (p2) p2.style.animationDuration = `${(17 / num).toFixed(1)}s`;
  if (p3) p3.style.animationDuration = `${(19 / num).toFixed(1)}s`;
};

window.setFloatingGlowStyle = function(style) {
  const orb1 = document.querySelector('.floating-glow-orb.orb-cyan');
  const orb2 = document.querySelector('.floating-glow-orb.orb-indigo');

  if (style === 'violet') {
    if (orb1) orb1.style.background = 'radial-gradient(circle, rgba(168, 85, 247, 0.3) 0%, transparent 70%)';
    if (orb2) orb2.style.background = 'radial-gradient(circle, rgba(236, 72, 153, 0.25) 0%, transparent 70%)';
  } else {
    if (orb1) orb1.style.background = '';
    if (orb2) orb2.style.background = '';
  }
};

// Realtime Clock Updater for Dynamic Island
function updateSmartClock() {
  const clock = document.getElementById('smartWindowTime');
  if (clock) {
    const now = new Date();
    const hrs = String(now.getHours()).padStart(2, '0');
    const mins = String(now.getMinutes()).padStart(2, '0');
    clock.textContent = `${hrs}:${mins}`;
  }
}
setInterval(updateSmartClock, 1000);
updateSmartClock();

