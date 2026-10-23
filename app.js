const GROUPS = {
  single: {
    label: "Monaural",
    note: "Rec-RIR and NeuBIRE estimates against one reference",
    cases: ["rec_rir_single", "neubire_v1_single"],
    colors: ["#d8894d", "#6b8fd6"],
  },
  binaural: {
    label: "Binaural",
    note: "Rec-RIR separate and NeuBIRE estimates against L/R reference",
    cases: ["rec_rir_separate", "neubire_v1_native"],
    colors: ["#d8894d", "#6b8fd6"],
  },
  four_channel: {
    label: "Four-channel",
    note: "Rec-RIR and NeuBIRE estimates against four reference channels",
    cases: ["rec_rir_four_channel", "neubire_v1_four_channel"],
    colors: ["#d8894d", "#6b8fd6"],
  },
};

const MODELS = {
  rec_rir_single: "Rec-RIR",
  neubire_v1_single: "NeuBIRE",
  rec_rir_separate: "Rec-RIR separate",
  neubire_v1_native: "NeuBIRE",
  rec_rir_four_channel: "Rec-RIR",
  neubire_v1_four_channel: "NeuBIRE",
};

const METRIC_META = {
  rir_l1_mae: { label: "RIR L1 MAE", unit: "normalized", precision: 4, range: 0.1 },
  rir_npm: { label: "NPM", unit: "dB", precision: 2, range: 30 },
  rt60_1s_mae: { label: "RT60 MAE", unit: "ms", precision: 2, scale: 1000, range: 0.6 },
  drr_1s_mae: { label: "DRR MAE", unit: "dB", precision: 2, range: 10 },
  c50_1s_mae: { label: "C50 MAE", unit: "dB", precision: 2, range: 10 },
  edc_1s_mae: { label: "EDC MAE", unit: "dB", precision: 2, range: 20 },
  iacc_full_1s_mae: { label: "IACC full", unit: "coefficient", precision: 3, range: 1 },
  iacc_early_1s_mae: { label: "IACC early", unit: "coefficient", precision: 3, range: 1 },
  iacc_late_1s_mae: { label: "IACC late", unit: "coefficient", precision: 3, range: 1 },
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
  rir_iacc_full_mae: { label: "IACC full MAE", unit: "coefficient", precision: 3, range: 1 },
  rir_iacc_early_mae: { label: "IACC early MAE", unit: "coefficient", precision: 3, range: 1 },
  rir_iacc_late_mae: { label: "IACC late MAE", unit: "coefficient", precision: 3, range: 1 },
  rir_itd_mae: { label: "ITD MAE", unit: "ms", precision: 3, range: 5 },
  rir_ild_mae: { label: "ILD MAE", unit: "dB", precision: 2, range: 20 },
  rir_ipd_mae: { label: "IPD MAE", unit: "rad", precision: 3, range: 3.2 },
  rir_doa_mae: { label: "DOA MAE", unit: "degrees", precision: 2, range: 90 },
};
const CHANNEL_PAIR_METRICS = new Set(["rir_itd_mae", "rir_ild_mae", "rir_ipd_mae", "rir_doa_mae"]);

let selectedGroup = "binaural";
let selectedSnr = 10;
let selectedSpacing = 3;
let selectedScene = "scene_0000";
let actualData = null;
let frequencyData = null;
let audioSource = null;
const $ = (id) => document.getElementById(id);
const dataScript = document.querySelector('script[src$="app.js"]');
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

function displayMetric(name, value) {
  if (value === null || value === undefined || !Number.isFinite(value)) return "--";
  const meta = metricMeta(name);
  return (value * (meta.scale || 1)).toFixed(meta.precision) + " " + meta.unit;
}

