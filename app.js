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
  rir_npm: { label: "NPM", unit: "dB", precision: 2, range: 30 },
  rt60_mae: { label: "RT60 MAE", unit: "ms", precision: 2, scale: 1000, range: 0.6 },
  rir_iacc_mae: { label: "IACC MAE", unit: "coefficient", precision: 3, range: 1 },
  rir_itd_mae: { label: "ITD MAE", unit: "ms", precision: 2, scale: 1000, range: 0.001 },
  rir_ild_mae: { label: "ILD MAE", unit: "dB", precision: 2, range: 10 },
  rir_ipd_mae: { label: "IPD MAE", unit: "rad", precision: 2, range: Math.PI },
};

let selectedGroup = "binaural";
let selectedSpacing = 3;
let selectedChannel = 0;
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
      const sample = data && (data.samples.find((item) => item.spacing_cm === selectedSpacing) || data.samples[0]);
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
  const height = Math.max(210, width * 0.28);
  const ratio = window.devicePixelRatio || 1;
  const plotLeft = 58;
  const plotWidth = Math.max(1, width - plotLeft - 8);
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.fillStyle = "#193c33";
  ctx.fillRect(0, 0, width, height);

  const currentEntries = entries();
  const reference = currentEntries[0]?.sample.reference_waveforms?.[selectedChannel] || [];
  const estimates = currentEntries.map((entry) => entry.sample.estimate_waveforms?.[selectedChannel] || entry.sample.waveform || []);
  const peak = Math.max.apply(null, [reference].concat(estimates).flatMap((values) => values.map((value) => Math.abs(value))).concat([1e-9]));
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

  const drawSeries = (values, color, dashed) => {
    if (!values.length) return;
    if (ctx.setLineDash) ctx.setLineDash(dashed ? [5, 4] : []);
    ctx.beginPath();
    values.forEach((value, index) => {
      const x = plotLeft + (index / Math.max(values.length - 1, 1)) * plotWidth;
      const y = height * 0.5 - (value / peak) * height * 0.44;
      index ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
    });
    ctx.strokeStyle = color;
    ctx.lineWidth = dashed ? 1.2 : 1.6;
    ctx.stroke();
    if (ctx.setLineDash) ctx.setLineDash([]);
  };

  drawSeries(reference, "#f1f3e8", true);
  estimates.forEach((values, index) => drawSeries(values, group().colors[index], false));
}

function render() {
  const currentEntries = entries();
  const reference = currentEntries[0]?.sample.reference_waveforms?.[selectedChannel] || [];
  const metrics = Array.from(new Set(currentEntries.flatMap((entry) => entry.data.metrics)));
  $("sample-id").textContent = currentEntries[0]?.sample.sample_id || "scene_0000_mic03cm";
  $("group-note").textContent = group().note;
  $("model-title").textContent = group().label + " comparison";
  $("model-note").textContent = "one reference plus " + currentEntries.length + " estimates";
  $("score-title").textContent = selectedGroup === "binaural" ? "Base + spatial metrics" : "Base metrics";
  $("channel-control").style.display = selectedGroup === "binaural" ? "flex" : "none";
  $("wave-legend").innerHTML =
    '<span class="legend-item"><i class="legend-reference"></i>Reference</span>' +
    currentEntries.map((entry, index) => '<span class="legend-item"><i style="background:' + group().colors[index] + '"></i>' + MODELS[entry.caseId] + "</span>").join("");
  $("scoreboard").innerHTML =
    '<table><thead><tr><th>Estimate</th>' +
    metrics.map((name) => "<th>" + metricMeta(name).label + "</th>").join("") +
    "</tr></thead><tbody>" +
    currentEntries
      .map((entry) => {
        return "<tr><th>" + MODELS[entry.caseId] + "</th>" +
          metrics.map((name) => "<td>" + displayMetric(name, entry.sample.scores[name]) + "</td>").join("") +
          "</tr>";
      })
      .join("") +
    "</tbody></table>";
  draw();
}

async function boot() {
  try {
    actualData = await (await fetch(dataUrl)).json();
    document.querySelector(".preview-badge").textContent = "ACTUAL REPORTS / 4 CASES";
    document.querySelector("#inspect .section-line>p").textContent = "Shared references with multiple estimate branches.";
    document.querySelector(".sample-note").textContent = "Dashed line is the reference; solid lines are estimates. Scoreboard values come from the same report sample.";
    $("spacing").innerHTML = Array.from(new Set(actualData.cases.rec_rir_single.samples.map((sample) => sample.spacing_cm)))
      .map((spacing) => '<option value="' + spacing + '">' + String(spacing).padStart(2, "0") + " cm</option>")
      .join("");
    render();
  } catch (error) {
    $("scoreboard").textContent = "Actual report data could not be loaded.";
  }
}

document.querySelectorAll("[data-group]").forEach((button) =>
  button.addEventListener("click", () => {
    document.querySelectorAll("[data-group]").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    selectedGroup = button.dataset.group;
    selectedChannel = 0;
    $("channel").value = "0";
    render();
  }),
);
$("spacing").addEventListener("change", (event) => {
  selectedSpacing = Number(event.target.value);
  render();
});
$("channel").addEventListener("change", (event) => {
  selectedChannel = Number(event.target.value);
  render();
});
window.addEventListener("resize", draw);
$("play").addEventListener("click", () => {
  const reference = entries()[0]?.sample.reference_waveforms?.[selectedChannel];
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
