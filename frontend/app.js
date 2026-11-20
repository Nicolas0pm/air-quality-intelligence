/* AIR QUALITY INTELLIGENCE — interfaz (React 18 + htm, sin compilación) */
const { useState, useEffect, useRef, useCallback } = React;
const html = htm.bind(React.createElement);

const C = { before: "#c2410c", after: "#0f766e", gray: "#94a3b8", ink: "#15232d" };
const POL = ["pm25", "pm10", "co2", "co"];
const NOM = { pm25: "PM2.5", pm10: "PM10", co2: "CO₂", co: "CO" };
const UNI = { pm25: "µg/m³", pm10: "µg/m³", co2: "ppm", co: "ppm" };
const fmt = (v, d = 1) => (v == null ? "—" : Number(v).toLocaleString("es-CO", { maximumFractionDigits: d, minimumFractionDigits: 0 }));
const fecha = (s) => new Date(s.replace(" ", "T")).toLocaleString("es-CO", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });

async function api(path, body) {
  const r = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {});
  const j = await r.json();
  if (!r.ok) throw new Error(j.error || r.statusText);
  return j;
}

Chart.defaults.font.family = "Inter, system-ui, sans-serif";
Chart.defaults.color = "#5d6f7b";
Chart.defaults.plugins.legend.labels.boxWidth = 12;

function ChartBox({ config, small }) {
  const ref = useRef(null);
  const chart = useRef(null);
  useEffect(() => {
    chart.current && chart.current.destroy();
    chart.current = new Chart(ref.current, { ...config, options: { responsive: true, maintainAspectRatio: false, animation: false, ...config.options } });
    return () => chart.current && chart.current.destroy();
  }, [JSON.stringify(config.data), JSON.stringify(config.options || {})]);
  return html`<div className=${"chart" + (small ? " sm" : "")}><canvas ref=${ref}></canvas></div>`;
}

function Nivel({ i, cat }) {
  if (i == null || !cat) return "—";
  const n = cat.niveles[i];
  return html`<span className="pill" style=${{ background: n.color }}>${n.nombre}</span>`;
}

function Medidores({ m, detalle, cat }) {
  return html`<div className="gauge">
    ${POL.map((p) => html`<div key=${p} style=${{ background: cat.niveles[detalle[p]].color }}>
      <div className="g-l">${NOM[p]}</div>
      <div className="g-v">${fmt(m[p], p === "co" ? 2 : 1)} <small style=${{ fontSize: 12 }}>${UNI[p]}</small></div>
      <div className="g-n">${cat.niveles[detalle[p]].nombre}</div>
    </div>`)}
  </div>`;
}

