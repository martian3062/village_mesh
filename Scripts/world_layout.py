"""Engine-independent seeded world geometry; all lengths are centimeters."""
import math
import random


def height(x, y):
    radius = math.hypot(x, y)
    blend = min(1.0, max(0.0, (radius - 17000.0) / 16000.0))
    blend = blend * blend * (3.0 - 2.0 * blend)
    hills = 700.0 + 650.0 * math.sin(x / 9500.0) * math.cos(y / 12000.0)
    hills += 220.0 * math.sin((x + y) / 3600.0)
    return blend * hills


def write_terrain(path, cells=128, extent=64000.0):
    """Z-up OBJ; Interchange reflects OBJ Y when converting handedness."""
    with open(path, "w") as stream:
        stream.write("o VillageTerrain\n")
        for j in range(cells + 1):
            for i in range(cells + 1):
                x = -extent + 2.0 * extent * i / cells
                y = -extent + 2.0 * extent * j / cells
                stream.write(f"v {x:.3f} {-y:.3f} {height(x, y):.3f}\n")
                stream.write(f"vt {x / 400.0:.5f} {y / 400.0:.5f}\n")
        for j in range(cells):
            for i in range(cells):
                a = j * (cells + 1) + i + 1
                b, c, d = a + 1, a + cells + 1, a + cells + 2
                stream.write(f"f {a}/{a} {d}/{d} {b}/{b}\nf {a}/{a} {c}/{c} {d}/{d}\n")


def write_groundcover(path, clear_site=None):
    rng = random.Random(604)
    plots = house_plots()
    vertices, faces = [], []
    for _ in range(18000):
        x, y = rng.uniform(-33000, 33000), rng.uniform(-33000, 33000)
        if clear_site and not clear_site(x,y,80):
            continue
        if not clear_site and 16500 < x < 22500 and -3500 < y < 5500:
            continue  # irrigation pond
        if not clear_site and abs(x) < 17000 and abs(y) < 17000:
            if min(abs(y - lane) for lane in (-12500, -7500, 0, 7500, 12500)) < 650:
                continue
            if min(abs(x - lane) for lane in (-12500, -7500, -2500, 2500, 7500, 12500)) < 600:
                continue
            if any(abs(x - px) < 850 and abs(y - py) < 750 for px, py, *_ in plots):
                continue
        z = height(x, y) + 3
        for blade in range(3):
            angle = rng.uniform(0, math.tau)
            dx, dy = math.cos(angle) * 15, math.sin(angle) * 15
            h = rng.uniform(35, 110)
            start = len(vertices) + 1
            vertices.extend(((x-dx, -y+dy, z), (x+dx, -y-dy, z),
                             (x+dx*1.5, -y-dy*1.5, z+h)))
            faces.append((start, start+1, start+2))
    with open(path, "w") as stream:
        stream.write("o VillageGroundcover\n")
        stream.write("vt 0 0\nvt 1 0\nvt 0.7 1\n")
        for vertex in vertices:
            stream.write("v %.3f %.3f %.3f\n" % vertex)
        for face in faces:
            stream.write("f %d/1 %d/2 %d/3\n" % face)


def house_plots():
    plots = []
    for row, y in enumerate((-10000, -5000, 5000, 10000)):
        for col, x in enumerate((-10000, -5000, 0, 5000, 10000)):
            plots.append((x, y, 0 if y > 0 else 180, 950, 800, 1 + (row + col) % 2, len(plots)))
    return plots
