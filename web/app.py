import os
import streamlit as st
from page.upload import upload_page
from page.sidebar import sidebar_header, sidebar_edit, sidebar_convert
from page.edit_instructions import edit
from page.to_rpa_dataset import to_rpa_dataset

st.set_page_config(
    page_title="ButlerHat Data",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.extremelycoolapp.com/help',
        'Report a bug': "https://www.extremelycoolapp.com/bug",
        'About': "# This is a header. This is an *extremely* cool app!"
    }
)

# Set color of sidebar #3f4a65
page_task, task_file = sidebar_header()

# Check if the user selected a task
if page_task == 'Upload':
    upload_page()

elif page_task == 'Edit':
    if not task_file:
        st.warning('No task selected')
    if task_file:
        edit(task_file)
        sidebar_edit()

elif page_task == "Convert":
    dir_path = os.path.join(st.secrets.paths.edited, st.session_state.project) if hasattr(st.session_state, 'project') else st.secrets.paths.edited
    # Check if any file is edited
    if len(os.listdir(dir_path)) == 0:
        st.warning('No files edited yet')
    else:
        to_rpa_dataset()
        sidebar_convert()

