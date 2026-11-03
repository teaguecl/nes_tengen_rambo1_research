# HWS7264 40-pin ZIF footprints. Pin 1 at origin, KiCad DIP convention.
P=2.54; ROW=15.24
BODY_W=17.72; BODY_L=50.75; TAB_L=55.80      # measured; tabs assumed symmetric
DRILL=0.8; PAD=1.6          # pins 0.2 x 0.62 mm (0.65 mm diagonal)
FINGER=11.0                  # clear space around the tabs
cx=ROW/2; cy=19*P/2
bx0,bx1=cx-BODY_W/2,cx+BODY_W/2; by0,by1=cy-BODY_L/2,cy+BODY_L/2
ty0,ty1=cy-TAB_L/2,cy+TAB_L/2
def pin_xy(n): return (0,(n-1)*P) if n<=20 else (ROW,(40-n)*P)
def rect(x0,y0,x1,y1,layer,wd=0.12):
    return [f'  (fp_line (start {a:.3f} {b:.3f}) (end {c:.3f} {d:.3f}) (stroke (width {wd}) (type solid)) (layer "{layer}"))'
            for a,b,c,d in [(x0,y0,x1,y0),(x1,y0,x1,y1),(x1,y1,x0,y1),(x0,y1,x0,y0)]]
def txt(t,x,y,layer,rot=0,size=1.0):
    return f'  (fp_text user "{t}" (at {x:.3f} {y:.3f} {rot}) (layer "{layer}") (effects (font (size {size} {size}) (thickness 0.15))))'
def make(name,flash):
    L=[f'(footprint "{name}"','  (version 20240108)','  (generator "rambo1_cart")','  (layer "F.Cu")',
       f'  (descr "Phoenix Enterprises HWS7264 40-pin 600 mil ZIF. Body {BODY_W}x{BODY_L} mm; actuator tabs to {TAB_L} mm, 2.5 mm above PCB (keep parts under them below 2.5 mm).")',
       '  (tags "ZIF DIP-40 socket")',
       f'  (property "Reference" "REF**" (at {cx:.3f} {ty0-1.2:.3f} 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))',
       f'  (property "Value" "{name}" (at {cx:.3f} {ty1+1.5:.3f} 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))',
       '  (attr through_hole)']
    for n in range(1,41):
        x,y=pin_xy(n); shape="rect" if n==1 else "circle"
        L.append(f'  (pad "{n}" thru_hole {shape} (at {x:.3f} {y:.3f}) (size {PAD} {PAD}) (drill {DRILL}) (layers "*.Cu" "*.Mask"))')
    L+=rect(bx0,by0,bx1,by1,"F.Fab",0.1)
    L+=rect(bx0,ty0,bx1,ty1,"Dwgs.User",0.1)
    L.append(txt("tabs 2.5 mm above PCB",cx,ty0-0.2,"Dwgs.User",0,0.7))
    L+=rect(bx0-0.15,by0-0.15,bx1+0.15,by1+0.15,"F.SilkS")
    # courtyard: body + 0.5 mm along the sides, widening to FINGER mm clear around each tab
    e=FINGER; m=0.5
    pts=[(bx0-e,ty0-e),(bx1+e,ty0-e),(bx1+e,by0+e),(bx1+m,by0+e),(bx1+m,by1-e),(bx1+e,by1-e),
         (bx1+e,ty1+e),(bx0-e,ty1+e),(bx0-e,by1-e),(bx0-m,by1-e),(bx0-m,by0+e),(bx0-e,by0+e)]
    for i in range(len(pts)):
        (a,b),(c,d)=pts[i],pts[(i+1)%len(pts)]
        L.append(f'  (fp_line (start {a:.3f} {b:.3f}) (end {c:.3f} {d:.3f}) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))')
    L.append(txt("finger clearance",cx,ty0-e+1.0,"Dwgs.User",0,0.7))
    L.append(txt("finger clearance",cx,ty1+e-1.0,"Dwgs.User",0,0.7))
    # pin-1 arrow outside the body
    L.append(f'  (fp_poly (pts (xy {bx0-0.4:.3f} 0) (xy {bx0-1.6:.3f} -0.7) (xy {bx0-1.6:.3f} 0.7)) (stroke (width 0.12) (type solid)) (fill solid) (layer "F.SilkS"))')
    if flash:
        # bracket outside left edge: rows 1-16 = chip, rows 17-20 = empty
        xb=bx0-2.4
        L.append(f'  (fp_line (start {xb:.3f} {-1.0:.3f}) (end {xb:.3f} {15*P+1.0:.3f}) (stroke (width 0.25) (type solid)) (layer "F.SilkS"))')
        L.append(txt("FLASH PIN 1 HERE - 32-PIN CHIP",xb-1.0,7.5*P,"F.SilkS",90,0.9))
        L.append(f'  (fp_line (start {xb:.3f} {16*P-0.8:.3f}) (end {xb:.3f} {19*P+0.8:.3f}) (stroke (width 0.12) (type dash)) (layer "F.SilkS"))')
        L.append(txt("EMPTY",xb-1.0,17.5*P,"F.SilkS",90,0.9))
    L.append(')')
    open(f"nes_cart.pretty/{name}.kicad_mod","w").write("\n".join(L)+"\n")
make("HWS7264_ZIF40",False)
make("HWS7264_ZIF40_Flash32",True)
print("body x",round(bx0,3),round(bx1,3),"y",round(by0,3),round(by1,3),"tabs y",round(ty0,3),round(ty1,3))
