const GROUPS = {
  single: {
    label: "Monaural",
    labelZh: "单通道",
    note: "Rec-RIR and NeuBIRE estimates against one reference",
    noteZh: "Rec-RIR 与 NeuBIRE 的估计结果共用一条参考 RIR",
    cases: ["rec_rir_single", "neubire_v1_single"],
    colors: ["#d8894d", "#6b8fd6"],
  },
  binaural: {
    label: "Binaural",
    labelZh: "双通道",
    note: "Rec-RIR separate and NeuBIRE estimates against L/R reference",
    noteZh: "Rec-RIR 分路与 NeuBIRE 的估计结果对比左右通道参考 RIR",
    cases: ["rec_rir_separate", "neubire_v1_native"],
    colors: ["#d8894d", "#6b8fd6"],
  },
  four_channel: {
    label: "Four-channel",
    labelZh: "四通道",
    note: "Rec-RIR separate and NeuBIRE separate estimates against four reference channels",
    noteZh: "Rec-RIR 分路与 NeuBIRE 分路的估计结果对比四通道参考 RIR",
    cases: ["rec_rir_four_channel", "neubire_v1_four_channel"],
    colors: ["#d8894d", "#6b8fd6"],
  },
};

const MODELS = {
  rec_rir_single: "Rec-RIR",
  neubire_v1_single: "NeuBIRE",
  rec_rir_separate: "Rec-RIR separate",
  neubire_v1_native: "NeuBIRE",
  rec_rir_four_channel: "Rec-RIR separate",
  neubire_v1_four_channel: "NeuBIRE separate",
};
const MODELS_ZH = {
  rec_rir_separate: "Rec-RIR 分路",
  rec_rir_four_channel: "Rec-RIR 分路",
  neubire_v1_four_channel: "NeuBIRE 分路",
};

const METRIC_META = {
  rir_l1_mae: { label: "RIR L1 MAE", unit: "normalized", precision: 4, range: 0.1 },
  rir_npm: { label: "NPM", unit: "dB", precision: 2, range: 30 },
  rt60_1s_mae: { label: "RT60 MAE", unit: "ms", precision: 2, scale: 1000, range: 0.6 },
  drr_1s_mae: { label: "DRR MAE", unit: "dB", precision: 2, range: 10 },
  c50_1s_mae: { label: "C50 MAE", unit: "dB", precision: 2, range: 10 },
  edc_1s_mae: { label: "EDC MAE", unit: "dB", precision: 2, range: 20 },
  iacc_full_1s_mae: { label: "IACC full", labelZh: "IACC 全段", unit: "coefficient", precision: 3, range: 1 },
  iacc_early_1s_mae: { label: "IACC early", labelZh: "IACC 早期", unit: "coefficient", precision: 3, range: 1 },
  iacc_late_1s_mae: { label: "IACC late", labelZh: "IACC 晚期", unit: "coefficient", precision: 3, range: 1 },
  itd_1s_mae: { label: "ITD", unit: "ms", precision: 3, range: 5 },
  ild_1s_mae: { label: "ILD", unit: "dB", precision: 2, range: 20 },
  ipd_1s_mae: { label: "IPD", unit: "rad", precision: 3, range: 3.2 },
  rt30_mae: { label: "RT30 MAE", unit: "s", precision: 3, range: 0.6 },
  rt60_mae: { label: "RT60 MAE", unit: "s", precision: 3, range: 0.6 },
  rir_drr_mae: { label: "DRR MAE", unit: "dB", precision: 2, range: 10 },
  rir_c50_mae: { label: "C50 MAE", unit: "dB", precision: 2, range: 10 },
  rir_c80_mae: { label: "C80 MAE", unit: "dB", precision: 2, range: 10 },
  rir_edc_mae: { label: "EDC MAE", unit: "dB", precision: 2, range: 20 },
  rir_iacc_mae: { label: "IACC MAE", unit: "coefficient", precision: 3, range: 1 },
  rir_iacc_full_mae: { label: "IACC full MAE", labelZh: "IACC 全段 MAE", unit: "coefficient", precision: 3, range: 1 },
  rir_iacc_early_mae: { label: "IACC early MAE", labelZh: "IACC 早期 MAE", unit: "coefficient", precision: 3, range: 1 },
  rir_iacc_late_mae: { label: "IACC late MAE", labelZh: "IACC 晚期 MAE", unit: "coefficient", precision: 3, range: 1 },
  rir_itd_mae: { label: "ITD MAE", unit: "ms", precision: 3, range: 5 },
  rir_ild_mae: { label: "ILD MAE", unit: "dB", precision: 2, range: 20 },
  rir_ipd_mae: { label: "IPD MAE", unit: "rad", precision: 3, range: 3.2 },
  rir_doa_mae: { label: "DOA MAE", unit: "degrees", precision: 2, range: 90 },
};
const CHANNEL_PAIR_METRICS = new Set(["rir_itd_mae", "rir_ild_mae", "rir_ipd_mae", "rir_doa_mae"]);

