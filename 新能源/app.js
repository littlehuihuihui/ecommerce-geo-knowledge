const colorSet = ["#22d3ee", "#38bdf8", "#818cf8", "#f59e0b", "#34d399", "#f472b6", "#f97316"];
const textColor = "#cbd5e1";
const axisColor = "rgba(148, 163, 184, 0.3)";

const chartMap = {};
const tabPanels = document.querySelectorAll(".tab-panel");
const tabButtons = document.querySelectorAll(".tab-btn");

function baseOption() {
  return {
    textStyle: { color: textColor, fontFamily: "Inter, Microsoft YaHei, sans-serif" },
    tooltip: { trigger: "axis", backgroundColor: "rgba(15,23,42,0.95)", borderColor: axisColor, textStyle: { color: "#e2e8f0" } },
    legend: { textStyle: { color: textColor } },
    grid: { left: 36, right: 20, top: 36, bottom: 28, containLabel: true },
    xAxis: { axisLine: { lineStyle: { color: axisColor } }, axisLabel: { color: textColor }, splitLine: { lineStyle: { color: "rgba(148,163,184,0.12)" } } },
    yAxis: { axisLine: { lineStyle: { color: axisColor } }, axisLabel: { color: textColor }, splitLine: { lineStyle: { color: "rgba(148,163,184,0.12)" } } }
  };
}

function makeChart(id, option) {
  const dom = document.getElementById(id);
  if (!dom) return;
  const chart = echarts.init(dom);
  chart.setOption(option);
  chartMap[id] = chart;
}

function initOverviewCharts() {
  const baseMonths = ["1月", "2月", "3月", "4月", "5月", "6月"];
  makeChart("baseOutputChart", {
    ...baseOption(),
    legend: { data: ["北京基地", "溧阳基地", "珠海基地", "成都基地"], textStyle: { color: textColor } },
    xAxis: { type: "category", data: baseMonths, axisLine: { lineStyle: { color: axisColor } }, axisLabel: { color: textColor } },
    yAxis: { type: "value", name: "GWh", axisLabel: { color: textColor }, splitLine: { lineStyle: { color: "rgba(148,163,184,0.12)" } } },
    series: [
      { name: "北京基地", type: "bar", data: [1.3, 1.5, 1.6, 1.8, 1.9, 2.0], itemStyle: { color: colorSet[0] } },
      { name: "溧阳基地", type: "bar", data: [1.1, 1.2, 1.4, 1.6, 1.7, 1.8], itemStyle: { color: colorSet[1] } },
      { name: "珠海基地", type: "bar", data: [0.9, 1.1, 1.2, 1.3, 1.4, 1.5], itemStyle: { color: colorSet[2] } },
      { name: "成都基地", type: "bar", data: [0.8, 0.9, 1.0, 1.2, 1.3, 1.4], itemStyle: { color: colorSet[4] } }
    ]
  });

  makeChart("capacityOrderChart", {
    ...baseOption(),
    xAxis: { type: "category", data: baseMonths, axisLine: { lineStyle: { color: axisColor } }, axisLabel: { color: textColor } },
    yAxis: { type: "value", min: 80, max: 110, axisLabel: { formatter: "{value}%" } },
    series: [
      { name: "产能达成率", type: "line", smooth: true, data: [90, 92, 95, 94, 97, 99], lineStyle: { color: colorSet[0] }, itemStyle: { color: colorSet[0] } },
      { name: "订单兑现率", type: "line", smooth: true, data: [88, 89, 91, 93, 95, 96], lineStyle: { color: colorSet[3] }, itemStyle: { color: colorSet[3] } }
    ]
  });

  makeChart("productMixChart", {
    tooltip: { trigger: "item" },
    legend: { bottom: 0, textStyle: { color: textColor } },
    series: [{
      type: "pie",
      radius: ["36%", "68%"],
      data: [
        { value: 42, name: "半固态动力电池" },
        { value: 28, name: "全固态样件" },
        { value: 20, name: "储能电池" },
        { value: 10, name: "消费类电池" }
      ],
      itemStyle: { borderColor: "#0f172a", borderWidth: 2 }
    }]
  });

  makeChart("baseHeatmapChart", {
    tooltip: { position: "top" },
    grid: { left: 40, right: 10, top: 26, bottom: 24, containLabel: true },
    xAxis: { type: "category", data: ["产量", "良率", "OEE", "单位能耗"], axisLabel: { color: textColor }, axisLine: { lineStyle: { color: axisColor } } },
    yAxis: { type: "category", data: ["北京", "溧阳", "珠海", "成都"], axisLabel: { color: textColor }, axisLine: { lineStyle: { color: axisColor } } },
    visualMap: { min: 70, max: 100, calculable: false, orient: "horizontal", left: "center", bottom: 0, textStyle: { color: textColor } },
    series: [{
      type: "heatmap",
      data: [
        [0, 0, 98], [1, 0, 97], [2, 0, 90], [3, 0, 75],
        [0, 1, 93], [1, 1, 95], [2, 1, 88], [3, 1, 81],
        [0, 2, 87], [1, 2, 92], [2, 2, 85], [3, 2, 83],
        [0, 3, 85], [1, 3, 94], [2, 3, 86], [3, 3, 80]
      ],
      label: { show: true, color: "#0f172a" }
    }]
  });

  makeChart("businessRadarChart", {
    radar: {
      indicator: [
        { name: "营收增长", max: 100 },
        { name: "产能利用", max: 100 },
        { name: "良率", max: 100 },
        { name: "成本控制", max: 100 },
        { name: "交付效率", max: 100 },
        { name: "创新指标", max: 100 }
      ],
      axisName: { color: textColor },
      splitLine: { lineStyle: { color: "rgba(148,163,184,0.25)" } },
      splitArea: { areaStyle: { color: ["rgba(30,41,59,0.12)", "rgba(30,41,59,0.24)"] } }
    },
    series: [{
      type: "radar",
      data: [{ value: [86, 92, 96, 83, 89, 94], name: "当前表现", areaStyle: { color: "rgba(56,189,248,0.25)" } }]
    }]
  });
}

