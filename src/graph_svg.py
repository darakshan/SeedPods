"""
Build an SVG visualization of the nugget directed graph (related links).
Uses (number, title) and (from, to) edges from the same data as the map matrix.
Force-directed layout via networkx.
"""

import html as _html
import math

import networkx as nx


def _node_edge_lists(nuggets):
    """From nuggets list, return (nodes, edges). nodes = [(id, label, slug, tags_list, status)], edges = [(from_id, to_id)]."""
    from nugget_parser import nugget_tag
    sorted_nuggets = sorted(nuggets, key=lambda n: (n.get("number", "").zfill(3), n.get("number", "")))
    nodes = []
    for n in sorted_nuggets:
        num = n.get("number", "")
        if not num:
            continue
        label = n.get("title", "Untitled") or "Untitled"
        slug = nugget_tag(n)
        tags_list = n.get("tags", [])
        status = n.get("status", "empty")
        nodes.append((num, label, slug, tags_list, status))
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
    for nid, *_ in nodes:
        G.add_node(nid)
    for a, b in edges:
        G.add_edge(a, b)
    n = G.number_of_nodes()
    k = 2.5 if n > 10 else 1.5
    raw = nx.spring_layout(G, k=k, iterations=80, seed=42)
    xs = [raw[nid][0] for nid, *_ in nodes]
    ys = [raw[nid][1] for nid, *_ in nodes]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    range_x = max_x - min_x or 1
    range_y = max_y - min_y or 1
    inner_w = width - 2 * padding
    inner_h = height - 2 * padding
    result = {}
    for nid, *_ in nodes:
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


def _rect_exit_t(dx, dy, hw, hh):
    """Return smallest positive t such that (t*dx, t*dy) lies on the rect [-hw,hw] x [-hh,hh] boundary."""
    candidates = []
    if dx > 0:
        candidates.append(hw / dx)
    elif dx < 0:
        candidates.append(-hw / dx)
    if dy > 0:
        candidates.append(hh / dy)
    elif dy < 0:
        candidates.append(-hh / dy)
    return min(candidates) if candidates else 1.0


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
    show_title: if True, use title as label; else use nugget tag (e.g. 003-inside).
    link_nuggets: if True, wrap each node in <a> to its nugget page.
    """
    nodes, edges = _node_edge_lists(nuggets)
    if not nodes:
        return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {} {}"></svg>'.format(width, height)

    padding = 80
    pos = _force_directed_layout(nodes, edges, width, height, padding)

    box_w = 50
    box_h = 22
    for nid, label, slug, tags_list, status in nodes:
        label_text = label if show_title else (slug or nid)
        lbl_len = len(str(label_text))
        box_w = max(box_w, max(50, lbl_len * 9))
        box_h = max(box_h, 22)
    pad_extra = 12
    box_w += pad_extra * 2
    box_h += pad_extra * 2
    hw, hh = box_w / 2, box_h / 2

    lines = []
    lines.append(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {} {}" class="map-graph-svg" width="100%" height="auto">'.format(
            width, height
        )
    )
    lines.append('  <defs>')
    lines.append('    <style>.map-graph-edge{stroke-width:3;fill:none}.map-graph-edge.unselected{opacity:0.12}.map-graph-node{fill:#fff;stroke:#c8a96e;stroke-width:1.5}.map-graph-label{font-family:system-ui,sans-serif;font-size:19px;fill:#000}.map-graph-node-link:hover .map-graph-node{stroke:#000;stroke-width:2}.map-graph-node-wrap.unselected{opacity:0.4}</style>')
    lines.append("  </defs>")

    for i, (from_id, to_id) in enumerate(edges):
        x1, y1 = pos.get(from_id, (0, 0))
        x2, y2 = pos.get(to_id, (0, 0))
        dx, dy = x2 - x1, y2 - y1
        dist = math.hypot(dx, dy) or 1
        t_from = min(_rect_exit_t(dx, dy, hw, hh), 1.0)
        t_to = min(_rect_exit_t(-dx, -dy, hw, hh), 1.0)
        x1 = x1 + t_from * dx
        y1 = y1 + t_from * dy
        x2 = x2 - t_to * dx
        y2 = y2 - t_to * dy
        stroke = EDGE_COLORS[i % NUM_EDGE_COLORS]
        lines.append(
            '  <line x1="{}" y1="{}" x2="{}" y2="{}" class="map-graph-edge" data-from="{}" data-to="{}" style="stroke:{};color:{}"/>'.format(
                x1, y1, x2, y2, _html.escape(from_id), _html.escape(to_id), stroke, stroke
            )
        )

    for nid, label, slug, tags_list, status in nodes:
        x, y = pos[nid]
        label_text = label if show_title else (slug or nid)
        label_esc = _html.escape(str(label_text))
        node_content = (
            '    <rect x="{}" y="{}" width="{}" height="{}" class="map-graph-node"/>'.format(
                -box_w / 2, -box_h / 2, box_w, box_h
            )
            + '\n    <text class="map-graph-label" text-anchor="middle" dominant-baseline="central">{}</text>'.format(
                label_esc
            )
        )
        data_attrs = ' data-nugget="{}" data-tags="{}" data-status="{}"'.format(
            _html.escape(nid),
            _html.escape(",".join(tags_list)),
            _html.escape(status),
        )
        wrap_class = "map-graph-node-wrap map-graph-node-link"
        if link_nuggets and slug:
            href = _html.escape(slug + ".html")
            lines.append('  <a href="{}" class="{}"{}>'.format(href, wrap_class, data_attrs))
            lines.append('    <g transform="translate({},{})">'.format(x, y))
            lines.append(node_content.replace("    ", "      "))
            lines.append("    </g>")
            lines.append("  </a>")
        else:
            lines.append('  <g class="map-graph-node-wrap"{}>'.format(data_attrs))
            lines.append('    <g transform="translate({},{})">'.format(x, y))
            lines.append(node_content.replace("    ", "    "))
            lines.append("    </g>")
            lines.append("  </g>")

    lines.append("</svg>")
    return "\n".join(lines)
