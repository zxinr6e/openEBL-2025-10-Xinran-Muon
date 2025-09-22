'''
Create a layout with many uturns, waveguide uturn cutback structure

Scripted layout using SiEPIC-Tools in the SiEPIC-EBeam-PDK "EBeam" technology

by Lukas Chrostowski, 2025 

- Silicon waveguides
- Euler bend uturns, different parameters
- 1550 nm, TE
 
Use instructions:

Run in Python, e.g., VSCode

pip install required packages:
 - klayout, SiEPIC, siepic_ebeam_pdk, numpy

'''

designer_name = 'LukasChrostowski'
top_cell_name = 'EBeam_%s_rings_singlebus' % designer_name
export_type = 'PCell'  # static: for fabrication, PCell: include PCells in file

import siepic_ebeam_pdk
print(siepic_ebeam_pdk)

# exit(0)
# echo "import siepic_ebeam_pdk, SiEPIC" | /Users/lukasc/.pyenv/versions/3.11.1/bin/python
# cd /Users/lukasc/Documents/GitHub/SiEPIC_EBeam_PDK/klayout; /Users/lukasc/.pyenv/versions/3.11.1/bin/python -m pip -m install .

tech = 'EBeam'

import pya
from pya import CellInstArray, Trans, DTrans, Library, DPoint
from SiEPIC.utils import get_technology_by_name
from SiEPIC.scripts import connect_cell, connect_pins_with_waveguide
from SiEPIC.utils import load_Waveguides_by_Tech
from SiEPIC.utils.layout import new_layout, floorplan, make_pin
import os


import SiEPIC
from SiEPIC._globals import Python_Env
from SiEPIC.scripts import zoom_out, export_layout
from SiEPIC.verification import layout_check
import os
import numpy



def layout_uturns(ly, columns = 27, rows = 20, radius = 5, p = 0.25):

    cell = ly.create_cell('uturns')

    # Create test structures for all the types of waveguides
    waveguide_types = load_Waveguides_by_Tech(tech)
    
    xmax = 0
    y = 0
    x = xmax
    if 1:
        # only run the first type
        waveguide_type = waveguide_types[0]
        waveguide_types = [waveguide_type]

    # Import the grating coupler from the SiEPIC EBeam Library
    cell_ebeam_gc = ly.create_cell("GC_TE_1550_8degOxide_BB", "EBeam")
    x = -cell_ebeam_gc.bbox().left
    y = -cell_ebeam_gc.bbox().bottom
    inst_GC1 = cell.insert(CellInstArray(cell_ebeam_gc.cell_index(), 
                    Trans(Trans.R0, x, y)))
    t_gc = Trans(Trans.R0, x, y + 127/dbu)
    inst_GC2 = cell.insert(CellInstArray(cell_ebeam_gc.cell_index(), 
                    t_gc))

    # Add the u-turn
    # (waveguide_type)
    pcell = ly.create_cell(
        "ebeam_test_uturn_euler",
        "EBeam_Beta",
        {
            "waveguide_type": waveguide_type["name"],
            "columns": columns,
            "rows": rows,
            "radius": radius,
            "p": p,
            "tot_bends": 2 * columns * rows,
        },
    )

    t = Trans(Trans.R0, inst_GC1.pinPoint('opt1').x+15/dbu, inst_GC1.pinPoint('opt1').y+0/dbu)
    inst = cell.insert(CellInstArray(pcell.cell_index(), t))
    y += pcell.bbox().height() + 2000
    xmax = max(xmax, x + inst.bbox().width())

    # testing label
    tot_bends = inst.pcell_parameter('tot_bends')
    text = pya.Text (f'opt_in_TE_1550_device_uturnEulerR{radius}n{tot_bends}', t_gc)
    TECHNOLOGY = get_technology_by_name(tech)
    cell.shapes(TECHNOLOGY["Text"]).insert(text)
    
    # waveguide connections
    connect_pins_with_waveguide(inst_GC1, 'opt1', inst, 'opt_input', waveguide_type=waveguide_type["name"], turtle_B=[5,-90,10,-90,5,90])
    connect_pins_with_waveguide(inst_GC2, 'opt1', inst, 'opt_output', waveguide_type=waveguide_type["name"], turtle_B=[5,90,10,90], turtle_A=[5,90])

    return ly, cell


# Run all permutations:
# All radii within one layout
# one gap per layout



sweep_columns = [[13], [1, 10], [27], [1, 5, 13], [27], [1, 5, 13]]
sweep_rows = [[10], [10,10], [20], [20, 20, 20], [20], [20, 20, 20]]
sweep_radius = [[10], [10,10], [5], [5, 5, 5], [5], [5, 5, 5]]
sweep_p = [[0.25], [0.25, 0.25], [0.25], [0.25, 0.25, 0.25], [0.5], [0.5, 0.5, 0.5]]

designer_name = 'LukasChrostowski'

for c1, rows1, radius1, p1 in zip(sweep_columns, sweep_rows, sweep_radius, sweep_p):
    # Create a new layout for the chip floor plan
    top_cell_name = f'EBeam_{designer_name}_uturns_r{radius1[0]}_c{c1[0]}_p{p1[0]}' 
    topcell, ly = new_layout(tech, "test", GUI=True, overwrite=True)
    dbu = ly.dbu

    print (c1, rows1, radius1, p1)
    for c, rows, radius, p in zip(c1, rows1, radius1, p1):
        # print (c, rows, radius, p)
        ly, cell = layout_uturns(ly, columns = c, rows = rows, radius = radius, p = p)
        topcell.insert(CellInstArray(cell.cell_index(), 
                    Trans(Trans.R0, topcell.bbox().right+1e3, 5e3)))

    floorplan(topcell, 605e3, 410e3)

    # Export for fabrication, removing PCells
    filename = top_cell_name
    path = os.path.dirname(os.path.realpath(__file__))
    if export_type == 'static':
        file_out = export_layout(cell, path, filename, relative_path = '..', format='oas', screenshot=True)
    else:
        file_out = os.path.join(path,'..',filename+'.oas')
        ly.write(file_out)

    # Display the layout in KLayout, using KLayout Package "klive", which needs to be installed in the KLayout Application
    if Python_Env == 'Script':
        from SiEPIC.utils import klive
        klive.show(file_out, technology=tech)

    print('layout script done')