function initProductionCharts() {
  makeChart("oeeTrendChart", {
    ...baseOption(),
    xAxis: { type: "category", data: ["W1", "W2", "W3", "W4", "W5", "W6"], axisLine: { lineStyle: { color: axisColor } }, axisLabel: { color: textColor } },
    yAxis: { type: "value", min: 70, max: 95, axisLabel: { formatter: "{value}%" } },
    series: [
      { name: "叠片线", type: "line", smooth: true, data: [81, 83, 85, 84, 86, 88], itemStyle: { color: colorSet[0] } },
      { name: "注液线", type: "line", smooth: true, data: [78, 80, 82, 83, 84, 86], itemStyle: { color: colorSet[1] } },
      { name: "化成分容线", type: "line", smooth: true, data: [79, 81, 84, 85, 86, 87], itemStyle: { color: colorSet[2] } }
    ]
  });

  makeChart("solidProcessChart", {
    ...baseOption(),
    xAxis: { type: "category", data: ["混料", "涂布", "叠片", "热压", "注液", "封装"], axisLabel: { color: textColor }, axisLine: { lineStyle: { color: axisColor } } },
    yAxis: { type: "value", name: "秒/片" },
    series: [{ type: "bar", data: [18, 24, 33, 29, 27, 22], itemStyle: { color: colorSet[3] } }]
  });

  makeChart("equipmentStatusChart", {
    tooltip: { trigger: "item" },
    legend: { bottom: 0, textStyle: { color: textColor } },
    series: [{
      type: "pie",
      radius: "68%",
      data: [
        { name: "运行", value: 126 },
        { name: "待机", value: 28 },
        { name: "保养", value: 14 },
        { name: "故障", value: 7 }
      ]
    }]
  });

  makeChart("workOrderChart", {
    ...baseOption(),
    xAxis: { type: "value", max: 100, axisLine: { lineStyle: { color: axisColor } }, axisLabel: { color: textColor } },
    yAxis: { type: "category", data: ["WO-2401", "WO-2402", "WO-2403", "WO-2404"], axisLabel: { color: textColor } },
    series: [
      { type: "bar", stack: "total", data: [72, 80, 65, 84], itemStyle: { color: colorSet[0] } },
      { type: "bar", stack: "total", data: [28, 20, 35, 16], itemStyle: { color: "rgba(148,163,184,0.35)" } }
    ]
  });

  makeChart("bottleneckChart", {
    ...baseOption(),
    xAxis: { type: "category", data: ["涂布", "辊压", "分切", "叠片", "焊接"], axisLabel: { color: textColor }, axisLine: { lineStyle: { color: axisColor } } },
    yAxis: { type: "value", name: "等待时长(min)" },
    series: [{ type: "bar", data: [32, 26, 18, 41, 22], itemStyle: { color: colorSet[6] } }]
  });
}

