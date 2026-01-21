import streamlit as st

def style_metric_cards() -> None:
    """
    Inject CSS to style st.metric containers as 'Bento Grid' cards.
    
    See: docs/spec/TSD_Layer3_PresentationLayer.md (ADR 5.4 & 7.1)
    """
    st.markdown("""
    <style>
    /* Force Brand Color via CSS Variable to avoid config.toml locking the theme */
    :root {
        --primary-color: #4F46E5;
    }

    div[data-testid="stMetric"], div[data-testid="metric-container"] {
        background-color: var(--secondary-background-color);
        color: var(--text-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 15px 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: transform 0.2s ease-in-out;
        min-height: 140px; /* Ensure uniform height for all cards */
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    
    /* Hover Effect for Interactivity */
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.1);
        border-color: var(--primary-color);
    }
    </style>
    """, unsafe_allow_html=True)
