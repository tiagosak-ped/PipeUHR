"""Aplicação web (Flask) do PipeUHR.

Fornece:
- ``/``        : página de entrada de dados (Tailwind CSS + DaisyUI).
- ``/solve``   : recebe o formulário, configura o modelo, chama o solver
				 (``GlobalOptimization.solve``) e o simulador de restrições,
				 e renderiza a página de resultados.

Os parâmetros editáveis são atributos do modelo ``GlobalOptimization``,
agrupados por categoria. Cada parâmetro é aplicado por instância (override)
e as áreas dos reservatórios são recalculadas.

Executar:
	py webapp/app.py
e acessar http://127.0.0.1:5000
"""

from __future__ import annotations

import datetime
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

# Garante que o pacote ``pipeuhr`` (na raiz do projeto) seja importável.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request

from pipeuhr import (
	ConstraintSimulator,
	DiverseSegment,
	DiverseSegmentKind,
	GlobalOptimization,
	HydraulicCircuit,
	PipeMaterial,
	PipeSegment,
	PipeType,
	SegmentPosition,
)

app = Flask(__name__)

TEMPLATES_DIR = Path(__file__).parent / "data" / "templates"
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)


def _slugify(name: str) -> str:
	"""Converte um nome livre em um slug seguro para uso como nome de arquivo."""
	normalized = unicodedata.normalize("NFKD", name)
	ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
	slug = re.sub(r"[^\w\s-]", "", ascii_name).strip().lower()
	return re.sub(r"[\s_-]+", "-", slug) or "template"


# ---------------------------------------------------------------------------
# Filtro Jinja2 para formatação numérica pt-BR (vírgula decimal, ponto milhar)
# Uso no template: {{ value|fmt_br(1) }} → "6.176,7"
# ---------------------------------------------------------------------------
def fmt_br(value, decimals=2):
	"""Formata um número no padrão brasileiro: ponto como separador de milhar,
	vírgula como separador decimal. Ex.: 1000.85 → '1.000,85'."""
	if value is None:
		return ""
	formatted = f"{value:,.{decimals}f}"
	# Swap separators: comma→@, dot→comma, @→dot
	formatted = formatted.replace(",", "@").replace(".", ",").replace("@", ".")
	return formatted


def fmt_br_signed(value, decimals=4):
	"""Igual a fmt_br, mas preserva sinal explícito (+/-)."""
	if value is None:
		return ""
	formatted = f"{value:+,.{decimals}f}"
	formatted = formatted.replace(",", "@").replace(".", ",").replace("@", ".")
	return formatted


app.jinja_env.filters["fmt_br"] = fmt_br
app.jinja_env.filters["fmt_br_signed"] = fmt_br_signed


# ---------------------------------------------------------------------------
# Metadados dos campos do formulário: (atributo, rótulo, unidade, passo).
# Agrupados por seção para renderização em accordion no template.
# ---------------------------------------------------------------------------
FIELD_GROUPS = [
	("Reservatórios", [
		("VOL_SUP_HM3", "Volume reservatório superior", "hm³", "0.1"),
		("VOL_INF_HM3", "Volume reservatório inferior", "hm³", "0.1"),
		("H_MED_SUP", "Altura média reservatório superior", "m", "0.1"),
		("H_MED_INF", "Altura média reservatório inferior", "m", "0.1"),
	]),
	("Operação", [
		("FLOW_TURBINE", "Vazão de turbinamento", "m³/s", "0.1"),
		("EFF_TURBINE", "Rendimento da turbina", "-", "0.01"),
		("EFF_PUMP", "Rendimento da bomba", "-", "0.01"),
		("N_MACHINES", "Quantidade de máquinas", "un", "1"),
		("HOURS_OFF", "Horas fora de operação/dia", "h", "0.5"),
	]),
	("Cotas (m)", [
		("COTA_TERRENO_SUP", "Cota terreno superior", "m", "0.1"),
		("COTA_TERRENO_INF", "Cota terreno inferior", "m", "0.1"),
		("COTA_POWERHOUSE", "Cota casa de força", "m", "0.1"),
		("BORDA_LIVRE", "Borda livre", "m", "0.1"),
	]),
	("Custos unitários", [
		("COST_LOW_PRESSURE", "Circuito baixa pressão", "MR$/km·m²", "0.0001"),
		("COST_HIGH_PRESSURE", "Circuito alta pressão", "MR$/km·m²", "0.0001"),
	]),
	("Cavitação", [
		("PATM_MCA", "Pressão atmosférica", "mca", "0.1"),
		("HVAPOR_MCA", "Pressão de vapor", "mca", "0.001"),
		("PUMP_SPEED_RPM", "Rotação nominal da bomba", "rpm", "0.1"),
	]),
	("Restrições", [
		("DAM_HEIGHT_MAX", "Altura máxima das barragens", "m", "1"),
		("POWER_MIN_PER_MACHINE", "Potência mínima por máquina", "MW", "1"),
		("RATIO_MAX", "Relação Pturb/Pbomb máxima", "-", "0.01"),
		("RATIO_MIN", "Relação Pturb/Pbomb mínima", "-", "0.01"),
		("HOURS_TURB_MIN", "Horas mínimas de turbinamento/dia", "h", "0.5"),
		("V_MAX_CONCRETE", "Velocidade máx. concreto", "m/s", "0.1"),
		("V_MAX_STEEL", "Velocidade máx. aço", "m/s", "0.1"),
		("V_MIN", "Velocidade mínima", "m/s", "0.1"),
		("HEAD_LOSS_MAX_FRAC", "Perda de carga máxima", "frac", "0.001"),
		("NPSH_SAFETY_FACTOR", "Fator de segurança NPSH", "-", "0.01"),
	]),
]