function initQualityCharts() {
  const points = [15.1, 14.9, 15.2, 15.0, 15.3, 14.8, 15.1, 15.4, 15.0, 14.9, 15.2, 15.1];
  makeChart("spcChart", {
    ...baseOption(),
    legend: { data: ["测量值", "UCL", "LCL", "CL"], textStyle: { color: textColor } },
    xAxis: { type: "category", data: points.map((_, i) => `样本${i + 1}`), axisLabel: { color: textColor }, axisLine: { lineStyle: { color: axisColor } } },
    yAxis: { type: "value", min: 14.6, max: 15.6 },
    series: [
      { name: "测量值", type: "line", data: points, itemStyle: { color: colorSet[0] } },
      { name: "UCL", type: "line", data: points.map(() => 15.45), lineStyle: { type: "dashed", color: "#f87171" }, symbol: "none" },
      { name: "LCL", type: "line", data: points.map(() => 14.75), lineStyle: { type: "dashed", color: "#f87171" }, symbol: "none" },
      { name: "CL", type: "line", data: points.map(() => 15.1), lineStyle: { type: "dotted", color: "#fbbf24" }, symbol: "none" }
    ]
  });

  makeChart("paretoChart", {
    ...baseOption(),
    legend: { data: ["缺陷数", "累计占比"], textStyle: { color: textColor } },
    xAxis: { type: "category", data: ["气泡", "边缘毛刺", "短路点", "厚度偏差", "封装缺陷"], axisLabel: { color: textColor, rotate: 20 }, axisLine: { lineStyle: { color: axisColor } } },
    yAxis: [{ type: "value", name: "件数" }, { type: "value", name: "累计%", max: 100 }],
    series: [
      { name: "缺陷数", type: "bar", data: [48, 37, 22, 18, 11], itemStyle: { color: colorSet[2] } },
      { name: "累计占比", type: "line", yAxisIndex: 1, data: [35, 62, 78, 91, 100], itemStyle: { color: colorSet[3] } }
    ]
  });

  makeChart("fpyTrendChart", {
    ...baseOption(),
    xAxis: { type: "category", data: ["1周", "2周", "3周", "4周", "5周", "6周"], axisLine: { lineStyle: { color: axisColor } }, axisLabel: { color: textColor } },
    yAxis: { type: "value", min: 92, max: 98, axisLabel: { formatter: "{value}%" } },
    series: [{ type: "line", smooth: true, areaStyle: { color: "rgba(34,211,238,0.2)" }, data: [94.5, 95.1, 95.6, 95.8, 96.0, 96.2], itemStyle: { color: colorSet[0] } }]
  });

  makeChart("complaintChart", {
    ...baseOption(),
    xAxis: { type: "category", data: ["1月", "2月", "3月", "4月", "5月", "6月"], axisLine: { lineStyle: { color: axisColor } }, axisLabel: { color: textColor } },
    yAxis: { type: "value", name: "天" },
    series: [{ type: "bar", data: [9, 8, 7, 6, 6, 5], itemStyle: { color: colorSet[4] } }]
  });

  makeChart("qualityCostChart", {
    tooltip: { trigger: "item" },
    series: [{
      type: "pie",
      radius: ["35%", "68%"],
      data: [
        { name: "预防成本", value: 26 },
        { name: "鉴定成本", value: 31 },
        { name: "内部失败成本", value: 28 },
        { name: "外部失败成本", value: 15 }
      ]
    }]
  });
}

