SHELL := /bin/zsh
PY := .venv/bin/python

.PHONY: setup snapshot snapshot-heavy gaps acesso obras all snapshot-commit test

setup:
	uv venv && uv pip install -e "pipeline[geo,network]"

snapshot:
	$(PY) -m rpmobility.snapshot

# slow/huge layers (zoneamento, logradouros, quadras) on demand
snapshot-heavy:
	$(PY) -m rpmobility.snapshot --heavy

gaps:
	$(PY) -m rpmobility.compile.ciclovia_gap \
		--city data/raw/snapshots/latest/ciclovias.geojson \
		--osm data/raw/osm/cycleways.geojson \
		--out apps/web/public/data/ciclovias

all: snapshot gaps obras projetos transporte

# weekly job (launchd calls this): fetch, diff, commit, push
snapshot-commit: snapshot
	@zsh scripts/commit-snapshot.sh

acesso:
	$(PY) -m rpmobility.compile.access_score \
		--bairros data/raw/snapshots/latest/bairros.geojson \
		--quadras data/raw/snapshots/latest/quadras.geojson \
		--pois data/raw/osm/pois.geojson \
		--with-censo \
		--out apps/web/public/data/acesso

obras:
	$(PY) -m rpmobility.compile.obras_timeline

projetos:
	$(PY) -m rpmobility.compile.obras_projetos \
		--obras data/raw/snapshots/latest/obras_pontos.geojson \
		--out apps/web/public/data/obras

transporte:
	$(PY) -m rpmobility.compile.stop_coverage \
		--bairros data/raw/snapshots/latest/bairros.geojson \
		--quadras data/raw/snapshots/latest/quadras.geojson \
		--stops data/raw/osm/stops.geojson \
		--out apps/web/public/data/transporte

zoneamento:
	$(PY) -m rpmobility.compile.zoneamento_mosaico \
		--parcels data/raw/snapshots/latest/zoneamento.geojson \
		--bairros data/raw/snapshots/latest/bairros.geojson \
		--quadras data/raw/snapshots/latest/quadras.geojson \
		--out apps/web/public/data/zoneamento

tiles:
	$(PY) -m rpmobility.publish.tiles

test:
	uv pip install -q -e "pipeline[dev]" && .venv/bin/python -m pytest pipeline/tests -q