function metricBasis(name, sample) {
  if (CHANNEL_PAIR_METRICS.has(name) && sample.estimate_waveforms?.length > 2) {
    return "mean of ch1/ch0 … ch" + (sample.estimate_waveforms.length - 1) + "/ch0 pairs";
  }
  if (name === "rir_iacc_full_mae") return "full RIR window";
  if (name === "rir_iacc_early_mae") return "ch0 direct peak–80 ms";
  if (name === "rir_iacc_late_mae") return "after ch0 direct peak +80 ms";
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
    if (name === "rir_npm") return "lag-invariant pair";
    if (name === "rir_l1_mae") return "normalized traces";
    if (name === "edc_1s_mae") return "decay curves";
    return "reference / estimate recorded";
  }
  const [, unit, scale] = mapping;
  const precision = unit === "ms" ? 3 : unit === "dB" ? 2 : 3;
  return "ref " + (ref[mapping[0]] * scale).toFixed(precision) + (unit ? " " + unit : "") +
    " / pred " + (pred[mapping[0]] * scale).toFixed(precision) + (unit ? " " + unit : "");
}

function formatAmplitude(value) {
  if (value === 0) return "0";
  return Math.abs(value) >= 0.001 ? value.toFixed(4) : value.toExponential(2);
}

function renderFrequencyBands() {
  const container = $("band-chart");
  if (!container || !frequencyData) return;
  const cases = group().cases;
  const metrics = frequencyData.metrics || [{ id: "spectrum", label: "Band error", unit: "dB" }];
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
        return '<div class="band-series"><span class="band-name">' + MODELS[caseId] + '</span><div class="band-track"><i style="left:' + left + '%;width:' + width + '%;background:' + group().colors[caseIndex] + '"></i><b style="left:' + marker + '%;background:' + group().colors[caseIndex] + '"></b></div><em>' + median.toFixed(metric.unit === "s" ? 3 : 2) + ' ' + metric.unit + '</em></div>';
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
      ? "channel " + channel
      : (channel === 0 ? "L / channel 0" : "R / channel 1");
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
  $("group-note").textContent = group().note;
  $("model-title").textContent = group().label + " comparison";
  $("model-note").textContent = "one reference plus " + currentEntries.length + " estimates";
  $("score-title").textContent = selectedGroup === "single" ? "Acoustic metrics" : "Acoustic + spatial metrics";
  $("wave-legend").innerHTML =
    '<span class="legend-item"><i class="legend-reference"></i>Reference</span>' +
    currentEntries.map((entry, index) => '<span class="legend-item"><i style="background:' + group().colors[index] + '"></i>' + MODELS[entry.caseId] + "</span>").join("");
  const bestValues = Object.fromEntries(metrics.map((name) => {
    const values = currentEntries.map((entry) => entry.sample.scores[name]).filter((value) => Number.isFinite(value));
    return [name, values.length ? Math.min(...values) : null];
  }));
  $("scoreboard").innerHTML = currentEntries
    .map((entry) => {
      return '<div class="scoreboard-row"><strong>' + MODELS[entry.caseId] + '</strong><div class="scoreboard-metrics">' +
        metrics.map((name) => {
          const value = entry.sample.scores[name];
          const best = Number.isFinite(value) && value === bestValues[name];
          return '<span class="' + (best ? 'best' : '') + '"><b>' + metricMeta(name).label + '</b><em>' + displayMetric(name, value) + '</em><small>' + metricBasis(name, entry.sample) + '</small></span>';
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
    document.querySelector(".preview-badge").textContent = "gpuRIR / 60 SAMPLES";
    document.querySelector("#inspect .section-line>p").textContent = "Shared references with multiple direct RIR estimate branches.";
    document.querySelector(".sample-note").textContent = "Dashed line is the reference; solid lines are estimates. Both channels share the same sample and scoreboard values use the same report row.";
    updateSnrOptions();
    updateSpacingOptions();
    updateSampleOptions();
    render();
  } catch (error) {
    $("scoreboard").textContent = "Actual report data could not be loaded.";
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
    $("play").textContent = "Play reference";
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
  $("play").textContent = "Stop";
  audioSource.onended = () => {
    audioSource = null;
    $("play").textContent = "Play reference";
  };
});
boot();
