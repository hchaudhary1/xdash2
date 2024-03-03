import streamlit as st
import numpy as np

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

## PAGE START ##
## PAGE START ##
def simple_screener_page():
    st.write("This is the Simple-Screener page.")

    # Initialize or increment the number of filters
    if 'num_filters' not in st.session_state:
        st.session_state.num_filters = 1

    # Display existing filters
    for i in range(st.session_state.num_filters):
        selected_range = log_scale_slider(
            label=f'Select a range of values #{i+1}',
            start=-10.0,
            end=10000000.0,
            num_values=100,
            default_range=None,
            key=f"slider_{i}"  # Ensure each slider has a unique key
        )
        st.write(f"You have selected a range from {selected_range[0]:.2f} to {selected_range[1]:.2f}")

    # Button to add a new filter
    if st.button('Add another filter'):
        st.session_state.num_filters += 1
        st.experimental_rerun()  # Force a rerun of the app to immediately reflect the change
