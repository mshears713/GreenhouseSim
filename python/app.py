"""
Smart Mini Greenhouse Control System - Streamlit Application

Main entry point for the interactive web dashboard.

Run with:
    streamlit run python/app.py

Educational Note:
This application demonstrates real-time data visualization, interactive
control, and integration of simulation with physical hardware.
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from python.ui.dashboard import GreenhouseDashboard

# Configure Streamlit page
st.set_page_config(
    page_title="Greenhouse Control System",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #2e7d32;
        text-align: center;
        padding: 1rem 0;
        border-bottom: 3px solid #4caf50;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f5f5f5;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #4caf50;
    }
    .status-good {
        color: #2e7d32;
        font-weight: bold;
    }
    .status-warning {
        color: #f57c00;
        font-weight: bold;
    }
    .status-error {
        color: #c62828;
        font-weight: bold;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Initialize and run dashboard
def main():
    """Main application entry point"""

    # Display header
    st.markdown('<div class="main-header">🌱 Smart Mini Greenhouse Control System</div>',
                unsafe_allow_html=True)

    # Initialize dashboard (uses session state for persistence)
    if 'dashboard' not in st.session_state:
        st.session_state.dashboard = GreenhouseDashboard()

    # Run dashboard
    st.session_state.dashboard.render()


if __name__ == "__main__":
    main()
