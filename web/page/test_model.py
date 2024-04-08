import os
import multiprocessing
import json
import time
import streamlit as st
import streamlit.components.v1 as components
import uvicorn
import requests
import sys
sys.path.append("/workspaces/ai-butlerhat/data-butlerhat/robotframework-butlerhat/interpreter-butlerhat/src")
from interpreter import InterpreterManager
import api.app as api
from ButlerRobot.src.data_types import Task
from web.page.edit_instructions import shape_task_to_timeline, show_timeline, show_context


def run_ai_server():
    uvicorn.run(api.app, host=api.settings["host"], port=api.settings["port"])  # type: ignore


def test_model():
    """
    Convert rpa task file json to a hugging face dataset (json)
    """
    st.title('Test the model in the interpreter')
    # Check if is dataset in rpa_dataset folder
    if not os.listdir(st.session_state.trained):
        st.warning('No model trained')
        st.stop()
    
    if 'testing_url' not in st.session_state:
        with st.form("Input the url of the page to test"):
            st.write("Input the url of the page to test")
            url = st.text_input("Url")
            submit = st.form_submit_button("Submit")
            if submit:
                st.session_state.testing_url = url
                st.rerun()
            st.stop()

    if 'server_thread' not in st.session_state:
        # Load the model api
        with st.status('Loading the Model and API...'):
            # Change model path
            st.write("Loading API.")
            api.settings['name_or_path'] = st.session_state.trained
            
            # Run the app with uvicorn (ASGI server)
            server_thread = multiprocessing.Process(target=run_ai_server)
            # Start the server process
            server_thread.start()
            st.session_state.server_thread = server_thread

            # Wait for the server to start. Check the /health endpoint
            st.write("Waiting for the server to start")
            for _ in range(30):
                try:
                    response = requests.get(f"http://localhost:{api.settings['port']}/health", timeout=10)
                    if response.status_code == 200:
                        break
                except requests.exceptions.ConnectionError:
                    pass
                time.sleep(1)
            else:
                st.error("Server did not start")
                # Shutdown thread
                server_thread.join()
                del st.session_state['server_thread']
                st.stop()

    if 'interpreter_id' not in st.session_state:
        # Get the interpreter
        with st.status('Starting the interpreter...'):
            st.write("Starting the interpreter")
            interpreter_manager = InterpreterManager()
            st.session_state.interpreter_manager = interpreter_manager
            interpreter_id = interpreter_manager.start_interpreter()
            st.session_state.interpreter_id = interpreter_id

            st.write("Loading the libraries")
            command_settings = f"*** Settings ***\nLibrary   ButlerRobot.AIBrowserLibrary  fix_bbox=${{False}}  ai_url=http://localhost:{api.settings['port']}/predict_rf  console=${{False}}  output_path={st.session_state.tested}  WITH NAME  Browser"
            start_test = "Start Task  Test interpreter"
            result = interpreter_manager.evaluate(interpreter_id, command_settings)
            st.write(f"Import Library: {result}")
            result = interpreter_manager.evaluate(interpreter_id, start_test)
            st.write(f"Start Test: {result}")
            st.write("Opening the browser")
            open_browser = f"New Stealth Persistent Context  userDataDir=/tmp/interpreter  headless=${{False}}  url={st.session_state.testing_url}  browser=chromium"
            result = interpreter_manager.evaluate(interpreter_id, open_browser)
            st.write(f"Open Browser: {result}")	
    else:
        interpreter_manager = st.session_state.interpreter_manager
        interpreter_id = st.session_state.interpreter_id
        
    
    # Create columns
    col1, col2 = st.columns([1,2])

    # Chat
    messages = col1.container(height=600)
    if prompt := col1.chat_input("Input prompt"):
        st.session_state.prompted = True
        messages.chat_message("user").write(prompt)
        response = interpreter_manager.evaluate(interpreter_id, "AI." + prompt)
        messages.chat_message("assistant").write(response)

    # VNC
    with col2:
        components.iframe(
            'http://localhost:6081?password=vscode&autoconnect=true&resize=scale&reconnect=true', 
            height=600
        )

    # Show actions
    # Load json of actions
    if 'prompted' not in st.session_state:
        st.stop()

    json_path = os.path.join(st.session_state.tested, "Start Task.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            task = Task.from_dict(json.load(f))
        items, groups = shape_task_to_timeline(task)
        item = show_timeline(items, groups)
        if item:
            step = task.find_step(item['id'])
            if isinstance(step, Task):
                main_color = st.secrets.theme.primaryColor
                st.markdown(f'## Edit <span style="color:{main_color}">{step.name}</span> Task', unsafe_allow_html=True)
                st.session_state.modified_form = st.form(key='Modiffy Task')
                st.session_state.input_ids = set()
                show_context(step)
                if st.session_state.modified_form.form_submit_button('Placeholder'):
                    st.info("Nothing to do here")
    else:
        st.write("No actions")


    
    





    
