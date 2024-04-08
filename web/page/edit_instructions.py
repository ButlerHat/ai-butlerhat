import copy
import os
import json
import pickle
import base64
import dataclasses
import logging
import streamlit as st
from typing import Optional
from io import BytesIO
from PIL import Image, ImageDraw
from streamlit_timeline import st_timeline
from ButlerRobot.src.data_types import SaveStatus, Task, PageAction, Step

def edit(task_file: str):

    main_color = st.secrets.theme.primaryColor
    st.markdown(f'# Edit <span style="color:{main_color}">{task_file.split(os.sep)[-1]}</span>', unsafe_allow_html=True)

    # Load task
    task = get_task_session(task_file)
    if not task:
        # This means that the user has changed the task file and he has not confirmed to continue.
        return

    # Timeline
    items, groups = shape_task_to_timeline(task)
    item = show_timeline(items, groups)

    url_params = st.query_params
    if not item:
        if 'item_id' in url_params:
            item = {'id': int(url_params['item_id'][0])}

    if item:
        url_params['item_id'] = [str(item['id'])]
        st.query_params = {**url_params}
        # == Create new task ==
        if item['id'] > st.secrets.configs.new_task_id_offset:
            page_action_id = item['id'] - st.secrets.configs.new_task_id_offset
            try:
                page_action: PageAction = st.session_state.task.find_step(page_action_id)
                create_new_task(page_action)
                return
            except ValueError:
                # This means is an edited Task
                pass

        # == Edit step ==
        step = task.find_step(item['id'])

        # Edit page action
        if isinstance(step, PageAction):
            new_step = edit_page_action(step)
            if new_step:
                task.replace_step_by_id(step.id, new_step)
                st.success('Action edited')
                show_modification_result(task)
                st.session_state.task = task
                st.session_state.edited_task = True
        
        # Show Task
        elif isinstance(step, Task):
            main_color = st.secrets.theme.primaryColor
            st.markdown(f'## Edit <span style="color:{main_color}">{step.name}</span> Task', unsafe_allow_html=True)
            st.session_state.modified_form = st.form(key='Modiffy Task')
            st.session_state.input_ids = set()
            show_context(step)
            # Create button to edit the task
            if st.session_state.modified_form.form_submit_button('Confirm Task', type='primary'):
                st.warning('Due to streamlit limitations, you need to reload with the button below to see the changes.')
                if st.button('Reload', type='primary'):
                    st.experimental_rerun()
                modify_all_tasks()
                    

def get_task_session(task_file: str) -> Task:
    """
    Get task from file. If file change and the task session is not empty, ask the user if he wants to continue.
    """

    # Check if the task needs to be load from file.
    load_from_file = False
    if not hasattr(st.session_state, 'task_file'):
        st.session_state.task_file = task_file
        load_from_file = True

    elif st.session_state.task_file != task_file:
        if hasattr(st.session_state, 'edited_task') and st.session_state.edited_task:
            load_from_file = error_not_saved(task_file)
            if not load_from_file:
                return None  # type: ignore
        else:
            st.session_state.task_file = task_file
            load_from_file = True
    
    if load_from_file:
        st.session_state.task = load_task(task_file)
    else:
        if not hasattr(st.session_state, 'task'):
            st.error("Task not loaded. Please reload the page.")
            exit()

    return st.session_state.task


def error_not_saved(new_task_file: str):
    """
    Unless the confirmation is given, the task session is not updated.
    """
    placeholder_error = st.empty()
    container_error = placeholder_error.container()
    container_error.warning("You have changed the task file. Continue?")

    # This error is shown until the user confirms to continue.
    if container_error.button("Yes I'm ready to rumble"):
        placeholder_error.empty()
        st.session_state.task_file = new_task_file
        return True
    else:
        return False
        

# Load functions
def load_task(task_file: str) -> Task:
    # Load task if json
    if task_file.endswith('.json'):
        with open(task_file, 'r') as f:
            return Task.from_dict(json.load(f))
    else:
        with open(task_file, 'rb') as f:
            return pickle.load(f)


