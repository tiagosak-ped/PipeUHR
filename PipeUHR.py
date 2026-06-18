"""PipeUHR — migração da planilha ``Planilha Chris.xlsm`` para Python.

Ponto de entrada que orquestra a solução, dividida em uma classe por aba
da planilha original (pacote ``pipeuhr``):

	aba ``aux``                       -> AuxData
	aba ``resistencia materiais``     -> MaterialStrength
	aba ``Turbinas Reversíveis``      -> ReversibleTurbines
	aba ``Hbarragem Custo...``        -> DamCostModel        (regressão grau 4)
	aba ``Potencia Custo equip...``   -> EquipmentCostModel  (regressão grau 2)
	aba ``Seleção de turbina``        -> TurbineSelection
	aba ``otimiz global``             -> GlobalOptimization  (Solver -> SLSQP)
	aba ``desenho``                   -> Drawing

O problema de otimização do Excel (Solver) é resolvido com
``scipy.optimize.minimize`` (SLSQP): minimizar o custo total da UHR
sujeito às restrições de velocidade, perda de carga, pressão nos
materiais, cavitação (NPSH), relação Pturb/Pbomb e potência mínima.
"""

from __future__ import annotations

from pipeuhr import (
	AuxData,
	ConstraintSimulator,
	DamCostModel,
	Drawing,
	EquipmentCostModel,
	GlobalOptimization,
	MaterialStrength,
	ReversibleTurbines,
	TurbineSelection,
)


def _print_header(title: str) -> None:
	print("\n" + "=" * 64)
	print(title)
	print("=" * 64)


