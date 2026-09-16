/**
 * MOBIX Dashboard Charts & Realtime Analytics
 * Renders glowing Chart.js line & donut charts matching reference mockup
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Live Clock update in Welcome Banner
  const clockElement = document.getElementById('liveClockText');
  if (clockElement) {
    function updateClock() {
      const now = new Date();
      const options = { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' };
      clockElement.textContent = now.toLocaleDateString('en-US', options);
    }
    updateClock();
    setInterval(updateClock, 1000);
  }

  // 2. Dashboard Charts Initialization
  const salesCanvas = document.getElementById('salesTrendChart');
  const brandCanvas = document.getElementById('brandSplitChart');

  if (!salesCanvas || !brandCanvas) return;

  fetch('/api/dashboard/charts')
    .then(res => res.json())
    .then(data => {
      renderCharts(data);
    })
    .catch(err => console.error("Error loading dashboard charts:", err));

  function renderCharts(data) {
    // 1. Sales Trend Area Chart (Clean Modern Line)
    const ctxSales = salesCanvas.getContext('2d');
    const gradient = ctxSales.createLinearGradient(0, 0, 0, 260);
    gradient.addColorStop(0, 'rgba(2, 132, 199, 0.25)');
    gradient.addColorStop(0.6, 'rgba(99, 102, 241, 0.08)');
    gradient.addColorStop(1, 'rgba(255, 255, 255, 0.0)');

    new Chart(ctxSales, {
      type: 'line',
      data: {
        labels: data.sales_trend.labels,
        datasets: [{
          label: 'Revenue (₹)',
          data: data.sales_trend.sales,
          borderColor: '#0284c7',
          borderWidth: 3,
          backgroundColor: gradient,
          fill: true,
          tension: 0.4,
          pointBackgroundColor: '#ffffff',
          pointBorderColor: '#0284c7',
          pointBorderWidth: 2.5,
          pointRadius: 5,
          pointHoverRadius: 7,
          pointHoverBackgroundColor: '#0284c7',
          pointHoverBorderColor: '#ffffff'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#0f172a',
            titleColor: '#38bdf8',
            bodyColor: '#ffffff',
            borderColor: '#cbd5e1',
            borderWidth: 1,
            padding: 12,
            boxPadding: 6,
            usePointStyle: true,
            callbacks: {
              label: (context) => ` Revenue: ₹${context.raw.toLocaleString()}`
            }
          }
        },
        scales: {
          x: {
            grid: { color: '#f1f5f9' },
            ticks: { color: '#64748b', font: { size: 11, weight: '600' } }
          },
          y: {
            grid: { color: '#f1f5f9' },
            ticks: {
              color: '#64748b',
              font: { size: 11, weight: '600' },
              callback: (val) => `₹${val >= 1000 ? (val/1000).toFixed(0) + 'k' : val}`
            }
          }
        }
      }
    });

    // 2. Top Selling Brands Donut Chart (Vibrant Palette)
    const ctxBrand = brandCanvas.getContext('2d');
    const brandColors = [
      '#0284c7', // Cyan / Blue
      '#3b82f6', // Blue
      '#8b5cf6', // Purple
      '#ec4899', // Pink
      '#f59e0b'  // Amber
    ];

    new Chart(ctxBrand, {
      type: 'doughnut',
      data: {
        labels: data.brand_split.labels,
        datasets: [{
          data: data.brand_split.values,
          backgroundColor: brandColors,
          borderColor: '#ffffff',
          borderWidth: 3,
          hoverOffset: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '72%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: '#475569',
              font: { size: 11.5, weight: '600' },
              padding: 14,
              usePointStyle: true,
              pointStyle: 'circle'
            }
          },
          tooltip: {
            backgroundColor: '#0f172a',
            titleColor: '#38bdf8',
            bodyColor: '#ffffff',
            borderColor: '#cbd5e1',
            borderWidth: 1,
            padding: 10,
            callbacks: {
              label: (ctx) => ` Stock / Sold: ${ctx.raw} units`
            }
          }
        }
      }
    });
  }
});
