# Boitier wind sim v3 : Arduino libre, couvercle clipsable avec ecran LCD 1602, USB a gauche et a droite,
# fixation M8 par 4 lumieres en croix (entraxe 40 a 90 mm). Necessite : pip install manifold3d trimesh
from manifold3d import Manifold, set_circular_segments
import trimesh, numpy as np, math, sys

# Arrondis legers : coins en plan via CrossSection, aretes haut/bas par couches decalees (marches < couche d'impression)
from manifold3d import CrossSection, JoinType, OpType

def rounded_rect(w, h, r):
    r = max(min(r, w/2 - 0.01, h/2 - 0.01), 0.01)
    return CrossSection.square([w - 2*r, h - 2*r], True).offset(r, JoinType.Round)

def rslab(cs, h, rt=1.0, rb=0.5, n=6):
    """Extrude cs sur h avec aretes du haut (rt) et du bas (rb) arrondies."""
    parts = []
    core0, core1 = rb, h - rt
    parts.append(cs.extrude(core1 - core0 + 0.002).translate([0, 0, core0 - 0.001]))
    for r, bottom in ((rb, True), (rt, False)):
        if r <= 0:
            continue
        for i in range(n):
            a, b = r*i/n, r*(i+1)/n
            zm = (a + b) / 2                            # distance au bord (0 = arete)
            d = -(r - (r*r - (r - zm)**2) ** 0.5)
            layer = cs.offset(d, JoinType.Round).simplify(0.02)
            if layer.is_empty():
                continue
            z0 = a if bottom else h - b
            parts.append(layer.extrude(b - a + 0.002).translate([0, 0, z0 - 0.001]))
    return Manifold.batch_boolean(parts, OpType.Add)

set_circular_segments(64)

# ---------- Parametres (mm) ----------
W, H, D = 180.0, 120.0, 55.0      # exterieur : largeur, hauteur, profondeur
WALL, BACK, LID_T = 3.0, 5.0, 3.0
M8_D = 8.6                         # largeur des lumieres M8
SLOT_R0, SLOT_R1 = 20.0, 45.0      # chaque bras va de 20 a 45 mm du centre -> entraxe 40 a 90 mm
NOTCH_W = 12.0                      # encoches de cables (parois haute et basse)
NOTCH_H = D - BACK - NOTCH_W/2 - 2.0  # profondeur : jusqu'a 2 mm du fond
NOTCH_X = [-35.0, 35.0, 70.0]
USB_W, USB_H = 10.0, 22.0          # encoches USB (parois gauche et droite)
LIP_H, LIP_T, CLEAR = 8.0, 1.6, 0.3   # levre du couvercle
SNAP = 1.0                         # saillie des bossettes de clips
GROOVE = 1.15                      # profondeur de la rainure dans la paroi
SNAP_Z = 4.0                       # distance bord -> rainure
# Ecran LCD 1602 (mesurez le votre avant d'imprimer)
LCD_C = (20.0, 0.0)                # centre de l'ecran sur le couvercle
LCD_WIN = (72.0, 25.0)             # fenetre pour le cadre noir de l'ecran (71 x 24 typique)
LCD_HOLES = (75.0, 31.0)           # entraxe des 4 trous de fixation (circuit 80 x 36)
LCD_STANDOFF = 4.0                 # hauteur des entretoises sous le couvercle
VENT_X = (-80.0, -35.0)            # zone des fentes d'aeration

def cube(x0, y0, z0, x1, y1, z1):
    return Manifold.cube([x1-x0, y1-y0, z1-z0]).translate([x0, y0, z0])
def cyl(x, y, z0, h, d):
    return Manifold.cylinder(h, d/2).translate([x, y, z0])
def diamond_x(x0, x1, y, z, depth):   # prisme triangulaire le long de X (section losange)
    s = depth*math.sqrt(2)
    return Manifold.cube([x1-x0, s, s], center=True).rotate([45, 0, 0]).translate([(x0+x1)/2, y, z])
def diamond_y(y0, y1, x, z, depth):   # idem le long de Y
    s = depth*math.sqrt(2)
    return Manifold.cube([s, y1-y0, s], center=True).rotate([0, 45, 0]).translate([x, (y0+y1)/2, z])

ix, iy = W/2-WALL, H/2-WALL

# ---------- Boitier ----------
CORNER_R = 6.0                    # rayon des coins en plan
box = rslab(rounded_rect(W, H, CORNER_R), D, rt=0.8, rb=1.2) - rounded_rect(2*ix, 2*iy, CORNER_R - WALL).extrude(D + 1).translate([0, 0, BACK])

# lumieres M8 en croix, centrees
for ang in (0, 90, 180, 270):
    c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    a = cyl(SLOT_R0*c, SLOT_R0*s, -1, BACK+2, M8_D)
    b = cyl(SLOT_R1*c, SLOT_R1*s, -1, BACK+2, M8_D)
    box -= Manifold.batch_hull([a, b])

