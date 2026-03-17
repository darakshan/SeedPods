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
# Extra vertical space (VERT_PAD) so nodes can be dragged above/below the graph.
DEFAULT_GRAPH_WIDTH = 1800
DEFAULT_GRAPH_HEIGHT = 1400
VERT_PAD = 250

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

    view_height = height + 2 * VERT_PAD
    lines = []
    lines.append(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 {} {} {}" class="map-graph-svg" width="100%" height="auto">'.format(
            -VERT_PAD, width, view_height
        )
    )
    bullet_r = 8
    lines.append('  <defs>')
    lines.append('    <style>.map-graph-edge{stroke-width:3;fill:none}.map-graph-edge-wrap.unselected .map-graph-edge,.map-graph-edge-wrap.unselected .map-graph-bullet{opacity:0.12}.map-graph-node{fill:#fff;stroke:#c8a96e;stroke-width:1.5}.map-graph-label{font-family:system-ui,sans-serif;font-size:19px;fill:#000}.map-graph-node-link:hover .map-graph-node{stroke:#000;stroke-width:2}.map-graph-node-wrap.unselected{opacity:0.4}</style>')
    lines.append("  </defs>")

    edge_data = []
    for i, (from_id, to_id) in enumerate(edges):
        x1, y1 = pos.get(from_id, (0, 0))
        x2, y2 = pos.get(to_id, (0, 0))
        dx, dy = x2 - x1, y2 - y1
        t_from = min(_rect_exit_t(dx, dy, hw, hh), 1.0)
        t_to = min(_rect_exit_t(-dx, -dy, hw, hh), 1.0)
        x1 = x1 + t_from * dx
        y1 = y1 + t_from * dy
        x2 = x2 - t_to * dx
        y2 = y2 - t_to * dy
        stroke = EDGE_COLORS[i % NUM_EDGE_COLORS]
        edge_data.append((from_id, to_id, x1, y1, x2, y2, stroke))

    for from_id, to_id, x1, y1, x2, y2, stroke in edge_data:
        lines.append('  <g class="map-graph-edge-wrap" data-from="{}" data-to="{}">'.format(_html.escape(from_id), _html.escape(to_id)))
        lines.append('    <line x1="{}" y1="{}" x2="{}" y2="{}" class="map-graph-edge" style="stroke:{}"/>'.format(x1, y1, x2, y2, stroke))
        lines.append('  </g>')

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
            lines.append('    <g class="map-graph-node-transform" transform="translate({},{})" data-x="{}" data-y="{}">'.format(x, y, x, y))
            lines.append(node_content.replace("    ", "      "))
            lines.append("    </g>")
            lines.append("  </a>")
        else:
            lines.append('  <g class="map-graph-node-wrap"{}>'.format(data_attrs))
            lines.append('    <g class="map-graph-node-transform" transform="translate({},{})" data-x="{}" data-y="{}">'.format(x, y, x, y))
            lines.append(node_content.replace("    ", "    "))
            lines.append("    </g>")
            lines.append("  </g>")

    for from_id, to_id, x1, y1, x2, y2, stroke in edge_data:
        lines.append('  <g class="map-graph-edge-wrap" data-from="{}" data-to="{}">'.format(_html.escape(from_id), _html.escape(to_id)))
        lines.append('    <circle class="map-graph-bullet map-graph-bullet-exit" cx="{}" cy="{}" r="{}" stroke="{}"/>'.format(x1, y1, bullet_r, stroke))
        lines.append('    <circle class="map-graph-bullet map-graph-bullet-enter" cx="{}" cy="{}" r="{}" stroke="{}"/>'.format(x2, y2, bullet_r, stroke))
        lines.append('  </g>')

    lines.append("</svg>")
    return "\n".join(lines)


MIN_TAG_COUNT_FOR_MAP = 3

