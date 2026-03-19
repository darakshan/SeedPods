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
        category = n.get("category", "")
        status = n.get("status", "empty")
        nodes.append((num, label, slug, [category] if category else [], status))
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
    "#888888",
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
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 {} {} {}" class="map-graph-svg" width="{}" height="{}" data-base-w="{}" data-base-h="{}" data-content-h="{}">'.format(
            -VERT_PAD, width, view_height, width, view_height, width, view_height, height
        )
    )
    bullet_r = 8
    lines.append('  <defs>')
    lines.append('    <style>.map-graph-edge{stroke-width:3;fill:none}.map-graph-edge-wrap.unselected .map-graph-edge,.map-graph-edge-wrap.unselected .map-graph-bullet{opacity:0.05}.map-graph-edge-wrap:not(.unselected) .map-graph-edge,.map-graph-edge-wrap:not(.unselected) .map-graph-bullet{opacity:0.5}.map-graph-node{fill:#fff;stroke:#c8a96e;stroke-width:1.5}.map-graph-label{font-family:system-ui,sans-serif;font-size:19px;fill:#000}.map-graph-node-link:hover .map-graph-node{stroke:#000;stroke-width:2}.map-graph-node-wrap.unselected{opacity:0.4}</style>')
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
            '    <rect x="{}" y="{}" width="{}" height="{}" rx="{}" ry="{}" class="map-graph-node"/>'.format(
                -box_w / 2, -box_h / 2, box_w, box_h, box_h / 2, box_h / 2
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
  var catCbs        = document.querySelectorAll('.map-filter-cat');
  var statusItemCbs = document.querySelectorAll('.map-filter-status-item');

  var selInfoEl = document.getElementById('map-selection-info');
  function apply(){
    var cats = [];
    catCbs.forEach(function(cb){ if(cb.checked) cats.push(cb.value); });
    var statuses = [];
    statusItemCbs.forEach(function(cb){ if(cb.checked) statuses.push(cb.value); });
    var anyFilter = cats.length > 0 || statuses.length > 0;
    document.querySelectorAll('.map-graph-node-wrap').forEach(function(el){
      var tags=(el.getAttribute('data-tags')||'').split(',').map(function(s){ return s.trim(); });
      var status=el.getAttribute('data-status')||'';
      var catMatch=cats.length===0||cats.some(function(c){ return tags.indexOf(c)>=0; });
      var statusMatch=statuses.length===0||statuses.indexOf(status)>=0;
      el.classList.toggle('unselected',!(catMatch&&statusMatch));
    });
    var selected=new Set();
    if(anyFilter){
      document.querySelectorAll('.map-graph-node-wrap:not(.unselected)').forEach(function(n){
        selected.add(n.getAttribute('data-nugget'));
      });
    }
    document.querySelectorAll('.map-graph-edge-wrap').forEach(function(el){
      var f=el.getAttribute('data-from'), t=el.getAttribute('data-to');
      el.classList.toggle('unselected',!(selected.has(f)&&selected.has(t)));
    });
    if(selInfoEl){
      var nc = document.querySelectorAll('.map-graph-node-wrap:not(.unselected)').length;
      var edgeSet = new Set();
      document.querySelectorAll('.map-graph-edge-wrap:not(.unselected)').forEach(function(el){
        edgeSet.add(el.getAttribute('data-from')+','+el.getAttribute('data-to'));
      });
      selInfoEl.textContent = nc+' node'+(nc!==1?'s':'')+', '+edgeSet.size+' edge'+(edgeSet.size!==1?'s':'');
    }
  }
  catCbs.forEach(function(cb){ cb.addEventListener('change',apply); });
  statusItemCbs.forEach(function(cb){ cb.addEventListener('change',apply); });
  document.querySelectorAll('.map-row-btn').forEach(function(btn){
    btn.addEventListener('click',function(){
      var action=btn.getAttribute('data-action');
      var cbs=(btn.getAttribute('data-target')==='cat')?catCbs:statusItemCbs;
      cbs.forEach(function(cb){ cb.checked=(action==='all'); });
      apply();
    });
  });
  apply();

  var svgEl       = document.querySelector('.map-graph-svg');
  var wrapEl      = document.querySelector('.map-graph-wrap');
  var innerEl     = wrapEl ? wrapEl.querySelector('.map-graph-inner') : null;
  var zoomLabelEl = document.getElementById('map-zoom-level');
  var baseW    = svgEl ? parseFloat(svgEl.getAttribute('data-base-w'))    : 1800;
  var baseH    = svgEl ? parseFloat(svgEl.getAttribute('data-base-h'))    : 1900;
  var contentH = svgEl ? parseFloat(svgEl.getAttribute('data-content-h')) : 1400;
  var zoomLevel = 1, normZoom = 1;
  var MIN_ZOOM = 0.25, MAX_ZOOM = 2, SQRT2 = Math.sqrt(2);
  var padX = 0, padY = 0;

  function formatZoom(z){
    if(z>=10) return z.toFixed(0)+'\u00d7';
    if(z>=1)  return z.toFixed(1)+'\u00d7';
    return z.toFixed(2)+'\u00d7';
  }
  function applyZoom(cxBase, cyBase){
    zoomLevel = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoomLevel));
    if(svgEl){
      svgEl.setAttribute('width',  Math.round(baseW*zoomLevel));
      svgEl.setAttribute('height', Math.round(baseH*zoomLevel));
    }
    if(zoomLabelEl) zoomLabelEl.textContent = formatZoom(zoomLevel/normZoom);
    if(cxBase!=null && wrapEl){
      wrapEl.scrollLeft = padX + cxBase*zoomLevel - wrapEl.clientWidth/2;
      wrapEl.scrollTop  = padY + cyBase*zoomLevel - wrapEl.clientHeight/2;
    }
  }
  function zoomBy(factor){
    var oldZoom=zoomLevel;
    zoomLevel=zoomLevel*factor;
    var cx=wrapEl ? (wrapEl.scrollLeft+wrapEl.clientWidth/2 -padX)/oldZoom : null;
    var cy=wrapEl ? (wrapEl.scrollTop +wrapEl.clientHeight/2-padY)/oldZoom : null;
    applyZoom(cx,cy);
  }
  var zoomInBtn  = document.getElementById('map-zoom-in');
  var zoomOutBtn = document.getElementById('map-zoom-out');
  if(zoomInBtn)  zoomInBtn.addEventListener('click', function(){ zoomBy(SQRT2);     });
  if(zoomOutBtn) zoomOutBtn.addEventListener('click', function(){ zoomBy(1/SQRT2); });

  if(wrapEl) wrapEl.addEventListener('touchstart',function(e){ if(e.touches.length>1) e.preventDefault(); },{passive:false});

  function setupLayout(resetScroll){
    var navEl     = document.querySelector('nav');
    var filtersEl = document.querySelector('.map-graph-filters');
    var navH      = navEl     ? navEl.offsetHeight     : 0;
    var filtersH  = filtersEl ? filtersEl.offsetHeight : 0;
    if(wrapEl) wrapEl.style.top = (navH + filtersH) + 'px';
    if(wrapEl && innerEl){
      padX = Math.round(wrapEl.clientWidth  * 0.2);
      padY = Math.round(wrapEl.clientHeight * 0.2);
      innerEl.style.padding = padY+'px '+padX+'px';
    }
    if(wrapEl){
      var fitRaw = Math.min(wrapEl.clientWidth/baseW, wrapEl.clientHeight/contentH);
      var n = Math.round(Math.log(fitRaw)/Math.log(SQRT2));
      zoomLevel = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, Math.pow(SQRT2,n)));
      normZoom = zoomLevel;
      applyZoom(null,null);
      if(resetScroll){
        var svgW = Math.round(baseW*zoomLevel);
        var svgH = Math.round(baseH*zoomLevel);
        wrapEl.scrollLeft = padX + Math.max(0, (svgW - wrapEl.clientWidth)  / 2);
        wrapEl.scrollTop  = padY + Math.max(0, (svgH - wrapEl.clientHeight) / 2);
      }
    }
  }
  setupLayout(true);
  if(document.fonts) document.fonts.ready.then(function(){
    var navEl = document.querySelector('nav');
    var filtersEl = document.querySelector('.map-graph-filters');
    var navH = navEl ? navEl.offsetHeight : 0;
    var filtersH = filtersEl ? filtersEl.offsetHeight : 0;
    if(wrapEl) wrapEl.style.top = (navH + filtersH) + 'px';
  });
  window.addEventListener('resize', function(){ setupLayout(true); });

  if (svgEl && typeof svgEl.createSVGPoint === 'function') {
    var pt = svgEl.createSVGPoint();
    var dragState = { active: false, wrap: null, g: null, startX: 0, startY: 0, startDx: 0, startDy: 0, didMove: false };
    var nodeHw = 0, nodeHh = 0;
    var _firstRect = document.querySelector('.map-graph-node');
    if (_firstRect) { nodeHw = parseFloat(_firstRect.getAttribute('width')) / 2; nodeHh = parseFloat(_firstRect.getAttribute('height')) / 2; }
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
      var vb = svgEl.viewBox.baseVal;
      var newX = Math.max(vb.x + nodeHw, Math.min(vb.x + vb.width - nodeHw, dragState.origX + dx));
      var newY = Math.max(vb.y + nodeHh, Math.min(vb.y + vb.height - nodeHh, dragState.origY + dy));
      dragState.g.setAttribute('transform', 'translate(' + newX + ',' + newY + ')');
      dragState.g.setAttribute('data-dx', newX - dragState.origX);
      dragState.g.setAttribute('data-dy', newY - dragState.origY);
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

    if (wrapEl) {
      wrapEl.addEventListener('touchstart', function(e) {
        if (e.touches.length === 1 && e.target.closest('.map-graph-node-wrap')) {
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
    categories = sorted(set(n.get("category", "") for n in nuggets if n.get("category", "")))
    cat_cbs = "".join(
        '<label class="map-cb-label"><input type="checkbox" class="map-filter-cat" value="{}"{}> {}</label>'.format(
            _html.escape(t), ' checked' if t.lower() == "consciousness" else "", _html.escape(t)
        )
        for t in categories
    )
    status_cbs = "".join(
        '<label class="map-cb-label"><input type="checkbox" class="map-filter-status-item" value="{}"> {}</label>'.format(
            _html.escape(s), _html.escape(s)
        )
        for s in (status_order or [])
    )
    row_btns_cat    = '<span class="map-row-btns"><button type="button" class="map-row-btn" data-action="all" data-target="cat">all</button><button type="button" class="map-row-btn" data-action="none" data-target="cat">none</button></span>'
    row_btns_status = '<span class="map-row-btns"><button type="button" class="map-row-btn" data-action="all" data-target="status">all</button><button type="button" class="map-row-btn" data-action="none" data-target="status">none</button></span>'
    controls_html = (
        '<div class="map-controls-top">'
        '<span class="map-graph-key-item"><span class="map-graph-key-dot map-graph-key-from"></span> from</span>'
        '<span class="map-graph-key-item"><span class="map-graph-key-dot map-graph-key-to"></span> to</span>'
        '<span class="map-controls-divider" aria-hidden="true"></span>'
        '<span id="map-selection-info" class="map-selection-info"></span>'
        '<span class="map-controls-divider" aria-hidden="true"></span>'
        '<button class="map-zoom-btn" id="map-zoom-out" type="button">\u2212</button>'
        '<button class="map-zoom-btn" id="map-zoom-in" type="button">+</button>'
        '<span class="map-zoom-label">zoom</span>'
        '<span id="map-zoom-level" class="map-zoom-level">1.0\u00d7</span>'
        '</div>'
    )
    filters_html = (
        '<div class="map-graph-filters">'
        + controls_html
        + '<div class="map-filter-row">' + cat_cbs + row_btns_cat + '</div>'
        + '<div class="map-filter-row map-filter-row--status">' + status_cbs + row_btns_status + '</div>'
        + '</div>'
    )
    svg = build_graph_svg(nuggets, show_title=False, link_nuggets=True, node_radius=40)
    page_style = '<style>html,body{overflow:hidden!important}.page-body{padding:0!important;animation:none!important;transform:none!important}.map-graph-wrap{position:fixed!important;left:0!important;right:0!important;bottom:0!important}.page-end{position:fixed!important;bottom:.5rem;left:50%!important;transform:translateX(-50%)!important;z-index:82!important;margin:0!important}</style>'
    return (
        page_style
        + '\n' + filters_html
        + '\n<div class="map-graph-wrap"><div class="map-graph-inner">'
        + svg
        + "</div></div>"
        + MAP_FILTER_SCRIPT
    )
