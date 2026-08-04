const demoData = {
  summary: {
    total_inventory_value: 1860000,
    dead_stock_value: 268000,
    sell_through_rate: 68.5,
    stockout_risk_sku_count: 8,
    inventory_turnover_days: 52.3,
    gmroi: 3.8,
    backorder_rate: 1.8
  },
  inventory_structure: [
    { category: "健康流转 / Healthy", value: 1120000, percentage: 60.2, definition: "0-60天 / 0-60 days", color: "#34d399" },
    { category: "潜在呆滞 / Potential Slow-moving", value: 472000, percentage: 25.4, definition: "60-90天 / 60-90 days", color: "#fbbf24" },
    { category: "严重呆滞 / Dead Stock", value: 268000, percentage: 14.4, definition: ">90天 / >90 days", color: "#fb7185" }
  ],
  sales_trend: {
    dates: Array.from({ length: 30 }, (_, i) => `Day${i + 1}`),
    daily_sales: [12, 14, 15, 16, 18, 20, 22, 22, 20, 18, 14, 10, 8, 6, 4, 6, 8, 11, 14, 16, 18, 19, 20, 21, 22, 20, 18, 15, 13, 12],
    inventory_balance: [380, 366, 351, 335, 317, 297, 275, 253, 233, 215, 201, 191, 183, 177, 173, 167, 159, 148, 134, 118, 100, 81, 61, 40, 18, 12, 10, 8, 6, 4],
    reorder_point: Array.from({ length: 30 }, () => 150)
  },
  stockout_risk: [
    { sku: "RS-CH-001", category: "Chandelier", on_hand: 45, daily_sales: 8, lead_time: 14, days_of_stock: 5.6, status: "🔴紧急", status_color: "#fb7185", suggested_reorder: 315 },
    { sku: "RS-SC-012", category: "Sconce", on_hand: 96, daily_sales: 7, lead_time: 12, days_of_stock: 13.7, status: "🟡预警", status_color: "#fb923c", suggested_reorder: 219 },
    { sku: "RS-PD-007", category: "Pendant", on_hand: 220, daily_sales: 4, lead_time: 20, days_of_stock: 55.0, status: "🟢正常", status_color: "#34d399", suggested_reorder: 0 },
    { sku: "RS-FL-021", category: "Floor Lamp", on_hand: 62, daily_sales: 3, lead_time: 17, days_of_stock: 20.7, status: "🟡预警", status_color: "#fb923c", suggested_reorder: 73 },
    { sku: "RS-TL-004", category: "Table Lamp", on_hand: 30, daily_sales: 6, lead_time: 16, days_of_stock: 5.0, status: "🔴紧急", status_color: "#fb7185", suggested_reorder: 240 },
    { sku: "RS-WS-009", category: "Wall Light", on_hand: 280, daily_sales: 2, lead_time: 12, days_of_stock: 140.0, status: "🔵过剩", status_color: "#60a5fa", suggested_reorder: 0 }
  ],
  abc_classification: [
    { class: "A", sku_count: 52, sku_percentage: 20, sales_contribution: 68.5, avg_gmroi: 5.2, strategy: "每日监控，安全库存45天，绝对不断货 / Daily monitoring, 45-day safety stock, zero stockout tolerance" },
    { class: "B", sku_count: 96, sku_percentage: 38, sales_contribution: 23.3, avg_gmroi: 3.4, strategy: "每周复盘，动态调拨，平衡周转与毛利 / Weekly review, dynamic allocation, balance turnover and margin" },
    { class: "C", sku_count: 102, sku_percentage: 42, sales_contribution: 8.2, avg_gmroi: 1.7, strategy: "低频补货，严格控量，优先去化尾货 / Low-frequency replenishment, strict quantity control, clear long-tail stock first" }
  ],
  business_recommendation: {
    dead_stock_value: 268000,
    target_recovery: 80000,
    reinvest_sku: "RS-CH-001",
    reinvest_amount: 45000,
    reinvest_gmroi: 5.2,
    projected_gmroi_after: 4.5
  }
};