function initEnergyCharts() {
  makeChart("energyCarbonChart", {
    ...baseOption(),
    legend: { data: ["单位能耗(kWh/kWh)", "单位碳排(kgCO2/kWh)"], textStyle: { color: textColor } },
    xAxis: { type: "category", data: ["1月", "2月", "3月", "4月", "5月", "6月"], axisLine: { lineStyle: { color: axisColor } }, axisLabel: { color: textColor } },
    yAxis: [{ type: "value" }, { type: "value" }],
    series: [
      { name: "单位能耗(kWh/kWh)", type: "line", data: [0.56, 0.54, 0.52, 0.5, 0.49, 0.47], itemStyle: { color: colorSet[1] } },
      { name: "单位碳排(kgCO2/kWh)", type: "line", yAxisIndex: 1, data: [0.31, 0.3, 0.29, 0.28, 0.27, 0.25], itemStyle: { color: colorSet[5] } }
    ]
  });

  makeChart("touLoadChart", {
    ...baseOption(),
    legend: { data: ["负荷(MW)", "电价(元/kWh)"], textStyle: { color: textColor } },
    xAxis: { type: "category", data: ["0", "4", "8", "12", "16", "20", "24"], axisLine: { lineStyle: { color: axisColor } }, axisLabel: { color: textColor } },
    yAxis: [{ type: "value" }, { type: "value" }],
    series: [
      { name: "负荷(MW)", type: "line", smooth: true, data: [52, 48, 63, 74, 70, 66, 55], itemStyle: { color: colorSet[0] } },
      { name: "电价(元/kWh)", type: "bar", yAxisIndex: 1, data: [0.42, 0.4, 0.71, 0.88, 0.92, 0.76, 0.52], itemStyle: { color: colorSet[3], opacity: 0.55 } }
    ]
  });

  makeChart("costBreakdownChart", {
    tooltip: { trigger: "item" },
    legend: { bottom: 0, textStyle: { color: textColor } },
    series: [{
      type: "pie",
      radius: "68%",
      data: [
        { name: "原材料", value: 58 },
        { name: "能源", value: 13 },
        { name: "人工", value: 9 },
        { name: "折旧", value: 12 },
        { name: "其他", value: 8 }
      ]
    }]
  });

  makeChart("savingProjectChart", {
    ...baseOption(),
    xAxis: { type: "category", data: ["余热回收", "空压优化", "峰谷移峰", "照明改造"], axisLabel: { color: textColor, rotate: 15 }, axisLine: { lineStyle: { color: axisColor } } },
    yAxis: { type: "value", name: "万元/年" },
    series: [{ type: "bar", data: [280, 160, 410, 62], itemStyle: { color: colorSet[4] } }]
  });

  makeChart("efficiencyBenchmarkChart", {
    ...baseOption(),
    xAxis: { type: "category", data: ["北京", "溧阳", "珠海", "成都"], axisLabel: { color: textColor }, axisLine: { lineStyle: { color: axisColor } } },
    yAxis: { type: "value", name: "kWh/kWh", inverse: true },
    series: [{ type: "bar", data: [0.45, 0.47, 0.5, 0.52], itemStyle: { color: colorSet[2] } }]
  });
}

