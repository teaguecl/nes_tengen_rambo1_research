# NES 72-pin cartridge edge, NESdev numbering. Edit these after measuring your donor board.
PITCH=2.50      # mm, per NESdev
PAD_W=1.70      # finger width (mm)
PAD_L=9.00      # finger length from board edge (mm)
N=36
L=[]
w=L.append
w('(footprint "NES_Edge_72_P2.50mm"')
w('  (version 20240108)')
w('  (generator "rambo1_cart")')
w('  (layer "F.Cu")')
w('  (descr "NES 72-pin cartridge edge fingers, NESdev numbering. Pins 1-36 on F.Cu (label/component side), 37-72 on B.Cu. Origin = centre of board edge.")')
w('  (tags "NES cartridge edge connector 72")')
w('  (property "Reference" "J1" (at 0 %.2f 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))' % (-PAD_L-2))
w('  (property "Value" "NES_Edge_72" (at 0 %.2f 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))' % (-PAD_L-4))
w('  (attr smd)')
for n in range(1,N+1):
    x=(18.5-n)*PITCH
    w(f'  (pad "{n}" smd rect (at {x:.3f} {-PAD_L/2:.3f}) (size {PAD_W:.2f} {PAD_L:.2f}) (layers "F.Cu" "F.Mask"))')
for m in range(37,73):
    x=(18.5-(m-36))*PITCH
    w(f'  (pad "{m}" smd rect (at {x:.3f} {-PAD_L/2:.3f}) (size {PAD_W:.2f} {PAD_L:.2f}) (layers "B.Cu" "B.Mask"))')
# board-edge reference line and labels
half=18*PITCH
w(f'  (fp_line (start {-half:.2f} 0) (end {half:.2f} 0) (stroke (width 0.1) (type dash)) (layer "Dwgs.User"))')
w(f'  (fp_text user "Board edge" (at 0 1.2 0) (layer "Dwgs.User") (effects (font (size 0.8 0.8) (thickness 0.12))))')
for lbl,n,layer in [("1",1,"F.SilkS"),("36",36,"F.SilkS")]:
    x=(18.5-n)*PITCH
    w(f'  (fp_text user "{lbl}" (at {x:.2f} {-PAD_L-0.9:.2f} 0) (layer "{layer}") (effects (font (size 0.8 0.8) (thickness 0.12))))')
for lbl,n in [("37",1),("72",36)]:
    x=(18.5-n)*PITCH
    w(f'  (fp_text user "{lbl}" (at {x:.2f} {-PAD_L-0.9:.2f} 0) (layer "B.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12)) (justify mirror)))')
w(')')
open("nes_cart.pretty/NES_Edge_72_P2.50mm.kicad_mod","w").write("\n".join(L)+"\n")
