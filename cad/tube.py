# Pieces de tube wind sim : reducteur ventilateur 140 mm -> tube 76 mm, et buse de sortie avec patte M8.
# Necessite : pip install manifold3d trimesh
from manifold3d import Manifold, set_circular_segments
import trimesh, numpy as np, sys

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

set_circular_segments(96)

TUBE_ID = 76.0        # diametre interieur du tube (mesurez le votre)
FIT = 0.4             # jeu : l'embout fait TUBE_ID - FIT
WALL = 2.4
SPIGOT_L = 30.0       # longueur d'emboitement dans le tube
FAN = 140.0           # cadre du ventilateur
FAN_HOLES = 124.5     # entraxe des trous (Noctua NF-A14)
FAN_HOLE_D = 5.2     # passage pour vis de ventilateur PC
FLANGE_T = 5.0
CONE_L = 45.0
OUT_D = 60.0          # diametre de sortie de la buse
VANE_T = 1.6

r_sp = (TUBE_ID - FIT) / 2  # rayon exterieur de l'embout

def frustum(z0, h, r0, r1):
    return Manifold.cylinder(h, r0, r1).translate([0, 0, z0])

# ---------- Reducteur 140 -> 76 ----------
# Bride et patte d'un seul tenant (meme epaisseur, contour arrondi), dessous plat pour le plateau.
# Trous de passage 5,2 mm : les vis de ventilateur PC classiques (ou celles fournies par Noctua)
# traversent la bride et se vissent dans le cadre du ventilateur, comme dans un boitier PC.
from manifold3d import CrossSection, JoinType
TAB_Y0, TAB_Y1 = FAN/2 - 2, FAN/2 + 50           # la patte depasse de 50 mm du cadre du ventilateur
tab2d = CrossSection([[(-10, TAB_Y0), (FAN/2, TAB_Y0), (FAN/2, TAB_Y1), (12, TAB_Y1)]])
plate2d = (CrossSection.square([FAN, FAN], True) + tab2d).offset(-5, JoinType.Round).offset(5, JoinType.Round)   # coins sortants arrondis, bords droits
plate2d = plate2d.offset(4, JoinType.Round).offset(-4, JoinType.Round).simplify(0.02)   # congés aussi dans les angles rentrants
flange = rslab(plate2d, FLANGE_T, rt=1.0, rb=0.0)
for sx in (-1, 1):
    for sy in (-1, 1):
        flange -= Manifold.cylinder(FLANGE_T+2, FAN_HOLE_D/2).translate([sx*FAN_HOLES/2, sy*FAN_HOLES/2, -1])
r_in0 = 67.0
flange -= Manifold.cylinder(FLANGE_T+2, r_in0).translate([0, 0, -1])
SLOT_Y = FAN/2 + 27                               # 27 mm du bord du ventilateur : place pour rondelle et cle
sa = Manifold.cylinder(FLANGE_T + 2, 8.6/2).translate([24, SLOT_Y, -1])
sb = Manifold.cylinder(FLANGE_T + 2, 8.6/2).translate([56, SLOT_Y, -1])
flange -= Manifold.batch_hull([sa, sb])
cone_o = frustum(FLANGE_T - 0.01, CONE_L, r_in0 + WALL, r_sp + WALL)
cone_i = frustum(FLANGE_T - 0.02, CONE_L + 0.04, r_in0, r_sp - WALL)   # interieur sans marche : pas de plafond a l entree de l embout
z_sp = FLANGE_T + CONE_L
spig = frustum(z_sp - 0.01, SPIGOT_L, r_sp, r_sp) - frustum(z_sp - 0.1, SPIGOT_L + 1, r_sp - WALL, r_sp - WALL)
reducer = flange + (cone_o - cone_i) + spig

# ---------- Buse de sortie ----------
z_c = SPIGOT_L
spig2 = frustum(0, SPIGOT_L + 1.0, r_sp, r_sp) - frustum(-1, SPIGOT_L + 3, r_sp - WALL, r_sp - WALL)
collar = frustum(z_c, 3.2, r_sp, r_sp + 3.2) + frustum(z_c + 3.2, 0.8, r_sp + 3.2, r_sp + 3.2)
collar -= frustum(z_c - 1, 6, r_sp - WALL, r_sp - WALL)
BAND_L = 16.0
BODY_L = 30.0
z_band = z_c + 3.2
band = frustum(z_band - 0.5, BAND_L + 0.5, r_sp + 3.2, r_sp + 3.2) - frustum(z_band - 1, BAND_L + 2, r_sp - WALL, r_sp - WALL)
z_b = z_band + BAND_L
r_out = OUT_D / 2
body_o = frustum(z_b, BODY_L, r_sp + 3.2, r_out + WALL)
body_i = frustum(z_b - 0.5, BODY_L + 1, r_sp - WALL, r_out)
vanes_raw = (Manifold.cube([2*r_sp, VANE_T, BODY_L - 6], center=True) +
             Manifold.cube([VANE_T, 2*r_sp, BODY_L - 6], center=True)).translate([0, 0, z_b + 6 + (BODY_L - 6)/2])