function initSupplyCharts() {
  makeChart("inventoryDaysChart", {
    ...baseOption(),
    legend: { data: ["库存天数", "安全阈值"], textStyle: { color: textColor } },
    xAxis: { type: "category", data: ["锂盐", "正极", "固态电解质", "铜箔", "隔膜"], axisLabel: { color: textColor, rotate: 15 }, axisLine: { lineStyle: { color: axisColor } } },
    yAxis: { type: "value", name: "天" },
    series: [
      { name: "库存天数", type: "bar", data: [18, 22, 14, 20, 16], itemStyle: { color: colorSet[0] } },
      { name: "安全阈值", type: "line", data: [15, 15, 12, 14, 12], itemStyle: { color: colorSet[6] } }
    ]
  });

  makeChart("supplierScoreChart", {
    ...baseOption(),
    xAxis: { type: "value", min: 80, max: 100, axisLine: { lineStyle: { color: axisColor } }, axisLabel: { color: textColor } },
    yAxis: { type: "value", min: 80, max: 100, axisLine: { lineStyle: { color: axisColor } }, axisLabel: { color: textColor } },
    series: [{
      type: "scatter",
      symbolSize: (val) => val[2] / 2,
      data: [
        [96, 94, 40, "供应商A"],
        [92, 91, 30, "供应商B"],
        [88, 90, 25, "供应商C"],
        [90, 84, 22, "供应商D"],
        [85, 87, 16, "供应商E"]
      ],
      label: { show: true, formatter: (p) => p.data[3], color: textColor, position: "top" },
      itemStyle: { color: colorSet[1] }
    }]
  });

  makeChart("supplyRiskChart", {
    ...baseOption(),
    xAxis: { type: "category", data: ["地缘风险", "产能风险", "物流风险", "质量风险", "财务风险"], axisLabel: { color: textColor }, axisLine: { lineStyle: { color: axisColor } } },
    yAxis: { type: "value", max: 100 },
    series: [{ type: "bar", data: [62, 48, 55, 43, 38], itemStyle: { color: "#fb7185" } }]
  });

  makeChart("purchaseCostChart", {
    ...baseOption(),
    legend: { data: ["碳酸锂(万元/吨)", "固态电解质(万元/吨)"], textStyle: { color: textColor } },
    xAxis: { type: "category", data: ["1月", "2月", "3月", "4月", "5月", "6月"], axisLine: { lineStyle: { color: axisColor } }, axisLabel: { color: textColor } },
    yAxis: { type: "value" },
    series: [
      { name: "碳酸锂(万元/吨)", type: "line", data: [9.8, 9.4, 8.9, 8.7, 8.5, 8.2], itemStyle: { color: colorSet[3] } },
      { name: "固态电解质(万元/吨)", type: "line", data: [15.2, 15.0, 14.7, 14.3, 14.1, 13.8], itemStyle: { color: colorSet[2] } }
    ]
  });

  makeChart("collaborationChart", {
    ...baseOption(),
    xAxis: { type: "category", data: ["需求锁定", "采购下单", "生产排程", "仓配执行", "客户交付"], axisLabel: { color: textColor, rotate: 15 }, axisLine: { lineStyle: { color: axisColor } } },
    yAxis: { type: "value", max: 100, axisLabel: { formatter: "{value}%" } },
    series: [{ type: "bar", data: [95, 91, 89, 93, 96], itemStyle: { color: colorSet[4] } }]
  });
}

function initTabs() {
  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabButtons.forEach((b) => b.classList.remove("active"));
      tabPanels.forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(btn.dataset.tab).classList.add("active");
      setTimeout(() => {
        Object.values(chartMap).forEach((chart) => chart.resize());
      }, 80);
    });
  });
}

async function exportAsPng() {
  const target = document.getElementById("dashboardCapture");
  const canvas = await html2canvas(target, { backgroundColor: "#0f172a", scale: 2, useCORS: true });
  const url = canvas.toDataURL("image/png");
  const link = document.createElement("a");
  link.download = "锂电池经营驾驶舱.png";
  link.href = url;
  link.click();
}

async function exportAsPdf() {
  const target = document.getElementById("dashboardCapture");
  const canvas = await html2canvas(target, { backgroundColor: "#0f172a", scale: 2, useCORS: true });
  const imgData = canvas.toDataURL("image/png");
  const { jsPDF } = window.jspdf;
  const pdf = new jsPDF("p", "mm", "a4");
  const pageWidth = 210;
  const pageHeight = 297;
  const ratio = canvas.width / canvas.height;
  let imgWidth = pageWidth - 10;
  let imgHeight = imgWidth / ratio;
  if (imgHeight > pageHeight - 10) {
    imgHeight = pageHeight - 10;
    imgWidth = imgHeight * ratio;
  }
  pdf.addImage(imgData, "PNG", 5, 5, imgWidth, imgHeight);
  pdf.save("锂电池经营驾驶舱.pdf");
}

function bindExportButtons() {
  document.getElementById("exportPngBtn").addEventListener("click", exportAsPng);
  document.getElementById("exportPdfBtn").addEventListener("click", exportAsPdf);
}

function bootstrap() {
  initOverviewCharts();
  initProductionCharts();
  initQualityCharts();
  initEnergyCharts();
  initSupplyCharts();
  initTabs();
  bindExportButtons();
  window.addEventListener("resize", () => {
    Object.values(chartMap).forEach((chart) => chart.resize());
  });
}

bootstrap();
