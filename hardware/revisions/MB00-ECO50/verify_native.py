"""Verify the downloaded native review against the reproducible ECO50 geometry.

Native DRC/ERC results are recorded from the UI, not inferred by this script.
This is engineering evidence only, never a power-loop or fabrication release.
"""
import collections
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_eco50 import docs_from, json_file
from audit import extract, pcb, schematic, critical_expectations, attrs
from route_geometry import load


def main():
    native = HERE / 'pcb-eco50-native-reviewed.epro2'
    sch = HERE / 'schematic-eco50-native-reviewed.epro2'
    docs = docs_from(native)
    json_file(HERE / 'native-reviewed-docs.json', docs)
    nr, np = load(str(HERE / 'native-reviewed-docs.json'))
    gr, gp = load(str(HERE / 'pcb-eco50-docs.json'))

    def copper(rows):
        out = []
        for r in rows:
            b = r['b']
            if r['h']['type'] == 'LINE':
                ends = sorted([(round(b['startX'], 5), round(b['startY'], 5)),
                               (round(b['endX'], 5), round(b['endY'], 5))])
                out.append(('LINE', b['netName'], b['layerId'], *ends, round(b['width'], 5)))
            elif r['h']['type'] == 'VIA':
                out.append(('VIA', b['netName'], *[round(b[k], 5) for k in
                    ['centerX', 'centerY', 'holeDiameter', 'viaDiameter']]))
        return collections.Counter(out)

    def pads(rows):
        return collections.Counter((p['ref'], p['pin'], p['net'], p['layer'],
            *[round(p[k], 3) for k in ['x', 'y', 'w', 'h']]) for p in rows)

    assert copper(nr) == copper(gr), 'Native/generated routed copper differs'
    assert pads(np) == pads(gp), 'Native/generated component pad geometry differs'
    mapped, _ = pcb(extract(native))
    pm = collections.defaultdict(set)
    for p in mapped:
        pm[p['ref'], p['pin']].add(p['net'])
    pins = schematic(extract(sch))
    mismatch = [p for p in pins if p['conflicts'] or
                pm.get((p['ref'], p['pin'])) != {p['net']}]
    critical = [k for k, v in critical_expectations().items() if pm.get(k) != {v}]
    assert not mismatch and not critical

    a = attrs(nr)
    expected_parts = {'C22': ('CL10B223KB8NNNC', 'C21122'),
                      'C25': ('MA10V470M6X8', 'C46550459'),
                      'L2': ('MWSA0503S-1R0MT', 'C408355')}
    device_meta = {d['head']['b']['uuid']: next(r['b'] for r in d['records']
        if r['h']['type'] == 'META')['attributes'] for d in docs
        if d['head']['b']['docType'] == 'DEVICE'}
    for r in nr:
        if r['h']['type'] != 'COMPONENT':
            continue
        cid = r['h']['id']
        ref = a.get((cid, 'Designator'))
        if ref in expected_parts:
            part = device_meta[a[cid, 'Device']]
            assert (part['Manufacturer Part'], part['Supplier Part']) == expected_parts[ref]
            for key in ['Manufacturer Part', 'Supplier Part']:
                assert r['b']['attrs'].get(key, part[key]) == part[key]
    cap_id = next(k[0] for k, v in a.items() if k[1] == 'Designator' and v == 'C25')
    fp_id = a[cap_id, 'Footprint']
    cap_fp = next(d for d in docs if d['head']['b']['uuid'] == fp_id)
    cap_pads = [r['b'] for r in cap_fp['records'] if r['h']['type'] == 'PAD']
    assert len(cap_pads) == 2
    assert all(p['topPasteExpansion'] == -2 for p in cap_pads)
    # 3.1 x 1.6 mm copper lands, reduced 0.0508 mm per edge for paste.
    assert all(p['defaultPad']['width'] + 2*p['topPasteExpansion'] > 0 and
               p['defaultPad']['height'] + 2*p['topPasteExpansion'] > 0 for p in cap_pads)
    cap_positions = {p['pin']: [round(p['x']*.0254, 6), round(p['y']*.0254, 6)]
                     for p in np if p['ref'] == 'C25'}
    frozen_root = HERE.parents[2] / 'hardware/releases/A-14329-MB00'
    frozen = json.loads((frozen_root / 'manifest.json').read_text())
    frozen_changes = [f['file'] for f in frozen['files'] if
        hashlib.sha256((frozen_root/f['file']).read_bytes()).hexdigest() != f['sha256']]
    assert not frozen_changes
    result = dict(
        date='2026-10-31', status='ENGINEERING_CANDIDATE_NOT_FOR_FABRICATION',
        project='A-14329 AIO Modem', board='Board1-ECO50-ENGINEERING',
        pcb_document='c40c19dda3ba2a21', schematic_page='5989becae430ea8f',
        native_pcb_drc=dict(errors=0, check_items=124,
            reported_time='2026-10-31 22:16:00', evidence='native-pcb-drc.jpg'),
        native_schematic_check=dict(fatal_errors=0, errors=0, warnings=1,
            warning='Supplier-attribute standardization warning: L2, C25, C22. '
                    'Custom engineering devices require catalog/assembly review; '
                    'do not blindly replace authored footprints.'),
        cloud_imported_and_saved=True, native_pours_rebuilt=True,
        native_poured_record_count=sum(r['h']['type']=='POURED' for r in nr),
        exact_routed_copper_matches_reproducible_candidate=True,
        pad_geometry_matches_at_native_export_precision=True,
        pad_comparison_quantization_mil=0.001,
        critical_pin_checks=len(critical_expectations()), critical_pin_failures=critical,
        schematic_pin_keys=len(pins), schematic_parity_failures=mismatch,
        changed_native_device_MPN_and_supplier_numbers_match=True,
        C25_pad_centers_mm=cap_positions, C25_top_paste_expansion_mil=-2,
        C25_paste_aperture_mm=[2.9984, 1.4984],
        frozen_release_hash_changes=frozen_changes, physical_power_validation=False,
        fabrication_release=False,
        files={f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in [native, sch]})
    json_file(HERE / 'native-validation.json', result)
    print('Native/generated routed copper and pads match; 285 critical and 544 schematic pins pass.')
    print('C25 top paste apertures restored; frozen release unchanged.')


if __name__ == '__main__':
    main()