const formatCurrency = (value) => `$${new Intl.NumberFormat("en-US").format(Math.round(value))}`;
const formatNumber = (value) => new Intl.NumberFormat("en-US").format(Number(value));
const formatPercent = (value) => `${Number(value).toFixed(1)}%`;

let agePieChart;
let dualAxisChart;

const METRIC_NOTE_ITEMS = [
  { name: "总库存货值 / Total Inventory Value", note: "口径：在库SKU按库存成本计价的总和；单位：美元($) / Sum of all on-hand SKU inventory cost in USD." },
  { name: "呆滞货值 / Dead Stock Value", note: "口径：库龄>90天SKU库存货值；用于评估积压风险 / Inventory value with aging >90 days, used for overstock risk." },
  { name: "动销率 / Sell-through Rate", note: "口径：近30天有销量SKU数 / 在售SKU总数；单位：% / SKUs sold in last 30 days divided by active SKUs." },
  { name: "断货风险SKU数 / Stockout Risk SKUs", note: "口径：可售天数<交期或<交期×1.5的SKU数量 / Count of SKUs with days of stock below lead-time thresholds." },
  { name: "库存周转天数 / Inventory Turnover Days", note: "口径：平均库存 / 日均销售成本；数值越低通常周转越快 / Lower value usually indicates faster turnover." },
  { name: "GMROI", note: "公式：年毛利额 / 平均库存成本 / Formula: Annual Gross Margin / Average Inventory Cost." },
  { name: "缺货率 / Backorder Rate", note: "口径：缺货订单行数 / 总订单行数；单位：% / Backordered order lines over total order lines." },
  { name: "可售天数 / Days of Stock", note: "公式：在手库存 / 日均销量 / Formula: On-hand Inventory / Daily Sales." },
  { name: "建议补货量 / Suggested Reorder", note: "公式：45天目标库存 - 在手库存 / Formula: 45-day target inventory minus on-hand inventory." },
  { name: "状态分级 / Status Rule", note: "紧急/预警/正常：基于可售天数与交期阈值 / Critical/Warning/Normal based on days-of-stock vs lead time." }
];

function applyStockoutLogic(row) {
  const days_of_stock = row.daily_sales > 0 ? row.on_hand / row.daily_sales : 0;
  const suggested_reorder = Math.max(0, Math.round(row.daily_sales * 45 - row.on_hand));
  let status = "🟢正常 / Normal";
  let status_color = "#34d399";
  if (days_of_stock < row.lead_time) {
    status = "🔴紧急 / Critical";
    status_color = "#fb7185";
  } else if (days_of_stock < row.lead_time * 1.5) {
    status = "🟡预警 / Warning";
    status_color = "#fb923c";
  } else if (days_of_stock > row.lead_time * 4) {
    status = "🔵过剩 / Excess";
    status_color = "#60a5fa";
  }
  return {
    ...row,
    days_of_stock: Number(days_of_stock.toFixed(1)),
    suggested_reorder,
    status,
    status_color
  };
}

function renderMetricNotes() {
  const container = document.getElementById("metricNotes");
  container.innerHTML = METRIC_NOTE_ITEMS.map(
    (item) => `
      <div class="metric-note-item">
        <strong>${item.name}</strong>
        <p>${item.note}</p>
      </div>
    `
  ).join("");
}

function renderKpi(summary) {
  document.getElementById("kpiTotalInventoryValue").textContent = formatCurrency(summary.total_inventory_value);
  document.getElementById("kpiDeadStockValue").textContent = formatCurrency(summary.dead_stock_value);
  document.getElementById("kpiSellThroughRate").textContent = formatPercent(summary.sell_through_rate);
  document.getElementById("kpiStockoutRiskSkuCount").textContent = formatNumber(summary.stockout_risk_sku_count);
  document.getElementById("kpiInventoryTurnoverDays").textContent = `${summary.inventory_turnover_days}天`;
  document.getElementById("kpiGmroi").textContent = summary.gmroi.toFixed(1);
  document.getElementById("kpiBackorderRate").textContent = formatPercent(summary.backorder_rate);
}

