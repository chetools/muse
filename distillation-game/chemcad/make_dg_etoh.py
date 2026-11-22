"""Build ethanol/water FLAS sims to find which XML field governs the
K-value model in ChemCAD: the ThermalModes modek attribute, the
<setting type_label="k value option"> entry, or both.

Variants (argv[1]): T = ThermalModes modek=10 only,
S = setting legacy_id=10/value=NRTL only, B = both, N = neither.

Build recipe (established 2026-11-21 by bisection against LoadSim
return codes; every step is load-bearing):
- start from the RAW linde.xml template (a ChemCAD-saved XML carries
  component-keyed sections that break under a component swap);
- swap ComponentIDs AND GeneralInfo NumberOfComponents (a stale
  count leaves a phantom component with no name and no properties);
- resize every <Components schema="2"> block to the new count;
- replace Streams and Equipment with the single FLAS unit (blob from
  the October study's make_p2_fs.py) and clear the cut streams;
- write the zip over the October base sim's members (minus .ppdb)
  with member names UNCHANGED (renaming members or the savestate
  references inside the XML is not required and the renamed builds
  failed to load).
Components: ethanol 134, water 62.
"""
import re
import sys
import zipfile

ZERO = "4c354bd6926fd07ef43c15ee9bb8b3b846524334a14079f25efdb9095ebd6177"
FLAS_BLOB = "4c354bd6926fd07ef43c15ee9bb8b3b800976cbe7e2992394694377e098e0316"
BASE = "/home/hatch/workspace/chemcad-vs-claude/chemcad/base_p2.ccsim"
LINDE_XML = "/home/hatch/workspace/chemcad-vs-claude/chemcad/linde/linde.xml"
XMLNAME = "Linde_ASU_run.xml"

variant = sys.argv[1]
# The template declares three components (NumberOfComponents=3);
# the build that loads carries only the two real IDs and lets the
# third slot stand empty (dg_e4.ccsim is the evidence: it loads and
# runs, and the empty slot takes no feed flow). Adding a third real
# ID (methanol, 117) or setting the count to 2 both made LoadSim
# return 203.
ids = [134, 62]
x = open(LINDE_XML).read()
idxml = "\n".join(f'            <Component ID="{i}" />' for i in ids)
x = re.sub(r"<ComponentIDs>.*?</ComponentIDs>",
           f"<ComponentIDs>\n{idxml}\n        </ComponentIDs>", x, flags=re.S)

if variant in ("T", "B"):
    x = re.sub(r'modek="\d+"', 'modek="10"', x, count=1)   # NRTL
if variant in ("S", "B"):
    x = x.replace('value="Peng-Robinson" legacy_id="9"',
                  'value="NRTL" legacy_id="10"')

items = "\n".join(
    f'                <item key="{k}" data="{ZERO}" />' for k in range(len(ids)))
x = re.sub(r'(<Components schema="2">).*?(</Components>)',
           lambda m: m.group(1) + "\n" + items + "\n            " + m.group(2),
           x, flags=re.S)

STREAM = """        <Stream sname="" ID="{sid}">
            <issdi issdi0="{sid}" issdi1="{srcu}" issdi2="{tgtu}" />
            <Components schema="2">
{items}
            </Components>
            <Settings1 schema="2" sfi="0" sti="{z}" spi="{z}" svi="0" shi="0" mass_frac="0" shoi="0" sfoi="0" wtentity="0" noentity="0" StreamCost="0" Humidity="0" FeedPressure="0" stoi="0" spoi="0" />
            <Settings2 iscfi="-1" isffi="-1" iffi="0" itfi="0" ipfi="0" ivfi="0" ihfi="0" isfi="0" />
            <Settings3 isnewi="0" descrete="0" iBatch="0" FlowDirection="0" FlowScaleEqp="0" StreamCostType="0" iFlashErr="0" />
        </Stream>
"""
streams = "".join(
    STREAM.format(sid=sid, srcu=s, tgtu=t, z=ZERO, items=items)
    for sid, s, t in ((1, 0, 1), (2, 1, 0), (3, 1, 0), (4, 1, 0))
)
x = re.sub(r"    <Streams>\n.*?\n    </Streams>",
           "    <Streams>\n" + streams + "    </Streams>", x, flags=re.S)

UNIT = """        <UnitOp ide="1" itype="4" uname="FLAS" ienew="1" ename="FLAS">
            <ioe>
                <Item key="0" data="1" />
                <Item key="1" data="1" />
                <Item key="2" data="-2" />
                <Item key="3" data="-3" />
                <Item key="4" data="-4" />
            </ioe>
            <eqs schema="2">
                <NUSPEC key="0" data="{blob}" />
            </eqs>
            <Errors nRunErr="0" />
            <misc ike="0" ihe="0" icon="0" ignore_elec="0" local_imms="0" local_llv="1" bip_set="0" nwar="0" nerr="0" err_code="0" />
        </UnitOp>
""".format(blob=FLAS_BLOB)
x = re.sub(r"    <Equipment>\n.*?\n    </Equipment>",
           "    <Equipment>\n" + UNIT + "    </Equipment>", x, flags=re.S)

x = x.replace('nscut="2"', 'nscut="0"')
x = re.sub(r"<CutStreams>.*?</CutStreams>", "<CutStreams />", x, flags=re.S)
x = re.sub(r"<ACCStreams>\s*<Stream ID=\"\d+\" />\s*<Stream ID=\"\d+\" />",
           '<ACCStreams>\n            <Stream ID="0" />\n            <Stream ID="0" />', x)

import time as _t
out = f"dgx_{variant.lower()}_{int(_t.time()) % 100000}.ccsim"
zin = zipfile.ZipFile(BASE)
zout = zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED)
for item in zin.namelist():
    if item.endswith(".ppdb"):
        continue
    data = zin.read(item)
    if item == XMLNAME:
        data = x.encode()
    zout.writestr(item, data)
zout.close()
print("wrote", out)
