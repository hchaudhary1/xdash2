import streamlit as st
import numpy as np
import uuid

def log_scale_slider(label, start, end, num_values=100, default_range=None, key=None):
    """
    Creates a log-scaled range slider with direct float values, adjusting for negative start values.

    Parameters:
    - label (str): The label displayed above the slider.
    - start (float): The start of the range.
    - end (float): The end of the range.
    - num_values (int): Number of discrete values in the slider.
    - default_range (tuple): The default selected range (start, end). If None, full range is selected.
    - key (str): Unique identifier for the slider.

    Returns:
    - tuple: Selected range (start, end) in the original scale.
    """
    # Shift values to ensure all are positive for geomspace
    shift = abs(min(start, 0)) + 1
    shifted_start = start + shift
    shifted_end = end + shift

    # Generate an array of log-spaced values with the shifted range
    log_values = np.geomspace(shifted_start, shifted_end, num=num_values)

    # Unshift the log_values to get back to the original intended range
    log_values_unshifted = log_values - shift

    # Generate labels for these values to be used in select_slider
    log_labels = [f"{value:.2f}" for value in log_values_unshifted]

    # Create a dictionary to map the labels back to the original values
    label_to_value = {label: value for label, value in zip(log_labels, log_values_unshifted)}

    # Determine the default range labels
    if default_range is not None:
        default_labels = (f"{default_range[0]:.2f}", f"{default_range[1]:.2f}")
    else:
        default_labels = (log_labels[0], log_labels[-1])

    # Use the labels as options in select_slider for user selection
    selected_labels = st.select_slider(
        label,
        options=log_labels,
        value=default_labels,  # Default to full range or specified default
        key=key  # Pass the key parameter to the select_slider
    )

    # Map the selected labels back to their original values
    selected_values = [label_to_value[label] for label in selected_labels]

    return selected_values[0], selected_values[1]

def create_custom_sentence(unique_id):
    """
    Function adjusted to accept a unique identifier for stable widget keys.
    """
    # Define the lists
    era = [
        "BeforeLive",
        "AfterLive",
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
        selected_interval = st.selectbox("Choose the interval", interval, key=f"interval_{unique_id}")
    with col2:
        selected_era = st.selectbox("Choose the era", era, key=f"era_{unique_id}")
    with col3:
        selected_category = st.selectbox("Choose the category", category, key=f"category_{unique_id}")

    # Construct and return the sentence
    return f"{selected_category}_{selected_era}_{selected_interval}"
    

## PAGE START ##
def simple_screener_page():
    st.write("Choose your filter settings:")

    # Initialize or increment the list of unique identifiers for filters
    if 'filter_ids' not in st.session_state:
        st.session_state.filter_ids = [str(uuid.uuid4())]

    # Lists to store the settings for all filters
    all_custom_sentences = []
    all_selected_ranges = []

    # Display existing filters and collect their selected ranges and sentences
    for unique_id in st.session_state.filter_ids:
        # Display and collect the custom sentence selection
        custom_sentence = create_custom_sentence(unique_id)
        all_custom_sentences.append(custom_sentence)
        
        # Display and collect the log scale slider selection for each filter
        selected_range = log_scale_slider(
            label=f'Select a range of values for {custom_sentence}',
            start=-10.0,
            end=10000000.0,
            num_values=100,
            default_range=None,
            key=f"slider_{unique_id}"  # Ensure each slider has a unique key
        )
        all_selected_ranges.append(selected_range)

    # Button to add a new filter
    if st.button('Add another filter'):
        # Append a new unique identifier for the new filter
        st.session_state.filter_ids.append(str(uuid.uuid4()))
        st.experimental_rerun()  # Force a rerun of the app to immediately reflect the change

    # Display the range settings and filter settings for all filters
    st.write("## Summary of Selected Settings")
    for i, (custom_sentence, selected_range) in enumerate(zip(all_custom_sentences, all_selected_ranges), start=1):
        st.write(f"### Filter #{i}")
        st.write(f"**Custom Sentence:** {custom_sentence}")
        st.write(f"**Selected Range:** {selected_range[0]:.2f} to {selected_range[1]:.2f}")
