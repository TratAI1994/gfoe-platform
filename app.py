"""
=============================================================================
GUEST FULFILLMENT OPTIMIZATION ENGINE (GFOE) — v4.4 ENTERPRISE EDITION
Architecture: Streamlit + PuLP MILP Solver + PyDeck 3D + Plotly Analytics
=============================================================================
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import time
import json
import itertools
from datetime import datetime, timedelta

# Optional heavy dependencies with graceful fallback
try:
    import pulp
    PULP_AVAILABLE = True
except ImportError:
    PULP_AVAILABLE = False

try:
    import pydeck as pdk
    PYDECK_AVAILABLE = True
except ImportError:
    PYDECK_AVAILABLE = False

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Guest Fulfillment Optimization Engine | Enterprise Suite",
    page_icon="⟐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# DESIGN SYSTEM & STYLES (Apple Dark / Executive Polished)
# -----------------------------------------------------------------------------
C = {
    "bg": "#000000",
    "surface": "#1c1c1e",
    "surface_card": "#2c2c2e",
    "border": "#3a3a3c",
    "text": "#f5f5f7",
    "text_muted": "#86868b",
    "accent": "#0a84ff",
    "green": "#30d158",
    "red": "#ff453a",
    "amber": "#ff9f0a",
    "purple": "#bf5af2",
    "cyan": "#64d2ff"
}

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: {C['text']};
        background-color: {C['bg']};
    }}

    .stApp {{
        background: radial-gradient(circle at 50% 0%, #1a1a24 0%, #000000 75%);
    }}

    /* Sidebar Toggle Button Visibility */
    [data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"] {{
        background: {C['accent']} !important;
        color: #ffffff !important;
        border-radius: 50% !important;
        box-shadow: 0 4px 14px rgba(10, 132, 255, 0.4) !important;
        z-index: 999999 !important;
    }}
    [data-testid="stSidebarCollapseButton"] svg,
    [data-testid="collapsedControl"] svg {{
        fill: #ffffff !important;
        stroke: #ffffff !important;
    }}

    .glass-card {{
        background: rgba(28, 28, 30, 0.75);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }}

    .kpi-title {{
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: {C['text_muted']};
        margin-bottom: 6px;
    }}

    .kpi-value {{
        font-size: 1.85rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        color: {C['text']};
        line-height: 1.1;
    }}

    .kpi-delta {{
        font-size: 0.75rem;
        font-weight: 500;
        margin-top: 6px;
    }}
    .delta-pos {{ color: {C['green']}; }}
    .delta-neg {{ color: {C['red']}; }}

    .mono {{
        font-family: 'JetBrains Mono', monospace;
    }}

    .badge {{
        display: inline-block;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
    }}
    .badge-green {{ background: rgba(48, 209, 88, 0.15); color: {C['green']}; }}
    .badge-blue {{ background: rgba(10, 132, 255, 0.15); color: {C['accent']}; }}
    .badge-amber {{ background: rgba(255, 159, 10, 0.15); color: {C['amber']}; }}
    .badge-red {{ background: rgba(255, 69, 58, 0.15); color: {C['red']}; }}
    .badge-purple {{ background: rgba(191, 90, 242, 0.15); color: {C['purple']}; }}

    .chat-bubble-user {{
        background: #0a84ff;
        color: #ffffff;
        padding: 10px 14px;
        border-radius: 14px 14px 2px 14px;
        margin-bottom: 8px;
        font-size: 0.85rem;
        max-width: 90%;
        margin-left: auto;
    }}
    .chat-bubble-assistant {{
        background: #2c2c2e;
        color: #f5f5f7;
        padding: 10px 14px;
        border-radius: 14px 14px 14px 2px;
        margin-bottom: 8px;
        font-size: 0.85rem;
        max-width: 90%;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# CORE DOMAIN DEFINITIONS & MASTER DATA
# -----------------------------------------------------------------------------
NODES = {
    "Metro Store Alpha": {
        "type": "Store", "lat": 40.7589, "lon": -73.9851, "zone": "Zone-1",
        "days": 2, "pick_cost": 5.00, "ship_cost": 4.00,
        "pick_capacity": 150, "current_utilization": 0.72,
        "inventory": {"TV": 1, "Diapers": 8, "Socks": 20, "Headphones": 4, "Coffee Maker": 2}
    },
    "Metro Store Beta": {
        "type": "Store", "lat": 40.6782, "lon": -73.9442, "zone": "Zone-1",
        "days": 2, "pick_cost": 5.00, "ship_cost": 5.00,
        "pick_capacity": 120, "current_utilization": 0.55,
        "inventory": {"TV": 0, "Diapers": 15, "Socks": 30, "Headphones": 6, "Coffee Maker": 5}
    },
    "Metro Store Gamma": {
        "type": "Store", "lat": 40.7282, "lon": -73.7949, "zone": "Zone-1",
        "days": 2, "pick_cost": 4.75, "ship_cost": 4.50,
        "pick_capacity": 100, "current_utilization": 0.85,
        "inventory": {"TV": 2, "Diapers": 4, "Socks": 15, "Headphones": 1, "Coffee Maker": 3}
    },
    "Regional DC East": {
        "type": "DC", "lat": 40.5000, "lon": -74.4000, "zone": "Zone-3",
        "days": 5, "pick_cost": 1.00, "ship_cost": 12.00,
        "pick_capacity": 5000, "current_utilization": 0.63,
        "inventory": {"TV": 50, "Diapers": 200, "Socks": 500, "Headphones": 80, "Coffee Maker": 120}
    },
    "Fulfillment Hub South": {
        "type": "Hub", "lat": 40.3500, "lon": -74.2000, "zone": "Zone-2",
        "days": 4, "pick_cost": 1.50, "ship_cost": 9.00,
        "pick_capacity": 3000, "current_utilization": 0.41,
        "inventory": {"TV": 30, "Diapers": 100, "Socks": 300, "Headphones": 45, "Coffee Maker": 60}
    }
}

CARRIERS = {
    "Express Courier": {"cost_multiplier": 1.00, "reliability": 0.98, "max_days": 2, "zones": ["Zone-1"]},
    "Ground Network": {"cost_multiplier": 1.15, "reliability": 0.95, "max_days": 5, "zones": ["Zone-1", "Zone-2", "Zone-3"]},
    "Premium Air": {"cost_multiplier": 1.85, "reliability": 0.97, "max_days": 2, "zones": ["Zone-1", "Zone-2", "Zone-3"]},
    "Economy Post": {"cost_multiplier": 0.90, "reliability": 0.91, "max_days": 3, "zones": ["Zone-1", "Zone-2", "Zone-3"]},
    "Same-Day Fleet": {"cost_multiplier": 2.50, "reliability": 0.99, "max_days": 1, "zones": ["Zone-1"]}
}

SKU_CATALOG = {
    "TV": {"size": "Large", "weight_kg": 18.5, "max_qty": 3, "icon": "📺"},
    "Diapers": {"size": "Medium", "weight_kg": 4.2, "max_qty": 10, "icon": "👶"},
    "Socks": {"size": "Small", "weight_kg": 0.2, "max_qty": 20, "icon": "🧦"},
    "Headphones": {"size": "Small", "weight_kg": 0.5, "max_qty": 5, "icon": "🎧"},
    "Coffee Maker": {"size": "Medium", "weight_kg": 3.8, "max_qty": 4, "icon": "☕"}
}

SLA_MAX_DAYS = {
    "Standard (5d)": 5,
    "Express (3d)": 3,
    "Rush (2d)": 2,
    "Same Day (1d)": 1
}

# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------
def get_surge_multiplier(utilization: float) -> float:
    """Calculates non-linear cost multiplier as capacity fills."""
    if utilization < 0.70:
        return 1.00
    elif utilization < 0.85:
        return 1.00 + (utilization - 0.70) * 1.5
    else:
        return 1.225 + (utilization - 0.85) * 3.5

def get_remaining_capacity(node_name: str) -> int:
    """Returns available discrete unit pick capacity for a node."""
    node = NODES[node_name]
    used = node["pick_capacity"] * node["current_utilization"]
    return max(0, int(node["pick_capacity"] - used))

def get_best_carrier(node_name: str, delivery_zone: str, sla_max_days: int):
    """
    Finds the lowest cost carrier satisfying BOTH zone and max SLA eligibility.
    Returns None if no carrier qualifies.
    """
    eligible = []
    for cname, cinfo in CARRIERS.items():
        if delivery_zone in cinfo["zones"] and cinfo["max_days"] <= sla_max_days:
            eligible.append((cname, cinfo["cost_multiplier"], cinfo["reliability"]))
    
    if not eligible:
        return None
    eligible.sort(key=lambda x: x[1])
    return eligible[0]

def _create_binary_var(name: str):
    """
    Bulletproof factory for binary decision variables across all PuLP versions.
    """
    cat_bin = getattr(pulp, 'LpBinary', 'Binary')
    try:
        return pulp.LpVariable(name, lowBound=0, upBound=1, cat=cat_bin)
    except TypeError:
        pass
    try:
        return pulp.LpVariable(name, 0, 1, cat_bin)
    except TypeError:
        pass
    try:
        return pulp.LpVariable(name, lowBound=0, upBound=1, category=cat_bin)
    except TypeError:
        pass
    return pulp.LpVariable(name, lowBound=0, upBound=1)

def apply_safe_styler_map(styler, func, subset=None):
    """Cross-version safe mapper for pandas.io.formats.style.Styler."""
    if hasattr(styler, "map"):
        return styler.map(func, subset=subset)
    elif hasattr(styler, "applymap"):
        return styler.applymap(func, subset=subset)
    return styler

def calculate_baseline(cart: dict, sla_max_days: int, delivery_zone: str) -> dict:
    """Simple greedy heuristic: fulfill from the node with the fastest ETA, then lowest shipping."""
    active_cart = {k: v for k, v in cart.items() if v > 0}
    if not active_cart: return None

    nodes = list(NODES.keys())
    nodes.sort(key=lambda n: (NODES[n]["days"], NODES[n]["ship_cost"]))

    assignments = {}
    for sku, qty in active_cart.items():
        for n in nodes:
            if NODES[n]["inventory"].get(sku, 0) >= qty and NODES[n]["days"] <= sla_max_days:
                if get_best_carrier(n, delivery_zone, sla_max_days):
                    assignments[sku] = n
                    break

    if len(assignments) != len(active_cart): return None

    used_nodes = set(assignments.values())
    pick_cost = sum(active_cart[sku] * NODES[n]["pick_cost"] for sku, n in assignments.items())
    ship_cost = sum(get_best_carrier(n, delivery_zone, sla_max_days)[1] * NODES[n]["ship_cost"] for n in used_nodes)

    return {"pick_cost": pick_cost, "ship_cost": ship_cost, "total_cost": pick_cost + ship_cost}

# -----------------------------------------------------------------------------
# MILP SOLVER CORE ENGINE (PuLP Branch-and-Cut)
# -----------------------------------------------------------------------------
def solve_milp(cart: dict, sla_max_days: int, delivery_zone: str) -> dict:
    t_start = time.perf_counter()
    active_cart = {k: v for k, v in cart.items() if v > 0}
    
    if not active_cart:
        return {
            "feasible": False,
            "reason": "Cart is empty",
            "solver_status": "Not Run",
            "latency_ms": 0,
            "variables_count": 0,
            "constraints_count": 0,
            "tight_constraints": [],
            "banned_nodes": []
        }

    skus = list(active_cart.keys())
    nodes = list(NODES.keys())

    prob = pulp.LpProblem("Guest_Fulfillment_Optimization", pulp.LpMinimize)

    x = {(sku, node): _create_binary_var(f"x_{sku}_{node}") for sku in skus for node in nodes}
    y = {node: _create_binary_var(f"y_{node}") for node in nodes}

    banned_nodes = []
    for node in nodes:
        node_info = NODES[node]
        if node_info["days"] > sla_max_days:
            banned_nodes.append((node, f"Node ETA ({node_info['days']}d) exceeds SLA ({sla_max_days}d)"))
            for sku in skus:
                prob += x[sku, node] == 0, f"SLA_Ban_{sku}_{node}"
            continue
        
        best_c = get_best_carrier(node, delivery_zone, sla_max_days)
        if best_c is None:
            banned_nodes.append((node, f"No carrier meets Zone ({delivery_zone}) & SLA ({sla_max_days}d)"))
            for sku in skus:
                prob += x[sku, node] == 0, f"NoCarrier_Ban_{sku}_{node}"
            continue

    for sku in skus:
        prob += pulp.lpSum([x[sku, node] for node in nodes]) == 1, f"Fulfill_{sku}"

    for sku in skus:
        for node in nodes:
            avail_inv = NODES[node]["inventory"].get(sku, 0)
            req_qty = active_cart[sku]
            if avail_inv < req_qty:
                prob += x[sku, node] == 0, f"InvLimit_{sku}_{node}"

    for node in nodes:
        rem_cap = get_remaining_capacity(node)
        prob += pulp.lpSum([active_cart[sku] * x[sku, node] for sku in skus]) <= rem_cap, f"Capacity_{node}"

    for node in nodes:
        for sku in skus:
            prob += y[node] >= x[sku, node], f"Activate_{sku}_{node}"

    cost_terms = []
    for node in nodes:
        node_info = NODES[node]
        best_c = get_best_carrier(node, delivery_zone, sla_max_days)
        c_mult = best_c[1] if best_c else 1.0
        surge_mult = get_surge_multiplier(node_info["current_utilization"])
        
        for sku in skus:
            qty = active_cart[sku]
            unit_pick = node_info["pick_cost"] * surge_mult
            cost_terms.append(qty * unit_pick * x[sku, node])
        
        effective_ship = node_info["ship_cost"] * c_mult
        cost_terms.append(effective_ship * y[node])

    prob += pulp.lpSum(cost_terms), "Total_Fulfillment_Cost"

    try:
        solver = pulp.PULP_CBC_CMD(msg=0)
        prob.solve(solver)
    except Exception:
        prob.solve()

    latency_ms = (time.perf_counter() - t_start) * 1000.0
    status_str = pulp.LpStatus[prob.status]

    if status_str != "Optimal":
        return {
            "feasible": False,
            "reason": f"No feasible fulfillment allocation found ({status_str})",
            "solver_status": status_str,
            "latency_ms": latency_ms,
            "variables_count": len(prob.variables()),
            "constraints_count": len(prob.constraints),
            "tight_constraints": [],
            "banned_nodes": banned_nodes
        }

    assignments = {}
    activated_nodes = []
    tight_constraints = []

    for node in nodes:
        y_val = pulp.value(y[node])
        if y_val and y_val > 0.5:
            activated_nodes.append(node)

    for sku in skus:
        for node in nodes:
            x_val = pulp.value(x[sku, node])
            if x_val and x_val > 0.5:
                assignments[sku] = node

    for name, c in prob.constraints.items():
        slack = c.slack
        if slack is not None and abs(slack) < 1e-5:
            tight_constraints.append(name)

    node_units = {}
    node_skus = {}
    for sku, node in assignments.items():
        node_units[node] = node_units.get(node, 0) + active_cart[sku]
        node_skus.setdefault(node, []).append(sku)

    total_pick = 0.0
    total_ship = 0.0
    carriers_used = {}
    max_days_seen = 0
    rel_scores = []

    for node, skus_in_node in node_skus.items():
        node_info = NODES[node]
        surge_mult = get_surge_multiplier(node_info["current_utilization"])
        best_c = get_best_carrier(node, delivery_zone, sla_max_days)
        c_name, c_mult, c_rel = best_c
        carriers_used[node] = c_name
        rel_scores.append(c_rel)

        for sku in skus_in_node:
            total_pick += active_cart[sku] * (node_info["pick_cost"] * surge_mult)
        
        total_ship += node_info["ship_cost"] * c_mult
        max_days_seen = max(max_days_seen, node_info["days"])

    total_cost = total_pick + total_ship
    composite_reliability = float(np.prod(rel_scores)) if rel_scores else 1.0

    return {
        "feasible": True,
        "assignments": assignments,
        "active_nodes": activated_nodes,
        "node_units": node_units,
        "node_skus": node_skus,
        "carriers_used": carriers_used,
        "total_cost": total_cost,
        "pick_cost": total_pick,
        "ship_cost": total_ship,
        "split_count": len(activated_nodes),
        "sla_days_achieved": max_days_seen,
        "composite_reliability": composite_reliability,
        "solver_status": "Optimal",
        "latency_ms": latency_ms,
        "variables_count": len(prob.variables()),
        "constraints_count": len(prob.constraints),
        "tight_constraints": tight_constraints,
        "banned_nodes": banned_nodes,
        "raw_variables": {v.name: pulp.value(v) for v in prob.variables() if pulp.value(v) is not None and pulp.value(v) > 0.01}
    }

# -----------------------------------------------------------------------------
# FALLBACK BRUTE-FORCE SOLVER
# -----------------------------------------------------------------------------
def solve_fallback_bruteforce(cart: dict, sla_max_days: int, delivery_zone: str) -> dict:
    t_start = time.perf_counter()
    active_cart = {k: v for k, v in cart.items() if v > 0}
    if not active_cart:
        return {"feasible": False, "reason": "Cart is empty", "solver_status": "Not Run", "latency_ms": 0}

    skus = list(active_cart.keys())
    nodes = list(NODES.keys())
    valid_nodes = []
    banned_nodes = []

    for n in nodes:
        if NODES[n]["days"] > sla_max_days:
            banned_nodes.append((n, f"ETA > {sla_max_days}d"))
            continue
        if get_best_carrier(n, delivery_zone, sla_max_days) is None:
            banned_nodes.append((n, "No Carrier Feasible"))
            continue
        valid_nodes.append(n)

    if not valid_nodes:
        return {
            "feasible": False,
            "reason": "All fulfillment nodes violate SLA or zone carrier constraints.",
            "solver_status": "Infeasible",
            "latency_ms": (time.perf_counter() - t_start) * 1000.0,
            "banned_nodes": banned_nodes
        }

    best_plan = None
    min_cost = float("inf")

    for assignment in itertools.product(valid_nodes, repeat=len(skus)):
        alloc = dict(zip(skus, assignment))
        node_loads = {}
        feasible = True

        for sku, node in alloc.items():
            qty = active_cart[sku]
            if NODES[node]["inventory"].get(sku, 0) < qty:
                feasible = False
                break
            node_loads[node] = node_loads.get(node, 0) + qty

        if not feasible:
            continue

        for node, load in node_loads.items():
            if load > get_remaining_capacity(node):
                feasible = False
                break
        if not feasible:
            continue

        cur_pick = 0.0
        cur_ship = 0.0
        used_nodes = set(alloc.values())
        for node in used_nodes:
            surge = get_surge_multiplier(NODES[node]["current_utilization"])
            bc = get_best_carrier(node, delivery_zone, sla_max_days)
            cur_ship += NODES[node]["ship_cost"] * bc[1]
            for sku, assigned_node in alloc.items():
                if assigned_node == node:
                    cur_pick += active_cart[sku] * (NODES[node]["pick_cost"] * surge)

        tot = cur_pick + cur_ship
        if tot < min_cost:
            min_cost = tot
            best_plan = (alloc, cur_pick, cur_ship, tot)

    latency_ms = (time.perf_counter() - t_start) * 1000.0

    if best_plan is None:
        return {
            "feasible": False,
            "reason": "No combination satisfies joint capacity and inventory constraints.",
            "solver_status": "Infeasible",
            "latency_ms": latency_ms,
            "banned_nodes": banned_nodes
        }

    alloc, pick_c, ship_c, tot_c = best_plan
    act_nodes = list(set(alloc.values()))
    carriers_used = {n: get_best_carrier(n, delivery_zone, sla_max_days)[0] for n in act_nodes}
    rel_scores = [get_best_carrier(n, delivery_zone, sla_max_days)[2] for n in act_nodes]

    return {
        "feasible": True,
        "assignments": alloc,
        "active_nodes": act_nodes,
        "node_units": {n: sum(active_cart[s] for s, assigned in alloc.items() if assigned == n) for n in act_nodes},
        "node_skus": {n: [s for s, assigned in alloc.items() if assigned == n] for n in act_nodes},
        "carriers_used": carriers_used,
        "total_cost": tot_c,
        "pick_cost": pick_c,
        "ship_cost": ship_c,
        "split_count": len(act_nodes),
        "sla_days_achieved": max(NODES[n]["days"] for n in act_nodes),
        "composite_reliability": float(np.prod(rel_scores)),
        "solver_status": "Optimal (Fallback Exhaustive)",
        "latency_ms": latency_ms,
        "variables_count": len(skus) * len(valid_nodes),
        "constraints_count": len(skus) + len(valid_nodes),
        "tight_constraints": ["Inventory/Capacity bound active"],
        "banned_nodes": banned_nodes,
        "raw_variables": {f"x_{s}_{n}": 1.0 for s, n in alloc.items()}
    }

def solve_optimization(cart: dict, sla: str, delivery_zone: str) -> dict:
    sla_days = SLA_MAX_DAYS.get(sla, 5)
    if PULP_AVAILABLE:
        try:
            return solve_milp(cart, sla_days, delivery_zone)
        except Exception:
            res = solve_fallback_bruteforce(cart, sla_days, delivery_zone)
            res["solver_status"] = "Optimal (Fallback Engine)"
            return res
    return solve_fallback_bruteforce(cart, sla_days, delivery_zone)

# -----------------------------------------------------------------------------
# SESSION STATE INITIALIZATION
# -----------------------------------------------------------------------------
if "cart" not in st.session_state:
    st.session_state.cart = {"TV": 1, "Diapers": 2, "Socks": 4, "Headphones": 0, "Coffee Maker": 1}

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "content": "Welcome to the Guest Fulfillment Optimization Engine. Adjust the order context in the sidebar and ask me any questions about routing decisions, active constraints, or margin tradeoffs."}
    ]

# -----------------------------------------------------------------------------
# SIDEBAR CONTROLS & CART CONFIGURATOR
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("<div style='font-size: 1.15rem; font-weight: 700; letter-spacing: -0.02em;'>Order Configuration</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size: 0.75rem; color: #86868b; margin-bottom: 16px;'>Simulate real-time guest checkout conditions</div>", unsafe_allow_html=True)

    # Preset scenarios
    st.markdown("<div class='kpi-title'>Quick Presets</div>", unsafe_allow_html=True)
    p_col1, p_col2, p_col3 = st.columns(3)
    if p_col1.button("Baby", use_container_width=True):
        st.session_state.cart = {"TV": 0, "Diapers": 8, "Socks": 6, "Headphones": 0, "Coffee Maker": 0}
        st.rerun()
    if p_col2.button("Tech", use_container_width=True):
        st.session_state.cart = {"TV": 2, "Diapers": 0, "Socks": 0, "Headphones": 3, "Coffee Maker": 0}
        st.rerun()
    if p_col3.button("Mix", use_container_width=True):
        st.session_state.cart = {"TV": 1, "Diapers": 2, "Socks": 5, "Headphones": 1, "Coffee Maker": 1}
        st.rerun()

    p_col4, p_col5 = st.columns(2)
    if p_col4.button("Big Order", use_container_width=True):
        st.session_state.cart = {"TV": 3, "Diapers": 10, "Socks": 15, "Headphones": 4, "Coffee Maker": 4}
        st.rerun()
    if p_col5.button("Reset", use_container_width=True):
        st.session_state.cart = {"TV": 0, "Diapers": 0, "Socks": 0, "Headphones": 0, "Coffee Maker": 0}
        st.rerun()

    st.markdown("<hr style='border-color: #2c2c2e; margin: 16px 0;'>", unsafe_allow_html=True)

    # SKU quantity adjusters
    st.markdown("<div class='kpi-title'>Guest Cart Items</div>", unsafe_allow_html=True)
    for sku, details in SKU_CATALOG.items():
        c_label, c_btn1, c_val, c_btn2 = st.columns([3, 1, 1, 1])
        c_label.markdown(f"<div style='font-size: 0.85rem; padding-top: 4px;'>{details['icon']} {sku}</div>", unsafe_allow_html=True)
        
        if c_btn1.button("-", key=f"dec_{sku}"):
            if st.session_state.cart[sku] > 0:
                st.session_state.cart[sku] -= 1
                st.rerun()
        
        c_val.markdown(f"<div style='text-align: center; font-weight: 600; font-size: 0.9rem; padding-top: 4px;'>{st.session_state.cart[sku]}</div>", unsafe_allow_html=True)
        
        if c_btn2.button("+", key=f"inc_{sku}"):
            if st.session_state.cart[sku] < details["max_qty"]:
                st.session_state.cart[sku] += 1
                st.rerun()

    st.markdown("<hr style='border-color: #2c2c2e; margin: 16px 0;'>", unsafe_allow_html=True)

    # SLA & Delivery Zone
    st.markdown("<div class='kpi-title'>Guest SLA Promise</div>", unsafe_allow_html=True)
    selected_sla = st.selectbox("Max Delivery Window", list(SLA_MAX_DAYS.keys()), index=0, label_visibility="collapsed")

    st.markdown("<div class='kpi-title' style='margin-top: 12px;'>Destination Zone</div>", unsafe_allow_html=True)
    selected_zone = st.selectbox("Guest Geo Zone", ["Zone-1", "Zone-2", "Zone-3"], index=0, label_visibility="collapsed")

    st.markdown("<hr style='border-color: #2c2c2e; margin: 16px 0;'>", unsafe_allow_html=True)

    # Copilot
    st.markdown("<div style='font-size: 0.95rem; font-weight: 700; letter-spacing: -0.01em;'>Decision Explainability Copilot</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size: 0.72rem; color: #86868b; margin-bottom: 10px;'>Constraint-grounded solver reasoning</div>", unsafe_allow_html=True)

    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_history[-4:]:
            bubble_class = "chat-bubble-user" if msg["role"] == "user" else "chat-bubble-assistant"
            st.markdown(f"<div class='{bubble_class}'>{msg['content']}</div>", unsafe_allow_html=True)

    user_query = st.chat_input("Ask about this routing decision...")
    if user_query:
        st.session_state.chat_history.append({"role": "user", "content": user_query})
        
        sol_eval = solve_optimization(st.session_state.cart, selected_sla, selected_zone)
        q_lower = user_query.lower()

        if "why not" in q_lower or "dc" in q_lower or "alpha" in q_lower or "beta" in q_lower or "gamma" in q_lower:
            response = "Node selection breakdown: Regional DC East offers $1.00 pick cost vs $5.00 in metro stores, but incurs $12.00 shipping and 5-day ETA. If the guest selects a 2-day or 3-day SLA, Regional DC is automatically pruned due to the hard delivery timeline constraint."
        elif "split" in q_lower:
            splits = sol_eval.get("split_count", 1)
            response = f"Current order split count: {splits}. An order split is triggered only when inventory is fragmented across multiple stores or when store pick capacity thresholds are reached."
        elif "cost" in q_lower or "expense" in q_lower:
            tot = sol_eval.get("total_cost", 0)
            pick = sol_eval.get("pick_cost", 0)
            ship = sol_eval.get("ship_cost", 0)
            response = f"Financial summary: Total fulfillment expense is ${tot:.2f} (Pick: ${pick:.2f}, Line-haul Shipping: ${ship:.2f}). Evaluated via MILP branch-and-cut optimization."
        elif "sla" in q_lower or "speed" in q_lower or "eta" in q_lower:
            achieved = sol_eval.get("sla_days_achieved", 0)
            target = SLA_MAX_DAYS.get(selected_sla, 5)
            response = f"SLA adherence: Promised window is {target} days; optimal network routing achieves fulfillment in {achieved} days."
        elif "tight" in q_lower or "constraint" in q_lower or "active" in q_lower:
            tc = sol_eval.get("tight_constraints", [])
            response = f"Currently active/tight constraints in solver: {len(tc)} constraints reached zero slack (exact SKU fulfillment, inventory bounds, and delivery window)."
        else:
            response = f"Current solution state: {sol_eval.get('solver_status')} in {sol_eval.get('latency_ms', 0):.1f}ms. Total cost: ${sol_eval.get('total_cost', 0.0):.2f}. Try asking: 'Why was this split?', 'Why not use Regional DC?', or 'What are the active constraints?'"

        st.session_state.chat_history.append({"role": "assistant", "content": response})
        st.rerun()

# -----------------------------------------------------------------------------
# MAIN VIEWPORT HEADER
# -----------------------------------------------------------------------------
top_col1, top_col2 = st.columns([3, 1])
with top_col1:
    st.markdown("<div style='font-size: 1.6rem; font-weight: 700; letter-spacing: -0.03em; margin-bottom: 2px;'>Guest Fulfillment Optimization Engine</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size: 0.85rem; color: #86868b; margin-bottom: 20px;'>Autonomous Order Routing, Micro-Fulfillment Intelligence & Capacity Orchestration</div>", unsafe_allow_html=True)

with top_col2:
    st.markdown("""
    <div style='text-align: right; padding-top: 6px;'>
        <span class='badge badge-green'>MILP Branch & Cut</span>
        <span class='badge badge-blue' style='margin-left: 4px;'>Live Telemetry</span>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# EXECUTE SOLVER FOR CURRENT STATE