_INT_FIELDS = {"N_MACHINES"}


# ---------------------------------------------------------------------------
# Segmentos: serialização / desserialização para o formulário
# ---------------------------------------------------------------------------

def default_segments_json() -> str:
	"""Retorna o JSON dos segmentos padrão para o formulário."""
	circuit = HydraulicCircuit.default_circuit()
	segments = []
	for seg in circuit.segments:
		if isinstance(seg, PipeSegment):
			segments.append({
				"type": "pipe",
				"name": seg.name,
				"length": seg.length,
				"slope": seg.slope,
				"material": seg.material.value,
				"pipe_type": seg.pipe_type.value,
				"position": seg.position.value,
			})
		elif isinstance(seg, DiverseSegment):
			segments.append({
				"type": "diverse",
				"name": seg.name,
				"kind": seg.kind.value,
				"position": seg.position.value,
				"diameter": seg.diameter,
				"angle": seg.angle,
			})
	return json.dumps(segments, ensure_ascii=False)


def _parse_segments_json(raw: str) -> HydraulicCircuit:
	"""Constrói um HydraulicCircuit a partir do JSON do formulário."""
	data = json.loads(raw)
	segments = []
	for item in data:
		if item["type"] == "pipe":
			segments.append(PipeSegment(
				name=item["name"],
				length=float(item["length"]),
				slope=float(item["slope"]),
				material=PipeMaterial(item["material"]),
				pipe_type=PipeType(item["pipe_type"]),
				position=SegmentPosition(item["position"]),
			))
		elif item["type"] == "diverse":
			segments.append(DiverseSegment(
				name=item["name"],
				kind=DiverseSegmentKind(item["kind"]),
				position=SegmentPosition(item["position"]),
				diameter=float(item["diameter"]) if item.get("diameter") else None,
				angle=float(item["angle"]) if item.get("angle") else None,
			))
	return HydraulicCircuit(segments)


# ---------------------------------------------------------------------------
# Helpers para o formulário
# ---------------------------------------------------------------------------

def default_values() -> dict:
	"""Valores padrão de cada parâmetro lidos da classe do modelo."""
	values = {}
	for _, fields in FIELD_GROUPS:
		for attr, *_ in fields:
			values[attr] = getattr(GlobalOptimization, attr)
	return values


def build_model(form) -> GlobalOptimization:
	"""Cria o modelo aplicando os overrides enviados pelo formulário."""
	# Segmentos
	raw_segments = form.get("segments_json", "")
	if raw_segments:
		circuit = _parse_segments_json(raw_segments)
	else:
		circuit = HydraulicCircuit.default_circuit()

	model = GlobalOptimization(circuit=circuit)
	for _, fields in FIELD_GROUPS:
		for attr, *_ in fields:
			raw = form.get(attr)
			if raw is None or raw == "":
				continue
			raw = raw.strip().replace(",", ".")  # tolera vírgula decimal
			value = int(float(raw)) if attr in _INT_FIELDS else float(raw)
			setattr(model, attr, value)
	# Recalcula as áreas dos reservatórios com os novos volumes/alturas.
	model.area_sup = model.VOL_SUP_HM3 * 1e6 / model.H_MED_SUP
	model.area_inf = model.VOL_INF_HM3 * 1e6 / model.H_MED_INF
	return model


# ---------------------------------------------------------------------------
# Esquema gráfico da UHR (modal em result.html)
# Combina a geometria de configuração (comprimento/inclinação/ângulo) com os
# SegmentState calculados (diâmetro/área/velocidade/perda/cota), na mesma
# ordem de avaliação do circuito, e consolida as cotas de referência.
# ---------------------------------------------------------------------------