MAP_FILTER_SCRIPT = """
<script>
(function(){
  var tagSel = document.getElementById('map-filter-tag');
  var statusSel = document.getElementById('map-filter-status');
  function apply(){
    var tagVal = tagSel && tagSel.value;
    var statusVal = statusSel && statusSel.value;
    document.querySelectorAll('.map-graph-node-wrap').forEach(function(el){
      var tags = (el.getAttribute('data-tags') || '').split(',').map(function(s){ return s.trim(); });
      var status = el.getAttribute('data-status') || '';
      var tagMatch = !tagVal || tags.indexOf(tagVal) >= 0;
      var statusMatch = !statusVal || status === statusVal;
      el.classList.toggle('unselected', !(tagMatch && statusMatch));
    });
    var selected = new Set();
    document.querySelectorAll('.map-graph-node-wrap:not(.unselected)').forEach(function(el){
      selected.add(el.getAttribute('data-nugget'));
    });
    document.querySelectorAll('.map-graph-edge-wrap').forEach(function(el){
      var fromId = el.getAttribute('data-from');
      var toId = el.getAttribute('data-to');
      var connected = selected.has(fromId) && selected.has(toId);
      el.classList.toggle('unselected', !connected);
    });
  }
  if (tagSel) tagSel.addEventListener('change', apply);
  if (statusSel) statusSel.addEventListener('change', apply);
  apply();
  var wrap = document.querySelector('.map-graph-wrap');
  if (wrap && wrap.scrollWidth > wrap.clientWidth) wrap.scrollLeft = (wrap.scrollWidth - wrap.clientWidth) / 2;
  if (wrap && wrap.scrollHeight > wrap.clientHeight) wrap.scrollTop = (wrap.scrollHeight - wrap.clientHeight) / 2;

  var svgEl = document.querySelector('.map-graph-svg');
  if (svgEl && typeof svgEl.createSVGPoint === 'function') {
    var pt = svgEl.createSVGPoint();
    var dragState = { active: false, wrap: null, g: null, startX: 0, startY: 0, startDx: 0, startDy: 0, didMove: false };
    function clientToSvg(clientX, clientY) {
      pt.x = clientX;
      pt.y = clientY;
      return pt.matrixTransform(svgEl.getScreenCTM().inverse());
    }
    function rectExitT(dx, dy, hw, hh) {
      var candidates = [];
      if (dx > 0) candidates.push(hw / dx);
      else if (dx < 0) candidates.push(-hw / dx);
      if (dy > 0) candidates.push(hh / dy);
      else if (dy < 0) candidates.push(-hh / dy);
      return candidates.length ? Math.min.apply(null, candidates) : 1;
    }
    function getNodePosition(nid) {
      var wraps = document.querySelectorAll('.map-graph-node-wrap');
      var w = null;
      for (var i = 0; i < wraps.length; i++) {
        if (wraps[i].getAttribute('data-nugget') === nid) { w = wraps[i]; break; }
      }
      if (!w) return { x: 0, y: 0 };
      var g = w.querySelector('.map-graph-node-transform');
      if (!g) return { x: 0, y: 0 };
      var x = parseFloat(g.getAttribute('data-x')) || 0;
      var y = parseFloat(g.getAttribute('data-y')) || 0;
      var dx = parseFloat(g.getAttribute('data-dx')) || 0;
      var dy = parseFloat(g.getAttribute('data-dy')) || 0;
      return { x: x + dx, y: y + dy };
    }
    function updateEdgesForNode(nodeId) {
      var rect = document.querySelector('.map-graph-node');
      if (!rect) return;
      var hw = parseFloat(rect.getAttribute('width')) / 2;
      var hh = parseFloat(rect.getAttribute('height')) / 2;
      var edgeWraps = document.querySelectorAll('.map-graph-edge-wrap');
      var seen = {};
      edgeWraps.forEach(function(w) {
        var fromId = w.getAttribute('data-from');
        var toId = w.getAttribute('data-to');
        if (fromId !== nodeId && toId !== nodeId) return;
        var key = fromId + ',' + toId;
        if (seen[key]) return;
        seen[key] = true;
        var fromPos = getNodePosition(fromId);
        var toPos = getNodePosition(toId);
        var dx = toPos.x - fromPos.x;
        var dy = toPos.y - fromPos.y;
        var dist = Math.sqrt(dx * dx + dy * dy) || 1;
        var tFrom = Math.min(rectExitT(dx, dy, hw, hh), 1);
        var tTo = Math.min(rectExitT(-dx, -dy, hw, hh), 1);
        var x1 = fromPos.x + tFrom * dx;
        var y1 = fromPos.y + tFrom * dy;
        var x2 = toPos.x - tTo * dx;
        var y2 = toPos.y - tTo * dy;
        document.querySelectorAll('.map-graph-edge-wrap[data-from="' + fromId + '"][data-to="' + toId + '"]').forEach(function(grp) {
          var line = grp.querySelector('.map-graph-edge');
          if (line) {
            line.setAttribute('x1', x1);
            line.setAttribute('y1', y1);
            line.setAttribute('x2', x2);
            line.setAttribute('y2', y2);
          }
          var exitC = grp.querySelector('.map-graph-bullet-exit');
          if (exitC) { exitC.setAttribute('cx', x1); exitC.setAttribute('cy', y1); }
          var enterC = grp.querySelector('.map-graph-bullet-enter');
          if (enterC) { enterC.setAttribute('cx', x2); enterC.setAttribute('cy', y2); }
        });
      });
    }
    function startDrag(wrap, clientX, clientY) {
      var g = wrap.querySelector('.map-graph-node-transform');
      if (!g) return;
      var origX = parseFloat(g.getAttribute('data-x')) || 0;
      var origY = parseFloat(g.getAttribute('data-y')) || 0;
      var dx = parseFloat(g.getAttribute('data-dx')) || 0;
      var dy = parseFloat(g.getAttribute('data-dy')) || 0;
      var p = clientToSvg(clientX, clientY);
      dragState.didMove = false;
      dragState.active = true;
      dragState.wrap = wrap;
      dragState.g = g;
      dragState.origX = origX;
      dragState.origY = origY;
      dragState.startX = p.x;
      dragState.startY = p.y;
      dragState.startDx = dx;
      dragState.startDy = dy;
    }
    function moveDrag(clientX, clientY) {
      if (!dragState.active || !dragState.g) return;
      var p = clientToSvg(clientX, clientY);
      var dx = dragState.startDx + (p.x - dragState.startX);
      var dy = dragState.startDy + (p.y - dragState.startY);
      dragState.g.setAttribute('transform', 'translate(' + (dragState.origX + dx) + ',' + (dragState.origY + dy) + ')');
      dragState.g.setAttribute('data-dx', dx);
      dragState.g.setAttribute('data-dy', dy);
      dragState.didMove = true;
      var nid = dragState.wrap && dragState.wrap.getAttribute('data-nugget');
      if (nid) updateEdgesForNode(nid);
    }
    function endDrag() {
      dragState.active = false;
      dragState.wrap = null;
      dragState.g = null;
    }
    document.querySelectorAll('.map-graph-node-wrap').forEach(function(wrap) {
      wrap.addEventListener('mousedown', function(e) {
        if (e.button !== 0) return;
        startDrag(wrap, e.clientX, e.clientY);
      });
      wrap.addEventListener('click', function(e) {
        if (dragState.didMove) {
          e.preventDefault();
          e.stopPropagation();
          dragState.didMove = false;
        }
      });
    });
    document.addEventListener('mousemove', function(e) {
      if (dragState.active) {
        e.preventDefault();
        moveDrag(e.clientX, e.clientY);
      }
    });
    document.addEventListener('mouseup', function() { endDrag(); });
    document.addEventListener('mouseleave', function() { endDrag(); });

    var wrapEl = document.querySelector('.map-graph-wrap');
    if (wrapEl) {
      wrapEl.addEventListener('touchstart', function(e) {
        if (e.target.closest('.map-graph-node-wrap')) {
          var wrap = e.target.closest('.map-graph-node-wrap');
          startDrag(wrap, e.touches[0].clientX, e.touches[0].clientY);
        }
      }, { passive: true });
      wrapEl.addEventListener('touchmove', function(e) {
        if (dragState.active && e.touches.length) {
          e.preventDefault();
          moveDrag(e.touches[0].clientX, e.touches[0].clientY);
        }
      }, { passive: false });
      wrapEl.addEventListener('touchend', endDrag);
      wrapEl.addEventListener('touchcancel', endDrag);
    }
  }
})();
</script>"""


