# Use for model merge and further inferencing with ollama
from loguru import logger
from unsloth import FastVisionModel

# 1. Load and Save the MERGED model in standard HuggingFace format
# INITIAL_MODEL = r"invoice_model_3"
INITIAL_MODEL = r'same_prompt_model'

# MERGE_MODEL_NAME = "invoice_model_merged_3"
MERGE_MODEL_NAME = 'same_prompt_model_merged'


model, tokenizer = FastVisionModel.from_pretrained(INITIAL_MODEL, load_in_4bit=True)
# model, tokenizer = FastVisionModel.from_pretrained(
#     INITIAL_MODEL,
#     load_in_4bit=False,      # ❗ important
#     device_map="cpu"         # ❗ force CPU
# )
model.save_pretrained_merged(MERGE_MODEL_NAME, tokenizer, save_method='merged_16bit')

logger.success('Model Merged Successfully')


# Push the merged model to Hugging Face Hub
# from unsloth import FastVisionModel
# from loguru import logger
# # 1. Load and Save the MERGED model in standard HuggingFace format

# INITIAL_MODEL = r"invoice_model_3"


# model, tokenizer = FastVisionModel.from_pretrained(INITIAL_MODEL, load_in_4bit=True)

# model.push_to_hub_merged(
#     "modelnexus/georgia-finetune",  # Replace with your HF username and desired repo name (e.g., "myuser/invoice-model-merged")
#     tokenizer,
#     save_method="merged_16bit",       # Matches your local save; use "merged_4bit" if you loaded in 4-bit originally
#     token="YOUR_HF_TOKEN"  # Paste your token here
# )