function renderInventoryStructure(inventory_structure) {
  const seriesData = inventory_structure.map((item) => ({
    name: `${item.category} (${item.definition})`,
    value: item.value,
    itemStyle: { color: item.color }
  }));

  agePieChart.setOption(
    {
      animationDuration: 500,
      tooltip: { trigger: "item", formatter: "{b}<br/>货值/Value: ${c}<br/>占比/Share: {d}%" },
      legend: { bottom: 0, textStyle: { color: "#cbd5e1" } },
      series: [
        {
          type: "pie",
          radius: ["40%", "70%"],
          label: { color: "#e2e8f0" },
          data: seriesData
        }
      ]
    },
    true
  );
}

function renderSalesTrend(sales_trend) {
  dualAxisChart.setOption(
    {
      animationDuration: 500,
      tooltip: { trigger: "axis" },
      legend: { top: 0, textStyle: { color: "#cbd5e1" } },
      grid: { left: 40, right: 40, top: 36, bottom: 28 },
      xAxis: {
        type: "category",
        data: sales_trend.dates,
        axisLine: { lineStyle: { color: "#64748b" } },
        axisLabel: { color: "#cbd5e1", interval: 4 }
      },
      yAxis: [
        {
          type: "value",
          name: "库存水位 / Inventory Level",
          axisLabel: { color: "#cbd5e1" },
          splitLine: { lineStyle: { color: "rgba(148,163,184,.15)" } }
        },
        {
          type: "value",
          name: "销量 / Sales",
          axisLabel: { color: "#cbd5e1" },
          splitLine: { show: false }
        }
      ],
      series: [
        {
          name: "库存结余 / Inventory Balance",
          type: "bar",
          yAxisIndex: 0,
          data: sales_trend.inventory_balance,
          itemStyle: { color: "#38bdf8" }
        },
        {
          name: "每日销量 / Daily Sales",
          type: "line",
          smooth: true,
          yAxisIndex: 1,
          data: sales_trend.daily_sales,
          itemStyle: { color: "#a78bfa" },
          lineStyle: { width: 2.5 }
        },
        {
          name: "再订购点 / Reorder Point",
          type: "line",
          yAxisIndex: 0,
          data: sales_trend.reorder_point,
          symbol: "none",
          lineStyle: { color: "#f59e0b", type: "dashed", width: 2 }
        }
      ]
    },
    true
  );
}

function renderStockoutTable(stockout_risk) {
  const tbody = document.getElementById("warningTableBody");
  const rows = stockout_risk.map(applyStockoutLogic);
  tbody.innerHTML = rows
    .map(
      (row) => `
      <tr style="background: ${row.status.includes("🔴") ? "rgba(239,68,68,0.08)" : row.status.includes("🟡") ? "rgba(245,158,11,0.08)" : "transparent"};">
        <td>${row.sku}</td>
        <td>${row.category}</td>
        <td>${formatNumber(row.on_hand)}</td>
        <td>${row.daily_sales}</td>
        <td>${row.lead_time}</td>
        <td>${row.days_of_stock}</td>
        <td><span class="tag ${row.status.includes("🔴") ? "tag-risk" : row.status.includes("🟡") ? "tag-warn" : "tag-ok"}">${row.status}</span></td>
        <td style="color:${row.status_color}">${row.status_color}</td>
        <td>${formatNumber(row.suggested_reorder)}</td>
      </tr>
    `
    )
    .join("");
}

function renderAbcTable(abc_classification) {
  const tbody = document.getElementById("abcTableBody");
  tbody.innerHTML = abc_classification
    .map(
      (row) => `
      <tr>
        <td>${row.class}</td>
        <td>${formatNumber(row.sku_count)}</td>
        <td>${formatPercent(row.sku_percentage)}</td>
        <td>${formatPercent(row.sales_contribution)}</td>
        <td>${row.avg_gmroi.toFixed(1)}</td>
        <td>${row.strategy}</td>
      </tr>
    `
    )
    .join("");
}