def shape_task_to_timeline(task: Task) -> tuple[list, list]:
    new_task_style = "color: black; background-color: #ffbd63;"
    task_style = "color: white; background-color: #28344d;"
    page_action_style = "color: white; background-color: #3f4a65;"
    created_style = "color: white; background-color: #006600;"
    bad_style = "color: white; background-color: #ff0000;"
    ignore_style = "color: white; background-color: #808080;"
    
    items = []
    groups = [
        {"id": 1, "content": "PageActions", "style": page_action_style},
        {"id": 2, "content": "Create Single-Task", "style": new_task_style}
    ]


    def step_to_item(step: Step, depth_id: int, add_new_task: bool =True) -> list[dict]:
        # Only add step of has all the attributes
        if not step.is_complete():
            logging.warning(f"Step {step.name} is not complete. It will not be shown in the timeline.")
            items = []
            # Recursive step. Create items for subtasks
            if isinstance(step, Task):
                for sub_step in step.steps:
                    items.extend(step_to_item(sub_step, depth_id, add_new_task))
            return items
        
        # Create item
        style = None
        assert step.context is not None, "Steps with no context must be ignored with step.is_complete()"
        if hasattr(step, 'status'):
            if step.status == SaveStatus.only_substeps:
                style = ignore_style
            elif step.status == SaveStatus.no_record:
                style = bad_style
        item_info = {
            "id": step.id,
            "content": step.name,
            "editable": False,
            "start": step.context.start_observation.time,
            "end": step.context.end_observation.time,
            "style": style
        }
        # Create item of page action
        if isinstance(step, PageAction):
            items = [{
                **item_info,
                "group": 1,
                "style": page_action_style if item_info['style'] is None else item_info['style']
            }]
            # Add New Task item if does not exist
            if add_new_task:
                items.append(
                    {
                    "id": step.id + st.secrets.configs.new_task_id_offset,
                    "content": "New Task",
                    "editable": False,
                    "start": step.context.start_observation.time,
                    "end": step.context.end_observation.time,
                    "group": 2,
                    "style": new_task_style if item_info['style'] is None else item_info['style']
                }
            )
            return items
        # Task
        # There is a bug where the page says that the step is not a Task. :(                
        else:  
            add_new_task = True  # By default add 'new task' item when the task has Page Actions and not is a created single task

            if hasattr(step, 'status') and step.status == SaveStatus.confirm_record:
                # Ignore task created by the user.
                items = [{
                    **item_info,
                    "group": 2,
                    "style": created_style if item_info['style'] is None else item_info['style']
                }]
                add_new_task = False  # The task is over 1000 (new_task_id_offset) so it is single task created by the user.
            else:
                # Add task item
                items = [{
                    **item_info,
                    "group": depth_id,
                    "style": task_style if item_info['style'] is None else item_info['style']
                }]
            
                # To calculate groups of timeline
                depth_id += 1
                if step_to_item.max_depth < depth_id:
                    step_to_item.max_depth = depth_id
            
            # Don't show childer if the task has only subtasks status. Parent will show them.
            if step.status == SaveStatus.only_substeps:
                return items

            # Recursive step. Create items for subtasks
            for sub_step in step.steps:  # type: ignore  # Always gonna be a Task
                items.extend(step_to_item(sub_step, depth_id, add_new_task))
            return items
    
    # Start at 3 because the group 1 is PageActions and 2 is Create Single-Task
    step_to_item.max_depth = 3  # Static variable
    if not isinstance(task, PageAction):
        items.extend(step_to_item(task, 3))

    else:
        items = step_to_item(task, 3)  # Depth does not matter because it is a PageAction

    # Iterate over all the items and reverse the group if is greater than 3
    for item in items:
        if item["group"] > 2:
            item["group"] = (step_to_item.max_depth - item["group"]) + 2
    # Add groups
    tasks_groups = [{"id": i, "content": f"Task ({i - (step_to_item.max_depth - 3)})", "style": task_style} for i in range(3, step_to_item.max_depth)]
    groups.extend(tasks_groups)

    return items, groups


def suggest_prompt(step: Step) -> str:
    return ""


# ====== Prints in page ======
 