/* ============================== DASHBOARD ============================== */
function Dashboard({ cat }) {
  const [d, setD] = useState(null);
  const [fuente, setFuente] = useState("");
  const [dias, setDias] = useState("");
  const [pred, setPred] = useState({ pm25: 120, filtros: "PRE,HEPA" });
  const [res, setRes] = useState(null);

  const cargar = useCallback(() => {
    const qs = new URLSearchParams();
    if (fuente) qs.set("fuente", fuente);
    if (dias) qs.set("desde", new Date(Date.now() - dias * 864e5).toISOString().slice(0, 10));
    api("/api/dashboard?" + qs).then(setD);
  }, [fuente, dias]);
  useEffect(cargar, [cargar]);
  useEffect(() => { api(`/api/prediccion?pm25=${pred.pm25}&filtros=${pred.filtros}`).then(setRes).catch(() => setRes(null)); }, [pred, d]);

  if (!d) return html`<p className="muted">Cargando…</p>`;
  const k = d.kpi;
  const combos = Object.keys(d.modelos);

  return html`<div>
    <h2>Dashboard de calidad del aire</h2>
    <p className="lead">Indicadores de entrada y salida de la cámara de purificación, eficiencia por tecnología y alertas.</p>
    <div className="toolbar">
      <div><label>Fuente del aire</label>
        <select value=${fuente} onChange=${(e) => setFuente(e.target.value)}>
          <option value="">Todas</option>${d.fuentes.map((f) => html`<option key=${f}>${f}</option>`)}
        </select></div>
      <div><label>Periodo</label>
        <select value=${dias} onChange=${(e) => setDias(e.target.value)}>
          <option value="">Todo el histórico</option><option value="7">Últimos 7 días</option><option value="3">Últimos 3 días</option>
        </select></div>
      <button className="btn ghost" onClick=${cargar}>Actualizar</button>
    </div>

    <div className="grid k4 mb">
      <div className="card kpi"><div className="lab">PM2.5 material particulado</div>
        <div className="val">${fmt(k.pm25_despues)}<small>µg/m³ salida</small></div>
        <div className="det">Entrada promedio <b className="b">${fmt(k.pm25_antes)}</b> → salida <b className="a">${fmt(k.pm25_despues)}</b></div></div>
      <div className="card kpi"><div className="lab">CO₂ concentración de gases</div>
        <div className="val">${fmt(k.co2_despues, 0)}<small>ppm salida</small></div>
        <div className="det">Entrada promedio <b className="b">${fmt(k.co2_antes, 0)}</b> ppm · CO ${fmt(k.co_antes)} → ${fmt(k.co_despues)} ppm</div></div>
      <div className="card kpi"><div className="lab">% reducción de contaminantes</div>
        <div className="val">${fmt(k.red_pm25)}<small>% PM2.5</small></div>
        <div className="det">PM10 ${fmt(k.red_pm10)} % · CO ${fmt(k.red_co)} % · CO₂ ${fmt(k.red_co2)} %</div></div>
      <div className="card kpi"><div className="lab">Tiempo de purificación</div>
        <div className="val">${fmt(k.minutos)}<small>min promedio</small></div>
        <div className="det">${k.purificadas} lotes tratados de ${k.sesiones}</div></div>
      <div className="card kpi"><div className="lab">Cumplimiento</div>
        <div className="val">${fmt(k.cumplimiento)}<small>%</small></div>
        <div className="det">Lotes que salen en nivel Bueno o Aceptable</div></div>
      <div className="card kpi"><div className="lab">Alertas abiertas</div>
        <div className="val" style=${{ color: "var(--crit)" }}>${(d.alertas_cnt["CRÍTICA"] || 0) + (d.alertas_cnt["ALTA"] || 0)}<small>críticas + altas</small></div>
        <div className="det">Críticas ${d.alertas_cnt["CRÍTICA"] || 0} · Altas ${d.alertas_cnt["ALTA"] || 0} · Medias ${d.alertas_cnt["MEDIA"] || 0}</div></div>
    </div>

    <div className="grid c2 mb">
      <div className="card"><h3>Antes vs. después de la filtración (promedio)</h3>
        <${ChartBox} config=${{ type: "bar",
          data: { labels: ["PM2.5 (µg/m³)", "PM10 (µg/m³)", "CO (ppm ×10)"],
            datasets: [
              { label: "Entrada", data: [k.pm25_antes, k.pm10_antes, k.co_antes * 10], backgroundColor: C.before, borderRadius: 4 },
              { label: "Salida", data: [k.pm25_despues, k.pm10_despues, k.co_despues * 10], backgroundColor: C.after, borderRadius: 4 }] },
          options: { plugins: { legend: { position: "top" } }, scales: { y: { beginAtZero: true, grid: { color: "#eef2f4" } }, x: { grid: { display: false } } } } }} />
      </div>
      <div className="card"><h3>PM2.5 por lote: entrada y salida</h3>
        <${ChartBox} config=${{ type: "line",
          data: { labels: d.serie.map((s) => fecha(s.fecha_ingreso)),
            datasets: [
              { label: "Entrada", data: d.serie.map((s) => s.pm25_in), borderColor: C.before, backgroundColor: C.before, pointRadius: 2, tension: .25 },
              { label: "Salida", data: d.serie.map((s) => s.pm25_out), borderColor: C.after, backgroundColor: C.after, pointRadius: 2, tension: .25 },
              { label: "Límite Bueno (12)", data: d.serie.map(() => 12), borderColor: C.gray, borderDash: [5, 4], pointRadius: 0, borderWidth: 1 }] },
          options: { scales: { y: { beginAtZero: true, title: { display: true, text: "µg/m³" }, grid: { color: "#eef2f4" } }, x: { ticks: { maxTicksLimit: 8 }, grid: { display: false } } } } }} />
      </div>
    </div>

    <div className="grid c2 mb">
      <div className="card"><h3>Eficiencia por combinación de filtros (% reducción)</h3>
        <${ChartBox} config=${{ type: "bar",
          data: { labels: d.eficiencia.map((e) => e.filtros.split(",").join(" + ")),
            datasets: [
              { label: "PM2.5", data: d.eficiencia.map((e) => e.red_pm25), backgroundColor: "#0f766e" },
              { label: "CO", data: d.eficiencia.map((e) => e.red_co), backgroundColor: "#6366f1" },
              { label: "CO₂", data: d.eficiencia.map((e) => e.red_co2), backgroundColor: "#d97706" }] },
          options: { indexAxis: "y", scales: { x: { min: 0, max: 100, grid: { color: "#eef2f4" } }, y: { grid: { display: false }, ticks: { font: { size: 11 } } } } } }} />
      </div>
      <div className="card"><h3>Nivel de contaminación al ingreso</h3>
        <${ChartBox} config=${{ type: "doughnut",
          data: { labels: d.niveles.map((n) => n.nivel), datasets: [{ data: d.niveles.map((n) => n.n), backgroundColor: d.niveles.map((n) => n.color), borderWidth: 2, borderColor: "#fff" }] },
          options: { cutout: "58%", plugins: { legend: { position: "right" } } } }} />
      </div>
    </div>

    <div className="grid c3">
      <div className="card"><h3>Alertas recientes</h3>
        <div className="alerts"><ul>
          ${d.alertas.map((a) => html`<li key=${a.id}><span className=${"sev " + a.severidad}>${a.severidad}</span> ${a.mensaje}
            <div className="t">Lote #${a.sesion_id} · ${a.fuente} · ${fecha(a.fecha_hora)}</div></li>`)}
        </ul></div>
      </div>
      <div className="card"><h3>Modelo predictivo de tiempo</h3>
        <p className="muted" style=${{ marginTop: 0, fontSize: 12 }}>Ajuste exponencial C(t) = F + (C₀ − F)·e<sup>−kt</sup> sobre el histórico. Estima los minutos para bajar el PM2.5 a 12 µg/m³.</p>
        <label>PM2.5 de entrada (µg/m³)</label>
        <input type="number" value=${pred.pm25} onChange=${(e) => setPred({ ...pred, pm25: e.target.value })} />
        <label style=${{ marginTop: 10 }}>Combinación de filtros</label>
        <select value=${pred.filtros} onChange=${(e) => setPred({ ...pred, filtros: e.target.value })}>
          ${combos.map((c) => html`<option key=${c} value=${c}>${c.split(",").join(" + ")}</option>`)}
        </select>
        ${res && html`<div style=${{ marginTop: 14 }}>
          <div className="kpi"><div className="val">${res.minutos == null ? "No alcanza" : res.minutos}<small>${res.minutos == null ? "" : "min estimados"}</small></div></div>
          <div className="muted" style=${{ fontSize: 12 }}>k = ${res.k} min⁻¹ · ${res.origen} (${res.sesiones} lotes)</div></div>`}
      </div>
    </div>
  </div>`;
}

/* ============================== MÓDULO 1 ============================== */
function Monitoreo({ cat, sesion, setSesion, ir }) {
  const [fuente, setFuente] = useState(cat.fuentes[0]);
  const [manual, setManual] = useState(false);
  const [m, setM] = useState({ pm25: 85, pm10: 160, co2: 900, co: 12 });
  const [err, setErr] = useState("");
  const [cargando, setCargando] = useState(false);

  const detectar = async () => {
    setErr(""); setCargando(true);
    try { setSesion(await api("/api/sesiones", { fuente, medicion: manual ? m : null })); }
    catch (e) { setErr(e.message); } finally { setCargando(false); }
  };
  const s = sesion && sesion.estado === "INGRESADO" ? sesion : null;

  return html`<div>
    <h2>Módulo 1 · Monitoreo del aire contaminado</h2>
    <p className="lead">El sensor de entrada detecta el ingreso de aire, registra fecha y hora, mide PM2.5, PM10, CO₂ y CO y clasifica el nivel.</p>
    <div className="card mb">
      <div className="row">
        <div><label>Fuente del aire</label>
          <select value=${fuente} onChange=${(e) => setFuente(e.target.value)}>${cat.fuentes.map((f) => html`<option key=${f}>${f}</option>`)}</select></div>
        <div><label>Origen de la medición</label>
          <select value=${manual ? "m" : "s"} onChange=${(e) => setManual(e.target.value === "m")}>
            <option value="s">Sensor simulado</option><option value="m">Registro manual</option></select></div>
        <div style=${{ flex: 0 }}><button className="btn" disabled=${cargando} onClick=${detectar}>Detectar ingreso de aire</button></div>
      </div>
      ${manual && html`<div className="row" style=${{ marginTop: 12 }}>
        ${POL.map((p) => html`<div key=${p}><label>${NOM[p]} (${UNI[p]})</label>
          <input type="number" step="0.1" value=${m[p]} onChange=${(e) => setM({ ...m, [p]: e.target.value })} /></div>`)}
      </div>`}
      ${err && html`<p className="err">${err}</p>`}
    </div>

    ${s && html`<div className="card">
      <div className="row" style=${{ marginBottom: 14, alignItems: "center" }}>
        <div><h3 style=${{ margin: 0 }}>Lote #${s.id} · ${s.fuente}</h3>
          <span className="muted">Ingreso: ${new Date(s.fecha_ingreso.replace(" ", "T")).toLocaleString("es-CO")}</span></div>
        <div style=${{ flex: 0 }}>Nivel global <${Nivel} i=${s.nivel_inicial} cat=${cat} /></div>
      </div>
      <${Medidores} m=${s.entrada} detalle=${s.detalle_inicial} cat=${cat} />
      ${s.alertas.length > 0 && html`<div className="alerts" style=${{ marginTop: 12 }}><ul>
        ${s.alertas.map((a) => html`<li key=${a.id}><span className=${"sev " + a.severidad}>${a.severidad}</span> ${a.mensaje}</li>`)}</ul></div>`}
      <p style=${{ marginTop: 14 }}><b>Tecnologías recomendadas:</b> ${s.recomendados.map((r) => cat.filtros[r].nombre).join(", ")}</p>
      <button className="btn" onClick=${() => ir("proceso")}>Continuar a descontaminación →</button>
    </div>`}
  </div>`;
}

/* ============================== MÓDULO 2 ============================== */
function Proceso({ cat, sesion, setSesion, ir }) {
  const s = sesion;
  const [sel, setSel] = useState(s ? s.recomendados : []);
  const [min, setMin] = useState(20);
  const [pred, setPred] = useState(null);
  const [anim, setAnim] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => { s && s.estado === "INGRESADO" && setSel(s.recomendados); }, [s && s.id]);
  useEffect(() => {
    if (!s || !sel.length) return setPred(null);
    api(`/api/prediccion?pm25=${s.entrada.pm25}&filtros=${sel.join(",")}`).then(setPred);
  }, [sel, s && s.id]);

  if (!s) return html`<div><h2>Módulo 2 · Proceso de descontaminación</h2>
    <div className="card">Primero registre un ingreso de aire en <a href="#" onClick=${(e) => { e.preventDefault(); ir("monitoreo"); }}>Monitoreo</a>.</div></div>`;

  const iniciar = async () => {
    setErr("");
    try {
      const r = await api(`/api/sesiones/${s.id}/purificar`, { filtros: sel, minutos: min });
      const proc = r.mediciones;
      let i = 1;
      setAnim({ datos: proc.slice(0, 1), total: proc.length });
      const t = setInterval(() => {
        i++;
        setAnim({ datos: proc.slice(0, i), total: proc.length });
        if (i >= proc.length) { clearInterval(t); setSesion(r); }
      }, Math.max(40, 3000 / proc.length));
    } catch (e) { setErr(e.message); }
  };
  const toggle = (f) => setSel(sel.includes(f) ? sel.filter((x) => x !== f) : [...sel, f]);
  const datos = anim ? anim.datos : (s.estado === "PURIFICADO" ? s.mediciones : [s.entrada]);
  const actual = datos[datos.length - 1];
  const terminado = s.estado === "PURIFICADO" && (!anim || anim.datos.length === anim.total);

  return html`<div>
    <h2>Módulo 2 · Proceso de descontaminación</h2>
    <p className="lead">Lote #${s.id} (${s.fuente}). Seleccione las tecnologías según los contaminantes detectados y el tiempo de funcionamiento.</p>
    ${s.estado === "INGRESADO" && !anim && html`<div className="card mb">
      <h3>Tipo de filtro</h3>
      <div className="filters">${Object.entries(cat.filtros).map(([k, f]) => html`
        <label key=${k} className=${"filter" + (sel.includes(k) ? " on" : "")}>
          <input type="checkbox" checked=${sel.includes(k)} onChange=${() => toggle(k)} />
          <div>${s.recomendados.includes(k) && html`<div className="rec">Recomendado</div>`}<b>${f.nombre}</b><span>${f.descripcion}</span></div>
        </label>`)}</div>
      <div className="row" style=${{ marginTop: 16 }}>
        <div><label>Tiempo de funcionamiento: <b>${min} min</b></label>
          <input type="range" min="5" max="60" step="5" value=${min} onChange=${(e) => setMin(+e.target.value)} /></div>
        <div className="muted">${pred && (pred.minutos == null ? "El modelo indica que esta combinación no lleva el PM2.5 a nivel Bueno." : `El modelo estima ${pred.minutos} min para llevar el PM2.5 a 12 µg/m³.`)}</div>
        <div style=${{ flex: 0 }}><button className="btn" disabled=${!sel.length} onClick=${iniciar}>Activar purificación</button></div>
      </div>
      ${err && html`<p className="err">${err}</p>`}
    </div>`}

    <div className="card">
      <div className="row" style=${{ marginBottom: 10 }}>
        <div><h3 style=${{ margin: 0 }}>Registro durante el proceso</h3>
          <span className="muted">Minuto ${actual.minuto} · PM2.5 ${fmt(actual.pm25)} µg/m³ · PM10 ${fmt(actual.pm10)} · CO₂ ${fmt(actual.co2, 0)} ppm · CO ${fmt(actual.co, 2)} ppm</span></div>
      </div>
      ${anim && html`<div className="progress mb"><div style=${{ width: (anim.datos.length / anim.total * 100) + "%" }}></div></div>`}
      <div className="grid c2">
        <${ChartBox} config=${{ type: "line",
          data: { labels: datos.map((d) => d.minuto), datasets: [
            { label: "PM2.5", data: datos.map((d) => d.pm25), borderColor: "#0f766e", pointRadius: 0 },
            { label: "PM10", data: datos.map((d) => d.pm10), borderColor: "#c2410c", pointRadius: 0 }] },
          options: { scales: { x: { title: { display: true, text: "minuto" } }, y: { beginAtZero: true, title: { display: true, text: "µg/m³" } } } } }} />
        <${ChartBox} config=${{ type: "line",
          data: { labels: datos.map((d) => d.minuto), datasets: [
            { label: "CO₂ (ppm)", data: datos.map((d) => d.co2), borderColor: "#d97706", pointRadius: 0, yAxisID: "y" },
            { label: "CO (ppm)", data: datos.map((d) => d.co), borderColor: "#6366f1", pointRadius: 0, yAxisID: "y1" }] },
          options: { scales: { x: { title: { display: true, text: "minuto" } }, y: { position: "left", title: { display: true, text: "CO₂ ppm" } }, y1: { position: "right", beginAtZero: true, grid: { display: false }, title: { display: true, text: "CO ppm" } } } } }} />
      </div>
      ${terminado && html`<button className="btn" style=${{ marginTop: 14 }} onClick=${() => ir("validacion")}>Ver validación del aire purificado →</button>`}
    </div>
  </div>`;
}

/* ============================== MÓDULO 3 ============================== */
const COLOR_RES = { Excelente: "#15803d", Satisfactorio: "#0f766e", Parcial: "#b45309", Insuficiente: "#b91c1c" };

function Validacion({ cat, sesion, ir }) {
  const s = sesion;
  if (!s || s.estado !== "PURIFICADO") return html`<div><h2>Módulo 3 · Validación del aire purificado</h2>
    <div className="card">Aún no hay un lote purificado. <a href="#" onClick=${(e) => { e.preventDefault(); ir("monitoreo"); }}>Registrar ingreso</a></div></div>`;
  return html`<div>
    <h2>Módulo 3 · Validación del aire purificado</h2>
    <p className="lead">Lote #${s.id} · ${s.fuente} · filtros ${s.filtros.split(",").map((f) => cat.filtros[f].nombre).join(", ")} · ${s.minutos} min.</p>
    <div className="banner" style=${{ background: COLOR_RES[s.resultado] + "18", color: COLOR_RES[s.resultado], border: "1px solid " + COLOR_RES[s.resultado] + "55" }}>
      Resultado del tratamiento: ${s.resultado} — nivel de entrada ${cat.niveles[s.nivel_inicial].nombre}, nivel de salida ${cat.niveles[s.nivel_final].nombre}.
    </div>
    <div className="grid c2 mb">
      <div className="card"><h3>Comparación de valores iniciales y finales</h3>
        <table><thead><tr><th>Contaminante</th><th className="n">Entrada</th><th className="n">Salida</th><th className="n">Reducción</th><th>Nivel final</th></tr></thead>
          <tbody>${POL.map((p) => html`<tr key=${p}><td>${NOM[p]} <span className="muted">(${UNI[p]})</span></td>
            <td className="n">${fmt(s.entrada[p], 2)}</td><td className="n">${fmt(s.salida[p], 2)}</td>
            <td className="n"><b>${fmt(s.reduccion[p])} %</b></td><td><${Nivel} i=${s.detalle_final[p]} cat=${cat} /></td></tr>`)}</tbody></table>
      </div>
      <div className="card"><h3>% de reducción por contaminante</h3>
        <${ChartBox} small config=${{ type: "bar",
          data: { labels: POL.map((p) => NOM[p]), datasets: [{ label: "% reducción", data: POL.map((p) => s.reduccion[p]), backgroundColor: POL.map((p) => s.reduccion[p] >= 60 ? C.after : s.reduccion[p] >= 20 ? "#d97706" : C.gray), borderRadius: 4 }] },
          options: { plugins: { legend: { display: false } }, scales: { y: { min: 0, max: 100 } } } }} />
      </div>
    </div>
    ${s.alertas.filter((a) => a.etapa === "salida").length > 0 && html`<div className="card mb"><h3>Alertas de salida</h3><div className="alerts"><ul>
      ${s.alertas.filter((a) => a.etapa === "salida").map((a) => html`<li key=${a.id}><span className=${"sev " + a.severidad}>${a.severidad}</span> ${a.mensaje}</li>`)}</ul></div></div>`}
    <button className="btn" onClick=${() => ir("monitoreo")}>Registrar un nuevo ingreso</button>
  </div>`;
}

/* ============================== REPORTES ============================== */
function Reportes({ cat, abrir }) {
  const [rows, setRows] = useState([]);
  useEffect(() => { api("/api/sesiones").then(setRows); }, []);
  const purif = rows.filter((r) => r.estado === "PURIFICADO");
  const porFuente = {};
  purif.forEach((r) => {
    const g = porFuente[r.fuente] || (porFuente[r.fuente] = { n: 0, pin: 0, pout: 0, ok: 0 });
    g.n++; g.pin += r.pm25_in; g.pout += r.pm25_out; g.ok += r.nivel_final <= 1 ? 1 : 0;
  });
  return html`<div>
    <h2>Reportes para la toma de decisiones</h2>
    <p className="lead">Histórico de lotes con mediciones de entrada y salida. Exportable a CSV o imprimible.</p>
    <div className="toolbar"><a className="btn" href="/api/reporte.csv">Descargar CSV</a><button className="btn ghost" onClick=${() => window.print()}>Imprimir reporte</button></div>
    <div className="card mb"><h3>Resumen por fuente</h3>
      <table><thead><tr><th>Fuente</th><th className="n">Lotes</th><th className="n">PM2.5 entrada</th><th className="n">PM2.5 salida</th><th className="n">Cumplimiento</th></tr></thead>
        <tbody>${Object.entries(porFuente).map(([f, g]) => html`<tr key=${f}><td>${f}</td><td className="n">${g.n}</td>
          <td className="n">${fmt(g.pin / g.n)}</td><td className="n">${fmt(g.pout / g.n)}</td><td className="n">${fmt(g.ok / g.n * 100)} %</td></tr>`)}</tbody></table>
    </div>
    <div className="card" style=${{ overflowX: "auto" }}><h3>Detalle de lotes</h3>
      <table><thead><tr><th>#</th><th>Ingreso</th><th>Fuente</th><th>Filtros</th><th className="n">Min</th>
        <th className="n">PM2.5 in/out</th><th className="n">CO₂ in/out</th><th className="n">CO in/out</th><th>Nivel inicial</th><th>Resultado</th></tr></thead>
        <tbody>${rows.map((r) => html`<tr key=${r.id} style=${{ cursor: "pointer" }} onClick=${() => abrir(r.id)}>
          <td>${r.id}</td><td style=${{ whiteSpace: "nowrap" }}>${fecha(r.fecha_ingreso)}</td><td>${r.fuente}</td><td>${r.filtros ? r.filtros.split(",").join(" + ") : "—"}</td>
          <td className="n">${r.minutos || "—"}</td><td className="n">${fmt(r.pm25_in)} / ${fmt(r.pm25_out)}</td>
          <td className="n">${fmt(r.co2_in, 0)} / ${fmt(r.co2_out, 0)}</td><td className="n">${fmt(r.co_in, 2)} / ${fmt(r.co_out, 2)}</td>
          <td><${Nivel} i=${r.nivel_inicial} cat=${cat} /></td>
          <td>${r.resultado ? html`<b style=${{ color: COLOR_RES[r.resultado] }}>${r.resultado}</b>` : "Pendiente"}</td></tr>`)}</tbody></table>
    </div>
  </div>`;
}

/* ============================== APP ============================== */
const TABS = [["dashboard", "Dashboard"], ["monitoreo", "1 · Monitoreo"], ["proceso", "2 · Descontaminación"], ["validacion", "3 · Validación"], ["reportes", "Reportes"]];

function App() {
  // Enlace directo: #pestaña o #pestaña/idLote (p. ej. #validacion/12)
  const [hTab, hId] = location.hash.slice(1).split("/");
  const [tab, setTab] = useState(hTab || "dashboard");
  const [cat, setCat] = useState(null);
  const [sesion, setSesion] = useState(null);
  useEffect(() => {
    api("/api/catalogo").then(setCat);
    if (hId) api("/api/sesiones/" + hId).then(setSesion).catch(() => {});
  }, []);
  const ir = (t) => { setTab(t); location.hash = t; window.scrollTo(0, 0); };
  const abrir = async (id) => {
    const s = await api("/api/sesiones/" + id);
    setSesion(s); ir(s.estado === "PURIFICADO" ? "validacion" : "proceso");
  };
  if (!cat) return html`<main><p className="muted">Conectando con el servidor…</p></main>`;
  const props = { cat, sesion, setSesion, ir, abrir };
  return html`<div>
    <header>
      <div><h1>AIR QUALITY <span>INTELLIGENCE</span></h1><div className="sub">Monitoreo, descontaminación y purificación del aire</div></div>
      <nav>${TABS.map(([k, t]) => html`<button key=${k} className=${tab === k ? "on" : ""} onClick=${() => ir(k)}>${t}</button>`)}</nav>
    </header>
    <main>
      ${tab === "dashboard" && html`<${Dashboard} ...${props} />`}
      ${tab === "monitoreo" && html`<${Monitoreo} ...${props} />`}
      ${tab === "proceso" && html`<${Proceso} ...${props} />`}
      ${tab === "validacion" && html`<${Validacion} ...${props} />`}
      ${tab === "reportes" && html`<${Reportes} ...${props} />`}
    </main>
  </div>`;
}

ReactDOM.createRoot(document.getElementById("root")).render(html`<${App} />`);