function renderGmroiCards(summary, abc_classification) {
  const gmroiCards = document.getElementById("gmroiCards");
  const classA = abc_classification.find((item) => item.class === "A");
  const classB = abc_classification.find((item) => item.class === "B");
  const classC = abc_classification.find((item) => item.class === "C");
  gmroiCards.innerHTML = `
    <div class="metric-card">
      <strong>整体GMROI / Overall GMROI: ${summary.gmroi.toFixed(1)}</strong>
      <p>库存周转天数 / Turnover Days: ${summary.inventory_turnover_days}d</p>
      <small>公式 / Formula: Annual Gross Margin / Average Inventory Cost</small>
    </div>
    <div class="metric-card">
      <strong>A/B类 GMROI: ${classA.avg_gmroi.toFixed(1)} / ${classB.avg_gmroi.toFixed(1)}</strong>
      <p>C类 GMROI: ${classC.avg_gmroi.toFixed(1)}</p>
      <small>优先提升低GMROI长尾SKU / Improve low-GMROI long-tail SKUs first</small>
    </div>
    <div class="metric-card">
      <strong>断货风险SKU / Stockout Risk SKUs: ${summary.stockout_risk_sku_count}</strong>
      <p>缺货率 / Backorder Rate: ${summary.backorder_rate.toFixed(1)}%</p>
      <small>补货节奏与交期联动 / Sync replenishment cadence with lead time</small>
    </div>
  `;
}

function renderBusinessRecommendation(business_recommendation) {
  const adviceCards = document.getElementById("adviceCards");
  adviceCards.innerHTML = `
    <div class="advice-card">
      <strong>清仓回收计划 / Clearance Recovery Plan</strong>
      <p>呆滞货值 / Dead Stock: ${formatCurrency(business_recommendation.dead_stock_value)}</p>
      <p>目标回收现金 / Target Recovery: ${formatCurrency(business_recommendation.target_recovery)}</p>
    </div>
    <div class="advice-card">
      <strong>补货投放建议 / Reinvestment Plan</strong>
      <p>建议补货SKU / Reinvest SKU: ${business_recommendation.reinvest_sku}</p>
      <p>补货金额 / Reinvest Amount: ${formatCurrency(business_recommendation.reinvest_amount)}</p>
    </div>
    <div class="advice-card">
      <strong>GMROI优化目标 / GMROI Target</strong>
      <p>目标SKU GMROI / Target SKU GMROI: ${business_recommendation.reinvest_gmroi.toFixed(1)}</p>
      <p>优化后预计GMROI / Projected GMROI: ${business_recommendation.projected_gmroi_after.toFixed(1)}</p>
    </div>
  `;
}

function renderAll(dataSource) {
  renderKpi(dataSource.summary);
  renderInventoryStructure(dataSource.inventory_structure);
  renderSalesTrend(dataSource.sales_trend);
  renderStockoutTable(dataSource.stockout_risk);
  renderAbcTable(dataSource.abc_classification);
  renderGmroiCards(dataSource.summary, dataSource.abc_classification);
  renderBusinessRecommendation(dataSource.business_recommendation);
}

function setupExport() {
  const button = document.getElementById("exportBtn");
  button.addEventListener("click", async () => {
    agePieChart.resize();
    dualAxisChart.resize();
    const dashboard = document.getElementById("dashboard");
    const canvas = await html2canvas(dashboard, {
      backgroundColor: "#0f172a",
      scale: 2,
      useCORS: true
    });
    const link = document.createElement("a");
    link.download = `inventory-health-dashboard-${Date.now()}.png`;
    link.href = canvas.toDataURL("image/png");
    link.click();
  });
}

function initCharts() {
  agePieChart = echarts.init(document.getElementById("agePieChart"));
  dualAxisChart = echarts.init(document.getElementById("dualAxisChart"));
}

function init() {
  initCharts();
  renderMetricNotes();
  renderAll(demoData);
  setupExport();
  window.addEventListener("resize", () => {
    agePieChart.resize();
    dualAxisChart.resize();
  });
}

init();