def map_directive_html(nuggets, status_order):
    """HTML for the @map directive: filters, key, interactive graph SVG, and filter/drag script."""
    tag_counts = {}
    for n in nuggets:
        for t in n.get("tags", []):
            tag_counts[t] = tag_counts.get(t, 0) + 1
    tags_with_min = sorted([t for t, c in tag_counts.items() if c >= MIN_TAG_COUNT_FOR_MAP])
    category_opts = '<option value="">All</option>' + "".join(
        '<option value="{}">{}</option>'.format(_html.escape(t), _html.escape(t)) for t in tags_with_min
    )
    status_opts = '<option value="">All</option>' + "".join(
        '<option value="{}">{}</option>'.format(_html.escape(s), _html.escape(s)) for s in (status_order or [])
    )
    filters_html = (
        '<div class="map-graph-filters">'
        '<label for="map-filter-tag">Category</label>'
        '<select id="map-filter-tag" aria-label="Filter by tag">' + category_opts + '</select>'
        ' <label for="map-filter-status">Status</label>'
        '<select id="map-filter-status" aria-label="Filter by status">' + status_opts + '</select>'
        "</div>"
    )
    key_html = (
        '<div class="map-graph-key" aria-hidden="true">'
        '<span class="map-graph-key-item"><span class="map-graph-key-dot map-graph-key-from"></span> from</span>'
        ' <span class="map-graph-key-item"><span class="map-graph-key-dot map-graph-key-to"></span> to</span>'
        '</div>'
    )
    svg = build_graph_svg(nuggets, show_title=False, link_nuggets=True, node_radius=40)
    return (
        filters_html
        + "\n"
        + key_html
        + '\n<div class="map-graph-wrap"><div class="map-graph-inner">'
        + svg
        + "</div></div>"
        + MAP_FILTER_SCRIPT
    )
