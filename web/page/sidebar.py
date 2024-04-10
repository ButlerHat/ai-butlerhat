import streamlit as st
import os
import json
import pickle
from streamlit_option_menu import option_menu


def show_projects():
    """
    Show directies in upload folder
    """
    project = None
    with st.expander('Project', expanded=False):
        if not hasattr(st.session_state, 'project'):
            st.session_state.project = 'default'
        
        st.session_state.project_basedir = os.path.join(st.secrets.paths.base_dir, st.session_state.project)
        if not os.path.exists(st.session_state.project_basedir):
            os.makedirs(st.session_state.project_basedir)
            
        # Show projects dirs
        dirs = next(os.walk(st.secrets.paths.base_dir))[1]
        project = st.session_state.project
        index = dirs.index(project)
        project = st.selectbox('Projects:', tuple(dirs), index=index)
        if project != st.session_state.project:
            st.session_state.task = None
            st.session_state.project = project
            del st.session_state['sidebar_task_file']
            st.rerun()
        st.session_state.project = project

        # Create new project
        with st.form('new_project_form'):
            new_project = st.text_input('New project name')
            submit = st.form_submit_button('Create project')
            if submit:
                if not new_project:
                    st.error('Project name is empty')
                if new_project in dirs:
                    st.error('Project already exists')
                st.session_state.project = new_project
            
                st.rerun()

        assert st.session_state.project, 'Project name is empty'
        # Configure directories
        st.session_state.upload = os.sep.join([st.session_state.project_basedir, st.secrets.paths.upload])
        st.session_state.edited = os.sep.join([st.session_state.project_basedir, st.secrets.paths.edited])
        st.session_state.rpa_dataset = os.sep.join([st.session_state.project_basedir, st.secrets.paths.rpa_dataset])
        st.session_state.pretraining_dataset = os.sep.join([st.session_state.project_basedir, st.secrets.paths.pretraining_dataset])
        st.session_state.trained = os.sep.join([st.session_state.project_basedir, st.secrets.paths.trained])
        st.session_state.tested = os.sep.join([st.session_state.project_basedir, st.secrets.paths.tested])

        # Create folders if not exist
        os.makedirs(st.session_state.upload, exist_ok=True)
        os.makedirs(st.session_state.edited, exist_ok=True)
        os.makedirs(st.session_state.rpa_dataset, exist_ok=True)
        os.makedirs(st.session_state.pretraining_dataset, exist_ok=True)
        os.makedirs(st.session_state.trained, exist_ok=True)
        os.makedirs(st.session_state.tested, exist_ok=True)

        return project


def show_tasks():
    # Check if there is files in the upload_data folder
    task_file = st.session_state.sidebar_task_file if hasattr(st.session_state, 'sidebar_task_file') else None
    file_edited, file_uploaded = "-", "-"

    with st.expander('Task selector', expanded=True):

        with st.form('task_form'):
            # List only files in the upload_data folder
            list_upload = os.listdir(st.session_state.upload)
            list_upload = [f for f in list_upload if os.path.isfile(os.path.join(st.session_state.upload, f))]

            if len(list_upload) == 0 and len(os.listdir(st.session_state.edited)) == 0:
                st.warning('No files uploaded yet')
            else:
                if len(list_upload) != 0:
                    st.write('Files uploaded')
                    # List all files in the upload_data folder
                    files = list_upload
                    files.append('-')
                    file_uploaded = st.selectbox('Tasks uploaded:', tuple(files), index=len(files)-1)
                if len(os.listdir(st.session_state.edited)) != 0:
                    st.write('Files edited')
                    # List all files in the edited_data folder
                    files = os.listdir(st.session_state.edited)
                    files.append('-')
                    file_edited = st.selectbox('Tasks edited:', tuple(files), index=len(files)-1)

            submit = st.form_submit_button('Submit')

            if submit:
                if file_edited != "-" and file_uploaded != "-":
                    st.error('Only slelect one file')
                else:
                    url_params = st.query_params
                    # Delete 'item_id' if exists in url_params
                    if 'item_id' in url_params:
                        del url_params['item_id']
                    st.query_params = {**url_params}
                    if file_uploaded != '-':
                        task_file = st.session_state.upload + os.sep + file_uploaded
                    elif file_edited != '-':
                        task_file = st.session_state.edited + os.sep + file_edited
                    else:
                        st.info('No file selected')
        
        st.session_state.sidebar_task_file = task_file
        return task_file

def show_save():
    # Save task
    save_empty = st.empty()  # Bug: Clears the task selectbox
    save_cont = save_empty.container()
    save_cont.title('Save')

    if hasattr(st.session_state, 'edited_task') and st.session_state.edited_task:
        task = st.session_state.task
        # Modify save name
        save_name = save_cont.text_input('Save name', f"{task.name}-edited.json")
        
        if save_cont.button('Save'):
            save_path = f'{st.session_state.edited}{os.sep}{save_name}'
            task.save(save_path)
            save_cont.success('Task saved')
            st.session_state.edited_task = False
    else:
        save_cont.info('No changes made yet')


def show_download(folder_path: str):
    
    # Check if edited directory is empty
    down_empty = st.empty()
    down_cont = down_empty.container()
    down_cont.title('Download')

    if len(os.listdir(folder_path)) == 0:
        down_cont.info('No files edited yet')
    else:
        # List all files in the edited_data folder
        files = os.listdir(folder_path)
        task_file = down_cont.selectbox('Modified task:', tuple(files))

        # Download json
        if task_file:
            if task_file.endswith('.json'):
                with open(f'{folder_path}{os.sep}{task_file}', 'r') as f:
                    json_data = json.load(f)
                down_cont.download_button(
                    label='Download json',
                    data=json.dumps(json_data),
                    file_name=f'{task_file}',
                    mime='application/json'
                )
            elif task_file.endswith('.jsonl'):
                json_data = ""
                with open(f'{folder_path}{os.sep}{task_file}', 'r') as f:
                    for line in f:
                        json_data += line
                down_cont.download_button(
                    label='Download jsonl',
                    data=json_data,
                    file_name=f'{task_file}',
                    mime='text/plain'
                )
            else:
                # Download pickle
                with open(f'{folder_path}{os.sep}{task_file}', 'rb') as f:
                    pickle_data = pickle.load(f)
                down_cont.download_button(
                    label='Download pickle',
                    data=pickle.dumps(pickle_data),
                    file_name=f'{task_file}',
                    mime='application/octet-stream'
                )

    
def sidebar_header():
    with st.sidebar:
        st.image(st.secrets.paths.logo)
        # Create a dropdown menu
        with st.expander('Navigation', expanded=True):
            options = {
                "Upload": "cloud-arrow-up", 
                "Edit": "pencil", 
                "Convert": "arrow-right",
                "Pretraining": "boxes",
                "Training": "gpu-card",
                "Test": "chat-dots"
            }
            default_index = 1
            
            page_task = option_menu(
                menu_title=None,
                options=list(options.keys()),
                icons=list(options.values()),
                default_index=default_index,
                styles={
                    "nav-link-selected": {"color": "black"}
                }
            )


        main_color = st.secrets.theme.primaryColor
        project = st.session_state.project if hasattr(st.session_state, 'project') else 'default'
        st.markdown(f'# Project <span style="color:{main_color}">{project}</span>', unsafe_allow_html=True)
        show_projects()

        st.title('Task selection')
        task_file = show_tasks()

        return page_task, task_file


def sidebar_edit():
    with st.sidebar:
        show_save()
        show_download(st.session_state.edited)

def sidebar_convert():
    with st.sidebar:
        show_download(st.session_state.rpa_dataset)
        