def build_scheme_payload(model: GlobalOptimization, state) -> tuple[list, dict]:
	"""Monta ``(segments, levels)`` para o desenho do circuito hidráulico.

	``evaluation_order()`` e ``state.segment_states`` são gerados na mesma
	sequência (tomada d'água → ANTES → DEPOIS → tomada d'água), portanto são
	combinados por índice. ``length``/``slope``/``angle``/``kind`` vêm das
	dataclasses de configuração; os demais campos, do ``SegmentState``.
	"""
	order = model.circuit.evaluation_order()
	segments: list[dict] = []
	for entry, ss in zip(order, state.segment_states):
		cfg = entry.get("segment")
		is_pipe_cfg = isinstance(cfg, PipeSegment)
		is_diverse_cfg = isinstance(cfg, DiverseSegment)
		segments.append({
			"name": ss.name,
			"segment_type": ss.segment_type,
			"position": ss.position.value,
			"material": ss.material,
			"is_pipe": ss.is_pipe,
			"pipe_type": ss.pipe_type,
			"diameter": ss.diameter,
			"area": ss.area,
			"velocity": ss.velocity,
			"head_loss": ss.head_loss,
			"cota": ss.cota,
			"length": cfg.length if is_pipe_cfg else None,
			"slope": cfg.slope if is_pipe_cfg else None,
			"angle": cfg.angle if is_diverse_cfg else None,
			"kind": cfg.kind.value if is_diverse_cfg else None,
		})

	levels = {
		"cota_max_sup": state.cota_max_sup,
		"cota_min_sup": state.cota_min_sup,
		"cota_tomada": state.cota_tomada,
		"cota_max_inf": state.cota_max_inf,
		"cota_min_inf": state.cota_min_inf,
		"cota_e": state.cota_e,
		"cota_powerhouse": model.COTA_POWERHOUSE,
	}
	return segments, levels


# ---------------------------------------------------------------------------
# Rotas de templates
# ---------------------------------------------------------------------------

@app.route("/templates/list")
def templates_list():
	"""Retorna a lista de templates salvos como JSON."""
	items = []
	for path in sorted(TEMPLATES_DIR.glob("*.json")):
		try:
			data = json.loads(path.read_text(encoding="utf-8"))
			items.append({"file": path.stem, "name": data.get("name", path.stem)})
		except Exception:
			pass
	return app.response_class(
		json.dumps(items, ensure_ascii=False),
		mimetype="application/json",
	)


@app.route("/templates/save", methods=["POST"])
def templates_save():
	"""Salva os dados do formulário como um template JSON nomeado."""
	body = request.get_json(force=True)
	name = (body.get("name") or "template").strip()
	slug = _slugify(name)
	payload = {
		"name": name,
		"saved_at": datetime.datetime.now().isoformat(timespec="seconds"),
		"params": body.get("params", {}),
		"segments": body.get("segments", []),
	}
	(TEMPLATES_DIR / f"{slug}.json").write_text(
		json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
	)
	return app.response_class(
		json.dumps({"ok": True, "file": slug}),
		mimetype="application/json",
	)


@app.route("/templates/load/<slug>")
def templates_load(slug):
	"""Carrega um template salvo pelo seu slug."""
	path = TEMPLATES_DIR / f"{slug}.json"
	if not path.exists():
		return app.response_class(
			json.dumps({"error": "not found"}),
			status=404,
			mimetype="application/json",
		)
	return app.response_class(
		path.read_text(encoding="utf-8"),
		mimetype="application/json",
	)


@app.route("/")
def index():
	return render_template("index.html",
						   groups=FIELD_GROUPS,
						   values=default_values(),
						   segments_json=default_segments_json())


@app.route("/solve", methods=["POST"])
def solve():
	model = build_model(request.form)
	result = model.solve()
	report = ConstraintSimulator(model).simulate(result)

	costs = [
		("C1 — Barragem superior", result.state.cost_dam_sup),
		("C2 — Barragem inferior", result.state.cost_dam_inf),
		("C3 — Casa de força", result.state.cost_powerhouse),
		("C4 — Circuito baixa pressão", result.state.cost_low_pressure),
		("C5 — Circuito alta pressão", result.state.cost_high_pressure),
	]

	# Variáveis de decisão dinâmicas
	decision = [
		("Altura barragem superior (h1)", result.state.h1, "m"),
		("Altura barragem inferior (h2)", result.state.h2, "m"),
	]
	for i, ps in enumerate(result.state.pipe_states()):
		decision.append((f"Diâmetro {ps.name}", ps.diameter, "m"))
	decision.append(("Horas de bombeamento/dia", result.state.hours_pump, "h"))

	# Esquema gráfico (modal): geometria dos segmentos + cotas de referência
	scheme_segments, scheme_levels = build_scheme_payload(model, result.state)

	return render_template("result.html",
						   result=result,
						   state=result.state,
						   report=report,
						   costs=costs,
						   decision=decision,
						   scheme_segments_json=json.dumps(
							   scheme_segments, ensure_ascii=False),
						   scheme_levels_json=json.dumps(scheme_levels))


if __name__ == "__main__":
	app.run(host="127.0.0.1", port=5000, debug=True)
