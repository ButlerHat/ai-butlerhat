import os
from collections import namedtuple
from datasets import load_from_disk
import streamlit as st
from core.models import AlfredTokenizer
from core.datasets.robotframework import HfRobotframeworkDatasetBuilder


def pretraining():
    """
    Convert rpa task file json to a hugging face dataset (json)
    """
    st.title('Preprocess RPA dataset for training')

    # Check if is dataset in rpa_dataset folder
    if not os.listdir(st.session_state.rpa_dataset):
        st.warning('No dataset found')
        st.stop()

    st.write('Dataset in rpa_dataset folder:', os.listdir(st.session_state.rpa_dataset))

    if st.button('Preprocess'):

        tokenizer = AlfredTokenizer.from_pretrained(
            st.secrets.paths.base_model,
            cache_dir= st.secrets.paths.hf_cache,
            use_fast=True
        )

        DataArgs = namedtuple('DataArgs', ['dataset_dir', 'max_samples', 'max_seq_length', 'image_size', 'validation_split', 'dataset_valid_dir'])
        data_args = DataArgs(
            dataset_dir=st.session_state.rpa_dataset,
            max_samples=-1, 
            max_seq_length=512,
            image_size=224,
            validation_split=0.1,
            dataset_valid_dir=""  # For now don't use validation set
        )

        # Build dataset
        st.markdown('# Dataset')
        dataset_builder = HfRobotframeworkDatasetBuilder(
            data_args,
            tokenizer,
            num_proc=1,  # This is an error that only happens in streamlit. If you run the main in core/datasets/robotframework.py it works with num_proc>1
            ocr_url=st.secrets.urls.ocr,
            print_func=st.write
        )

        with st.status("Converting data..."):
            new_dataset = dataset_builder.build_dataset()
            new_dataset.save_to_disk(st.session_state.pretraining_dataset)

    # Show dataset num examples if st.pretraining_dataset is not empty
    if os.listdir(st.session_state.pretraining_dataset):
        # Load dataset
        dataset = load_from_disk(st.session_state.pretraining_dataset)
        st.markdown('## Processed dataset info')
        st.markdown(f'- Train split: {len(dataset["train"])}')
        st.markdown(f'- Validation split: {len(dataset["validation"])}')

        