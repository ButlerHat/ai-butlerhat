import os
import streamlit as st
from web.page.upload import upload_page
from web.page.sidebar import sidebar_header, sidebar_edit, sidebar_convert
from web.page.edit_instructions import edit
from web.page.to_rpa_dataset import to_rpa_dataset
from web.page.pretraining import pretraining
from web.page.training import training

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

# Sidebar must be loaded first
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
    # Check if any file is edited
    if len(os.listdir(st.session_state.edited)) == 0:
        st.warning('No files edited yet')
    else:
        to_rpa_dataset()
        sidebar_convert()

elif page_task == "Pretraining":
    pretraining()

elif page_task == "Training":
    training()