# rainure de clipsage sur tout le pourtour interieur
gz = D - SNAP_Z
box -= diamond_x(-ix, ix, iy, gz, GROOVE) + diamond_x(-ix, ix, -iy, gz, GROOVE)
box -= diamond_y(-iy, iy, ix, gz, GROOVE) + diamond_y(-iy, iy, -ix, gz, GROOVE)

# encoches de cables en haut et en bas (ouvertes cote couvercle)
for x in NOTCH_X:
    for top in (True, False):
        y0, y1 = (iy-1, H/2+1) if top else (-H/2-1, -iy+1)
        box -= cube(x-NOTCH_W/2, y0, D-NOTCH_H, x+NOTCH_W/2, y1, D+1)
        box -= Manifold.cylinder(WALL+2, NOTCH_W/2).rotate([90, 0, 0]).translate(
            [x, y1, D-NOTCH_H])

# encoches USB a gauche et a droite (y = 0)
for left in (True, False):
    x0, x1 = (-W/2-1, -ix+1) if left else (ix-1, W/2+1)
    box -= cube(x0, -USB_W/2, D-USB_H, x1, USB_W/2, D+1)
    box -= Manifold.cylinder(WALL+2, USB_W/2).rotate([0, 90, 0]).translate(
        [x0, 0, D-USB_H])

# encoche pour soulever le couvercle (paroi gauche)
box -= cube(-W/2-1, -43, D-3, -ix+1, -27, D+1)

# pontets pour colliers de serrage, sous chaque encoche
for x in NOTCH_X:
    for sy in (-1, 1):
        y = sy*(iy-11)
        box += cube(x-6, y-3, BACK, x+6, y+3, BACK+5) - cube(x-2.5, y-4, BACK-0.1, x+2.5, y+4, BACK+2.2)

# ---------- Couvercle clipsable ----------
lx, ly = ix-CLEAR, iy-CLEAR
lid = rslab(rounded_rect(W, H, CORNER_R), LID_T, rt=0.6, rb=1.0)
lip = rounded_rect(2*lx, 2*ly, CORNER_R - WALL - CLEAR).extrude(LIP_H + 0.01).translate([0, 0, LID_T - 0.01]) - rounded_rect(2*(lx-LIP_T), 2*(ly-LIP_T), max(CORNER_R - WALL - CLEAR - LIP_T, 0.5)).extrude(LIP_H + 2).translate([0, 0, LID_T - 1])
sz = LID_T + SNAP_Z
tabs = [("x", -25, 25, ly), ("x", -25, 25, -ly), ("y", 15, 45, lx), ("y", 15, 45, -lx)]
for axis, a0, a1, face in tabs:
    if axis == "x":
        lip += diamond_x(a0, a1, face, sz, SNAP)
        for e in (a0-1.0, a1+1.0):   # fentes de souplesse de part et d'autre de la languette
            y0, y1 = (face-LIP_T-0.5, face+0.5) if face > 0 else (face-0.5, face+LIP_T+0.5)
            lip -= cube(e-1, y0, LID_T+0.6, e+1, y1, LID_T+LIP_H+1)
    else:
        lip += diamond_y(a0, a1, face, sz, SNAP)
        for e in (a0-1.0, a1+1.0):
            x0, x1 = (face-LIP_T-0.5, face+0.5) if face > 0 else (face-0.5, face+LIP_T+0.5)
            lip -= cube(x0, e-1, LID_T+0.6, x1, e+1, LID_T+LIP_H+1)
lid += lip
# fentes d'aeration
for i in range(6):
    yv = -22.5 + i*9
    lid -= cube(VENT_X[0], yv-1.5, -1, VENT_X[1], yv+1.5, LID_T+1)

# ecran LCD : fenetre, entretoises et trous fraises pour vis M3 depuis l'exterieur
lcx, lcy = LCD_C
lid -= cube(lcx-LCD_WIN[0]/2, lcy-LCD_WIN[1]/2, -1, lcx+LCD_WIN[0]/2, lcy+LCD_WIN[1]/2, LID_T+1)
for sx in (-1, 1):
    for sy in (-1, 1):
        hx, hy = lcx+sx*LCD_HOLES[0]/2, lcy+sy*LCD_HOLES[1]/2
        lid += cyl(hx, hy, LID_T-0.01, LCD_STANDOFF+0.01, 7.0)
        lid -= cyl(hx, hy, -1, LID_T+LCD_STANDOFF+2, 3.4)
        lid -= Manifold.cylinder(1.8, 6.6/2, 3.4/2).translate([hx, hy, -0.001])

def export(m, path):
    mesh = m.to_mesh()
    t = trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3], faces=np.asarray(mesh.tri_verts))
    t.export(path)
    print(path, "watertight:", t.is_watertight, "bbox:", np.round(t.bounds, 2).tolist())
    return t

export(box, "../stl/windsim-boitier-arduino.stl")
export(lid, "../stl/windsim-couvercle.stl")
