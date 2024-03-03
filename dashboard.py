import pandas as pd
from pygwalker.api.streamlit import StreamlitRenderer, init_streamlit_comm
import streamlit as st
import streamlit.components.v1 as components
from simple_screener import simple_screener_page
from tearsheet import single_tearsheet

st.set_page_config(layout="wide")

# Hide the Streamlit settings menu
hide_settings_menu = """
    <style>
        #MainMenu {visibility: hidden;}
    </style>
    """
st.markdown(hide_settings_menu, unsafe_allow_html=True)


def data_explorer_page():
    st.write("Advanced Explorer page. It may take a second to load...")
    renderer = get_pyg_renderer()
    renderer.render_explore()


@st.cache_data
def get_pyg_renderer() -> "StreamlitRenderer":
    df = pd.read_csv(
        "./output.csv",
        na_values=[
            "#N/A N/A",
            "#N/A",
            "N/A",
            "n/a",
            "nan",
            "NaN",
            "NA",
            "nan",
            "NAN",
            "",
        ],
    )

    return StreamlitRenderer(
        df, spec="pygwalker-config.json", debug=False, tooltips=False
    )


init_streamlit_comm()

PAGES = {
    "Simple Selector": simple_screener_page,
    "Advacned Explorer": data_explorer_page,
    "Single ID QuantStat": single_tearsheet,
}

selection = st.sidebar.radio("Navigation:", list(PAGES.keys()))
page_function = PAGES[selection]
page_function()
