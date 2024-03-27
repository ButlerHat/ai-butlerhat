import os
import glob
import streamlit as st
from stqdm import stqdm
import rpa_dataset.to_rpa_dataset as rpa_converter


def to_rpa_dataset():
    """
    Convert rpa task file json to a hugging face dataset (json)
    """
    st.title('Convert RPA task to HuggingFace dataset')

    # Edited and output directory
    dir_path = os.path.join(st.secrets.paths.edited, st.session_state.project) if hasattr(st.session_state, 'project') else st.secrets.paths.edited
    out_dir_path = os.path.join(st.secrets.paths.rpa_dataset, st.session_state.project) if hasattr(st.session_state, 'project') else st.secrets.paths.rpa_dataset

    # List edited files in the edited_data folder and add a checkbox
    files = [x for x in glob.glob(dir_path + '/**/*.json', recursive=True)]
    for i, file_path in enumerate(files):
        st.checkbox(file_path.split('/')[-1], value=True, key=f'file_{i}')


    if st.button('Convert to RPA dataset'):
        # Get all checked files
        files: list[str] = [file for i, file in enumerate(files) if st.session_state[f'file_{i}']]
        
        total_examples: int = 0
        with stqdm(files) as sqdm_files:
            with st.status('Converting files...'):
                for file_path in files:
                    st.write(f'Processing {file_path}...')
                    hf_dataset = rpa_converter.to_rpa_dataset(file_path, only_confirmed=True)
                    out_path = file_path.replace(dir_path, out_dir_path).replace('.json', '.jsonl')
                    # Save dataset
                    hf_dataset.to_json(out_path)
                    st.write(f'Processed {os.path.basename(out_path)}. Number of examples: {len(hf_dataset)}')
                    total_examples += len(hf_dataset)
                    sqdm_files.update(1)

        st.success(f'Total examples: {total_examples}')
            