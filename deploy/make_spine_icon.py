#!/usr/bin/env python3
"""Render the Growing Spine icon (spine + sprouts) to a 256x256 PNG.

Usage:  python3 make_spine_icon.py [output_path]
Default output is growing-spine.png next to this script. On the laptop the icon
is deployed to ~/.local/share/icons/growing-spine.png (see README.md).
Same design the observer draws at runtime in observer.py:_make_spine_icon()."""
import sys, os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # no display needed
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage, QPainter, QColor, QPen, QBrush, QPainterPath
from PyQt6.QtCore import Qt


def main():
    out = (sys.argv[1] if len(sys.argv) > 1
           else os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "growing-spine.png"))
    app = QApplication(sys.argv)
    S, k = 256, 4   # 256px canvas, 4x the 64px design
    img = QImage(S, S, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    bone  = QColor("#D4A853"); cord = QColor("#9B6E3A")
    green = QColor("#5CB85C"); leaf = QColor("#4CAF50"); dark = QColor("#3E2A0A")
    p.setPen(QPen(cord, 2.0*k, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(32*k, 22*k, 32*k, 60*k)
    p.setPen(QPen(dark, 1.0*k)); p.setBrush(QBrush(bone))
    for i in range(4):
        p.drawRoundedRect(19*k, (24 + i*10)*k, 26*k, 6*k, 3*k, 3*k)
    p.setPen(QPen(green, 2.5*k, Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(32*k, 22*k, 32*k, 8*k)
    lft = QPainterPath(); lft.moveTo(32*k, 20*k)
    lft.cubicTo(30*k, 15*k, 21*k, 13*k, 15*k, 8*k); p.drawPath(lft)
    rgt = QPainterPath(); rgt.moveTo(32*k, 20*k)
    rgt.cubicTo(34*k, 15*k, 43*k, 13*k, 49*k, 8*k); p.drawPath(rgt)
    p.setPen(QPen(dark, 0.5*k)); p.setBrush(QBrush(leaf))
    p.drawEllipse(28*k, 4*k, 9*k, 6*k)
    p.drawEllipse(11*k, 5*k, 8*k, 6*k)
    p.drawEllipse(45*k, 5*k, 8*k, 6*k)
    p.end()
    print("SAVED" if img.save(out) else "FAILED", out)


if __name__ == "__main__":
    main()
