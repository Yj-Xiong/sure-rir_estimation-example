const GROUPS = {
  single: {
    label: "Single-channel",
    note: "Rec-RIR and NeuBIRE v1 estimates against one reference",
    cases: ["rec_rir_single", "neubire_v1_single"],
    colors: ["#d8894d", "#6b8fd6"],
  },
  binaural: {
    label: "Binaural",
    note: "Rec-RIR separate and NeuBIRE native estimates against L/R reference",
    cases: ["rec_rir_separate", "neubire_v1_native"],
    colors: ["#d8894d", "#6b8fd6"],
  },
};

const MODELS = {
  rec_rir_single: "Rec-RIR",
  neubire_v1_single: "NeuBIRE v1",
  rec_rir_separate: "Rec-RIR separate",
  neubire_v1_native: "NeuBIRE v1 native",
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
  interchannel_delay_1s_mae: { label: "ITD", unit: "samples", precision: 2, range: 64 },
};

let selectedGroup = "binaural";
let selectedSnr = 10;
let selectedSpacing = 3;
let selectedScene = "scene_0000";
let actualData = null;
let audioSource = null;
const $ = (id) => document.getElementById(id);
const dataScript = document.querySelector('script[src$="app.js"]');
const dataUrl = dataScript ? new URL("data/results.json", dataScript.src).href : "data/results.json";
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

function formatAmplitude(value) {
  if (value === 0) return "0";
  return Math.abs(value) >= 0.001 ? value.toFixed(4) : value.toExponential(2);
}

function draw() {
  const canvas = $("wave");
  const ctx = canvas.getContext("2d");
  const width = canvas.clientWidth || 1200;
  const channelCount = selectedGroup === "binaural" ? 2 : 1;
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
  const drawSeries = (values, color, dashed, top, plotHeight) => {
    if (!values.length) return;
    if (ctx.setLineDash) ctx.setLineDash(dashed ? [5, 4] : []);
    ctx.beginPath();
    values.forEach((value, index) => {
      const x = plotLeft + (index / Math.max(values.length - 1, 1)) * plotWidth;
      const y = top + plotHeight * 0.5 - value * plotHeight * 0.42;
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
    ctx.fillText("+1.0", plotLeft - 7, top + 12);
    ctx.fillText("0", plotLeft - 7, top + rowHeight / 2 + 4);
    ctx.fillText("-1.0", plotLeft - 7, top + rowHeight - 4);
    ctx.textAlign = "left";
    ctx.font = "10px var(--mono), monospace";
    ctx.fillText(channel === 0 ? "L / channel 0" : "R / channel 1", plotLeft + 8, top + 14);
    drawSeries(reference, "#f1f3e8", true, top, rowHeight);
    estimates.forEach((values, index) => drawSeries(values, group().colors[index], false, top, rowHeight));
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
  $("score-title").textContent = selectedGroup === "binaural" ? "Base + spatial metrics" : "Base metrics";
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
          return '<span class="' + (best ? 'best' : '') + '"><b>' + metricMeta(name).label + '</b><em>' + displayMetric(name, value) + '</em></span>';
        }).join("") +
        "</div></div>";
    })
    .join("");
  draw();
}

async function boot() {
  try {
    actualData = await (await fetch(dataUrl)).json();
    document.querySelector(".preview-badge").textContent = "REC-BIR DIRECT RIR / 60 SAMPLES";
    document.querySelector("#inspect .section-line>p").textContent = "Shared references with multiple direct RIR estimate branches.";
    document.querySelector(".sample-note").textContent = "Dashed line is the reference; solid lines are estimates. Both channels share the same sample and scoreboard values use the same report row.";
    updateSnrOptions();
    $("spacing").innerHTML = Array.from(new Set(actualData.cases.rec_rir_single.samples.map((sample) => sample.spacing_cm)))
      .map((spacing) => '<option value="' + spacing + '">' + String(spacing).padStart(2, "0") + " cm</option>")
      .join("");
    updateSampleOptions();
    render();
  } catch (error) {
    $("scoreboard").textContent = "Actual report data could not be loaded.";
  }
}

function updateSampleOptions() {
  const samples = actualData.cases.rec_rir_single.samples.filter((sample) => sample.snr_db === selectedSnr && sample.spacing_cm === selectedSpacing);
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
