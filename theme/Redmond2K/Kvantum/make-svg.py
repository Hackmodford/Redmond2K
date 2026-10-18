#!/usr/bin/env python3
"""Generate Redmond2K.svg for Kvantum (Qt widget style).

Every element is pixel art, 1 SVG unit = 1 logical px, so Qt's high-DPI
scaling doubles the bevels the same way GTK does. Frames are cut into the
9 Kvantum pieces (corners, edges, interior) from a small prototype grid.

All element names start with "w-" so nothing silently falls back to the
dark default Kvantum theme.  Run:  ./make-svg.py > Redmond2K.svg
"""

# Palette (keep in sync with gtk-3.0/gtk.css)
C = {
    "W": "#FFFFFF",  # light
    "F": "#D4D0C8",  # face
    "S": "#7F7F7F",  # shadow
    "D": "#3F3F3F",  # border
    "K": "#000000",
    "N": "#002468",  # selection
    "Y": "#FFFFE1",  # tooltip
}

out = []
cursor = [0, 0]
row_h = [0]
max_w = [0]


def place(w, h):
    x, y = cursor
    cursor[0] += w + 2
    max_w[0] = max(max_w[0], cursor[0])
    row_h[0] = max(row_h[0], h)
    return x, y


def newrow():
    cursor[0] = 0
    cursor[1] += row_h[0] + 4
    row_h[0] = 0