vanes = vanes_raw ^ frustum(z_b, BODY_L, r_sp - WALL + 0.5, r_out + 0.5)
nozzle = Manifold.batch_boolean([spig2, collar, band, body_o - body_i, vanes], __import__('manifold3d').OpType.Add)


# ---------- Support de buse deporte (version gauche ; la droite est son miroir) ----------
# Platine vissee sur le cote du montant SOUS le support d'ecran (2 vis M8 dans la meme rainure, a 30 mm).
# Le bras s'ecarte de ARM_X mm du montant pour passer devant la plaque du support d'ecran et ses vis,
# monte, puis tient la buse dans un collier serre par une vis M4.
ARM_T = 20.0                      # epaisseur de la piece (direction de la buse)
PLATE_H = 90.0                    # hauteur de la platine
BOLT_Z = (12.0, 78.0)             # trous M8 (entraxe 66 mm), le bras part au milieu
R_IN = r_sp + 3.2 + 0.25          # serre la bande de la buse
R_OUT = R_IN + 6.0
C = (-85.0, 180.0)                # centre du collier : ecart au montant, hauteur au-dessus du bas de la platine
# bras en courbe de Bezier : part a l'horizontale du milieu de la platine, arrive a la verticale sous le collier
P0 = (-6.0, PLATE_H/2)
P3 = (C[0], C[1] - R_OUT + 3.0)
P1 = (P0[0] - 55.0, P0[1])
P2 = (P3[0], P3[1] - 55.0)
def bez(t):
    u = 1 - t
    return (u**3*P0[0] + 3*u*u*t*P1[0] + 3*u*t*t*P2[0] + t**3*P3[0],
            u**3*P0[1] + 3*u*u*t*P1[1] + 3*u*t*t*P2[1] + t**3*P3[1])
N = 40
pts = [bez(i/N) for i in range(N + 1)]
rads = [12.0 - 4.0*(i/N) for i in range(N + 1)]          # bras effile : 24 mm a la base, 16 mm sous le collier
shape = CrossSection.square([6.0, PLATE_H]).translate([-6.0, 0.0])
for k in range(N):
    shape += CrossSection.batch_hull([CrossSection.circle(rads[k], 48).translate(pts[k]),
                                      CrossSection.circle(rads[k+1], 48).translate(pts[k+1])])
shape += CrossSection.circle(R_OUT, 160).translate(C)
shape -= CrossSection.circle(R_IN, 160).translate(C)
shape += CrossSection.square([22.0, 12.0]).translate([C[0] - 11.0, C[1] + R_OUT - 4.0])   # oreilles de serrage
shape = shape.offset(4.0, JoinType.Round).offset(-4.0, JoinType.Round).offset(-1.5, JoinType.Round).offset(1.5, JoinType.Round).simplify(0.02)
shape = shape ^ CrossSection.square([400.0, 400.0]).translate([-400.0, -10.0])   # rien ne depasse dans le profile
holder = rslab(shape, ARM_T, rt=1.5, rb=0.8).rotate([90, 0, 0]).translate([0, ARM_T/2, 0])
# fente de serrage du collier, coupee apres les arrondis pour qu'elle reste ouverte (3 mm)
holder -= Manifold.cube([3.0, ARM_T + 2, R_OUT - R_IN + 14.0]).translate([C[0] - 1.5, -ARM_T/2 - 1, C[1] + R_IN - 1.0])
for z in BOLT_Z:                                                     # trous M8 de la platine (axe x)
    holder -= Manifold.cylinder(12, 8.6/2).rotate([0, 90, 0]).translate([-9.0, 0, z])
holder -= Manifold.cylinder(40, 4.4/2).rotate([0, 90, 0]).translate([C[0] - 20.0, 0, C[1] + R_OUT + 2.0])   # vis M4

def export(m, path):
    mesh = m.to_mesh()
    t = trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3], faces=np.asarray(mesh.tri_verts), process=True)
    t.merge_vertices()
    t.export(path)
    print(path, "watertight:", t.is_watertight, "bbox:", np.round(t.bounds, 1).tolist())

export(reducer, "../stl/windsim-reducteur-gauche.stl")
export(reducer.mirror([1, 0, 0]), "../stl/windsim-reducteur-droit.stl")
# buse imprimee sortie en bas : les ailettes partent du plateau, aucun pont
nozzle_print = nozzle.mirror([0, 0, 1])
nozzle_print = nozzle_print.translate([0, 0, -nozzle_print.bounding_box()[2]])
export(nozzle_print, "../stl/windsim-buse-76.stl")
# support pose a plat sur le plateau (epaisseur de 20 mm a la verticale)
holder_flat = holder.rotate([-90, 0, 0]).translate([0, 0, ARM_T/2])
export(holder_flat, "../stl/windsim-support-buse-gauche.stl")
export(holder_flat.mirror([1, 0, 0]), "../stl/windsim-support-buse-droit.stl")
