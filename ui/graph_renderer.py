"""Interactive graph visualization renderer using vis-network and HTML iframe."""

import json

COLOR_PALETTE: dict[str, str] = {
    "Supplier": "#4A90D9",
    "Port": "#E67E22",
    "Component": "#27AE60",
    "Product": "#8E44AD",
    "Country": "#C0392B",
    "Event": "#E74C3C",
    "Article": "#95A5A6",
    "Customer": "#F39C12",
    "Facility": "#16A085",
    "Entity": "#34495E",
}


def generate_subgraph_html(
    nodes: list[dict[str, str | dict[str, str | int | float | bool]]],
    edges: list[dict[str, str | dict[str, str | int | float | bool]]],
    height: int = 500,
) -> str:
    """Generate self-contained interactive vis-network HTML widget for Streamlit."""
    vis_nodes = []
    for n in nodes:
        node_id = str(n.get("id", ""))
        label_type = str(n.get("label", "Entity"))
        name = str(n.get("name", node_id))
        color = COLOR_PALETTE.get(label_type, "#34495E")

        props = n.get("properties", {})
        props_str = (
            "<br>".join(f"<b>{k}:</b> {v}" for k, v in props.items())
            if isinstance(props, dict)
            else ""
        )
        tooltip = f"<div style='font-family:sans-serif;font-size:12px;'><b>[{label_type}] {name}</b><br>{props_str}</div>"

        vis_nodes.append(
            {
                "id": node_id,
                "label": f"{name}\n({label_type})",
                "title": tooltip,
                "color": {
                    "background": color,
                    "border": "#FFFFFF",
                    "highlight": {"background": "#F1C40F", "border": "#FFFFFF"},
                },
                "font": {"color": "#FFFFFF", "size": 12, "face": "system-ui"},
                "shape": "dot" if label_type != "Port" else "box",
                "size": 22 if label_type in ["Port", "Product"] else 18,
            }
        )

    vis_edges = []
    for e in edges:
        source_id = str(e.get("source", ""))
        target_id = str(e.get("target", ""))
        rel_type = str(e.get("type", "CONNECTED_TO"))

        vis_edges.append(
            {
                "from": source_id,
                "to": target_id,
                "label": rel_type,
                "arrows": "to",
                "color": {"color": "#7F8C8D", "highlight": "#F1C40F"},
                "font": {"color": "#BDC3C7", "size": 10, "align": "middle"},
                "smooth": {"type": "continuous"},
            }
        )

    nodes_json = json.dumps(vis_nodes)
    edges_json = json.dumps(vis_edges)

    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
      <style>
        body {{
          margin: 0;
          padding: 0;
          background-color: #0E1117;
          overflow: hidden;
        }}
        #network {{
          width: 100%;
          height: {height}px;
          border: 1px solid #262730;
          border-radius: 8px;
          background-color: #161B22;
        }}
      </style>
    </head>
    <body>
      <div id="network"></div>
      <script type="text/javascript">
        const container = document.getElementById('network');
        const data = {{
          nodes: new vis.DataSet({nodes_json}),
          edges: new vis.DataSet({edges_json})
        }};
        const options = {{
          physics: {{
            stabilization: false,
            barnesHut: {{
              gravitationalConstant: -4000,
              springConstant: 0.04,
              springLength: 95
            }}
          }},
          interaction: {{
            hover: true,
            tooltipDelay: 100,
            zoomView: true,
            dragView: true
          }}
        }};
        const network = new vis.Network(container, data, options);
      </script>
    </body>
    </html>
    """
    return html_template