const initialQuery = new URLSearchParams(window.location.search);
let selectedGroup = Object.prototype.hasOwnProperty.call(GROUPS, initialQuery.get("group"))
  ? initialQuery.get("group") : "single";
let selectedSnr = Number(initialQuery.get("snr")) || 10;
let selectedSpacing = Number(initialQuery.get("spacing")) || 3;
let selectedScene = initialQuery.get("scene") || "scene_0000";
let actualData = null;
let frequencyData = null;
let audioSource = null;
const $ = (id) => document.getElementById(id);
const IS_ZH = new URLSearchParams(window.location.search).get("lang") === "zh";
const localize = (english, chinese) => IS_ZH ? chinese : english;
const modelLabel = (caseId) => IS_ZH ? (MODELS_ZH[caseId] || MODELS[caseId]) : MODELS[caseId];

function applyStaticLocale() {
  document.documentElement.lang = IS_ZH ? "zh-CN" : "en";
  document.querySelectorAll(".language-switch a").forEach((link) => {
    if (link.dataset.language === (IS_ZH ? "zh" : "en")) link.setAttribute("aria-current", "page");
    link.addEventListener("click", () => {
      const destination = new URL(link.href);
      destination.hash = window.location.hash;
      destination.searchParams.set("group", selectedGroup);
      destination.searchParams.set("snr", selectedSnr);
      destination.searchParams.set("spacing", selectedSpacing);
      destination.searchParams.set("scene", selectedScene);
      link.href = destination.href;
    });
  });
  if (!IS_ZH) return;

  document.title = "RIR / SURE 评测示例";
  document.querySelector('meta[name="description"]').content = "SURE RIR 通道感知评测示例";
  const copy = {
    ".wordmark em": "RIR 示例",
    '.header nav a[href="#inspect"]': "结果",
    '.header nav a[href="#frequency"]': "频段",
    '.header nav a[href="#rules"]': "规则",
    '.header nav a[href="#reproduce"]': "复现",
    '.header nav a[href^="https://github.com/Yj-Xiong/sure-rir_estimation-example"]': "仓库 ↗",
    ".preview-badge": "网页预览",
    ".hero .kicker": "通道感知评测 / 001",
    ".hero h1 span": "结果可追溯。",
    ".hero .hero-copy": "SURE RIR 估计任务的评测示例。对比单通道、双通道和四通道结果，并查看相同参考 RIR 下的逐通道指标。",
    ".hero-specs div:nth-child(1) span": "测试样本",
    ".hero-specs div:nth-child(1) small": "信噪比 × 样本对 × 间距",
    ".hero-specs div:nth-child(2) span": "采样率",
    ".hero-specs div:nth-child(2) small": "固定信噪比与四麦克风数据集",
    ".hero-specs div:nth-child(3) span": "指标",
    ".hero-specs div:nth-child(3) strong": "声学 + 空间",
    "#coverage-title": "一条评测链路，多种使用路径",
    ".coverage .section-line>p": "统一的报告格式用于比较单通道与多通道模型的不同输出路径。",
    ".coverage-intro .mini-label": "评测覆盖范围",
    ".coverage-intro h3": "跨分支评测",
    ".coverage-intro p": "每个分支均计算基础 RIR 指标；输出具有有效通道对时，再计算空间指标。",
    ".coverage-head span:nth-child(1)": "模型类型",
    ".coverage-head span:nth-child(2)": "单通道使用",
    ".coverage-head span:nth-child(3)": "多通道使用",
    ".coverage-row:nth-child(2) strong": "单通道",
    ".coverage-row:nth-child(2) span:nth-child(3) em": "基础指标 + 适用的空间指标",
    ".coverage-row:nth-child(3) strong": "多通道",
    ".coverage-row:nth-child(3) span:nth-child(2) em": "相同的基础指标口径",
    ".coverage-row:nth-child(3) span:nth-child(3) em": "各通道相对 ch0 评分；通道对误差取平均",
    "#inspect .section-line h2": "对比结果分支",
    "#inspect .section-line>p": "每个分支使用相同参考 RIR，对比多个估计结果。",
    '.result-tabs button[data-group="single"] small': "Rec-RIR · NeuBIRE",
    '.result-tabs button[data-group="binaural"] small': "Rec-RIR 分路 · NeuBIRE",
    '.result-tabs button[data-group="four_channel"] small': "Rec-RIR 分路 · NeuBIRE 分路",
    ".wave-card .mini-label": "估计 / 参考波形叠加",
    "#play": "播放参考波形",
    "#model-title": "单通道结果对比",
    "#model-note": "一组参考与两个估计结果",
    ".score-card .mini-label": "评分表",
    "#score-title": "声学指标",
    ".score-direction": "越低越好",
    ".sample-note": "虚线为参考 RIR，实线为所选分支的估计 RIR。",
    "#frequency .section-line h2": "分频段声学指标误差",
    "#frequency .section-line>p": "归一化 RIR 经频段滤波后计算 RT60、C50 和 EDC 误差。",
    ".frequency-head p": "标记为误差中位数；浅色区间表示第 25 至 75 百分位。",
    "#rules .section-line h2": "评测规则",
    "#rules .section-line>p": "统一 JSONL 格式，按通道数使用对应指标。",
    ".rule-grid article:nth-child(1) h3": "基础 RIR 质量",
    ".rule-grid article:nth-child(1) p": "先计算每个通道分支的 NPM、RT30、RT60 和 EDC，再添加空间指标。",
    ".rule-grid article:nth-child(2) h3": "空间指标汇总",
    ".rule-grid article:nth-child(2) p": "IACC 仅用于双通道，分别计算全段、早期和晚期窗口。ITD、ILD、IPD 和 DOA 逐一比较 chN 与 ch0，再对通道对误差取平均。",
    ".rule-grid article:nth-child(3) h3": "数据来源",
    ".rule-grid article:nth-child(3) p": "参考 RIR 不进入模型输入。报告保留评测链路、节点 ID 和逐通道对结果。",
    "#reproduce .section-line h2": "复现页面全部结果",
    "#reproduce .section-line>p": "6 个场景 · 每场景 60 条 · 推理、评分、汇总",
    ".repro-intro>p": "按以下流程重新生成上方四个单/双通道场景和两个四通道场景：从两份 manifest 选样，在集群运行两类模型，评估 360 条模型结果，并汇总页面数据及分频段误差。",
    ".repro-links a:nth-child(1)": "完整六场景复现教程 ↗",
    ".repro-links a:nth-child(2)": "NeuBIRE 四通道说明 ↗",
    ".repro-links a:nth-child(3)": "Rec-RIR 源码 ↗",
    ".repro-links a:nth-child(4)": "Rec-RIR 论文 ↗",
    ".repro-links a:nth-child(5)": "示例仓库 ↗",
    ".repro-links a:nth-child(6)": "指标覆盖",
    ".repro-links a:nth-child(7)": "四麦样本选择",
    ".repro-links a:nth-child(8)": "旧数据集样本选择",
    ".repro-links a:nth-child(9)": "数据来源",
    ".repro-steps li:nth-child(1) h3": "准备源码和样本选择",
    ".repro-steps li:nth-child(1) .repro-step-head span": "旧数据集 60 条 + 四麦数据集 60 条",
    ".repro-steps li:nth-child(1) p a": "复现教程",
    ".repro-steps li:nth-child(2) h3": "运行四个单/双通道场景",
    ".repro-steps li:nth-child(2) .repro-step-head span": "Rec-RIR 与 NeuBIRE · 4090 队列",
    ".repro-steps li:nth-child(2) p": "运行脚本生成四份各 60 条的 manifest 和 RIR WAV。NeuBIRE 单通道结果取原生双通道估计的 ch0，与页面展示的波形一致。",
    ".repro-steps li:nth-child(3) h3": "运行两个四通道场景",
    ".repro-steps li:nth-child(3) .repro-step-head span": "Rec-RIR 与 NeuBIRE · 4090 队列",
    ".repro-steps li:nth-child(3) p": "Rec-RIR 逐通道运行；NeuBIRE 分两组双通道运行。两者均以同一直达峰裁剪锚点合并四条输出路径。",
    ".repro-steps li:nth-child(4) h3": "评估并汇总全部六个场景",
    ".repro-steps li:nth-child(4) .repro-step-head span": "360 条模型结果 · CPU 队列",
    ".repro-steps li:nth-child(4) p": "四个单/双通道场景使用已发布的 Rec-BIR/FiNS 一秒评测协议，两个四通道场景使用固定版本的 SURE RIR 指标集合。CPU 任务汇总候选 JSON，并从完整 RIR WAV 计算分频段误差。",
    ".repro-steps li:nth-child(5) h3": "验证候选数据",
    ".repro-steps li:nth-child(5) .repro-step-head span": "六个场景 · 每场景 60 条",
    ".repro-steps li:nth-child(5) p": "评分任务在完成前检查分支 ID、样本顺序、指标均值、波形形状、有限分数以及原始 WAV 的频段数据。",
    ".repro-steps li:nth-child(6) h3": "检查并发布",
    ".repro-steps li:nth-child(6) .repro-step-head span": "页面数据 · 频段分布",
    ".repro-steps li:nth-child(6) p": "比较新结果与仓库中的页面数据，审核数值变化后再一起发布两份 JSON。",
    "footer span": "SURE / RIR 评测示例",
    "footer a:nth-of-type(1)": "NeuBIRE 复现说明 ↗",
    "footer a:nth-of-type(2)": "Rec-RIR 源码 ↗",
    "footer a:nth-of-type(3)": "示例仓库 ↗",
    "footer a:nth-of-type(4)": "SURE Harness ↗",
  };
  Object.entries(copy).forEach(([selector, value]) => {
    const element = document.querySelector(selector);
    if (element) element.textContent = value;
  });
  const leading = {
    ".hero h1": "RIR 评分，",
    ".coverage-row:nth-child(2) span:nth-child(2)": "直接评估通道 0",
    ".coverage-row:nth-child(2) span:nth-child(3)": "逐通道推理并合并为目标通道数",
    ".coverage-row:nth-child(3) span:nth-child(2)": "通道 0 投影",
    ".coverage-row:nth-child(3) span:nth-child(3)": "原生多通道输出",
    '.result-tabs button[data-group="single"] strong': "单通道",
    '.result-tabs button[data-group="binaural"] strong': "双通道",
    '.result-tabs button[data-group="four_channel"] strong': "四通道",
    ".repro-steps li:nth-child(1) p": "使用固定版本的评测引擎、已有 Rec-BIR 模型与检查点，以及两份测试 manifest。请在 CPU 资源中准备依赖；完整前置条件见",
  };
  Object.entries(leading).forEach(([selector, value]) => {
    const node = document.querySelector(selector)?.firstChild;
    if (node?.nodeType === 3) node.nodeValue = value;
  });
  $("spacing").parentElement.firstChild.nodeValue = "间距 ";
  $("sample").parentElement.firstChild.nodeValue = "样本 ";
  document.querySelector(".status").lastChild.nodeValue = " 报告数据";
  document.querySelector(".repro-steps li:nth-child(1) p").lastChild.nodeValue = "。";
  $("wave").setAttribute("aria-label", "估计与参考 RIR 波形");
  $("band-chart").setAttribute("aria-label", "分频段声学指标误差");
  document.querySelector(".coverage-table").setAttribute("aria-label", "RIR 评测的通道覆盖范围");
}

