import os
import math
import itertools
import functools
from typing import Iterator, Callable

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.collections import PatchCollection

# ---------------------------------------------------------------------------
# Тип: полигон — кортеж кортежей координат
# ---------------------------------------------------------------------------

Polygon = tuple  # tuple[tuple[float, float], ...]


# ===========================================================================
# 1. ВИЗУАЛИЗАЦИЯ
# ===========================================================================


def visualize(
    polygons_iter: Iterator[Polygon],
    title: str = "Polygons",
    ax: plt.Axes = None,
    show: bool = True,
) -> None:
    polygons = list(polygons_iter)
    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(8, 6))

    patches = [MplPolygon(list(p), closed=True) for p in polygons]
    coll = PatchCollection(
        patches,
        alpha=0.4,
        facecolors=plt.cm.tab20.colors[: len(patches)],
        edgecolors="black",
        linewidths=1,
    )
    ax.add_collection(coll)
    ax.autoscale_view()
    ax.set_aspect("equal")
    ax.set_title(title)

    if standalone and show:
        plt.tight_layout()
        plt.savefig("output/polygons_visual.png", dpi=100)
        plt.close()


# ===========================================================================
# 2. ГЕНЕРАТОРЫ БЕСКОНЕЧНЫХ ПОСЛЕДОВАТЕЛЬНОСТЕЙ
# ===========================================================================


def gen_rectangle(
    w: float = 1.0, h: float = 1.0, gap: float = 0.2
) -> Iterator[Polygon]:
    """Генерирует прямоугольники"""
    x = 0.0
    while True:
        yield ((x, 0), (x + w, 0), (x + w, h), (x, h))
        x += w + gap


def gen_triangle(side: float = 1.0, gap: float = 0.2) -> Iterator[Polygon]:
    h = side * math.sqrt(3) / 2
    x = 0.0
    while True:
        yield ((x, 0), (x + side, 0), (x + side / 2, h))
        x += side + gap


def gen_hexagon(r: float = 1.0, gap: float = 0.2) -> Iterator[Polygon]:
    dx = r * math.sqrt(3) + gap
    cx = r
    while True:
        verts = tuple(
            (
                cx + r * math.cos(math.radians(60 * i + 30)),
                r * math.sin(math.radians(60 * i + 30)),
            )
            for i in range(6)
        )
        yield verts
        cx += dx


# ===========================================================================
# 3. ТРАНСФОРМАЦИИ
# ===========================================================================


def tr_translate(dx: float, dy: float) -> Callable[[Polygon], Polygon]:
    """Поворот"""
    return lambda poly: tuple((x + dx, y + dy) for x, y in poly)


def tr_rotate(
    angle_deg: float, cx: float = 0.0, cy: float = 0.0
) -> Callable[[Polygon], Polygon]:
    """Поворот на angle_deg градусов относительно точки"""
    rad = math.radians(angle_deg)
    cos_a, sin_a = math.cos(rad), math.sin(rad)

    def rotate(poly: Polygon) -> Polygon:
        result = []
        for x, y in poly:
            x -= cx
            y -= cy
            result.append((x * cos_a - y * sin_a + cx, x * sin_a + y * cos_a + cy))
        return tuple(result)

    return rotate


def tr_symmetry(axis: str = "x", val: float = 0.0) -> Callable[[Polygon], Polygon]:
    if axis == "x":
        return lambda poly: tuple((x, 2 * val - y) for x, y in poly)
    return lambda poly: tuple((2 * val - x, y) for x, y in poly)


def tr_homothety(
    k: float, cx: float = 0.0, cy: float = 0.0
) -> Callable[[Polygon], Polygon]:
    return lambda poly: tuple((cx + k * (x - cx), cy + k * (y - cy)) for x, y in poly)


# ===========================================================================
# 5. ФИЛЬТРЫ  (возвращают True/False для filter)
# ===========================================================================


def _polygon_area(poly: Polygon) -> float:
    n = len(poly)
    return (
        abs(
            sum(
                poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1]
                for i in range(n)
            )
        )
        / 2
    )


def _side_lengths(poly: Polygon) -> list:
    """Длины сторон полигона"""
    n = len(poly)
    return [
        math.hypot(poly[(i + 1) % n][0] - poly[i][0], poly[(i + 1) % n][1] - poly[i][1])
        for i in range(n)
    ]


