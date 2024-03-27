import os
import json
import pandas as pd
import logging
from ButlerRobot.src.data_types import PageAction, SaveStatus, Step, Task
from ButlerRobot.src.data_to_ai.data_example_builder import AIExampleBuilder
from datasets import Dataset

logger = logging.getLogger(__name__)


# Remove task with status no_record, only_substeps must be managed in web
def filter_steps(task: Task, only_confirmed: bool = True):
    # For root
    if task.status == SaveStatus.no_record:
        task.steps = []
        return
    
    # All substeps must be complete
    complete_steps = []
    for step in task.steps:
        if not step.is_complete():
            logger.warning(f'Step {step.name} is not complete')
            # Try to save tasks of not complete step and want to be recorded. 
            if isinstance(step, Task):
                task_inside = [t for t in step.steps if isinstance(t, Task)]
                complete_steps += task_inside
                logger.info(f'Saved {len(task_inside)} tasks from step {step.name}')
        else:
            complete_steps.append(step)
    task.steps = complete_steps

    # Remove task not confirmed if only_confirmed is True
    if only_confirmed:
        # Save nested confirmed tasks
        confirmed_tasks = []
        for sub_task in task.steps:
            if isinstance(sub_task, Task) and sub_task.status == SaveStatus.to_record and sub_task.has_confirmed_tasks_inside():
                confirmed_tasks += sub_task.steps
            else:
                confirmed_tasks.append(sub_task)
        task.steps = confirmed_tasks

        # Remove not confirmed tasks
        def filter_not_confirm(x: Step) -> bool:
            # Pass if is complete, is a confirmed task or is a page action
            return isinstance(x, Task) and x.status == SaveStatus.confirm_record \
                or isinstance(x, PageAction) and task.status == SaveStatus.confirm_record
        task.steps = [step for step in task.steps if filter_not_confirm(step)]

    # Remove task with status no_record        
    task.steps = [step for step in task.steps if step.status != SaveStatus.no_record]
    for step in task.steps:
        if isinstance(step, Task):
            filter_steps(step)

def sanetize_broken_root(root: Task):
    # Sanetize root if is not complete
    if not root.is_complete():
        root.status = SaveStatus.to_record
        if not root.context:
            assert root.steps[0].context, 'All steps must be complete'
            root.context = root.steps[0].context
        if not root.context.start_observation.is_complete():
            def get_start_observation(step: Step) -> Step:
                if step.context and step.context.start_observation.is_complete():
                    return step
                if isinstance(step, Task):
                    for sub_step in step.steps:
                        return get_start_observation(sub_step)
                raise Exception('Cannot find start observation')
            root.context.start_observation = get_start_observation(root).context.start_observation  # type: ignore
        if not root.context.end_observation.is_complete():
            def get_end_observation(step: Step) -> Step:
                if step.context and step.context.end_observation.is_complete():
                    return step
                if isinstance(step, Task):
                    reversed_steps = step.steps[::-1]
                    for sub_step in reversed_steps:
                        return get_end_observation(sub_step)
                raise Exception('Cannot find end observation')
            root.context.end_observation = get_end_observation(root).context.end_observation  # type: ignore

def to_rpa_dataset(file_path: str, only_confirmed: bool) -> Dataset:

    task: Task = Task.from_dict(json.load(open(file_path, 'r')))

    filter_steps(task, only_confirmed)
    sanetize_broken_root(task)

    dataset_builder = AIExampleBuilder(task, history_with_tasks=False)
    examples = dataset_builder.build()
    pd_dataset = pd.DataFrame(data=[e.to_dict() for e in examples])
    return Dataset.from_pandas(pd_dataset)
    

if __name__ == '__main__':
    import glob

    # Get files from /workspaces/ai-butlerhat/data-butlerhat/Web/frontend/data/edit ended with .pickle
    dir_path = '/workspaces/ai-butlerhat/data-butlerhat/robotframework-butlerhat/TestSuites/CicloZero/data/edit'
    out_dir_path = '/workspaces/ai-butlerhat/data-butlerhat/robotframework-butlerhat/TestSuites/CicloZero/data/to_rpa_dataset'
    only_confirmed = True
    # Get all files ended with .pickle recursively
    files = [x for x in glob.glob(dir_path + '/**/*.pickle', recursive=True)]

    total_examples = 0
    for file in files:
        print(f'Processing {file}...')

        # TODO: Remove this when all tasks are saved with new format
        IS_TASK_OLD = 'not asked'

        hf_dataset = to_rpa_dataset(file, only_confirmed)
        out_path = file.replace(dir_path, out_dir_path).replace('.pickle', '.jsonl')
        hf_dataset.to_json(out_path)
        print(f'Processed {os.path.basename(out_path)}. Number of examples: {len(hf_dataset)}')
        total_examples += len(hf_dataset)
    print(f'Total examples: {total_examples}')
        