# -----------------------------------------------------------------------------
opt_result = solve_optimization(st.session_state.cart, selected_sla, selected_zone)

# -----------------------------------------------------------------------------
# EXECUTIVE KPI SUMMARY RIBBON
# -----------------------------------------------------------------------------
kpi_c1, kpi_c2, kpi_c3, kpi_c4, kpi_c5 = st.columns(5)

with kpi_c1:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("<div class='kpi-title'>Total Fulfillment Cost</div>", unsafe_allow_html=True)
    if opt_result["feasible"]:
        st.markdown(f"<div class='kpi-value'>${opt_result['total_cost']:.2f}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='kpi-delta delta-pos'>Pick: ${opt_result['pick_cost']:.2f} | Ship: ${opt_result['ship_cost']:.2f}</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='kpi-value' style='color: #ff453a;'>N/A</div>", unsafe_allow_html=True)
        st.markdown("<div class='kpi-delta delta-neg'>Infeasible allocation</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with kpi_c2:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("<div class='kpi-title'>Active Shipments / Splits</div>", unsafe_allow_html=True)
    if opt_result["feasible"]:
        splits = opt_result["split_count"]
        badge = "delta-pos" if splits == 1 else "delta-neg"
        split_desc = "Single Box Unified" if splits == 1 else f"{splits}-Way Split Shipment"
        st.markdown(f"<div class='kpi-value'>{splits}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='kpi-delta {badge}'>{split_desc}</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='kpi-value'>0</div>", unsafe_allow_html=True)
        st.markdown("<div class='kpi-delta delta-neg'>No route</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with kpi_c3:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("<div class='kpi-title'>Promise Adherence</div>", unsafe_allow_html=True)
    if opt_result["feasible"]:
        days = opt_result["sla_days_achieved"]
        max_s = SLA_MAX_DAYS[selected_sla]
        st.markdown(f"<div class='kpi-value'>{days}d <span style='font-size: 1rem; color: #86868b; font-weight:400;'>/ {max_s}d max</span></div>", unsafe_allow_html=True)
        st.markdown("<div class='kpi-delta delta-pos'>Within SLA Promise Window</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='kpi-value' style='color: #ff453a;'>Breached</div>", unsafe_allow_html=True)
        st.markdown("<div class='kpi-delta delta-neg'>SLA unachievable</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with kpi_c4:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("<div class='kpi-title'>Composite Reliability</div>", unsafe_allow_html=True)
    if opt_result["feasible"]:
        rel = opt_result["composite_reliability"] * 100
        st.markdown(f"<div class='kpi-value'>{rel:.1f}%</div>", unsafe_allow_html=True)
        st.markdown("<div class='kpi-delta delta-pos'>Carrier On-Time Probability</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='kpi-value'>0.0%</div>", unsafe_allow_html=True)
        st.markdown("<div class='kpi-delta delta-neg'>No carrier match</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with kpi_c5:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("<div class='kpi-title'>Solver Latency</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='kpi-value'>{opt_result.get('latency_ms', 0):.1f}ms</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='kpi-delta delta-pos'>{opt_result.get('solver_status', 'N/A')} Status</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# APPLICATION NAVIGATION TABS
# -----------------------------------------------------------------------------
tabs = st.tabs([
    "⟐ Optimization Engine",
    "◉ Demand Forecast ML",
    "◈ Store Capacity & Surge",
    "⌁ Carrier Dynamic Routing",
    "⚗ A/B Policy Sandbox",
    "◎ Network Pulse — Simulated Operations",
    "⟡ OKRs & P&L Impact",
    "⌘ Microservice Architecture"
])

# -----------------------------------------------------------------------------
# TAB 1: OPTIMIZATION ENGINE & DECISION TRACE
# -----------------------------------------------------------------------------
with tabs[0]:
    st.markdown("<div style='font-size: 1.15rem; font-weight: 600; margin-bottom: 12px;'>Optimal Fulfillment Routing Allocation</div>", unsafe_allow_html=True)

    if not opt_result["feasible"]:
        st.error(f"Fulfillment Infeasible: {opt_result['reason']}")
        if opt_result.get("banned_nodes"):
            st.markdown("**Banned Node Diagnostics:**")
            for b_node, b_reason in opt_result["banned_nodes"]:
                st.markdown(f"- **{b_node}**: `{b_reason}`")
    else:
        alloc_cols = st.columns(len(opt_result["active_nodes"]))
        for idx, node_name in enumerate(opt_result["active_nodes"]):
            node_data = NODES[node_name]
            skus_assigned = opt_result["node_skus"][node_name]
            carrier = opt_result["carriers_used"][node_name]
            units = opt_result["node_units"][node_name]
            
            with alloc_cols[idx]:
                st.markdown(f"""
                <div class='glass-card' style='border-top: 3px solid {C['accent']};'>
                    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
                        <span style='font-weight: 700; font-size: 0.95rem;'>{node_name}</span>
                        <span class='badge badge-blue'>{node_data['type']}</span>
                    </div>
                    <div style='font-size: 0.8rem; color: #86868b; margin-bottom: 12px;'>
                        Transit Time: <b style='color:#f5f5f7;'>{node_data['days']} Days</b> | Carrier: <b style='color:#f5f5f7;'>{carrier}</b>
                    </div>
                    <div style='font-size: 0.72rem; text-transform: uppercase; color: #86868b; font-weight: 600;'>Assigned Items:</div>
                """, unsafe_allow_html=True)
                
                for s in skus_assigned:
                    qty = st.session_state.cart[s]
                    st.markdown(f"""
                    <div style='display: flex; justify-content: space-between; font-size: 0.82rem; padding: 4px 0; border-bottom: 1px solid rgba(255,255,255,0.05);'>
                        <span>{SKU_CATALOG[s]['icon']} {s}</span>
                        <span class='mono' style='font-weight: 600;'>{qty} units</span>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown(f"""
                    <div style='margin-top: 12px; font-size: 0.8rem; color: #86868b;'>
                        Total Pick Load: <b style='color:#f5f5f7;'>{units} units</b>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        with st.expander("⌘ Decision Trace — MILP Branch-and-Cut Optimization Internals", expanded=False):
            dt_col1, dt_col2, dt_col3, dt_col4 = st.columns(4)
            dt_col1.metric("Solver Status", opt_result.get("solver_status", "N/A"))
            dt_col2.metric("Execution Latency", f"{opt_result.get('latency_ms', 0):.2f} ms")
            dt_col3.metric("Decision Variables", opt_result.get("variables_count", 0))
            dt_col4.metric("Active Constraints", opt_result.get("constraints_count", 0))

            st.markdown("<div style='margin-top: 16px; font-size: 0.85rem; font-weight: 600;'>Active / Tight Constraints in Optimal Tableau:</div>", unsafe_allow_html=True)
            tight = opt_result.get("tight_constraints", [])
            if tight:
                t_cols = st.columns(min(len(tight), 3))
                for idx, t_name in enumerate(tight[:6]):
                    t_cols[idx % 3].markdown(f"<div style='font-size: 0.75rem; font-family: monospace; background: #2c2c2e; padding: 6px 10px; border-radius: 6px; margin-bottom: 6px;'>✓ {t_name} (Slack = 0.000)</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div style='font-size: 0.8rem; color: #86868b;'>No unconstrained bottlenecks reached zero slack.</div>", unsafe_allow_html=True)

            if opt_result.get("raw_variables"):
                st.markdown("<div style='margin-top: 12px; font-size: 0.85rem; font-weight: 600;'>Variable Assignments:</div>", unsafe_allow_html=True)
                st.json(opt_result["raw_variables"])

        # Cost Anatomy & Sankey Diagram 
        st.markdown("<div style='font-size: 1.15rem; font-weight: 600; margin: 32px 0 16px 0;'>Cost Anatomy & Fulfillment Flow</div>", unsafe_allow_html=True)
        v_col1, v_col2 = st.columns(2)

        with v_col1:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            wf = go.Figure(go.Waterfall(
                orientation="v",
                measure=["relative", "relative", "total"],
                x=["Picking", "Shipping", "Total"],
                y=[opt_result["pick_cost"], opt_result["ship_cost"], opt_result["total_cost"]],
                text=[f"${opt_result['pick_cost']:.2f}", f"${opt_result['ship_cost']:.2f}", f"${opt_result['total_cost']:.2f}"],
                textposition="outside",
                connector={"line": {"color": C['border']}},
                increasing={"marker": {"color": C['accent']}},
                totals={"marker": {"color": C['purple']}}
            ))
            wf.update_layout(
                title="Cost Build-Up",
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color=C['text'], family="Inter"),
                margin=dict(l=20, r=20, t=40, b=20), height=280
            )
            st.plotly_chart(wf, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with v_col2:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            baseline = calculate_baseline(st.session_state.cart, SLA_MAX_DAYS[selected_sla], selected_zone)

            if baseline:
                comp = go.Figure()
                comp.add_trace(go.Bar(name='Picking', x=['Baseline Heuristic', 'GFOE MILP'],
                                      y=[baseline["pick_cost"], opt_result["pick_cost"]],
                                      marker_color=C['amber'],
                                      text=[f"${baseline['pick_cost']:.2f}", f"${opt_result['pick_cost']:.2f}"],
                                      textposition="inside"))
                comp.add_trace(go.Bar(name='Shipping', x=['Baseline Heuristic', 'GFOE MILP'],
                                      y=[baseline["ship_cost"], opt_result["ship_cost"]],
                                      marker_color=C['accent'],
                                      text=[f"${baseline['ship_cost']:.2f}", f"${opt_result['ship_cost']:.2f}"],
                                      textposition="inside"))
                comp.update_layout(
                    title="Cost: Baseline vs Optimization",
                    barmode='stack',
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color=C['text'], family="Inter"),
                    margin=dict(l=20, r=20, t=40, b=20), height=280
                )
                st.plotly_chart(comp, use_container_width=True)
            else:
                st.info("Baseline heuristic could not find a feasible route. MILP Optimization is required for this cart.")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 0.95rem; font-weight: 600; margin-bottom: 12px;'>Network Fulfillment Flow</div>", unsafe_allow_html=True)

        labels = ["Guest Order"] + list(opt_result["node_skus"].keys()) + [s for s in st.session_state.cart if st.session_state.cart[s] > 0]
        idx = {l: i for i, l in enumerate(labels)}
        srcs, tgts, vals, colors = [], [], [], []

        for node, skus in opt_result["node_skus"].items():
            srcs.append(idx["Guest Order"])
            tgts.append(idx[node])
            vals.append(sum(st.session_state.cart[s] for s in skus))
            colors.append("rgba(10, 132, 255, 0.4)") 

            for sku in skus:
                srcs.append(idx[node])
                tgts.append(idx[sku])
                vals.append(st.session_state.cart[sku])
                colors.append("rgba(191, 90, 242, 0.4)") 

        sk = go.Figure(data=[go.Sankey(
            node=dict(
                pad=20, thickness=20,
                line=dict(color=C['border'], width=0),
                label=labels,
                color=[C['accent']] + [C['surface_card']] * (len(labels)-1)
            ),
            link=dict(source=srcs, target=tgts, value=vals, color=colors)
        )])
        sk.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color=C['text'], family="Inter"),
            margin=dict(l=10, r=10, t=10, b=10), height=320
        )
        st.plotly_chart(sk, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Network Node Master Inventory Status Table (Native Styled DataFrame)
    st.markdown("<div style='font-size: 1.15rem; font-weight: 600; margin: 24px 0 12px 0;'>Network Node Inventory & Capacity Overview</div>", unsafe_allow_html=True)
    
    node_table_data = []
    for n_name, n_data in NODES.items():
        rem_cap = get_remaining_capacity(n_name)
        surge = get_surge_multiplier(n_data['current_utilization'])
        inv_str = ", ".join([f"{k}: {v}" for k, v in n_data['inventory'].items() if v > 0])
        
        node_table_data.append({
            "Node Name": n_name,
            "Type": n_data['type'],
            "Zone": n_data['zone'],
            "ETA": f"{n_data['days']} Days",
            "Base Pick": f"${n_data['pick_cost']:.2f}",
            "Base Ship": f"${n_data['ship_cost']:.2f}",
            "Utilization": f"{int(n_data['current_utilization']*100)}% ({rem_cap} avail)",
            "Surge": f"{surge:.2f}x",
            "Active Inventory": inv_str
        })
        
    df_nodes = pd.DataFrame(node_table_data)
    
    def color_surge_val(val):
        if "1.00x" in str(val):
            return "color: #30d158; font-weight: 600;"
        elif "x" in str(val):
            return "color: #ff9f0a; font-weight: 600;"
        return ""

    st_nodes = apply_safe_styler_map(df_nodes.style, color_surge_val, subset=['Surge'])
    st.dataframe(st_nodes, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# TAB 2: DEMAND FORECAST ML
# -----------------------------------------------------------------------------
with tabs[1]:
    st.markdown("<div style='font-size: 1.15rem; font-weight: 600;'>Machine Learning Demand Forecast with Uncertainty Bands</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size: 0.85rem; color: #86868b; margin-bottom: 16px;'>30-day forward projection modeling seasonality, trend, and confidence intervals</div>", unsafe_allow_html=True)

    fc_col1, fc_col2 = st.columns([1, 3])
    with fc_col1:
        sel_sku = st.selectbox("Select Forecast SKU", list(SKU_CATALOG.keys()))
        conf_interval = st.slider("Confidence Interval", 0.80, 0.99, 0.95, 0.05)
        promo_lift = st.checkbox("Simulate Promo Campaign (+25%)", value=False)
        stock_threshold = st.number_input("Node Safety Stock Threshold", value=35)

    np.random.seed(42)
    dates_hist = [datetime.now().date() - timedelta(days=i) for i in range(60, 0, -1)]
    dates_future = [datetime.now().date() + timedelta(days=i) for i in range(30)]

    base_demand = {"TV": 8, "Diapers": 45, "Socks": 90, "Headphones": 18, "Coffee Maker": 22}[sel_sku]
    hist_vals = [max(1, int(base_demand + 0.15*base_demand*np.sin(i/3.5) + np.random.normal(0, base_demand*0.12))) for i in range(60)]
    
    lift = 1.25 if promo_lift else 1.0
    future_vals = [max(1, int(base_demand * lift + 0.15*base_demand*np.sin((i+60)/3.5) + np.random.normal(0, base_demand*0.08))) for i in range(30)]
    
    z_score = 1.96 if conf_interval == 0.95 else (1.64 if conf_interval == 0.90 else 2.58)
    upper_band = [int(v + z_score * (base_demand * 0.15)) for v in future_vals]
    lower_band = [max(0, int(v - z_score * (base_demand * 0.15))) for v in future_vals]

    with fc_col2:
        fig_fc = go.Figure()

        fig_fc.add_trace(go.Scatter(
            x=dates_hist, y=hist_vals,
            mode='lines', name='Historical Demand',
            line=dict(color='#86868b', width=2)
        ))

        fig_fc.add_trace(go.Scatter(
            x=dates_future, y=future_vals,
            mode='lines', name='Forecast (P50)',
            line=dict(color=C['accent'], width=3)
        ))

        fig_fc.add_trace(go.Scatter(
            x=dates_future + dates_future[::-1],
            y=upper_band + lower_band[::-1],
            fill='toself',
            fillcolor='rgba(10, 132, 255, 0.15)',
            line=dict(color='rgba(255,255,255,0)'),
            name=f'{int(conf_interval*100)}% Confidence Band'
        ))

        fig_fc.add_hline(y=stock_threshold, line_dash="dash", line_color=C['red'], annotation_text="Safety Stock Threshold")

        fig_fc.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color=C['text'], family="Inter"),
            margin=dict(l=20, r=20, t=30, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(gridcolor='#2c2c2e'),
            yaxis=dict(gridcolor='#2c2c2e', title="Daily Units")
        )
        st.plotly_chart(fig_fc, use_container_width=True)

    st.markdown("<div style='font-size: 1rem; font-weight: 600; margin-top: 16px;'>Monte Carlo Risk Simulation (1,000 Iterations)</div>", unsafe_allow_html=True)
    sim_runs = 1000
    sim_demand = np.random.normal(loc=np.mean(future_vals), scale=base_demand*0.2, size=sim_runs)
    sim_stockout = np.sum(sim_demand > stock_threshold) / sim_runs * 100

    mc_c1, mc_c2, mc_c3 = st.columns(3)
    mc_c1.metric("Stockout Risk (Next 30d)", f"{sim_stockout:.1f}%", delta="-2.4% vs last week", delta_color="inverse")
    mc_c2.metric("Expected Mean Daily Demand", f"{np.mean(future_vals):.1f} units")
    mc_c3.metric("P90 Peak Daily Stress", f"{np.percentile(sim_demand, 90):.1f} units")

# -----------------------------------------------------------------------------
# TAB 3: STORE CAPACITY & SURGE INTELLIGENCE
# -----------------------------------------------------------------------------
with tabs[2]:
    st.markdown("<div style='font-size: 1.15rem; font-weight: 600;'>Store Fulfillment Capacity & Dynamic Surge Multipliers</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size: 0.85rem; color: #86868b; margin-bottom: 16px;'>Non-linear cost expansion protects store labor and prevents backroom congestion</div>", unsafe_allow_html=True)

    cap_c1, cap_c2 = st.columns([1, 1])

    with cap_c1:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 0.95rem; font-weight: 600; margin-bottom: 12px;'>Store Pick Capacity Utilization</div>", unsafe_allow_html=True)
        
        for n_name, n_info in NODES.items():
            if n_info["type"] == "Store":
                util = n_info["current_utilization"]
                used_units = int(n_info["pick_capacity"] * util)
                max_cap = n_info["pick_capacity"]
                surge = get_surge_multiplier(util)
                color = C['green'] if util < 0.70 else (C['amber'] if util < 0.85 else C['red'])
                
                st.markdown(f"""
                <div style='margin-bottom: 14px;'>
                    <div style='display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 4px;'>
                        <span style='font-weight: 600;'>{n_name}</span>
                        <span class='mono'>{used_units} / {max_cap} units ({int(util*100)}%) — Surge: <b>{surge:.2f}x</b></span>
                    </div>
                    <div style='background: #2c2c2e; border-radius: 6px; height: 8px; width: 100%; overflow: hidden;'>
                        <div style='background: {color}; width: {util*100}%; height: 100%;'></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with cap_c2:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 0.95rem; font-weight: 600; margin-bottom: 8px;'>Dynamic Surge Multiplier Curve</div>", unsafe_allow_html=True)
        
        curve_x = np.linspace(0.0, 1.0, 100)
        curve_y = [get_surge_multiplier(u) for u in curve_x]
        
        fig_curve = go.Figure()
        fig_curve.add_trace(go.Scatter(x=curve_x*100, y=curve_y, mode='lines', line=dict(color=C['accent'], width=3)))
        fig_curve.add_vrect(x0=70, x1=85, fillcolor="rgba(255, 159, 10, 0.15)", line_width=0, annotation_text="Soft Surge (1.0x-1.22x)")
        fig_curve.add_vrect(x0=85, x1=100, fillcolor="rgba(255, 69, 58, 0.15)", line_width=0, annotation_text="Hard Surge (>1.22x)")
        
        fig_curve.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color=C['text'], family="Inter"),
            margin=dict(l=10, r=10, t=20, b=10),
            xaxis=dict(title="Node Utilization %", gridcolor='#2c2c2e'),
            yaxis=dict(title="Cost Multiplier", gridcolor='#2c2c2e'),
            height=260
        )
        st.plotly_chart(fig_curve, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# TAB 4: CARRIER DYNAMIC ROUTING & RELIABILITY
# -----------------------------------------------------------------------------
with tabs[3]:
    st.markdown("<div style='font-size: 1.15rem; font-weight: 600;'>Multi-Carrier Matrix & On-Time Performance (OTP)</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size: 0.85rem; color: #86868b; margin-bottom: 16px;'>Dynamic cost multipliers and geographic SLA constraints across national and regional 3PL partners</div>", unsafe_allow_html=True)

    c_mat1, c_mat2 = st.columns([3, 2])

    with c_mat1:
        carrier_table_data = []
        for cname, cinfo in CARRIERS.items():
            zones_str = ", ".join(cinfo["zones"])
            rel_pct = f"{cinfo['reliability']*100:.1f}%"
            carrier_table_data.append({
                "Carrier Partner": cname,
                "Cost Multiplier": f"{cinfo['cost_multiplier']:.2f}x",
                "Historical OTP": rel_pct,
                "Max SLA": f"{cinfo['max_days']} Days",
                "Coverage Zones": zones_str
            })
            
        df_carriers = pd.DataFrame(carrier_table_data)
        
        def color_reliability(val):
            try:
                num = float(str(val).strip('%'))
                return 'color: #30d158; font-weight: 600;' if num >= 95.0 else 'color: #ff9f0a; font-weight: 600;'
            except Exception:
                return ''
                
        st_carriers = apply_safe_styler_map(df_carriers.style, color_reliability, subset=['Historical OTP'])
        st.dataframe(st_carriers, use_container_width=True, hide_index=True)

    with c_mat2:
        carrier_names = list(CARRIERS.keys())
        c_costs = [CARRIERS[c]["cost_multiplier"] for c in carrier_names]
        c_rels = [CARRIERS[c]["reliability"] * 100 for c in carrier_names]

        fig_car = go.Figure()
        fig_car.add_trace(go.Scatter(
            x=c_costs, y=c_rels,
            mode='markers+text',
            text=carrier_names,
            textposition="top center",
            marker=dict(size=14, color=C['accent'], line=dict(width=2, color='#ffffff'))
        ))

        fig_car.update_layout(
            title="Carrier Tradeoff: Cost vs Reliability",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color=C['text'], family="Inter"),
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis=dict(title="Cost Multiplier", gridcolor='#2c2c2e'),
            yaxis=dict(title="Reliability %", gridcolor='#2c2c2e', range=[88, 101]),
            height=280
        )
        st.plotly_chart(fig_car, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 5: A/B POLICY EXPERIMENTATION
# -----------------------------------------------------------------------------
with tabs[4]:
    st.markdown("<div style='font-size: 1.15rem; font-weight: 600;'>Causal Policy Experimentation Sandbox (A/B Test)</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size: 0.85rem; color: #86868b; margin-bottom: 16px;'>Evaluate MILP routing engine against legacy heuristics across simulated order batches</div>", unsafe_allow_html=True)

    ab_c1, ab_c2 = st.columns([1, 2])
    with ab_c1:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 0.95rem; font-weight: 600; margin-bottom: 10px;'>Simulation Parameters</div>", unsafe_allow_html=True)
        batch_size = st.slider("Simulated Order Batch Size", 100, 2000, 500, 100)
        policy_a = st.selectbox("Policy A (Baseline)", ["Heuristic: Nearest Node First", "Heuristic: Pure Lowest Shipping Cost"])
        policy_b = st.selectbox("Policy B (Treatment)", ["GFOE: Full MILP Multi-Echelon", "GFOE: Balanced Surge Aware"])
        run_sim = st.button("Run Causal Simulation", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    np.random.seed(101)
    cost_a = np.random.normal(21.40, 3.2, batch_size)
    cost_b = np.random.normal(18.10, 2.6, batch_size)

    mean_a = np.mean(cost_a)
    mean_b = np.mean(cost_b)
    diff = ((mean_b - mean_a) / mean_a) * 100

    with ab_c2:
        res_c1, res_c2, res_c3 = st.columns(3)
        res_c1.metric("Baseline Avg Cost", f"${mean_a:.2f}")
        res_c2.metric("Treatment Avg Cost", f"${mean_b:.2f}")
        res_c3.metric("Net Cost Reduction", f"{abs(diff):.1f}%", delta=f"{diff:.1f}% (p < 0.001)", delta_color="inverse")

        fig_dist = go.Figure()
        fig_dist.add_trace(go.Histogram(x=cost_a, name='Baseline Policy A', marker_color='rgba(255, 69, 58, 0.6)', nbinsx=30))
        fig_dist.add_trace(go.Histogram(x=cost_b, name='Treatment Policy B', marker_color='rgba(48, 209, 88, 0.6)', nbinsx=30))
        fig_dist.update_layout(
            barmode='overlay',
            title="Order Fulfillment Cost Distribution (USD)",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color=C['text'], family="Inter"),
            margin=dict(l=10, r=10, t=35, b=10),
            xaxis=dict(title="Cost per Order ($)", gridcolor='#2c2c2e'),
            yaxis=dict(title="Order Count", gridcolor='#2c2c2e'),
            height=260
        )
        st.plotly_chart(fig_dist, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 6: NETWORK PULSE — SIMULATED OPERATIONS (PyDeck 3D)
# -----------------------------------------------------------------------------
with tabs[5]:
    st.markdown("<div style='font-size: 1.15rem; font-weight: 600;'>Network Pulse — Simulated Operations & Real-Time Flow</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size: 0.85rem; color: #86868b; margin-bottom: 16px;'>Simulated live geospatial order dispatching across metro nodes, fulfillment hubs, and regional distribution centers</div>", unsafe_allow_html=True)

    orders_data = [
        {"id": "ORD-9021", "dest_lat": 40.7128, "dest_lon": -74.0060, "source": "Metro Store Alpha", "sla": "Rush (2d)", "status": "In Transit"},
        {"id": "ORD-9022", "dest_lat": 40.6500, "dest_lon": -73.9500, "source": "Metro Store Beta", "sla": "Express (3d)", "status": "Picking"},
        {"id": "ORD-9023", "dest_lat": 40.7800, "dest_lon": -73.8800, "source": "Metro Store Gamma", "sla": "Same Day (1d)", "status": "In Transit"},
        {"id": "ORD-9024", "dest_lat": 40.8200, "dest_lon": -74.1000, "source": "Regional DC East", "sla": "Standard (5d)", "status": "Dispatched"},
        {"id": "ORD-9025", "dest_lat": 40.6000, "dest_lon": -74.1500, "source": "Fulfillment Hub South", "sla": "Express (3d)", "status": "In Transit"}
    ]

    arc_records = []
    for ord_item in orders_data:
        src = NODES[ord_item["source"]]
        arc_records.append({
            "from_name": ord_item["source"],
            "to_name": ord_item["id"],
            "from_lat": src["lat"],
            "from_lon": src["lon"],
            "to_lat": ord_item["dest_lat"],
            "to_lon": ord_item["dest_lon"]
        })

    nodes_df = pd.DataFrame([
        {"name": k, "lat": v["lat"], "lon": v["lon"], "type": v["type"], "cap": v["pick_capacity"]}
        for k, v in NODES.items()
    ])

    if PYDECK_AVAILABLE:
        arc_data = pd.DataFrame(arc_records)

        arc_layer = pdk.Layer(
            "ArcLayer",
            data=arc_data,
            get_source_position=["from_lon", "from_lat"],
            get_target_position=["to_lon", "to_lat"],
            get_source_color=[48, 209, 88, 220],     
            get_target_color=[191, 90, 242, 220],   
            get_width=4,
            get_tilt=25,                            
            pickable=True,
            auto_highlight=True
        )

        node_layer = pdk.Layer(
            "ColumnLayer",                          
            data=nodes_df,
            get_position=["lon", "lat"],
            get_elevation="cap",                    
            elevation_scale=5,
            radius=1200,
            get_fill_color=[10, 132, 255, 220],     
            pickable=True,
            extruded=True                           
        )

        view_state = pdk.ViewState(
            latitude=40.68,
            longitude=-74.05,
            zoom=9.8,
            pitch=50,                               
            bearing=-25                             
        )

        deck = pdk.Deck(
            layers=[node_layer, arc_layer],
            initial_view_state=view_state,
            map_style=pdk.map_styles.CARTO_DARK,     
            tooltip={
                "html": "<b>Node:</b> {from_name}<br/><b>Order:</b> {to_name}",
                "style": {"color": "#ffffff", "backgroundColor": "#1c1c1e"}
            }
        )

        st.pydeck_chart(deck, use_container_width=True)
    else:
        fig_map = go.Figure()
        for arc in arc_records:
            fig_map.add_trace(go.Scattermapbox(
                mode="lines",
                lon=[arc["from_lon"], arc["to_lon"]],
                lat=[arc["from_lat"], arc["to_lat"]],
                line=dict(width=2, color=C['accent']),
                hoverinfo="none"
            ))
        fig_map.add_trace(go.Scattermapbox(
            mode="markers+text",
            lon=nodes_df["lon"],
            lat=nodes_df["lat"],
            text=nodes_df["name"],
            textposition="top center",
            marker=dict(size=12, color=C['green'])
        ))
        fig_map.update_layout(
            mapbox_style="carto-darkmatter",
            mapbox=dict(center=dict(lat=40.68, lon=-74.00), zoom=9),
            margin=dict(l=0, r=0, t=0, b=0),
            height=450,
            showlegend=False
        )
        st.plotly_chart(fig_map, use_container_width=True)

    # Simulated Live Dispatch Table 
    st.markdown("<div style='font-size: 0.95rem; font-weight: 600; margin-top: 16px;'>Active Simulated Dispatches</div>", unsafe_allow_html=True)
    
    dispatch_table_data = []
    for od in orders_data:
        dispatch_table_data.append({
            "Order ID": od['id'],
            "Source": od['source'],
            "Promised SLA": od['sla'],
            "Status": od['status'],
            "Destination Coords": f"{od['dest_lat']:.4f}, {od['dest_lon']:.4f}"
        })
        
    df_dispatch = pd.DataFrame(dispatch_table_data)
    st.dataframe(df_dispatch, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# TAB 7: OKRs & ENTERPRISE P&L SIMULATOR
# -----------------------------------------------------------------------------
with tabs[6]:
    st.markdown("<div style='font-size: 1.15rem; font-weight: 600;'>Executive OKRs & Enterprise P&L Impact Modeling</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size: 0.85rem; color: #86868b; margin-bottom: 20px;'>Direct alignment with executive objectives and multi-million dollar annual margin levers</div>", unsafe_allow_html=True)

    okr1, okr2, okr3, okr4 = st.columns(4)

    with okr1:
        st.markdown("""
        <div class='glass-card'>
            <div class='kpi-title'>O1: Digital Purchasability</div>
            <div class='kpi-value'>91.2%</div>
            <div class='kpi-delta delta-pos'>Target: 94.0% (+4.2% YoY)</div>
            <div style='margin-top: 10px; background: #2c2c2e; height: 6px; border-radius: 3px;'>
                <div style='background: #30d158; width: 72%; height: 100%;'></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with okr2:
        st.markdown("""
        <div class='glass-card'>
            <div class='kpi-title'>O2: Ship Expense Reduction</div>
            <div class='kpi-value'>$18.10</div>
            <div class='kpi-delta delta-pos'>Baseline: $19.80 (-8.6%)</div>
            <div style='margin-top: 10px; background: #2c2c2e; height: 6px; border-radius: 3px;'>
                <div style='background: #0a84ff; width: 86%; height: 100%;'></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with okr3:
        st.markdown("""
        <div class='glass-card'>
            <div class='kpi-title'>O3: Delivery Accuracy (DDA)</div>
            <div class='kpi-value'>96.2%</div>
            <div class='kpi-delta delta-pos'>Target: 97.5% (+2.0% YoY)</div>
            <div style='margin-top: 10px; background: #2c2c2e; height: 6px; border-radius: 3px;'>
                <div style='background: #bf5af2; width: 61%; height: 100%;'></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with okr4:
        st.markdown("""
        <div class='glass-card'>
            <div class='kpi-title'>O4: Guest Experience NPS</div>
            <div class='kpi-value'>71</div>
            <div class='kpi-delta delta-pos'>Target: 74 (+3 pts)</div>
            <div style='margin-top: 10px; background: #2c2c2e; height: 6px; border-radius: 3px;'>
                <div style='background: #ff9f0a; width: 50%; height: 100%;'></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='font-size: 1.05rem; font-weight: 600; margin-top: 24px;'>Enterprise P&L Value Creation Simulator</div>", unsafe_allow_html=True)
    
    pl_c1, pl_c2, pl_c3 = st.columns(3)
    with pl_c1:
        annual_orders_m = st.number_input("Annual Digital Order Volume (Millions)", value=180.0, step=10.0)
    with pl_c2:
        baseline_cost_order = st.number_input("Baseline Cost per Order ($)", value=19.80, step=0.50)
    with pl_c3:
        opt_reduction_pct = st.slider("Optimization Cost Reduction %", 2.0, 20.0, 11.0, 0.5)

    annual_gross_spend = annual_orders_m * 1e6 * baseline_cost_order
    annual_savings = annual_gross_spend * (opt_reduction_pct / 100.0)
    capital_investment = 8.5e6
    payback_months = (capital_investment / annual_savings) * 12

    val_c1, val_c2, val_c3 = st.columns(3)
    val_c1.metric("Annual Run-Rate Cost Savings", f"${annual_savings/1e6:.1f}M / yr", delta=f"{opt_reduction_pct}% Margin Improvement")
    val_c2.metric("Total Enterprise Fulfillment Spend", f"${(annual_gross_spend - annual_savings)/1e6:.1f}M")
    val_c3.metric("Capital Payback Velocity", f"{payback_months:.1f} Months", delta="High ROI CapEx")

# -----------------------------------------------------------------------------
# TAB 8: MICROSERVICE ARCHITECTURE
# -----------------------------------------------------------------------------
with tabs[7]:
    st.markdown("<div style='font-size: 1.15rem; font-weight: 600;'>Enterprise Microservice Architecture & Data Flow</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size: 0.85rem; color: #86868b; margin-bottom: 16px;'>Decoupled high-throughput routing engine designed for sub-50ms execution at 50,000 requests/sec peak checkout scale</div>", unsafe_allow_html=True)

    arch_dot = """
    digraph G {
        rankdir=LR;
        bgcolor="transparent";
        node [shape=box, style="filled,rounded", fontname="Inter", fontsize=10, fontcolor="#f5f5f7", margin="0.2,0.1"];
        edge [fontname="Inter", fontsize=8, fontcolor="#86868b", color="#3a3a3c", arrowsize=0.7];

        subgraph cluster_0 {
            label = "Presentation & Channel Layer";
            color = "#0a84ff";
            style = "dashed";
            fontcolor = "#0a84ff";
            fontname = "Inter";
            Web [label="Web / Mobile App", fillcolor="#1c1c1e"];
            POS [label="Store POS", fillcolor="#1c1c1e"];
            OMS [label="Order Management (OMS)", fillcolor="#1c1c1e"];
        }

        subgraph cluster_1 {
            label = "Decision API & Routing Core";
            color = "#30d158";
            style = "dashed";
            fontcolor = "#30d158";
            fontname = "Inter";
            FastAPI [label="FastAPI Gateway\n(Async Orchestrator)", fillcolor="#1c1c1e", color="#30d158"];
            MILP [label="MILP Optimization Core\n(Branch-and-Cut)", fillcolor="#1c1c1e", color="#30d158"];
            RuleEngine [label="Business Policy Filter\n(SLA / Dangerous Goods)", fillcolor="#1c1c1e"];
        }

        subgraph cluster_2 {
            label = "Data Platform & Streaming Fabric";
            color = "#bf5af2";
            style = "dashed";
            fontcolor = "#bf5af2";
            fontname = "Inter";
            Kafka [label="Kafka Event Stream\n(Order Dispatches)", fillcolor="#1c1c1e"];
            Redis [label="Redis In-Memory Cache\n(Node Capacity & Rates)", fillcolor="#1c1c1e"];
            GraphDB [label="Network Topology DB\n(Transit Matrix)", fillcolor="#1c1c1e"];
        }

        subgraph cluster_3 {
            label = "Feedback & Continuous Learning";
            color = "#ff9f0a";
            style = "dashed";
            fontcolor = "#ff9f0a";
            fontname = "Inter";
            MLForecaster [label="Demand Forecaster (ML)\n(Prophet / LightGBM)", fillcolor="#1c1c1e"];
            Telemetry [label="Post-Fulfillment Telemetry\n(Carrier OTP Tracking)", fillcolor="#1c1c1e"];
        }

        Web -> OMS [label="Checkout"];
        POS -> OMS;
        OMS -> FastAPI [label="Route Request"];
        FastAPI -> Redis [label="Fetch Real-Time Cap"];
        FastAPI -> RuleEngine;
        RuleEngine -> MILP [label="Pruned Problem"];
        MILP -> FastAPI [label="Optimal Allocation"];
        FastAPI -> OMS [label="Dispatch Instructions"];
        FastAPI -> Kafka [label="Order Allocated"];
        Kafka -> Telemetry;
        Telemetry -> MLForecaster [label="Training Actuals"];
        MLForecaster -> Redis [label="Update Dynamic Multipliers"];
        GraphDB -> MILP [label="Transit Matrix"];
    }
    """
    st.graphviz_chart(arch_dot)

    st.markdown("<div style='font-size: 1rem; font-weight: 600; margin: 20px 0 10px 0;'>Production Readiness & Scalability Safeguards</div>", unsafe_allow_html=True)
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        st.markdown("""
        <div class='glass-card'>
            <div style='font-weight: 600; font-size: 0.88rem; margin-bottom: 6px; color: #0a84ff;'>1. Sub-50ms SLA Guarantee</div>
            <div style='font-size: 0.78rem; color: #86868b;'>Pre-solve candidate node pruning limits MILP branch-and-cut variable space to <100 nodes per SKU, guaranteeing fast execution within guest checkout timeouts.</div>
        </div>
        """, unsafe_allow_html=True)
    with sc2:
        st.markdown("""
        <div class='glass-card'>
            <div style='font-weight: 600; font-size: 0.88rem; margin-bottom: 6px; color: #30d158;'>2. Graceful Degraded Mode</div>
            <div style='font-size: 0.78rem; color: #86868b;'>If the mathematical solver exceeds 75ms or fails, execution falls back instantly to cached greedy heuristic routing to prevent guest purchase friction.</div>
        </div>
        """, unsafe_allow_html=True)
    with sc3:
        st.markdown("""
        <div class='glass-card'>
            <div style='font-weight: 600; font-size: 0.88rem; margin-bottom: 6px; color: #bf5af2;'>3. Redis Distributed Locks</div>
            <div style='font-size: 0.78rem; color: #86868b;'>Atomic decrements on store node pick capacity prevent race conditions and over-allocation during peak flash sales and Black Friday surges.</div>
        </div>
        """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# EXECUTIVE FOOTER & DISCLAIMER
# -----------------------------------------------------------------------------
st.markdown("<hr style='border-color: #2c2c2e; margin: 30px 0 16px 0;'>", unsafe_allow_html=True)
st.markdown("""
<div style='text-align: center; font-size: 0.75rem; color: #86868b; margin-bottom: 20px;'>
    Guest Fulfillment Optimization Engine (GFOE) v4.4 • Mixed-Integer Linear Programming • Multi-Echelon Available-to-Promise Intelligence<br>
    Simulated fulfillment network for executive product demonstration. All nodes, inventory, costs, carriers, and forecasts are illustrative.
</div>
""", unsafe_allow_html=True)