def flt_convex_polygon(poly: Polygon) -> bool:
    """Тру, если полигон выпуклый"""
    n = len(poly)
    if n < 3:
        return False
    sign = None
    for i in range(n):
        ax = poly[(i + 1) % n][0] - poly[i][0]
        ay = poly[(i + 1) % n][1] - poly[i][1]
        bx = poly[(i + 2) % n][0] - poly[(i + 1) % n][0]
        by = poly[(i + 2) % n][1] - poly[(i + 1) % n][1]
        cross = ax * by - ay * bx
        if cross != 0:
            cur = 1 if cross > 0 else -1
            if sign is None:
                sign = cur
            elif sign != cur:
                return False
    return True


def flt_angle_point(point: tuple) -> Callable[[Polygon], bool]:
    """Тру, если у полигона есть вершина в заданной точке"""
    return lambda poly: any(
        math.isclose(x, point[0]) and math.isclose(y, point[1]) for x, y in poly
    )


def flt_square(max_area: float) -> Callable[[Polygon], bool]:
    """True, если площадь полигона меньше max_area."""
    return lambda poly: _polygon_area(poly) < max_area


def flt_short_side(max_side: float) -> Callable[[Polygon], bool]:
    """True, если кратчайшая сторона меньше max_side."""
    return lambda poly: min(_side_lengths(poly)) < max_side


def flt_point_inside(point: tuple) -> Callable[[Polygon], bool]:
    """Тру, если точка находится внутри выпуклого полигона"""
    px, py = point

    def inside(poly: Polygon) -> bool:
        if not flt_convex_polygon(poly):
            return False
        n = len(poly)
        crossings = 0
        for i in range(n):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % n]
            if ((y1 <= py < y2) or (y2 <= py < y1)) and px < x1 + (py - y1) / (
                y2 - y1
            ) * (x2 - x1):
                crossings += 1
        return crossings % 2 == 1

    return inside


def flt_polygon_angles_inside(ref_poly: Polygon) -> Callable[[Polygon], bool]:
    """Тру, если хотя бы одна вершина ref_poly находится внутри полигона"""

    def check(poly: Polygon) -> bool:
        return any(flt_point_inside(v)(poly) for v in ref_poly)

    return check


# ===========================================================================
# 7. ДЕКОРАТОРЫ
# ===========================================================================


def decorator_filter(filter_fn: Callable) -> Callable:
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            new_args = [
                (
                    filter(filter_fn, a)
                    if hasattr(a, "__iter__") and not isinstance(a, (str, tuple))
                    else a
                )
                for a in args
            ]
            return func(*new_args, **kwargs)

        return wrapper

    return decorator


def decorator_transform(transform_fn: Callable) -> Callable:
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            new_args = [
                (
                    map(transform_fn, a)
                    if hasattr(a, "__iter__") and not isinstance(a, (str, tuple))
                    else a
                )
                for a in args
            ]
            return func(*new_args, **kwargs)

        return wrapper

    return decorator


# ===========================================================================
# 8. АГРЕГИРУЮЩИЕ ФУНКЦИИ (все 5, доп. задание 4 + 5)
# ===========================================================================


def agr_origin_nearest(polygons: list[Polygon]) -> tuple:
    """Вершина, ближайшая к началу координат, среди всех полигонов"""
    all_pts = list(itertools.chain.from_iterable(polygons))
    return functools.reduce(
        lambda a, b: a if math.hypot(*a) <= math.hypot(*b) else b, all_pts
    )


def agr_max_side(polygons: list[Polygon]) -> float:
    """Длина самой длинной стороны среди всех полигонов"""
    all_sides = list(itertools.chain.from_iterable(map(_side_lengths, polygons)))
    return functools.reduce(lambda a, b: a if a >= b else b, all_sides)


def agr_min_area(polygons: list[Polygon]) -> float:
    """Минимальная площадь среди всех полигонов"""
    return functools.reduce(
        lambda a, b: a if a <= b else b, map(_polygon_area, polygons)
    )


def agr_perimeter(polygons: list[Polygon]) -> float:
    """Суммарный периметр всех полигонов"""
    return functools.reduce(
        lambda acc, poly: acc + sum(_side_lengths(poly)), polygons, 0.0
    )


def agr_area(polygons: list[Polygon]) -> float:
    """Площадь всех полигонов"""
    return functools.reduce(lambda acc, poly: acc + _polygon_area(poly), polygons, 0.0)


# ===========================================================================
# ДЕМОНСТРАЦИЯ
# ===========================================================================

os.makedirs("output", exist_ok=True)

