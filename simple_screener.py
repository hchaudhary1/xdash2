import numpy as np
import pandas as pd
import pyperclip
import streamlit as st
import uuid
from st_aggrid import AgGrid, GridOptionsBuilder
from tearsheet import generate_12mo_plot


def log_scale_slider(label, start, end, key=None):
    """
    Creates a log-scaled range slider with direct float values, adjusting for negative start values.

    Parameters:
    - label (str): The label displayed above the slider.
    - start (float): The start of the range.
    - end (float): The end of the range.
    - key (str): Unique identifier for the slider.

    Returns:
    - tuple: Selected range (start, end) in the original scale.
    """
    # Shift values to ensure all are positive for geomspace
    shift = abs(min(start, 0)) + 1
    shifted_start = start + shift
    shifted_end = end + shift

    # Generate an array of log-spaced values with the shifted range
    log_values = np.geomspace(shifted_start, shifted_end, num=1000)

    # Unshift the log_values to get back to the original intended range
    log_values_unshifted = log_values - shift

    # Generate labels for these values to be used in select_slider
    log_labels = [f"{value:.2f}" for value in log_values_unshifted]

    # Create a dictionary to map the labels back to the original values
    label_to_value = {
        label: value for label, value in zip(log_labels, log_values_unshifted)
    }

    default_labels = (log_labels[0], log_labels[-1])

    # Use the labels as options in select_slider for user selection
    selected_labels = st.select_slider(
        label,
        options=log_labels,
        value=default_labels,  # Default to full range or specified default
        key=key,  # Pass the key parameter to the select_slider
    )

    # Map the selected labels back to their original values
    selected_values = [label_to_value[label] for label in selected_labels]

    return selected_values[0], selected_values[1]


def create_custom_df_column(unique_id):
    """
    Function adjusted to accept a unique identifier for stable widget keys.
    """
    # Define the lists
    era = [
        "AfterLive",
        "BeforeLive",
    ]

    interval = [
        "01mo",
        "03mo",
        "06mo",
        "12mo",
        "13moToMax",
    ]

    category = [
        "GainTotalPct",
        "GainAnnualizedPct",
        "DrawdownMaxPct",
        "Calmar",
        "Sharpe",
        "DayBestPct",
        "DayWorstPct",
        "DayAvgPct",
        "DayStdDevPct",
    ]

    # Create columns for the select boxes
    col1, col2, col3 = st.columns(3)

    # Use the unique_id as part of the key for each widget
    with col1:
        selected_interval = st.selectbox(
            "Time range:", interval, key=f"interval_{unique_id}"
        )
    with col2:
        selected_era = st.selectbox("When:", era, key=f"era_{unique_id}")
    with col3:
        selected_category = st.selectbox(
            "Metric:", category, key=f"category_{unique_id}"
        )

    # Construct and return the df_column
    return f"{selected_category}_{selected_era}_{selected_interval}"


## PAGE STREAMLIT START ##
def simple_screener_page():
    # Load the DataFrame at the very start
    df = pd.read_csv("output.csv")

    st.write("## 1. Choose your filters:")

    # Initialize or increment the list of unique identifiers for filters
    if "filter_ids" not in st.session_state:
        st.session_state.filter_ids = [str(uuid.uuid4())]
    if "sort_id" not in st.session_state:
        st.session_state.sort_id = [str(uuid.uuid4())]

    # Lists to store the settings for all filters
    all_custom_df_columns = []
    all_selected_ranges = []

    # Initialize a variable to hold the filtered DataFrame
    filtered_df = df.copy()

    # Display existing filters and collect their selected ranges and df_columns
    for unique_id in st.session_state.filter_ids:
        # Display and collect the custom df_column selection
        custom_df_column = create_custom_df_column(unique_id)
        all_custom_df_columns.append(custom_df_column)

        # Get the min and max for the selected df_column
        column_min = filtered_df[custom_df_column].min()
        column_max = filtered_df[custom_df_column].max()

        # Display and collect the log scale slider selection for each filter
        selected_range = log_scale_slider(
            label=f"Select a range of values for {custom_df_column}",
            start=column_min,
            end=column_max,
            key=f"slider_{unique_id}",  # Ensure each slider has a unique key
        )
        all_selected_ranges.append(selected_range)

        # Apply the filter to the filtered_df
        filtered_df = filtered_df[
            (filtered_df[custom_df_column] >= selected_range[0])
            & (filtered_df[custom_df_column] <= selected_range[1])
        ]

    # Button to add a new filter
    if st.button("Add another filter"):
        # Append a new unique identifier for the new filter
        st.session_state.filter_ids.append(str(uuid.uuid4()))
        st.rerun()  # Force a rerun of the app to immediately reflect the change

    # Display the range settings and filter settings for all filters
    # st.write("## Summary of Selected Settings")
    # for i, (custom_df_column, selected_range) in enumerate(zip(all_custom_df_columns, all_selected_ranges), start=1):
    #     st.write(f"### Filter #{i}")
    #     st.write(f"**Custom df_column:** {custom_df_column}")
    #     st.write(f"**Selected Range:** {selected_range[0]:.2f} to {selected_range[1]:.2f}")

    st.write("## 2. Sort by:")
    custom_df_column = create_custom_df_column(st.session_state.sort_id)
    st.write("(or click on column name to manually sort, below)")

    # Display the filtered DataFrame or a summary
    st.write("## 3. Filtered List:")

    # Reset the index of the DataFrame and then display it without the index column
    sorted_df = filtered_df.sort_values(by=custom_df_column, ascending=False)

    # Configure the grid options
    gb = GridOptionsBuilder.from_dataframe(sorted_df.reset_index(drop=True))
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
    gb.configure_selection("single")
    gridOptions = gb.build()

    # Display the table with AgGrid using the configured options
    response = AgGrid(sorted_df.reset_index(drop=True), gridOptions=gridOptions)
    selected_row = response["selected_rows"]
    print(selected_row)
    if selected_row:
        selected_symphony_id = selected_row[0]["id"]
        copy_button = st.button("Copy ID to Clipboard")
        if copy_button:
            pyperclip.copy(selected_symphony_id)

        copy_url_btn = st.button("Copy URL to Clipboard")
        if copy_url_btn:
            pyperclip.copy(
                "https://app.composer.trade/symphony/"
                + selected_symphony_id
                + "/factsheet"
            )
        st.write(f"## 4. Return for prior 12 months ({selected_symphony_id}):")
        generate_12mo_plot(selected_symphony_id)
