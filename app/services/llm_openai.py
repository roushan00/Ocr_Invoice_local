# import os
# import base64
# from openai import OpenAI
# from model.georgia_inv import Invoice
# from prompt.georgia_prompts import prompt_for_georgia
# from typing import Optional
# from loguru import logger
# from services.memoery_clean import unload_model_memory
# from dotenv import load_dotenv

# load_dotenv()

# MODEL_NAME = os.getenv("MODEL_NAME")

# # Initialize the OpenAI client pointing to Ollama
# client = OpenAI(
#     base_url='http://localhost:11434/v1/',
#     api_key='ollama',  # Required but ignored by Ollama
# )

# def encode_image(image_path):
#     """Helper to convert local image to base64 string"""
#     with open(image_path, "rb") as image_file:
#         return base64.b64encode(image_file.read()).decode('utf-8')

# def extract_invoice_from_image(image_path, retries=1) -> Optional[Invoice]:
#     attempt = 0
#     base64_image = encode_image(image_path)

#     while attempt <= retries:
#         try:
#             # Using the OpenAI SDK format
#             response = client.chat.completions.create(
#                 model=MODEL_NAME,
#                 messages=[{
#                     "role": "user",
#                     "content": [
#                         {"type": "text", "text": prompt_for_georgia},
#                         {
#                             "type": "image_url",
#                             "image_url": {
#                                 "url": f"data:image/jpeg;base64,{base64_image}"
#                             },
#                         },
#                     ],
#                 }],
#                 # Ollama supports JSON schema via the OpenAI endpoint
#                 response_format={
#                     "type": "json_object",
#                     "schema": Invoice.model_json_schema()
#                 },
#                 temperature=0,
#             )

#             # Extract content from the OpenAI response object
#             content = response.choices[0].message.content

#             # Validate JSON
#             invoice = Invoice.model_validate_json(content)
#             return invoice

#         except Exception as e:
#             logger.warning(f"Attempt {attempt+1} failed for {image_path}: {e}")
#             attempt += 1
#             if attempt <= retries:
#                 logger.info("Retrying...")
#                 unload_model_memory()
#             else:
#                 logger.error(f"❌ Failed to extract {image_path} after retries.")
#                 return None