applyStaticLocale();
const dataScript = document.querySelector("script[data-rir-app]");
const dataUrl = dataScript ? new URL("data/results.json", dataScript.src).href : "data/results.json";
const frequencyUrl = dataScript ? new URL("data/frequency_error.json", dataScript.src).href : "data/frequency_error.json";
const group = () => GROUPS[selectedGroup];
const entries = () =>
  group().cases
    .map((caseId) => {
      const data = actualData && actualData.cases && actualData.cases[caseId];
      const sample = data && (data.samples.find((item) => item.snr_db === selectedSnr && item.spacing_cm === selectedSpacing && item.scene_id === selectedScene) || data.samples.find((item) => item.snr_db === selectedSnr && item.spacing_cm === selectedSpacing) || data.samples[0]);
      return { caseId, data, sample };
    })
    .filter((entry) => entry.data && entry.sample);

function metricMeta(name) {
  return METRIC_META[name] || { label: name, unit: "score", precision: 2, range: 1 };
}

function metricLabel(name) {
  const meta = metricMeta(name);
  return IS_ZH ? (meta.labelZh || meta.label) : meta.label;
}

function unitLabel(unit) {
  if (!IS_ZH) return unit;
  return { normalized: "归一化", coefficient: "系数", degrees: "度", score: "分" }[unit] || unit;
}

