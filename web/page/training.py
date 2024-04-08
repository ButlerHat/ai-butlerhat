import os
import logging
import json
import streamlit as st
from streamlit.logger import get_logger
import run_robotframework


class StreamlitLogHandler(logging.Handler):
    def __init__(self, widget_update_func):
        super().__init__()
        self.widget_update_func = widget_update_func

    def emit(self, record):
        msg = self.format(record)
        self.widget_update_func(msg)


# Function to load the JSON configuration
def load_config(path):
    with open(path, 'r') as file:
        return json.load(file)

# Function to save the modified JSON configuration
def save_config(path, config):
    with open(path, 'w') as file:
        json.dump(config, file, indent=4)


logger = get_logger(run_robotframework.__name__)
handler = StreamlitLogHandler(st.code)
logger.addHandler(handler)


def training():

    # Get the path to the configuration file
    config_path = None
    if 'trained' in st.session_state:
        config_path = out_config_path = os.path.join(st.session_state.trained, 'training.json')
        if not os.path.exists(config_path):
            config_path = st.secrets["paths"]["default_training_json"]
    else:
        raise ValueError('No trained path found')

    # Load the configuration file
    config = load_config(config_path)

    # Extract in other dictionary values that cannot be modified
    config_readonly = {
        "dataset_name": st.session_state.pretraining_dataset,
        "max_seq_length": config["max_seq_length"],
        "model_name_or_path": st.secrets.paths.base_model,
        "model_type": config["model_type"],
        "output_dir": st.session_state.trained,
    }

    # Override the configuration with the read-only values
    config.update(config_readonly)

    # Create a Streamlit form to display and edit the configuration values
    with st.form("config_form"):
        st.write("### Configuration Settings")
        
        # Dynamically create inputs for each key in the JSON file. If key in read only, disable the input
        for key in config.keys():
            disabled: bool = key in config_readonly
            if isinstance(config[key], bool):
                config[key] = st.checkbox(f"{key}", value=config[key], disabled=disabled)
            elif isinstance(config[key], int):
                config[key] = st.number_input(f"{key}", value=config[key], format="%d", disabled=disabled)
            elif isinstance(config[key], float):
                config[key] = st.number_input(f"{key}", value=config[key], format="%f", disabled=disabled)
            else:
                config[key] = st.text_input(f"{key}", value=str(config[key]), disabled=disabled)
        
        # Submit button for the form
        submitted = st.form_submit_button("Save Configuration")
        
        # Save the configuration if the submit button is pressed
        if submitted:
            save_config(out_config_path, config)
            st.success("Configuration saved!")

    # Run your task
    st.markdown('# Train the model')

    # run_robotframework.main()
