const MODELS = {
  "rec-rir": { name: "Rec-RIR", mode: "single-channel", note: "actual SURE report; channel 0", caseId: "rec_rir_single" },
  "neubire-single": { name: "NeuBIRE v1", mode: "single-channel", note: "channel 0 duplicated to both inputs", caseId: "neubire_v1_single" },
  "rec-rir-separate": { name: "Rec-RIR separate", mode: "multi-channel", note: "independent L / R passes merged", caseId: "rec_rir_separate" },
  "neubire-mint": { name: "NeuBIRE v1 native", mode: "multi-channel", note: "native two-channel BIR output", caseId: "neubire_v1_native" },
};

const METRIC_META = {
  rir_npm: { label: "NPM", unit: "dB", precision: 2, range: 30 },
  rt60_mae: { label: "RT60 MAE", unit: "ms", precision: 2, scale: 1000, range: 0.6 },
  rir_iacc_mae: { label: "IACC MAE", unit: "coefficient", precision: 3, range: 1 },
  rir_itd_mae: { label: "ITD MAE", unit: "ms", precision: 2, scale: 1000, range: 0.001 },
  rir_ild_mae: { label: "ILD MAE", unit: "dB", precision: 2, range: 10 },
  rir_ipd_mae: { label: "IPD MAE", unit: "rad", precision: 2, range: Math.PI },
  rir_doa_mae: { label: "DOA MAE", unit: "deg", precision: 2, range: 90 },
  rir_drr_mae: { label: "DRR MAE", unit: "dB", precision: 2, range: 10 },
  rir_c50_mae: { label: "C50 MAE", unit: "dB", precision: 2, range: 10 },
  rir_c80_mae: { label: "C80 MAE", unit: "dB", precision: 2, range: 10 },
};

let selectedModel = "neubire-mint";
let selectedSpacing = 3;
let actualData = null;
let audioSource = null;
const $ = (id) => document.getElementById(id);
const model = () => MODELS[selectedModel];
const caseData = () => actualData && actualData.cases && actualData.cases[model().caseId];
const selectedSample = () => {
  const data = caseData();
  return data && (data.samples.find((sample) => sample.spacing_cm === selectedSpacing) || data.samples[0]);
};
const dataScript = document.querySelector('script[src$="app.js"]');
const dataUrl = dataScript ? new URL("data/results.json", dataScript.src).href : "data/results.json";

function metricMeta(name) {
  return METRIC_META[name] || { label: name, unit: "score", precision: 2, range: 1 };
}

function displayMetric(name, value) {
  if (value === null || value === undefined || !Number.isFinite(value)) return "--";
  const meta = metricMeta(name);
  return (value * (meta.scale || 1)).toFixed(meta.precision) + " " + meta.unit;
}

function scoreWidth(name, value) {
  if (!Number.isFinite(value)) return 8;
  const range = metricMeta(name).range;
  return Math.max(8, 100 - Math.min((Math.abs(value) / range) * 100, 92));
}

function formatAmplitude(value) {
  if (value === 0) return "0";
  return Math.abs(value) >= 0.001 ? value.toFixed(4) : value.toExponential(2);
}