def main() -> None:
	# --- Dados de referência (abas aux / resistencia / turbinas) ---
	_print_header("Dados de referência")
	materials = MaterialStrength()
	print(f"Resistência concreto (ponto C): "
		  f"{materials.concrete_strength_kgf_m2:,.0f} Kgf/m²")
	print(f"Resistência aço (ponto D):      "
		  f"{materials.steel_strength_kgf_m2:,.0f} Kgf/m²")
	print(f"Gravidade: {AuxData.GRAVITY} m/s²  |  "
		  f"Peso específico água: {AuxData.WATER_DENSITY} Kgf/m³")

	turbines = ReversibleTurbines()
	print(f"Relação média Pturb/Pbomb (UHRs reais): "
		  f"{turbines.average_ratio:.4f}")

	# --- Regressões de custo (Solver -> numpy.polyfit) ---
	_print_header("Regressões de custo (mínimos quadrados)")
	dam_cost = DamCostModel(refit=True)
	equip_cost = EquipmentCostModel(refit=True)
	print("Custo barragem  C(H) = a0 + a1·H + a2·H² + a3·H³ + a4·H⁴")
	print(f"  coeficientes a0..a4 = "
		  f"{', '.join(f'{c:.6g}' for c in dam_cost.coeffs)}")
	print(f"  soma dos quadrados (resíduo) = {dam_cost.sum_squared_error():,.2f}")
	print("Custo equipamento C(P) = a0 + a1·P + a2·P²")
	print(f"  coeficientes a0..a2 = "
		  f"{', '.join(f'{c:.6g}' for c in equip_cost.coeffs)}")
	print(f"  soma dos quadrados (resíduo) = {equip_cost.sum_squared_error():,.2f}")

	# --- Otimização global (Solver -> SLSQP) ---
	_print_header("Otimização global do custo da UHR (SLSQP)")
	model = GlobalOptimization(dam_cost=dam_cost,
							   equipment_cost=equip_cost,
							   material_strength=materials)
	result = model.solve()
	st = result.state

	print(f"Convergência: {result.success}  ({result.message})")
	print(f"Iterações: {result.iterations}")
	print("\nVariáveis de decisão otimizadas:")
	print(f"  Altura barragem superior  h1 = {st.h1:8.3f} m")
	print(f"  Altura barragem inferior  h2 = {st.h2:8.3f} m")
	for ps in st.pipe_states():
		print(f"  Diâmetro {ps.name:<20s} D  = {ps.diameter:8.3f} m")
	print(f"  Horas de bombeamento/dia     = {st.hours_pump:8.3f} h")

	print("\nVelocidades (m/s):")
	for ps in st.pipe_states():
		print(f"  {ps.name} = {ps.velocity:.3f}", end="  |  ")
	print()

	print("\nPerda de carga (m):")
	print(f"  recalque = {st.head_loss_recalque:.3f}  |  "
		  f"sucção = {st.head_loss_suction:.3f}  |  "
		  f"total = {st.head_loss_total:.3f}")

	print("\nAlturas (m):")
	print(f"  bruta turb. HBt = {st.head_gross_turb:.3f}  |  "
		  f"líquida HLt = {st.head_net_turb:.3f}")
	print(f"  bruta bomb. HBb = {st.head_gross_pump:.3f}  |  "
		  f"líquida HLb = {st.head_net_pump:.3f}")

	print("\nPotências (MW/máquina):")
	print(f"  turbinamento = {st.power_turbine:.2f}  |  "
		  f"bombeamento = {st.power_pump:.2f}  |  "
		  f"relação = {st.power_ratio:.4f}")

	print("\nCavitação (NPSH):")
	print(f"  disponível = {st.npsh_available:.3f}  |  "
		  f"requerido = {st.npsh_required:.3f}  |  "
		  f"relação = {st.npsh_ratio:.3f}")

	print("\nCustos (milhões R$ - jan/26):")
	print(f"  C1 barragem superior  = {st.cost_dam_sup:10.2f}")
	print(f"  C2 barragem inferior  = {st.cost_dam_inf:10.2f}")
	print(f"  C3 casa de força      = {st.cost_powerhouse:10.2f}")
	print(f"  C4 circuito baixa P.  = {st.cost_low_pressure:10.2f}")
	print(f"  C5 circuito alta P.   = {st.cost_high_pressure:10.2f}")
	print(f"  CT CUSTO TOTAL        = {st.cost_total:10.2f}")

	# --- Simulador de verificação das restrições ---
	_print_header("Simulador: verificação das restrições")
	simulator = ConstraintSimulator(model)
	report = simulator.simulate(result)
	print(report)

	# --- Seleção de turbina (aba Seleção de turbina) ---
	_print_header("Seleção de turbina")
	avg_head = (st.head_gross_turb + st.head_gross_pump) / 2
	selection = TurbineSelection.select(
		total_flow=model.FLOW_TURBINE,
		n_machines=model.N_MACHINES,
		average_head=avg_head,
	)
	print(f"Vazão por máquina: {selection.flow_per_machine:.2f} m³/s")
	print(f"Desnível médio:    {selection.average_head:.2f} m")
	print(f"Tipo de turbina:   {selection.turbine_type}")
	print(f"  -> {selection.note}")

	# --- Cotas para desenho (aba desenho) ---
	_print_header("Cotas para desenho")
	drawing = Drawing(
		station=st,
		cota_terreno_sup=model.COTA_TERRENO_SUP,
		cota_terreno_inf=model.COTA_TERRENO_INF,
		cota_casa_forca=model.COTA_POWERHOUSE,
	)
	levels = drawing.levels()
	print(f"Cota topo barragem superior: {levels.cota_topo_barragem_sup:.2f} m")
	print(f"Cota máx reserv. superior:   {levels.cota_max_reserv_sup:.2f} m")
	print(f"Cota mín reserv. superior:   {levels.cota_min_reserv_sup:.2f} m")
	print(f"Cota tomada d'água:          {levels.cota_tomada_dagua:.2f} m")
	print(f"Cota B:                      {levels.cota_b:.2f} m")
	print(f"Cota C:                      {levels.cota_c:.2f} m")
	print(f"Cota topo barragem inferior: {levels.cota_topo_barragem_inf:.2f} m")
	print(f"Cota máx reserv. inferior:   {levels.cota_max_reserv_inf:.2f} m")
	print(f"Cota mín reserv. inferior:   {levels.cota_min_reserv_inf:.2f} m")
	print(f"Cota E:                      {levels.cota_e:.2f} m")
	print(f"Cota D:                      {levels.cota_d:.2f} m")
	print(f"Cota casa de força:          {levels.cota_casa_forca:.2f} m")


if __name__ == "__main__":
	main()
