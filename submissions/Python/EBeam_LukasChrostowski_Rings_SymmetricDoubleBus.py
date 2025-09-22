'''
Scripted layout for ring resonators using SiEPIC-Tools
in the SiEPIC-EBeam-PDK "EBeam" technology

by Lukas Chrostowski, 2025 

- Silicon waveguides
- Several ring resonators with different radii and gap
- Symmetric double-bus
- 1550 nm, TE
 
Use instructions:

Run in Python, e.g., VSCode

pip install required packages:
 - klayout, SiEPIC, siepic_ebeam_pdk, numpy

'''

designer_name = 'LukasChrostowski'
top_cell_name = 'EBeam_%s_rings_symmetric_doublebus' % designer_name
export_type = 'PCell'  # static: for fabrication, PCell: include PCells in file

import siepic_ebeam_pdk
tech_name = 'EBeam'

import pya
from pya import *

import SiEPIC
from SiEPIC._globals import Python_Env
from SiEPIC.scripts import zoom_out, export_layout
from SiEPIC.verification import layout_check
import os
import numpy


# Example layout function
def dbl_bus_ring_res(
    sweep_radius = [3,       5, 5, 5,         10, 10, 10, 10],
    sweep_gap    = [0.07, 0.07, 0.08, 0.09, 0.08, 0.09, 0.10, 0.11]
):

    # Import functions from SiEPIC-Tools
    from SiEPIC.extend import to_itype
    from SiEPIC.scripts import connect_cell, connect_pins_with_waveguide
    from SiEPIC.utils.layout import new_layout, floorplan

    # Create a layout for testing a double-bus ring resonator.
    # uses:
    #  - the SiEPIC EBeam Library
    # creates the layout in the presently selected cell
    # deletes everything first
    
    # Configure parameter sweep  
    pol = 'TE'
    print (f'Layout: g={sweep_gap}, r={sweep_radius}')
    x_offset = 67
    wg_bend_radius = 5

    wg_width = 0.5
    
    '''
    Create a new layout using the EBeam technology,
    with a top cell
    and Draw the floor plan
    '''    
    cell, ly = new_layout(tech_name, top_cell_name, GUI=True, overwrite = True)
    floorplan(cell, 605e3, 410e3)

    if SiEPIC.__version__ < '0.5.1':
        raise Exception("Errors", "This example requires SiEPIC-Tools version 0.5.1 or greater.")

    # Layer mapping:
    LayerSiN = ly.layer(ly.TECHNOLOGY['Si'])
    fpLayerN = cell.layout().layer(ly.TECHNOLOGY['FloorPlan'])
    TextLayerN = cell.layout().layer(ly.TECHNOLOGY['Text'])
    
    
    # Create a sub-cell for our Ring resonator layout
    top_cell = cell
    dbu = ly.dbu
    cell = cell.layout().create_cell("RingResonator")
    t = Trans(Trans.R0, 40 / dbu, 14 / dbu)

    # place the cell in the top cell
    top_cell.insert(CellInstArray(cell.cell_index(), t))
    
    # Import cell from the SiEPIC EBeam Library
    cell_ebeam_gc = ly.create_cell("GC_%s_1550_8degOxide_BB" % pol, "EBeam")
    # get the length of the grating coupler from the cell
    gc_length = cell_ebeam_gc.bbox().width()*dbu
    # spacing of the fibre array to be used for testing
    GC_pitch = 127

    # Loop through the parameter sweep
    for i in range(len(sweep_gap)):
        
        # place layout at location:
        if i==0:
            x=0
        else:
            # next device is placed at the right-most element + length of the grating coupler
            # or 60 microns from the previous grating coupler, whichever is greater
            x = max(inst_dc2.bbox().right*dbu + gc_length + 1, instGCs[0].trans.disp.x*dbu + 60)
        
        # get the parameters
        r = sweep_radius[i]
        g = sweep_gap[i]
        
        # Grating couplers, Ports 0, 1, 2, 3 (from the bottom up)
        instGCs = []
        for i in range(0,4):
            t = Trans(Trans.R0, to_itype(x,dbu), i*127/dbu)
            instGCs.append( cell.insert(CellInstArray(cell_ebeam_gc.cell_index(), t)) )
        
        # Label for automated measurements, laser on Port 2, detectors on Ports 1, 3, 4
        t = Trans(Trans.R90, to_itype(x,dbu), to_itype(GC_pitch*2,dbu))
        text = Text ("opt_in_%s_1550_device_%s_RingDoubleSymmetric%sr%sg%s" % (pol.upper(), designer_name, pol.upper(),r,int(round(g*1000))), t)
        text.halign = 1
        cell.shapes(TextLayerN).insert(text).text_size = 5/dbu
                  
        # Ring resonator from directional coupler PCells
        cell_dc = ly.create_cell("ebeam_dc_halfring_straight", "EBeam", { "r": r, "w": wg_width, "g": g, "bustype": 0 } )
        y_ring = GC_pitch*3/2
        # first directional coupler
        t1 = Trans(Trans.R270, to_itype(x+wg_bend_radius, dbu), to_itype(y_ring, dbu))
        inst_dc1 = cell.insert(CellInstArray(cell_dc.cell_index(), t1))
        # add 2nd directional coupler, snapped to the first one
        inst_dc2 = connect_cell(inst_dc1, 'pin2', cell_dc, 'pin4')
        
        # Create paths for waveguides, with the type defined in WAVEGUIDES.xml in the PDK
        waveguide_type='Strip TE 1550 nm, w=500 nm'
        
        # GC1 to bottom-left of ring pin3
        connect_pins_with_waveguide(instGCs[1], 'opt1', inst_dc1, 'pin3', waveguide_type=waveguide_type)
        
        # GC2 to top-left of ring pin1
        connect_pins_with_waveguide(instGCs[2], 'opt1', inst_dc1, 'pin1', waveguide_type=waveguide_type)
        
        # GC0 to top-right of ring
        connect_pins_with_waveguide(instGCs[0], 'opt1', inst_dc2, 'pin1', waveguide_type=waveguide_type)
        
        # GC3 to bottom-right of ring
        connect_pins_with_waveguide(instGCs[3], 'opt1', inst_dc2, 'pin3', waveguide_type=waveguide_type)

    # Introduce an error, to demonstrate the Functional Verification
    # inst_dc2.transform(Trans(1000,-1000))

    return ly, cell