function draw() {
  const canvas = $("wave");
  const ctx = canvas.getContext("2d");
  const width = canvas.clientWidth || 1200;
  const height = Math.max(210, width * 0.28);
  const ratio = window.devicePixelRatio || 1;
  const plotLeft = 58;
  const plotWidth = Math.max(1, width - plotLeft - 8);
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.fillStyle = "#193c33";
  ctx.fillRect(0, 0, width, height);

  const sample = selectedSample();
  const values = (sample && sample.waveform) || [];
  const peak = Math.max.apply(null, values.map((value) => Math.abs(value)).concat([1e-9]));
  ctx.strokeStyle = "#315a49";
  ctx.lineWidth = 1;
  for (let index = 0; index <= 4; index += 1) {
    const y = (height * index) / 4;
    ctx.beginPath();
    ctx.moveTo(plotLeft, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }
  ctx.fillStyle = "#b8c9bd";
  ctx.font = "11px system-ui";
  ctx.textAlign = "right";
  ctx.fillText("+" + formatAmplitude(peak), plotLeft - 7, 12);
  ctx.fillText("0", plotLeft - 7, height / 2 + 4);
  ctx.fillText("-" + formatAmplitude(peak), plotLeft - 7, height - 4);

  if (!values.length) {
    ctx.textAlign = "left";
    ctx.fillText("No report available", plotLeft + 12, height / 2);
    return;
  }
  ctx.beginPath();
  values.forEach((value, index) => {
    const x = plotLeft + (index / Math.max(values.length - 1, 1)) * plotWidth;
    const y = height * 0.5 - (value / peak) * height * 0.44;
    index ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
  });
  ctx.strokeStyle = "#d5ed9a";
  ctx.lineWidth = 1.6;
  ctx.stroke();
}

function render() {
  const currentModel = model();
  const data = caseData();
  const sample = selectedSample();
  $("sample-id").textContent =
    (sample && sample.sample_id) || "scene_0000_mic" + String(selectedSpacing).padStart(2, "0") + "cm";
  $("model-title").textContent = currentModel.name + " / " + currentModel.mode;
  $("model-note").textContent = currentModel.note;
  const metrics = (data && data.metrics) || [];
  const values = (sample && sample.scores) || {};
  $("bars").innerHTML = metrics
    .map((name) => {
      const meta = metricMeta(name);
      const value = values[name];
      return '<div class="score-row"><div><strong>' + meta.label + "</strong><small>actual report · " + meta.unit + '</small></div><div class="track"><i style="width:' + scoreWidth(name, value) + '%"></i></div><div class="score-value">' + displayMetric(name, value) + "</div></div>";
    })
    .join("");
  $("play").disabled = !sample;
  $("play").textContent = sample ? "Play RIR shape" : "Unavailable";
  draw();
}

async function boot() {
  try {
    actualData = await (await fetch(dataUrl)).json();
    document.querySelector(".preview-badge").textContent = "ACTUAL REPORTS / 4 CASES";
    document.querySelector("#inspect .section-line>p").textContent = "Loaded from four actual SURE report cases.";
    document.querySelector(".sample-note").textContent = "Scores and waveform shape are loaded from actual SURE reports; no synthetic score is generated.";
    $("spacing").innerHTML = Array.from(new Set(actualData.cases.rec_rir_single.samples.map((sample) => sample.spacing_cm)))
      .map((spacing) => '<option value="' + spacing + '">' + String(spacing).padStart(2, "0") + " cm</option>")
      .join("");
    render();
  } catch (error) {
    $("bars").textContent = "Actual report data could not be loaded.";
  }
}

$("spacing").addEventListener("change", (event) => {
  selectedSpacing = Number(event.target.value);
  render();
});
document.querySelectorAll("[data-model]").forEach((button) =>
  button.addEventListener("click", () => {
    document.querySelectorAll("[data-model]").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    selectedModel = button.dataset.model;
    render();
  }),
);
window.addEventListener("resize", draw);
$("play").addEventListener("click", () => {
  const sample = selectedSample();
  if (!sample) return;
  if (audioSource) {
    audioSource.stop();
    audioSource = null;
    $("play").textContent = "Play RIR shape";
    return;
  }
  const context = new AudioContext();
  const buffer = context.createBuffer(1, context.sampleRate, context.sampleRate);
  const data = buffer.getChannelData(0);
  const wave = sample.waveform;
  for (let index = 0; index < data.length; index += 1) {
    data[index] = wave[Math.min(wave.length - 1, Math.floor((index / data.length) * wave.length))] * 0.5;
  }
  audioSource = context.createBufferSource();
  audioSource.buffer = buffer;
  audioSource.connect(context.destination);
  audioSource.start();
  $("play").textContent = "Stop";
  audioSource.onended = () => {
    audioSource = null;
    $("play").textContent = "Play RIR shape";
  };
});
boot();
