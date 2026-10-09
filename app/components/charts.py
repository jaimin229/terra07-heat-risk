"""UI and Chart Components for HeatLens Streamlit App."""

from typing import Dict, Any, List
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px


def render_waterfall_chart(cell_contributions: List[Dict[str, Any]], cell_score: float) -> go.Figure:
    """Renders Plotly waterfall chart showing indicator contributions relative to study area median."""
    labels = [c["label"] for c in cell_contributions]
    deltas = [c["excess_vs_median"] for c in cell_contributions]

    # Color: red for excess risk, teal/green for protective factors
    colors = ["#e11d48" if d > 0 else "#059669" for d in deltas]

    fig = go.Figure(go.Bar(
        x=deltas,
        y=labels,
        orientation="h",
        marker=dict(color=colors),
        text=[f"{'+' if d > 0 else ''}{d:.1f} pts" for d in deltas],
        textposition="outside",
    ))

    fig.update_layout(
        title="<b>Why This Score? Indicator Excess vs Area Median</b>",
        xaxis_title="Points Deviation from Median (Positive = Adds Risk)",
        yaxis=dict(autorange="reversed"),
        margin=dict(l=10, r=20, t=40, b=30),
        height=380,
        template="plotly_white",
    )
    return fig


def render_score_gauge(score: float, tier: str) -> go.Figure:
    """Renders an interactive semicircular gauge for risk score."""
    tier_colors = {
        "Low": "#10b981",
        "Moderate": "#f59e0b",
        "High": "#f97316",
        "Extreme": "#dc2626",
    }
    color = tier_colors.get(tier, "#f97316")

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"<b>Heat Risk Index</b><br><span style='color:{color};font-size:16px;'>{tier.upper()} RISK</span>", 'font': {'size': 20}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#374151"},
            'bar': {'color': color, 'thickness': 0.3},
            'steps': [
                {'range': [0, 25], 'color': '#d1fae5'},
                {'range': [25, 50], 'color': '#fef3c7'},
                {'range': [50, 75], 'color': '#ffedd5'},
                {'range': [75, 100], 'color': '#fee2e2'},
            ],
            'threshold': {
                'line': {'color': "#b91c1c", 'width': 3},
                'thickness': 0.75,
                'value': 75.0,
            }
        }
    ))
    fig.update_layout(height=260, margin=dict(l=20, r=20, t=40, b=20), template="plotly_white")
    return fig


def render_cumulative_benefit_curve(actions_df: pd.DataFrame, current_budget: float) -> go.Figure:
    """Renders cumulative benefit curve: Risk Points Averted vs Cumulative Cost in INR."""
    if actions_df.empty:
        return go.Figure()

    df = actions_df.sort_values("benefit_cost", ascending=False).copy()
    costs_cr = df["cumulative_cost_inr"] / 10_000_000.0  # ₹ Crores
    impacts = df["cumulative_impact"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=costs_cr,
        y=impacts,
        mode="lines+markers",
        line=dict(color="#2563eb", width=3),
        marker=dict(size=6, color="#1e40af"),
        name="Cumulative Impact",
        hovertemplate="Cumulative Cost: ₹%{x:.2f} Cr<br>Risk Pts Averted: %{y:.1f}<extra></extra>",
    ))

    # Mark current budget threshold
    budget_cr = current_budget / 10_000_000.0
    fig.add_vline(
        x=budget_cr,
        line_dash="dash",
        line_color="#dc2626",
        annotation_text=f"Budget: ₹{budget_cr:.2f} Cr",
        annotation_position="top left",
    )

    fig.update_layout(
        title="<b>Diminishing Returns: Risk Points Averted vs Budget</b>",
        xaxis_title="Investment (₹ Crores)",
        yaxis_title="Total Person-Risk Points Averted",
        height=360,
        margin=dict(l=10, r=20, t=40, b=30),
        template="plotly_white",
    )
    return fig


def render_rank_ci_chart(top_cells_df: pd.DataFrame) -> go.Figure:
    """Renders 90% rank interval chart for top priority cells under 1,000 Dirichlet draws."""
    if top_cells_df.empty:
        return go.Figure()

    df = top_cells_df.head(25).sort_values("median_rank", ascending=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["median_rank"],
        y=df["cell_id"].astype(str),
        mode="markers",
        marker=dict(color="#dc2626", size=8),
        error_x=dict(
            type="data",
            symmetric=False,
            array=df["rank_ci_upper"] - df["median_rank"],
            arrayminus=df["median_rank"] - df["rank_ci_lower"],
            color="#94a3b8",
            thickness=1.5,
            width=3,
        ),
        name="Rank (5th - 95th Percentile CI)",
    ))

    fig.update_layout(
        title="<b>Rank Robustness (1,000 Monte-Carlo Perturbations)</b>",
        xaxis_title="Rank (1 = Highest Risk in City)",
        yaxis_title="Cell ID",
        yaxis=dict(autorange="reversed"),
        height=450,
        margin=dict(l=10, r=20, t=40, b=30),
        template="plotly_white",
    )
    return fig