# Рис 1: 7 фигур трёх типов (itertools.islice + chain)
rects = list(itertools.islice(gen_rectangle(1, 0.6), 7))
tris = list(itertools.islice(gen_triangle(1.0), 7))
hexs = list(itertools.islice(gen_hexagon(0.6), 7))

tris_shifted = list(map(tr_translate(0, 2.5), tris))
hexs_shifted = list(map(tr_translate(0, 5.5), hexs))

fig, ax = plt.subplots(figsize=(10, 7))
visualize(
    iter(rects + tris_shifted + hexs_shifted),
    title="7 прямоугольников, 7 треугольников, 7 шестиугольников",
    ax=ax,
    show=False,
)
plt.tight_layout()
plt.savefig("output/fig1_generators.png", dpi=100)
plt.close()

# Рис. 2: Трансформации
base = list(itertools.islice(gen_rectangle(1, 0.5), 6))

band1 = list(map(tr_rotate(20), base))
band2 = list(map(tr_translate(0, 4), map(tr_rotate(20), base)))
band3 = list(map(tr_translate(0, 8), map(tr_rotate(20), base)))

crossing1 = list(map(tr_rotate(30, 3, 3), base))
crossing2 = list(map(tr_translate(2, 2), map(tr_rotate(-30, 3, 3), base)))

tris2 = list(itertools.islice(gen_triangle(1.0), 6))
sym_tris = list(map(tr_symmetry("x", 0), tris2))
sym_tris_shifted = list(map(tr_translate(0, -2), sym_tris))

scales = [0.5, 0.7, 1.0, 1.3, 1.7]
base_quad = ((0.5, 0.5), (1.5, 0.5), (1.5, 1.5), (0.5, 1.5))
scaled_quads = list(map(lambda k: tr_homothety(k)(base_quad), scales))

fig, axes = plt.subplots(2, 2, figsize=(12, 10))


def _draw(ax, polys, title):
    visualize(iter(polys), title=title, ax=ax, show=False)


_draw(axes[0, 0], band1 + band2 + band3, "Три параллельные ленты под углом")
_draw(axes[0, 1], crossing1 + crossing2, "Две пересекающиеся ленты")
_draw(axes[1, 0], tris2 + sym_tris_shifted, "Симметричные ленты треугольников")
_draw(axes[1, 1], scaled_quads, "Четырёхугольники в разном масштабе")

plt.tight_layout()
plt.savefig("output/fig2_transforms.png", dpi=100)
plt.close()

# Доп. задание 2: все 3 сценария фильтрации

# Сценарий 1: ровно 6 фигур из band1+band2+band3
all_bands = band1 + band2 + band3
filtered_6 = list(itertools.islice(filter(flt_convex_polygon, iter(all_bands)), 6))

# Сценарий 2: ≤4 фигуры с кратчайшей стороной
# < 0.55 из ≥15 фигур разного масштаба
many_scaled = list(
    map(
        lambda k: tr_homothety(k)(base_quad),
        [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0, 1.2, 1.5, 1.8, 2.0, 2.5, 3.0, 3.5, 4.0],
    )
)
small_side_4 = list(
    itertools.islice(filter(flt_short_side(0.55), iter(many_scaled)), 4)
)

# Сценарий 3: фильтрация ≥15 пересекающихся фигур — отбираем выпуклые
many_mixed = list(itertools.islice(gen_hexagon(0.5, 0.1), 15)) + scaled_quads
convex_only = list(filter(flt_convex_polygon, iter(many_mixed)))

# Доп. задание 8: агрегирующие функции
sample_polys = rects + tris + hexs
print("Ближайшая вершина к (0,0):", agr_origin_nearest(sample_polys))
print("Макс. сторона:            ", round(agr_max_side(sample_polys), 4))
print("Мин. площадь:             ", round(agr_min_area(sample_polys), 4))
print("Суммарный периметр:       ", round(agr_perimeter(sample_polys), 4))
print("Суммарная площадь:        ", round(agr_area(sample_polys), 4))

# Демонстрация декораторов


@decorator_filter(flt_convex_polygon)
def show_convex(polygons_iter):
    return list(polygons_iter)


@decorator_transform(tr_translate(5, 0))
def shift_right(polygons_iter):
    return list(polygons_iter)


convex_demo = show_convex(iter(many_mixed))
shifted_demo = shift_right(iter(rects))

print("Выпуклых фигур в many_mixed:", len(convex_demo))
print("Первый shifted rect:", shifted_demo[0])

print("Все файлы сохранены в output/")