def emit(name, grid, w=None, h=None):
    """grid: list of strings, '.' = transparent. Bounds always w x h."""
    gh = len(grid)
    gw = len(grid[0]) if gh else 0
    w = w or gw
    h = h or gh
    x0, y0 = place(w, h)
    s = [f'<g id="{name}">',
         f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" opacity="0"/>']
    for y, line in enumerate(grid):
        x = 0
        while x < len(line):
            c = line[x]
            if c == ".":
                x += 1
                continue
            run = x
            while run < len(line) and line[run] == c:
                run += 1
            s.append(f'<rect x="{x0 + x}" y="{y0 + y}" width="{run - x}" '
                     f'height="1" fill="{C[c]}"/>')
            x = run
    s.append("</g>")
    out.append("".join(s))


def bevel(rings, interior, w, h):
    """rings: [(TL, BR[, tl-corners]), ...] outermost first. Bottom/right
    win at corners, like Win32 DrawEdge, unless a third item is given."""
    grid = []
    for y in range(h):
        line = ""
        for x in range(w):
            r = min(x, y, w - 1 - x, h - 1 - y)
            if r >= len(rings):
                line += interior
                continue
            tl, br = rings[r][:2]
            is_br = x == w - 1 - r or y == h - 1 - r
            # Win2K raised edges: the top-left colour of each ring also
            # takes that ring's top-right and bottom-left corners.
            if len(rings[r]) > 2 and (x, y) in ((w - 1 - r, r), (r, h - 1 - r)):
                is_br = False
            line += br if is_br else tl
        grid.append(line)
    return grid


def frame(name, state, rings, interior=".", sides=None):
    """Emit the 9 pieces of a frame from a (2f+1)^2 prototype."""
    f = len(rings)
    n = 2 * f + 1
    g = bevel(rings, interior, n, n)
    pre = f"{name}-{state}"
    col = lambda x0, x1, y0, y1: [l[x0:x1] for l in g[y0:y1]]
    emit(pre, [interior], 1, 1)
    emit(f"{pre}-top", col(f, f + 1, 0, f))
    emit(f"{pre}-bottom", col(f, f + 1, f + 1, n))
    emit(f"{pre}-left", col(0, f, f, f + 1))
    emit(f"{pre}-right", col(f + 1, n, f, f + 1))
    emit(f"{pre}-topleft", col(0, f, 0, f))
    emit(f"{pre}-topright", col(f + 1, n, 0, f))
    emit(f"{pre}-bottomleft", col(0, f, f + 1, n))
    emit(f"{pre}-bottomright", col(f + 1, n, f + 1, n))
    newrow()


RAISED = [("F", "D", "tl-corners"), ("W", "S", "tl-corners")]  # face then highlight, like Win2K EDGE_RAISED
SUNKEN = [("S", "W"), ("D", "F")]
ETCHED = [("S", "W"), ("W", "S")]

# Push buttons: 3px frame so the default button's black ring fits inside
# the same outer size, as on Win2K.
frame("w-button", "normal", RAISED + [("F", "F")], "F")
frame("w-button", "pressed", [("K", "K"), ("S", "S"), ("F", "F")], "F")
frame("w-button", "toggled", SUNKEN + [("F", "F")], "F")
pre = "w-button-default"
g = bevel([("K", "K")] + RAISED, "F", 7, 7)
emit(pre, ["."], 1, 1)
for side, (x0, x1, y0, y1) in {
        "top": (3, 4, 0, 3), "bottom": (3, 4, 4, 7), "left": (0, 3, 3, 4),
        "right": (4, 7, 3, 4), "topleft": (0, 3, 0, 3), "topright": (4, 7, 0, 3),
        "bottomleft": (0, 3, 4, 7), "bottomright": (4, 7, 4, 7)}.items():
    emit(f"{pre}-{side}", [l[x0:x1] for l in g[y0:y1]])
newrow()
emit("button-default-indicator", ["."], 1, 1)  # fixed name; hide default's

# Small raised buttons: tool, header, spin, drop-down, scrollbar thumb.
frame("w-sbutton", "normal", RAISED, "F")
frame("w-sbutton", "pressed", [("S", "S"), ("F", "F")], "F")
frame("w-sbutton", "toggled", SUNKEN, "F")
# Toolbar buttons: flat, thin 1px bevel on hover/press (ring 2 empty).
frame("w-tbutton", "normal", [(".", "."), (".", ".")], ".")
frame("w-tbutton", "focused", [("W", "S"), (".", ".")], ".")
frame("w-tbutton", "pressed", [("S", "W"), (".", ".")], ".")
frame("w-tbutton", "toggled", [("S", "W"), (".", ".")], ".")

frame("w-lineedit", "normal", SUNKEN, "W")
frame("w-common", "normal", SUNKEN, ".")
frame("w-group", "normal", ETCHED, ".")
# Tab pane: white on the outermost edge (unlike buttons) so it lines up
# with the tabs' outer white edge.
frame("w-tabframe", "normal", [("W", "D"), ("F", "S")], "F")
frame("w-menu", "normal", [("F", "D"), ("W", "S"), ("F", "F")], "F")
frame("w-menubaritem", "focused", [("W", "S")], ".")
frame("w-menubaritem", "pressed", [("S", "W")], ".")
frame("w-menubaritem", "toggled", [("S", "W")], ".")
frame("w-progress", "normal", [("S", "W"), ("F", "F")], "F")
frame("w-tooltip", "normal", [("K", "K")], "Y")
frame("w-slider", "normal", SUNKEN, "F")

# Tabs (top orientation, no bottom frame): chamfered corners like Win2K.
# The top frame is 4px: the selected tab uses all of it, unselected tabs
# leave 2px empty so the selected one stands 2px taller.
TAB_TOP = {
    "toggled": (["..", ".W", "WF", "WF"], ["W", "F", "F", "F"],
                ["..", "D.", "SD", "SD"]),
    "normal": (["..", "..", "..", ".W"], [".", ".", "W", "F"],
               ["..", "..", "..", "D."]),
}
for st, (tl, top, tr) in TAB_TOP.items():
    p = f"w-tab-{st}"
    emit(p, ["F"])
    emit(f"{p}-top", top)
    emit(f"{p}-left", ["WF"])
    emit(f"{p}-right", ["SD"])
    emit(f"{p}-topleft", tl)
    emit(f"{p}-topright", tr)
    for s in ("bottom", "bottomleft", "bottomright"):
        emit(f"{p}-{s}", ["."], 1, 1)
    newrow()

# Scrollbar
emit("w-groove-normal", ["WF", "FW"])  # dithered trough
frame("w-thumb", "normal", RAISED, "F")
emit("w-grip-normal", ["."], 1, 1)
newrow()


def tri(direction, size, ox, oy):
    """7x4 Win2K arrow, apex pointing `direction`, top-left at ox,oy."""
    px = set()
    for i in range(4):
        for j in range(i, 7 - i):
            if direction == "down":
                px.add((ox + j, oy + i))
            elif direction == "up":
                px.add((ox + j, oy + 3 - i))
            elif direction == "right":
                px.add((ox + i, oy + j))
            else:
                px.add((ox + 3 - i, oy + j))
    return px


def paint(base, pts, c):
    g = [list(l) for l in base]
    for x, y in pts:
        if 0 <= y < len(g) and 0 <= x < len(g[0]):
            g[y][x] = c
    return ["".join(l) for l in g]


def arrow_origin(d, box):
    """Centre a 7x4 (or 4x7) arrow in a box; Win2K biases down/right."""
    if d in ("up", "down"):
        return (box - 7) // 2, (box - 4) // 2
    return (box - 4) // 2, (box - 7) // 2


DIRS = ("up", "down", "left", "right")

# 16x16 scrollbar / combo buttons with the arrow baked in.
for d in DIRS:
    ox, oy = arrow_origin(d, 16)
    up = bevel(RAISED, "F", 16, 16)
    dn = bevel([("S", "S"), ("F", "F")], "F", 16, 16)
    emit(f"w-sarrow-{d}-normal", paint(up, tri(d, 16, ox, oy), "K"))
    emit(f"w-sarrow-{d}-pressed", paint(dn, tri(d, 16, ox + 1, oy + 1), "K"))
    dis = paint(up, tri(d, 16, ox + 1, oy + 1), "W")
    emit(f"w-sarrow-{d}-disabled", paint(dis, tri(d, 16, ox, oy), "S"))
    if d == "down":
        emit("w-carrow-normal", paint(up, tri(d, 16, ox, oy), "K"))
        emit("w-carrow-pressed", paint(dn, tri(d, 16, ox + 1, oy + 1), "K"))
        emit("w-carrow-disabled", paint(dis, tri(d, 16, ox, oy), "S"))
newrow()

# Spin buttons: Kvantum joins the field and both buttons into one control and
# draws no edges between them, but each arrow is a 16x16 square filling its
# button between the top/bottom frames. So the arrow element carries the
# middle 16 rows of a whole 16x20 button, side bevels included.
for d, rows in (("up", ((7, 7), (6, 8), (5, 9))),
                ("down", ((5, 9), (6, 8), (7, 7)))):
    pts = {(x, 6 + i) for i, (a, b) in enumerate(rows) for x in range(a, b + 1)}
    shift = {(x + 1, y + 1) for x, y in pts}
    up = bevel(RAISED, "F", 16, 20)[2:18]
    dn = bevel([("S", "S"), ("F", "F")], "F", 16, 20)[2:18]
    emit(f"w-spin-{d}-normal", paint(up, pts, "K"))
    emit(f"w-spin-{d}-pressed", paint(dn, shift, "K"))
    emit(f"w-spin-{d}-disabled", paint(paint(up, shift, "W"), pts, "S"))
newrow()

# Bare 8x8 arrows (spin, drop-down, headers, menus).
blank8 = ["." * 8] * 8
for d in DIRS:
    ox, oy = arrow_origin(d, 7)
    emit(f"w-arrow-{d}-normal", paint(blank8, tri(d, 8, ox, oy), "K"))
    emit(f"w-arrow-{d}-focused", paint(blank8, tri(d, 8, ox, oy), "K"))
    emit(f"w-arrow-{d}-pressed", paint(blank8, tri(d, 8, ox + 1, oy + 1), "K"))
    dis = paint(blank8, tri(d, 8, ox + 1, oy + 1), "W")
    emit(f"w-arrow-{d}-disabled", paint(dis, tri(d, 8, ox, oy), "S"))
    if d in ("left", "right"):  # submenu arrows, white on the selection
        emit(f"w-menuitem-{d}-normal", paint(blank8, tri(d, 8, ox, oy), "K"))
        emit(f"w-menuitem-{d}-focused", paint(blank8, tri(d, 8, ox, oy), "W"))
        emit(f"w-menuitem-{d}-disabled", paint(blank8, tri(d, 8, ox, oy), "S"))
newrow()

# Check boxes and radio buttons (13x13 cell).
CHECK = ["......X", ".....XX", "X...XXX", "XX.XXX.", "XXXXX..", ".XXX...",
         "..X...."]
check_pts = {(3 + x, 3 + y) for y, l in enumerate(CHECK)
             for x, c in enumerate(l) if c == "X"}
box = bevel(SUNKEN, "W", 13, 13)
emit("w-check-normal", box)
emit("w-check-checked-normal", paint(box, check_pts, "K"))
emit("w-check-tristate-normal", paint(box, check_pts, "S"))
blank13 = ["." * 13] * 13
emit("menu-w-check-normal", blank13)
emit("menu-w-check-checked-normal", paint(blank13, check_pts, "K"))
emit("menu-w-check-checked-focused", paint(blank13, check_pts, "W"))
emit("menu-w-check-tristate-normal", paint(blank13, check_pts, "S"))

RADIO = ["....SSSS.....", "..SSDDDDSS...", ".SDDWWWWDDW..", ".SDWWWWWWFW..",
         "SDWWWWWWWWFW.", "SDWWWWWWWWFW.", "SDWWWWWWWWFW.", "SDWWWWWWWWFW.",
         ".SDWWWWWWFW..", ".SFFWWWWFFW..", "..WWFFFFWW...", "....WWWW.....",
         "............."]
dot = {(x, y) for y in range(4, 8) for x in range(4, 8)} - {
    (4, 4), (7, 4), (4, 7), (7, 7)}
emit("w-radio-normal", RADIO)
emit("w-radio-checked-normal", paint(RADIO, dot, "K"))
emit("menu-w-radio-normal", blank13)
emit("menu-w-radio-checked-normal", paint(blank13, dot, "K"))
emit("menu-w-radio-checked-focused", paint(blank13, dot, "W"))
newrow()

# Menus
emit("w-menuitem-focused", ["N"])
emit("w-menuitem-pressed", ["N"])
emit("w-menuitem-toggled", ["N"])
emit("w-menuitem-separator", [".", ".", ".", "S", "W", ".", ".", ".", "."])

# Item views: no hover, navy selection.
emit("w-itemview-normal", ["."])
emit("w-itemview-focused", ["."])
emit("w-itemview-pressed", ["N"])
emit("w-itemview-toggled", ["N"])
newrow()

# Toolbar: invisible interior (makes it "stylable" so ToolbarButton applies),
# raised handle bar and etched separator.
emit("w-toolbar-normal", ["F"])
emit("w-toolbar-handle", ["..WFS..."])
emit("w-toolbar-separator", [".SW."])
emit("header-separator", ["SD"])  # fixed name
emit("w-progress-pattern-normal", ["NNNNNNNN.."])
emit("w-slidercursor-normal", bevel(RAISED, "F", 11, 11))
emit("w-splitter-normal", ["."])
emit("w-splitter-grip-normal", ["."])

# Focus: 1px dotted rectangle (tiled every 2px).
emit("w-focus-top", ["K."])
emit("w-focus-bottom", ["K."])
emit("w-focus-left", ["K", "."])
emit("w-focus-right", ["K", "."])
for c in ("topleft", "topright", "bottomleft", "bottomright"):
    emit(f"w-focus-{c}", ["K"])
newrow()

# Tree expander: 9x9 boxed +/-
tb = bevel([("S", "S")], "W", 9, 9)
minus = {(x, 4) for x in range(2, 7)}
emit("w-tree-minus-normal", paint(tb, minus, "K"))
emit("w-tree-plus-normal", paint(tb, minus | {(4, y) for y in range(2, 7)}, "K"))

# Size grip: three diagonal ridges, bottom-right corner.
sg = []
for y in range(12):
    l = ""
    for x in range(12):
        k = x + y - 11
        l += {1: "W", 2: "S", 3: "S"}.get(k % 4, ".") if 0 < k <= 12 else "."
    sg.append(l)
emit("w-sizegrip-normal", sg)
newrow()

W = max_w[0]
H = cursor[1] + row_h[0] + 4
print(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
      f'viewBox="0 0 {W} {H}" shape-rendering="crispEdges">')
print("\n".join(out))
print("</svg>")
