import os
import json
import streamlit as st


def upload_page():
    st.title('Upload your data')
    # Upload file
    uploaded_file = st.file_uploader("Choose a data file", type="json")  # Change file type to json
    # JSON handling
    if uploaded_file is not None:
        is_file = save_file(uploaded_file)
        if is_file:
            st.title(f'Task: {uploaded_file.name}')
            info = st.empty()
            info.info('Loading data... This can take a few seconds')
            # Read json file
            with st.spinner('Loading data...'):
                uploaded_file.seek(0)
                # Show json
                json_data = json.load(uploaded_file)
            st.json(json_data, expanded=False)
            info.empty()
        

def save_file(st_file):
    save = True
    if os.path.exists(f'{st.secrets.paths.upload}{os.sep}{st_file.name}'):
        save = overwrite_file()  # Ensure this function prompts user for overwriting or not

    if not save:
        return False
    
    # Save JSON file
    with st.spinner('Saving data...'):
        with open(f"{st.secrets.paths.upload}{os.sep}{st_file.name}", 'wb') as f:
            f.write(st_file.getbuffer())
    
    # Save json
    st.success('File uploaded successfully')
    with st.sidebar:
        st.info("Navigate to Edit to show the task")
    return True


def overwrite_file():
    holder_warning = st.empty()
    holder_overwrite = st.empty()
    holder_cancel = st.empty()
    holder_error = st.empty()
    holder_warning.warning('File already exists. Overwrite?')
    # Ask the user if he wants to overwrite the file or not with dialog
    overwrite_btn = holder_overwrite.button('Overwrite', key='overwrite')
    cancel_btn = holder_cancel.button('Cancel', key='cancel',)
    if overwrite_btn:
        holder_warning.empty()
        holder_overwrite.empty()
        holder_cancel.empty()
        holder_error.empty()
        return True
    if cancel_btn:
        holder_warning.empty()
        holder_overwrite.empty()
        holder_cancel.empty()
        holder_error.error('Upload canceled. Upload a new file')
        return False
    return False

    