function displayMetric(name, value) {
  if (value === null || value === undefined || !Number.isFinite(value)) return "--";
  const meta = metricMeta(name);
  return (value * (meta.scale || 1)).toFixed(meta.precision) + " " + unitLabel(meta.unit);
}

function metricBasis(name, sample) {
  if (CHANNEL_PAIR_METRICS.has(name) && sample.estimate_waveforms?.length > 2) {
    return localize("mean of ch1/ch0 … ch", "ch1/ch0 至 ch") +
      (sample.estimate_waveforms.length - 1) + localize("/ch0 pairs", "/ch0 通道对误差的平均值");
  }
  if (name === "rir_iacc_full_mae") return localize("full RIR window", "完整 RIR 窗口");
  if (name === "rir_iacc_early_mae") return localize("ch0 direct peak–80 ms", "ch0 直达峰至 80 ms");
  if (name === "rir_iacc_late_mae") return localize("after ch0 direct peak +80 ms", "ch0 直达峰后 80 ms 起");
  return referenceBasis(name, sample);
}

function referenceBasis(name, sample) {
  const ref = sample.reference_metrics || {};
  const pred = sample.prediction_metrics || {};
  const scalarMap = {
    rt60_1s_mae: ["rt60_1s", "s", 1000],
    drr_1s_mae: ["drr_1s", "dB", 1],
    c50_1s_mae: ["c50_1s", "dB", 1],
    iacc_full_1s_mae: ["iacc_full_1s", "", 1],
    iacc_early_1s_mae: ["iacc_early_1s", "", 1],
    iacc_late_1s_mae: ["iacc_late_1s", "", 1],
    itd_1s_mae: ["itd_1s_ms", "ms", 1],
    ild_1s_mae: ["ild_1s_db", "dB", 1],
    ipd_1s_mae: ["ipd_1s_rad", "rad", 1],
  };
  const mapping = scalarMap[name];
  if (!mapping || !Number.isFinite(ref[mapping[0]]) || !Number.isFinite(pred[mapping[0]])) {
    if (name === "rir_npm") return localize("lag-invariant pair", "延迟不变的通道对");
    if (name === "rir_l1_mae") return localize("normalized traces", "归一化波形");
    if (name === "edc_1s_mae") return localize("decay curves", "能量衰减曲线");
    return localize("reference / estimate recorded", "已记录参考值 / 估计值");
  }
  const [, unit, scale] = mapping;
  const precision = unit === "ms" ? 3 : unit === "dB" ? 2 : 3;
  return localize("ref ", "参考 ") + (ref[mapping[0]] * scale).toFixed(precision) + (unit ? " " + unit : "") +
    localize(" / pred ", " / 估计 ") + (pred[mapping[0]] * scale).toFixed(precision) + (unit ? " " + unit : "");
}