def show_context(step: Step, depth: str = "0", expanded=False):
    with st.session_state.modified_form:
        if not step.is_complete():
            # Set to no record if is not complete and is not the root
            if step.id != st.session_state.task.id:
                step.status = SaveStatus.no_record
            st.warning("This step does not have a context.")
        else:
            # Create container
            context_c = st.expander(f"PageAction context", expanded) if isinstance(step, PageAction) else st.container()
            context_c.markdown('### Context')
            # Create 2 columns
            col1, col2 = context_c.columns(2)

            col1.write('Start Observation + Action location')
            assert step.context is not None, "Steps with no context must be ignored with step.is_complete()"
            start_image = Image.open(BytesIO(base64.b64decode(step.context.start_observation.screenshot)))
            # Draw in start_image the action bounding box
            draw = ImageDraw.Draw(start_image)
            if isinstance(step, PageAction):
                if not step.action_args.bbox:
                    st.warning("The action does not have a bounding box.")
                else:
                    draw.rectangle(step.action_args.bbox.pillow_print(), outline="red", width=5)
            
            # Draw pointer in start_image
            point_len = 2

            x = step.context.start_observation.pointer_xy[0]
            y = step.context.start_observation.pointer_xy[1]
            draw.ellipse((x-point_len, y-point_len, x+point_len, y+point_len), fill="blue", outline="blue")

            col1.image(start_image, use_column_width=True)

            col2.write('End Observation')
            end_image = Image.open(BytesIO(base64.b64decode(step.context.end_observation.screenshot)))
            # Draw pointer in end_image
            x = step.context.end_observation.pointer_xy[0]
            y = step.context.end_observation.pointer_xy[1]
            draw = ImageDraw.Draw(end_image)
            draw.ellipse((x-point_len, y-point_len, x+point_len, y+point_len), fill="blue", outline="blue")
            
            col2.image(end_image, use_column_width=True)

        if isinstance(step, Task):
            confirm_task_instruction(step)

            st.markdown('---')
            for i, sub_step in enumerate(step.steps):
                main_color = st.secrets.theme.primaryColor
                sub_step_type = "# Page Action" if isinstance(sub_step, PageAction) else " Task"
                step_arg = f"({sub_step.action_args.string})" if isinstance(sub_step, PageAction) else ""
                enumeration = f'{depth}.{i}' if depth != "0" else f'{i}'
                st.markdown(f'##{sub_step_type} {enumeration}: <span style="color:{main_color}">{sub_step.name}{step_arg}</span>', unsafe_allow_html=True)
                show_context(sub_step, enumeration)


def modiffy_page_args(step: PageAction, read_only: bool = False) -> Optional[PageAction]:
    if read_only:
        st.info("This is a read only view of the task. You can modify it in the page action.")
    with st.form('Edit Action'):
        col1, col2, col3 = st.columns(3)
        selector = col1.text_input('Selector', value=step.action_args.selector_dom, disabled=read_only)
        action_type = col2.text_input('String', value=step.action_args.string, disabled=read_only)
        submit = col3.form_submit_button('Submit', disabled=read_only)

        if submit:
            step.action_args.selector_dom = str(selector)
            step.action_args.string = action_type
            return step


def show_modification_result(task: Task):
    st.markdown("### Result")
    dict_task = dataclasses.asdict(task)
    st.json(dict_task, expanded=False)


def show_timeline(items, groups) -> Optional[dict]:
    height = max((len(groups) * 100) + 200, 400) 
    with st.expander('Timeline', expanded=True):
        item = st_timeline(items, groups=groups, options={}, height=f"{height}px")
    return item