# Run all permutations:
# All radii within one layout
# one gap per layout
sweep_radius = [[12, 15, 20, 25, 30, 40], [2, 3, 4, 5, 6, 7, 8, 9, 10]]
sweep_radius_desc = ['large','small']
sweep_gap    = [0.07, 0.08, 0.09, 0.10, 0.11, 0.12, 0.14, 0.16, 0.18, 0.20, 0.22, 0.24, 0.26, 0.28, 0.30]

for r, desc in zip(sweep_radius, sweep_radius_desc):
    print(r,desc)
    for g in sweep_gap:
        ly, cell = dbl_bus_ring_res(sweep_radius = r, 
                                    sweep_gap = len(r)*[g])


        # Export for fabrication, removing PCells
        path = os.path.dirname(os.path.realpath(__file__))
        filename, extension = os.path.splitext(os.path.basename(__file__))
        filename += f'_g={int(g*1000)}_{desc}'
        if export_type == 'static':
            file_out = export_layout(cell, path, filename, relative_path = '..', format='oas', screenshot=True)
        else:
            file_out = os.path.join(path,'..',filename+'.oas')
            ly.write(file_out)

    #    file = os.path.join(path,'..',filename)

        '''
        from SiEPIC.verification import layout_check
        print('SiEPIC_EBeam_PDK: example_Ring_resonator_sweep.py - verification')
        file_lyrdb = os.path.join(path,filename+'.lyrdb')
        num_errors = layout_check(cell = cell, verbose=False, GUI=True, file_rdb=file_lyrdb)
        '''

        # Display the layout in KLayout, using KLayout Package "klive", which needs to be installed in the KLayout Application
        if Python_Env == 'Script':
            from SiEPIC.utils import klive
            klive.show(file_out, technology=tech_name)

        print('layout script done')