function formatAmplitude(value) {
  if (value === 0) return "0";
  return Math.abs(value) >= 0.001 ? value.toFixed(4) : value.toExponential(2);
}

function renderFrequencyBands() {
  const container = $("band-chart");
  if (!container || !frequencyData) return;
  const cases = group().cases;
  const metrics = frequencyData.metrics || [{ id: "spectrum", label: localize("Band error", "频段误差"), unit: "dB" }];
  container.innerHTML = metrics.map((metric) => {
    const values = cases.flatMap((caseId) => frequencyData.cases[caseId]?.bands ? Object.values(frequencyData.cases[caseId].bands).map((item) => (item[metric.id]?.p75 ?? item.p75_db ?? 0)) : []);
    const maxValue = Math.max(...values, 1e-6);
    const rows = frequencyData.bands.map((band, index) => {
      const bars = cases.map((caseId, caseIndex) => {
        const bandData = frequencyData.cases[caseId]?.bands?.[String(index)];
        const item = bandData?.[metric.id] || bandData;
        const median = item?.median ?? item?.median_db;
        const p25 = item?.p25 ?? item?.p25_db;
        const p75 = item?.p75 ?? item?.p75_db;
        if (!item || median === null || median === undefined) return "";
        const left = Math.max(0, (p25 / maxValue) * 100);
        const width = Math.max(1, ((p75 - p25) / maxValue) * 100);
        const marker = Math.min(100, Math.max(0, (median / maxValue) * 100));
        return '<div class="band-series"><span class="band-name">' + modelLabel(caseId) + '</span><div class="band-track"><i style="left:' + left + '%;width:' + width + '%;background:' + group().colors[caseIndex] + '"></i><b style="left:' + marker + '%;background:' + group().colors[caseIndex] + '"></b></div><em>' + median.toFixed(metric.unit === "s" ? 3 : 2) + ' ' + metric.unit + '</em></div>';
      }).join("");
      return '<div class="band-row"><strong>' + band.label + '</strong><div class="band-values">' + bars + '</div></div>';
    }).join("");
    return '<div class="band-metric"><h3>' + metric.label + ' <small>' + metric.unit + '</small></h3>' + rows + '</div>';
  }).join("");
}

