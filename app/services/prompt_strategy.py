from app.prompts.general_prompt import INVOICE_PROMPT as GENERAL_PROMPT
from app.prompts.georgia_prompt import INVOICE_PROMPT as GEORGIA_PROMPT

def get_prompt_for_distributor(distributor_name: str) -> str:
    if not distributor_name.strip() or distributor_name:
        return GENERAL_PROMPT

    name = distributor_name.strip().lower()

    if name == "georgia crown distributing co.":
        return GEORGIA_PROMPT
    # elif name == "":
    #     return
    else:
        return GENERAL_PROMPT