# src/renderer.py
"""
Complete renderer used by the prototype.
Provides MoviePyRenderer with support for:
 - generic shapes (circle, rectangle, triangle, arrow, text)
 - wave (sine) plotting with moving point
 - parabola plotting for quadratic visuals (parabola, vertex, roots)
 - sorting bar visualization (rectangle bars + compare/swap animation)
 - labels and simple transitions (fade, scale)
This single-file implementation replaces any fragmentary versions you may have.
"""
from moviepy.editor import VideoClip
from PIL import Image, ImageDraw, ImageFont
import os
import math
import re
import numpy as np
from typing import Dict, Any, List, Tuple

DEFAULT_FPS = 24
DEFAULT_SIZE = (960, 540)

COLOR_MAP = {
    "default": (30, 144, 255),
    "accent": (255, 165, 0),
    "highlight": (255, 215, 0),
    "green": (34, 139, 34),
    "red": (220, 20, 60),
    "gray": (180, 180, 180),
    "white": (255,255,255)
}

def _element_positions(num: int, size: Tuple[int,int]) -> List[Tuple[int,int]]:
    w, h = size
    positions = []
    gap = max(120, w // (num + 1))
    start_x = (w - gap*(num-1))//2 if num>1 else w//2
    for i in range(num):
        x = start_x + i*gap
        positions.append((x, h//2))
    return positions

def _lerp(a, b, t):
    return a + (b - a) * t

def text_size(draw: ImageDraw.Draw, text: str, font: ImageFont.ImageFont) -> Tuple[int,int]:
    try:
        return draw.textsize(text, font=font)
    except Exception:
        try:
            bbox = draw.textbbox((0,0), text, font=font)
            return (bbox[2] - bbox[0], bbox[3] - bbox[1])
        except Exception:
            try:
                return font.getsize(text)
            except Exception:
                return (len(text) * 6, 12)

def _draw_shape(draw: ImageDraw.Draw, el: Dict[str,Any], pos: Tuple[int,int], color: Tuple[int,int,int], scale: float=1.0, opacity: float=1.0, font=None):
    x, y = pos
    kind = (el.get("type") or "circle").lower()
    col = tuple(int(c * opacity) for c in color)
    if kind == "circle":
        r = int(40 * scale)
        draw.ellipse([x-r, y-r, x+r, y+r], fill=col, outline=(0,0,0))
    elif kind == "rectangle":
        w, h = int(80*scale), int(120*scale)
        draw.rectangle([x-w//2, y-h//2, x+w//2, y+h//2], fill=col, outline=(0,0,0))
    elif kind == "triangle":
        pts = [(x, y-int(60*scale)), (x-int(50*scale), y+int(30*scale)), (x+int(50*scale), y+int(30*scale))]
        draw.polygon(pts, fill=col, outline=(0,0,0))
    elif kind in ("text", "equation"):
        fnt = font or ImageFont.load_default()
        txt = el.get("description","").replace("_"," ")
        w_txt, h_txt = text_size(draw, txt, fnt)
        draw.text((x - w_txt//2, y - h_txt//2), txt, font=fnt, fill=col)
    elif kind == "arrow":
        dx = int(60*scale)
        draw.line([x-dx, y, x+dx, y], fill=col, width=max(3,int(4*scale)))
        draw.polygon([(x+dx,y), (x+dx-10*scale,y-8*scale), (x+dx-10*scale,y+8*scale)], fill=col)
    elif kind == "line":
        draw.line([50, pos[1]+60, DEFAULT_SIZE[0]-50, pos[1]+60], fill=col, width=2)
    elif kind == "wave":
        # wave drawn separately by _draw_wave
        pass
    elif kind == "parabola":
        # parabola drawn separately by _draw_parabola
        pass
    else:
        r = int(30 * scale)
        draw.ellipse([x-r, y-r, x+r, y+r], fill=col, outline=(0,0,0))

def _draw_label(draw: ImageDraw.Draw, text: str, pos: Tuple[int,int], color=(255,255,255), font=None):
    fnt = font or ImageFont.load_default()
    w_txt, h_txt = text_size(draw, text, fnt)
    # solid background rectangle
    bg_box = [pos[0]-w_txt//2-6, pos[1]-h_txt//2-3, pos[0]+w_txt//2+6, pos[1]+h_txt//2+3]
    draw.rectangle(bg_box, fill=(0,0,0))
    draw.text((pos[0]-w_txt//2, pos[1]-h_txt//2), text, font=fnt, fill=color)

def _draw_wave(draw: ImageDraw.Draw, size, progress):
    w, h = size
    cy = h//2 + 60
    draw.line([50, cy, w-50, cy], fill=(200,200,200))
    points = []
    total_pixels = w-100
    for i in range(0, total_pixels):
        x = 50 + i
        t = (i / total_pixels) * (2*math.pi*2)
        y = cy - int(math.sin(t + 2*math.pi*progress) * 60)
        points.append((x,y))
    draw.line(points, fill=(30,144,255), width=3)
    mp_x = int(50 + total_pixels * (progress % 1.0))
    mp_t = (mp_x - 50) / total_pixels * (2*math.pi*2)
    mp_y = cy - int(math.sin(mp_t) * 60)
    draw.ellipse([mp_x-8, mp_y-8, mp_x+8, mp_y+8], fill=(255,0,0))

def _parabola_points(size, a=1.0, b=0.0, c=0.0, samples=400):
    w, h = size
    X = 6.0
    pts = []
    cy = h//2 + 60
    scale_y = 30
    for i in range(samples):
        sx = -X + (2*X) * (i / (samples-1))
        y = a * sx * sx + b * sx + c
        px = int((sx + X) / (2*X) * (w - 100) + 50)
        py = int(cy - y * scale_y)
        pts.append((px, py))
    return pts

def _draw_parabola(draw: ImageDraw.Draw, size, a=1.0, b=0.0, c=0.0):
    pts = _parabola_points(size, a, b, c, samples=600)
    draw.line(pts, fill=(255,215,0), width=3)

def _compute_vertex_and_roots(a,b,c):
    if a == 0:
        return (None, None), []
    vx = -b/(2*a)
    vy = a*vx*vx + b*vx + c
    disc = b*b - 4*a*c
    roots = []
    if disc < 0:
        roots = []
    elif disc == 0:
        r = -b/(2*a)
        roots = [r]
    else:
        r1 = (-b + math.sqrt(disc)) / (2*a)
        r2 = (-b - math.sqrt(disc)) / (2*a)
        roots = [r1, r2]
    return (vx, vy), roots

class MoviePyRenderer:
    def __init__(self, fps=DEFAULT_FPS, size=DEFAULT_SIZE):
        self.fps = fps
        self.size = size
        os.makedirs("outputs", exist_ok=True)
        try:
            self.font = ImageFont.truetype("arial.ttf", 18)
            self.font_title = ImageFont.truetype("arial.ttf", 26)
        except Exception:
            self.font = ImageFont.load_default()
            self.font_title = ImageFont.load_default()

    def render(self, plan: Dict[str,Any], output_filename: str = None) -> str:
        visual_elements = plan.get("visual_elements", [])
        seq = plan.get("animation_sequence", [])
        # build step timing
        steps = []
        t = 0.0
        for s in seq:
            d = float(s.get("duration", 2.5))
            steps.append({"meta": s, "start": t, "end": t+d})
            t += d
        total_duration = max(0.5, t) + 0.8

        positions = _element_positions(len(visual_elements), self.size)
        base_state = {}
        for i, el in enumerate(visual_elements):
            base_state[el["id"]] = {
                "pos": positions[i],
                "scale": 1.0,
                "opacity": 1.0,
                "color": COLOR_MAP.get("default")
            }

        # sorting layout for rectangle bars
        is_sorting = any("compare" in (s.get("action","") or "").lower() or "swap" in (s.get("action","") or "").lower() for s in seq)
        if is_sorting:
            w,h = self.size
            rects = [e for e in visual_elements if e.get("type")=="rectangle"]
            num = len(rects) or 1
            gap = int(w / (num + 1))
            idx = 0
            for e in visual_elements:
                if e.get("type")=="rectangle":
                    base_state[e["id"]]["pos"] = (gap*(idx+1), int(h*0.6))
                    idx += 1

        # try to parse parabola coefficients if present in description
        parabola_spec = None
        for el in visual_elements:
            if (el.get("type") or "").lower() == "parabola":
                desc = el.get("description","")
                m = re.search(r'([+-]?\d*\.?\d*)x\^?2\s*([+-]?\d*\.?\d*)x\s*([+-]?\d+\.?\d*)', desc.replace(' ', ''))
                if m:
                    def to_num(s):
                        s = s.replace('+','')
                        return float(s) if s not in ('','+') else 1.0
                    try:
                        a = to_num(m.group(1))
                        b = to_num(m.group(2))
                        c = float(m.group(3))
                    except Exception:
                        a,b,c = 1.0,0.0,0.0
                else:
                    # default sample parabola
                    a,b,c = 1.0, 0.0, -4.0
                parabola_spec = (a,b,c)
                break

        def make_frame(t_frame):
            # find active step and rel progress
            current = steps[-1] if steps else {"meta":{}, "start":0, "end": total_duration}
            rel = 0.0
            for s in steps:
                if t_frame < s["end"]:
                    current = s
                    rel = (t_frame - s["start"]) / max((s["end"]-s["start"]), 1e-6)
                    rel = max(0.0, min(1.0, rel))
                    break

            img = Image.new('RGB', self.size, (13,17,23))
            draw = ImageDraw.Draw(img)

            # Title and subtitle
            draw.text((20,10), plan.get("title","Educational Animation"), fill=(220,220,220), font=self.font_title)
            subtitle = plan.get("core_concept","")
            draw.text((20,40), subtitle[:80], fill=(180,180,180), font=self.font)

            # draw global parabola / wave background if any
            if parabola_spec is not None:
                _draw_parabola(draw, self.size, *parabola_spec)

            if any((el.get("type") or "").lower() == "wave" for el in visual_elements):
                _draw_wave(draw, self.size, t_frame/total_duration)

            meta = current.get("meta", {})
            action = (meta.get("action","") or "").lower()
            elems_in_step = meta.get("elements", []) or []

            # handle compare/swap animation
            if "compare" in action or "swap" in action:
                rects = [e for e in visual_elements if e.get("type")=="rectangle"]
                if len(rects) >= 2:
                    a_id, b_id = rects[0]["id"], rects[1]["id"]
                    a_pos = base_state[a_id]["pos"]
                    b_pos = base_state[b_id]["pos"]
                    px = int(_lerp(a_pos[0], b_pos[0], rel))
                    py = a_pos[1] - 80
                    draw.line([px-20, py, px+20, py], fill=COLOR_MAP["highlight"], width=4)
                    draw.polygon([(px+20,py),(px+12,py-8),(px+12,py+8)], fill=COLOR_MAP["highlight"])
                    if rel > 0.5:
                        swap_t = (rel - 0.5) * 2.0
                        base_state[a_id]["pos"] = (int(_lerp(a_pos[0], b_pos[0], swap_t)), a_pos[1])
                        base_state[b_id]["pos"] = (int(_lerp(b_pos[0], a_pos[0], swap_t)), b_pos[1])
            elif "show inputs" in action or "show outputs" in action:
                for eid in elems_in_step:
                    if eid in base_state:
                        base_state[eid]["opacity"] = _lerp(0.2, 1.0, rel)
                        base_state[eid]["scale"] = _lerp(0.8, 1.0, rel)
                        base_state[eid]["color"] = COLOR_MAP.get("accent")
            elif "introduce" in action:
                for eid in elems_in_step:
                    if eid in base_state:
                        base_state[eid]["opacity"] = _lerp(0.0, 1.0, rel)
                        base_state[eid]["scale"] = _lerp(0.6, 1.0, rel)
            elif "plot_parabola" in action or "plot parabola" in action:
                # optionally animate parabola draw progress using rel
                pass
            elif "highlight_roots" in action:
                # roots highlighting handled when drawing roots
                pass

            # draw elements
            for i, el in enumerate(visual_elements):
                eid = el["id"]
                st = base_state.get(eid, {})
                pos = st.get("pos", (100 + i*100, self.size[1]//2))
                scale = st.get("scale", 1.0)
                opacity = st.get("opacity", 1.0)
                color = st.get("color", COLOR_MAP["default"])

                if (el.get("type") or "").lower() == "rectangle" and is_sorting:
                    # draw bar proportional to any numeric in description
                    try:
                        num = int(''.join(filter(str.isdigit, el.get("description",""))) or 50)
                    except Exception:
                        num = 50
                    bar_h = int(60 + (num % 100) * 1.2)
                    bx, by = pos
                    bar_w = int(40 * scale)
                    top = by - bar_h
                    draw.rectangle([bx-bar_w//2, top, bx+bar_w//2, by], fill=color)
                    _draw_label(draw, el.get("description",""), (bx, top-18), color=(220,220,220), font=self.font)
                elif (el.get("type") or "").lower() == "parabola":
                    # already drawn globally; draw vertex/roots markers if present
                    if parabola_spec is not None:
                        a,b,c = parabola_spec
                        (vx, vy), roots = _compute_vertex_and_roots(a,b,c)
                        if vx is not None:
                            # map to pixels
                            w,h = self.size
                            X = 6.0
                            px = int((vx + X) / (2*X) * (w - 100) + 50)
                            py = int(h//2 + 60 - vy * 30)
                            draw.ellipse([px-6, py-6, px+6, py+6], fill=(255,0,0))
                            _draw_label(draw, "Vertex", (px, py-18), font=self.font)
                        # roots markers
                        for r in roots:
                            w,h = self.size
                            X = 6.0
                            rx = int((r + X) / (2*X) * (w - 100) + 50)
                            ry = int(h//2 + 60 - 0 * 30)  # roots are on x-axis: y=0
                            draw.rectangle([rx-6, ry-6, rx+6, ry+6], fill=(0,255,0))
                            _draw_label(draw, f"x={round(r,2)}", (rx, ry-18), font=self.font)
                elif (el.get("type") or "").lower() == "wave":
                    # wave drawn already
                    pass
                else:
                    _draw_shape(draw, el, pos, color, scale=scale, opacity=opacity, font=self.font)
                    desc = el.get("description","")
                    if desc and (el.get("type") or "").lower() not in ("text","equation","parabola"):
                        _draw_label(draw, desc, (pos[0], pos[1]-int(60*scale)), color=(240,240,240), font=self.font)

                if (el.get("type") or "").lower() in ("text","equation"):
                    txt = el.get("description","")
                    _draw_label(draw, txt, (pos[0], pos[1]), color=(255,255,255), font=self.font)

            return np.array(img)

        clip = VideoClip(make_frame, duration=total_duration)
        clip = clip.set_fps(self.fps)
        if not output_filename:
            output_filename = os.path.join("outputs", "animation_render.mp4")
        clip.write_videofile(output_filename, codec="libx264", audio=False, verbose=False, logger=None)
        return output_filename