function draw() {
  const canvas = $("wave");
  const ctx = canvas.getContext("2d");
  const width = canvas.clientWidth || 1200;
  const channelCount = selectedGroup === "four_channel" ? 4 : (selectedGroup === "binaural" ? 2 : 1);
  const rowHeight = Math.max(170, width * 0.19);
  const rowGap = channelCount === 2 ? 24 : 0;
  const height = rowHeight * channelCount + rowGap;
  const ratio = window.devicePixelRatio || 1;
  const plotLeft = 58;
  const plotWidth = Math.max(1, width - plotLeft - 8);
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.fillStyle = "#193c33";
  ctx.fillRect(0, 0, width, height);

  const currentEntries = entries();
  const drawSeries = (values, color, dashed, top, plotHeight, scale) => {
    if (!values.length) return;
    if (ctx.setLineDash) ctx.setLineDash(dashed ? [5, 4] : []);
    ctx.beginPath();
    values.forEach((value, index) => {
      const x = plotLeft + (index / Math.max(values.length - 1, 1)) * plotWidth;
      const y = top + plotHeight * 0.5 - (value / scale) * plotHeight * 0.42;
      index ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
    });
    ctx.strokeStyle = color;
    ctx.lineWidth = dashed ? 1.2 : 1.6;
    ctx.stroke();
    if (ctx.setLineDash) ctx.setLineDash([]);
  };

  for (let channel = 0; channel < channelCount; channel += 1) {
    const top = channel * (rowHeight + rowGap);
    const reference = currentEntries[0]?.sample.reference_waveforms?.[channel] || [];
    const estimates = currentEntries.map((entry) => entry.sample.estimate_waveforms?.[channel] || entry.sample.waveform || []);
    const observedPeak = Math.max(
      ...[reference].concat(estimates).flatMap((values) => values.map((value) => Math.abs(value))),
      1e-6,
    );
    const axisPeak = observedPeak * 1.1;
    ctx.fillStyle = "#193c33";
    ctx.fillRect(0, top, width, rowHeight);
    ctx.strokeStyle = "#315a49";
    ctx.lineWidth = 1;
    for (let index = 0; index <= 4; index += 1) {
      const y = top + (rowHeight * index) / 4;
      ctx.beginPath();
      ctx.moveTo(plotLeft, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }
    ctx.fillStyle = "#b8c9bd";
    ctx.font = "11px system-ui";
    ctx.textAlign = "right";
    ctx.fillText("+" + formatAmplitude(axisPeak), plotLeft - 7, top + 12);
    ctx.fillText("0", plotLeft - 7, top + rowHeight / 2 + 4);
    ctx.fillText("-" + formatAmplitude(axisPeak), plotLeft - 7, top + rowHeight - 4);
    ctx.textAlign = "left";
    ctx.font = "10px var(--mono), monospace";
    const channelLabel = selectedGroup === "four_channel"
      ? localize("channel ", "通道 ") + channel
      : (channel === 0 ? localize("L / channel 0", "左 / 通道 0") : localize("R / channel 1", "右 / 通道 1"));
    ctx.fillText(channelLabel, plotLeft + 8, top + 14);
    drawSeries(reference, "#f1f3e8", true, top, rowHeight, axisPeak);
    estimates.forEach((values, index) => drawSeries(values, group().colors[index], false, top, rowHeight, axisPeak));
  }
}

function render() {
  const currentEntries = entries();
  const metrics = Array.from(new Set(currentEntries.flatMap((entry) => entry.data.metrics)));
  const selectedSample = currentEntries[0]?.sample;
  $("sample-id").textContent = selectedSample ? selectedSample.sample_id + " / " + selectedSample.snr_db + " dB" : "scene_0000_mic03cm";
  $("group-note").textContent = localize(group().note, group().noteZh);
  $("model-title").textContent = localize(group().label + " comparison", group().labelZh + "结果对比");
  $("model-note").textContent = localize("one reference plus ", "一组参考 RIR 与 ") + currentEntries.length + localize(" estimates", " 组估计结果");
  $("score-title").textContent = selectedGroup === "single"
    ? localize("Acoustic metrics", "声学指标")
    : localize("Acoustic + spatial metrics", "声学 + 空间指标");
  $("wave-legend").innerHTML =
    '<span class="legend-item"><i class="legend-reference"></i>' + localize("Reference", "参考 RIR") + "</span>" +
    currentEntries.map((entry, index) => '<span class="legend-item"><i style="background:' + group().colors[index] + '"></i>' + modelLabel(entry.caseId) + "</span>").join("");
  const bestValues = Object.fromEntries(metrics.map((name) => {
    const values = currentEntries.map((entry) => entry.sample.scores[name]).filter((value) => Number.isFinite(value));
    return [name, values.length ? Math.min(...values) : null];
  }));
  $("scoreboard").innerHTML = currentEntries
    .map((entry) => {
      return '<div class="scoreboard-row"><strong>' + modelLabel(entry.caseId) + '</strong><div class="scoreboard-metrics">' +
        metrics.map((name) => {
          const value = entry.sample.scores[name];
          const best = Number.isFinite(value) && value === bestValues[name];
          return '<span class="' + (best ? 'best' : '') + '"><b>' + metricLabel(name) + '</b><em>' + displayMetric(name, value) + '</em><small>' + metricBasis(name, entry.sample) + '</small></span>';
        }).join("") +
        "</div></div>";
    })
    .join("");
  draw();
  renderFrequencyBands();
}

function groupSamples() {
  const firstCase = group().cases[0];
  return actualData.cases[firstCase]?.samples || [];
}

function updateSpacingOptions() {
  const spacings = Array.from(new Set(groupSamples().map((sample) => sample.spacing_cm))).sort((left, right) => left - right);
  $("spacing").innerHTML = spacings
    .map((spacing) => '<option value="' + spacing + '">' + String(spacing).padStart(2, "0") + " cm</option>")
    .join("");
  if (!spacings.includes(selectedSpacing)) selectedSpacing = spacings[0];
  $("spacing").value = selectedSpacing;
}

async function boot() {
  try {
    [actualData, frequencyData] = await Promise.all([
      fetch(dataUrl).then((response) => response.json()),
      fetch(frequencyUrl).then((response) => response.json()),
    ]);
    document.querySelector(".preview-badge").textContent = localize("gpuRIR / 60 SAMPLES", "gpuRIR / 60 条样本");
    document.querySelector("#inspect .section-line>p").textContent = localize(
      "Shared references with multiple direct RIR estimate branches.",
      "多条直达 RIR 估计分支共用参考 RIR。",
    );
    document.querySelector(".sample-note").textContent = localize(
      "Dashed line is the reference; solid lines are estimates. Both channels share the same sample and scoreboard values use the same report row.",
      "虚线为参考 RIR，实线为估计 RIR。各通道使用同一条样本，评分表取自同一报告行。",
    );
    document.querySelectorAll("[data-group]").forEach((button) =>
      button.classList.toggle("active", button.dataset.group === selectedGroup));
    updateSnrOptions();
    updateSpacingOptions();
    updateSampleOptions();
    render();
  } catch (error) {
    $("scoreboard").textContent = localize("Actual report data could not be loaded.", "无法加载实际评测报告数据。");
  }
}

function updateSampleOptions() {
  const samples = groupSamples().filter((sample) => sample.snr_db === selectedSnr && sample.spacing_cm === selectedSpacing);
  $("sample").innerHTML = samples
    .map((sample) => '<option value="' + sample.scene_id + '">' + sample.scene_id + " / " + sample.sample_id + "</option>")
    .join("");
  if (!samples.some((sample) => sample.scene_id === selectedScene)) selectedScene = samples[0]?.scene_id || "scene_0000";
  $("sample").value = selectedScene;
}

function updateSnrOptions() {
  const snrs = Array.from(new Set(actualData.cases.rec_rir_single.samples.map((sample) => sample.snr_db))).sort((left, right) => left - right);
  $("snr").innerHTML = snrs
    .map((snr) => '<option value="' + snr + '">' + snr + " dB</option>")
    .join("");
  if (!snrs.includes(selectedSnr)) selectedSnr = snrs[0] || 10;
  $("snr").value = selectedSnr;
}

document.querySelectorAll("[data-group]").forEach((button) =>
  button.addEventListener("click", () => {
    document.querySelectorAll("[data-group]").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    selectedGroup = button.dataset.group;
    updateSpacingOptions();
    updateSampleOptions();
    render();
  }),
);
$("spacing").addEventListener("change", (event) => {
  selectedSpacing = Number(event.target.value);
  updateSampleOptions();
  render();
});
$("snr").addEventListener("change", (event) => {
  selectedSnr = Number(event.target.value);
  updateSampleOptions();
  render();
});
$("sample").addEventListener("change", (event) => {
  selectedScene = event.target.value;
  render();
});
window.addEventListener("resize", draw);
$("play").addEventListener("click", () => {
  const reference = entries()[0]?.sample.reference_waveforms?.[0];
  if (!reference) return;
  if (audioSource) {
    audioSource.stop();
    audioSource = null;
    $("play").textContent = localize("Play reference", "播放参考波形");
    return;
  }
  const context = new AudioContext();
  const buffer = context.createBuffer(1, context.sampleRate, context.sampleRate);
  const data = buffer.getChannelData(0);
  for (let index = 0; index < data.length; index += 1) {
    data[index] = reference[Math.min(reference.length - 1, Math.floor((index / data.length) * reference.length))] * 0.5;
  }
  audioSource = context.createBufferSource();
  audioSource.buffer = buffer;
  audioSource.connect(context.destination);
  audioSource.start();
  $("play").textContent = localize("Stop", "停止");
  audioSource.onended = () => {
    audioSource = null;
    $("play").textContent = localize("Play reference", "播放参考波形");
  };
});
boot();