def create_new_task(page_action: PageAction):
    main_color = st.secrets.theme.primaryColor
    st.markdown(f'## Create new Task from <span style="color:{main_color}">{page_action.name}({page_action.action_args.string})</span>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1.form('New Task OCR'):
        suggested_prompt = suggest_prompt(page_action)
        prompt1 = st.text_input('Task name', suggested_prompt)
        submit_button1 = st.form_submit_button('Submit')

    with col2.form('New Task Manual'):
        prompt2 = st.text_input('Suggested with ocr', '')
        submit_button2 = st.form_submit_button('Submit')
    
    with st.spinner('Creating new task...'):
        if submit_button1 or submit_button2:
            prompt = prompt1 if prompt1 else prompt2
            new_task = Task(page_action.id + st.secrets.configs.new_task_id_offset, prompt, context=page_action.context, steps=[page_action], status=SaveStatus.confirm_record)

            if modify_session_task(page_action.id, new_task):
                st.markdown('### Updated timeline')
                items, groups = shape_task_to_timeline(st.session_state.task)
                show_timeline(items, groups)

    show_context(page_action, expanded=True)
    modiffy_page_args(page_action, read_only=True)


def confirm_task_instruction(task: Task):        
    st.markdown(f'### Edit Instruction')
    st.text_input('Instruction', value=task.name, key=f'edit_{task.id}')
    col1, _, _ = st.columns(3)  # To make selectbox smaller
    select_idx = {SaveStatus.confirm_record: 0, SaveStatus.to_record: 0, SaveStatus.only_substeps: 1, SaveStatus.no_record: 2}
    col1.selectbox('Good to record?', ["Yes, record all", "Use only sub-steps", "No, not even sub-steps"], index=select_idx[task.status], key=f'record_{task.id}')
    if not hasattr(st.session_state, 'input_ids'):
        st.session_state.input_ids = set()
    st.session_state.input_ids.add(task.id)


def edit_page_action(step: PageAction):
    main_color = st.secrets.theme.primaryColor
    st.markdown(f'## Edit <span style="color:{main_color}">{step.name}</span> PageAction', unsafe_allow_html=True)
    show_context(step)

    st.header('Edit Action')
    return modiffy_page_args(step)


def modify_all_tasks():
    has_modiffied = False
    for task_id in st.session_state.input_ids:
        task = st.session_state.task.find_step(task_id)
        if not task:
            continue
        
        # Skip root task
        if task_id == st.session_state.task.id:
            continue
        
        new_task: Task = copy.deepcopy(task)
        name = st.session_state.get(f'edit_{task_id}') if st.session_state.get(f'edit_{task_id}') else task.name
        new_task.name = name  # type: ignore
        record_response = st.session_state.get(f'record_{task_id}') if st.session_state.get(f'record_{task_id}') else ''
        is_modiffy = False
        if not record_response:
            # Not modify if not shown in the page
            continue
        elif record_response == 'Yes, record all':
            new_task.status = SaveStatus.confirm_record
            is_modiffy = modify_session_task(task.id, new_task)
        elif record_response == 'Use only sub-steps':
            new_task.status = SaveStatus.only_substeps
            parent: Task = st.session_state.task.get_parent(task_id)
            # Get the first parent that is recordable
            while parent.id != st.session_state.task.id and hasattr(parent, 'status') and parent.status != SaveStatus.to_record and parent.status != SaveStatus.confirm_record:
                parent = st.session_state.task.get_parent(parent.id)
            # Insret the steps in the parent
            if parent:
                # Search task in parent and replace it with task.steps
                i = parent.steps.index(task)
                parent.steps = parent.steps[:i] + task.steps + parent.steps[i+1:]
                is_modiffy = True
                st.success(f'Task {parent.name} modified')
        else:
            # Set status to no_record
            new_task.status = SaveStatus.no_record
            new_task.set_status_to_all_children(SaveStatus.no_record)
            is_modiffy = modify_session_task(task.id, new_task)

        if not has_modiffied and is_modiffy:
            has_modiffied = True

    if has_modiffied:
        st.markdown('### Updated timeline')
        items, groups = shape_task_to_timeline(st.session_state.task)
        show_timeline(items, groups)
    
    st.session_state.input_ids = set()
    

def modify_session_task(old_step_id: int, new_task: Task) -> bool:
    """
    Removes old_step from parent task and adds new_task.
    """
    is_modiffied = st.session_state.task.replace_step_by_id(old_step_id, new_task)
    if is_modiffied:
        st.success(f'Task {new_task.name} created')
        st.session_state.edited_task = True

        # Remove item_id from query params
        params = st.query_params
        if 'item_id' in params:
            del params['item_id']
        st.query_params = {**params}
        return True
    else:
        st.error('Task not created')
        return False
    
    
    



