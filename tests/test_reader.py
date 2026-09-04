from PIL import Image

from ventanita import reader

BADGE = (33, 192, 99)
DARK = (17, 27, 33)


def _column(height, badge_rows, width=4):
    """A synthetic strip of the chat list: dark background, badge-green on
    the given y ranges, badge drawn slightly off-center like the real thing."""
    img = Image.new("RGB", (width, height), DARK)
    for top, bottom in badge_rows:
        for y in range(top, bottom):
            img.putpixel((width - 2, y), BADGE)
    return img


def test_cluster_rows_collapses_one_badge_into_one_row():
    ys = list(range(10, 30))  # a 20px-tall badge lights up 20 rows
    assert reader.cluster_rows(ys, row_height=80) == [10]


def test_cluster_rows_keeps_badges_on_separate_rows():
    ys = list(range(10, 30)) + list(range(100, 120)) + list(range(190, 210))
    assert reader.cluster_rows(ys, row_height=80) == [10, 100, 190]


def test_cluster_rows_empty():
    assert reader.cluster_rows([], row_height=80) == []


def test_badge_pixel_rows_finds_every_green_row():
    img = _column(60, [(5, 10), (40, 45)])
    assert reader.badge_pixel_rows(img) == [5, 6, 7, 8, 9, 40, 41, 42, 43, 44]


def test_badge_pixel_rows_ignores_near_miss_colors():
    img = Image.new("RGB", (4, 10), (33, 150, 99))  # green channel off by > tolerance
    assert reader.badge_pixel_rows(img) == []


def test_two_badges_two_rows_end_to_end_on_synthetic_image():
    img = _column(300, [(30, 50), (120, 140)])
    rows = reader.cluster_rows(reader.badge_pixel_rows(img), row_height=90)
    assert rows == [30, 120]
