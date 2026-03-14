"""
Build an SVG visualization of the nugget directed graph (related links).
Uses (number, title) and (from, to) edges from the same data as the map matrix.
Force-directed layout via networkx.
"""

import html as _html
import math

import networkx as nx


def _node_edge_lists(nuggets):
    """From nuggets list, return (nodes, edges). nodes = [(id, label, filename)], edges = [(from_id, to_id)]."""
    sorted_nuggets = sorted(nuggets, key=lambda n: (n.get("number", "").zfill(3), n.get("number", "")))
    nodes = []
    for n in sorted_nuggets:
        num = n.get("number", "")
        if not num:
            continue
        label = n.get("title", "Untitled") or "Untitled"
        filename = n.get("filename", "") or ""
        nodes.append((num, label, filename))
    edges = []
    for n in sorted_nuggets:
        from_id = n.get("number", "")
        if not from_id:
            continue
        for to_id in n.get("related", []):
            if to_id:
                edges.append((from_id, to_id))
    return nodes, edges


def _force_directed_layout(nodes, edges, width, height, padding):
    """
    Return dict node_id -> (x, y) in SVG space.
    Uses networkx spring_layout with higher k to spread nodes; scales to fit viewBox.
    """
    G = nx.DiGraph()
    for nid, _, _ in nodes:
        G.add_node(nid)
    for a, b in edges:
        G.add_edge(a, b)
    n = G.number_of_nodes()
    k = 2.5 if n > 10 else 1.5
    raw = nx.spring_layout(G, k=k, iterations=80, seed=42)
    xs = [raw[nid][0] for nid, _, _ in nodes]
    ys = [raw[nid][1] for nid, _, _ in nodes]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    range_x = max_x - min_x or 1
    range_y = max_y - min_y or 1
    inner_w = width - 2 * padding
    inner_h = height - 2 * padding
    result = {}
    for nid, _, _ in nodes:
        x, y = raw[nid]
        sx = padding + (x - min_x) / range_x * inner_w
        sy = padding + (y - min_y) / range_y * inner_h
        result[nid] = (sx, sy)
    return result


# Canvas sized for ~40 nodes with titles; force-directed spread reduces arrow overlap.
DEFAULT_GRAPH_WIDTH = 1800
DEFAULT_GRAPH_HEIGHT = 1400

EDGE_COLORS = (
    "#cc0000",
    "#e57300",
    "#d4af37",
    "#00cc00",
    "#0000cc",
    "#6600cc",
)
NUM_EDGE_COLORS = len(EDGE_COLORS)


def build_graph_svg(
    nuggets,
    width=DEFAULT_GRAPH_WIDTH,
    height=DEFAULT_GRAPH_HEIGHT,
    node_radius=20,
    show_title=True,
    link_nuggets=True,
):
    """
    Build an SVG string for the directed graph of nugget related links.
    Uses force-directed layout so nodes spread out and arrowheads overlap less.

    nuggets: list of nugget dicts (number, title, filename, related).
    width, height: SVG viewBox (defaults give room for titles).
    node_radius: circle radius for each node.
    show_title: if True, use title as label; else use filename (e.g. 003-inside).
    link_nuggets: if True, wrap each node in <a> to its nugget page.
    """
    nodes, edges = _node_edge_lists(nuggets)
    if not nodes:
        return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {} {}"></svg>'.format(width, height)

    padding = 80
    pos = _force_directed_layout(nodes, edges, width, height, padding)

    lines = []
    lines.append(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {} {}" class="map-graph-svg" width="100%" height="auto">'.format(
            width, height
        )
    )
    lines.append('  <defs>')
    lines.append('    <style>.map-graph-edge{stroke-width:2;fill:none}.map-graph-node{fill:#fff;stroke:#c8a96e;stroke-width:1.5}.map-graph-label{font-family:system-ui,sans-serif;font-size:18px;fill:#000}.map-graph-node-link:hover .map-graph-node{stroke:#000;stroke-width:2}</style>')
    lines.append(
        '    <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth">'
    )
    lines.append('      <path d="M0,0 L0,6 L9,3 z" fill="currentColor"/>')
    lines.append("    </marker>")
    lines.append("  </defs>")

    for i, (from_id, to_id) in enumerate(edges):
        x1, y1 = pos.get(from_id, (0, 0))
        x2, y2 = pos.get(to_id, (0, 0))
        dx, dy = x2 - x1, y2 - y1
        dist = math.hypot(dx, dy) or 1
        shrink = (node_radius + 6) / dist
        x1 += dx * shrink
        y1 += dy * shrink
        x2 -= dx * shrink
        y2 -= dy * shrink
        stroke = EDGE_COLORS[i % NUM_EDGE_COLORS]
        lines.append(
            '  <line x1="{}" y1="{}" x2="{}" y2="{}" class="map-graph-edge" style="stroke:{};color:{}" marker-end="url(#arrow)"/>'.format(
                x1, y1, x2, y2, stroke, stroke
            )
        )

    for nid, label, fname in nodes:
        x, y = pos[nid]
        label_text = label if show_title else (fname or nid)
        label_esc = _html.escape(str(label_text))
        node_content = (
            '    <circle r="{}" class="map-graph-node"/>'.format(node_radius)
            + '\n    <text class="map-graph-label" text-anchor="middle" dominant-baseline="central">{}</text>'.format(
                label_esc
            )
        )
        if link_nuggets and fname:
            href = _html.escape(fname + ".html")
            lines.append('  <a href="{}" class="map-graph-node-link">'.format(href))
            lines.append('    <g transform="translate({},{})">'.format(x, y))
            lines.append(node_content.replace("    ", "      "))
            lines.append("    </g>")
            lines.append("  </a>")
        else:
            lines.append('  <g transform="translate({},{})">'.format(x, y))
            lines.append(node_content.replace("    ", "    "))
            lines.append("  </g>")

    lines.append("</svg>")
    return "\n".join(lines)
