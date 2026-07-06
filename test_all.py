import json
import base64

from typing import Any

import numpy as np

from openai import OpenAI
from prompt_georgia import prompt_for_georgia

# Setup OpenAI client pointed to Ollama
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"  # Arbitrary string – Ollama ignores it
)

# Load and encode your image
def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

image_base64 = encode_image("test_data/Georgia_new_merged_page-0102.jpg")


# Call the model
response = client.chat.completions.create(
    model="georgia-inv:latest",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_for_georgia},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                }
            ]
        }
    ],
    temperature=0.0,      # Greedy decoding → most reliable probabilities
    max_tokens=4096,      # Increase for complex invoices with many line items
    logprobs=True,
    top_logprobs=5        # Optional but useful if you later want alternative tokens
)

generated_text = response.choices[0].message.content.strip()
print("Full generated output:\n", generated_text)

# Parse the full JSON
try:
    extracted: dict[str, Any] = json.loads(generated_text)
except json.JSONDecodeError as e:
    print("JSON parsing failed:", e)
    extracted = {}

print("\nExtracted data (pretty):\n", json.dumps(extracted, indent=4))

# ---------- Confidence scoring per field ----------
if response.choices[0].logprobs is None:
    print("Logprobs not returned – check Ollama version / model support.")
else:
    logprob_contents = response.choices[0].logprobs.content
    if not logprob_contents:
        print("No logprobs available.")
    else:
        # Build lists of tokens and their probabilities
        tokens: list[str] = [item.token for item in logprob_contents if item.logprob is not None]
        probs: list[float] = [np.exp(item.logprob) for item in logprob_contents if item.logprob is not None]

        # Reconstruct text from tokens (should match generated_text exactly or very closely)
        reconstructed = "".join(tokens)
        if reconstructed != generated_text:
            print("Warning: reconstructed text differs from generated_text (minor whitespace/special token differences possible).")

        text_to_search = generated_text  # Use the actual output for searching value strings

        def compute_field_confidences(data: Any) -> Any:
            """Recursively compute confidence (%) for every leaf field value."""
            if isinstance(data, dict):
                conf = {}
                for key, value in data.items():
                    if isinstance(value, (dict, list)):
                        conf[key] = compute_field_confidences(value)
                    else:
                        # Serialize the primitive value exactly as it appears in JSON
                        value_str = json.dumps(value)
                        start_pos = text_to_search.find(value_str)
                        if start_pos == -1:
                            conf[key] = None  # Not found – possibly formatting issue
                            continue
                        end_pos = start_pos + len(value_str)

                        # Find all tokens that overlap this character span
                        field_probs = []
                        current_pos = 0
                        for i, token in enumerate(tokens):
                            token_end = current_pos + len(token)
                            if current_pos < end_pos and token_end > start_pos:
                                field_probs.append(probs[i])
                            current_pos = token_end

                        if field_probs:
                            # Arithmetic mean probability → confidence %
                            conf[key] = round(float(np.mean(field_probs)) * 100, 2)
                        else:
                            conf[key] = None
                return conf
            elif isinstance(data, list):
                return [compute_field_confidences(item) for item in data]
            else:
                # Should not reach here (leaves are handled in dict)
                return None

        confidences = compute_field_confidences(extracted)

        print("\n=== Per-field confidence scores (%) ===\n")
        print(json.dumps(confidences, indent=4))

        # Optional: overall confidence (average of all leaf confidences)
        def flatten_confidences(conf_dict: Any) -> list[float]:
            flats = []
            if isinstance(conf_dict, dict):
                for v in conf_dict.values():
                    flats.extend(flatten_confidences(v))
            elif isinstance(conf_dict, list):
                for item in conf_dict:
                    flats.extend(flatten_confidences(item))
            elif isinstance(conf_dict, (int, float)) and conf_dict is not None:
                flats.append(conf_dict)
            return flats

        all_confs = flatten_confidences(confidences)
        if all_confs:
            overall_conf = np.mean(all_confs)
            print(f"\nOverall average confidence: {overall_conf:.2f}%")





'''
(.venv) administrator@spark-1eaa:~/Desktop/Dhruvin/confidence_Score$ python3 test_all.py 
Extracted data (pretty):
 {
    "distributor_name": "GEORGIA CROWN DISTRIBUTING CO.",
    "distributor_address": "100 Georgia Crown Drive McDonough, GA 30253",
    "city": "SYLV:Sylvester",
    "country": "XWORT:Worth County",
    "distributor_state_permit_no": "47632",
    "distributor_phone": "800-342-2350",
    "sold_to_name": "POUR HOUSE SYLVESTER, LLC",
    "sold_to_address": "201 W Franklin St. Sylvester, GA 31791",
    "sold_to_phone": "253-230-5182",
    "customer_account_no": "14321018000",
    "invoice_no": "DS943561",
    "invoice_date": "12/02/24",
    "page_no": "33",
    "customer_purchase_order_no": null,
    "route_no": "12173001",
    "salesman_liquor": "1440",
    "salesman_wine": "1440",
    "salesman_beer": "1440",
    "salesman_misc": "1440",
    "license_liquor": "0112856",
    "license_wine": "0112856",
    "license_beer": "0112856",
    "special_instructions": null,
    "items": [
        {
            "line_no": "449",
            "product_code": "00497218",
            "upc": "857641002296",
            "case_quantity": 1,
            "bottle_quantity": null,
            "size": "187ML",
            "pack": "24",
            "description": "BUZZBALLZ PINEAPPLE COLADA CHI",
            "unit_price": 84.0,
            "discount": 21.12,
            "net_bottle_price": 2.62,
            "net_amount": 62.88
        },
        {
            "line_no": "450",
            "product_code": "00497248",
            "upc": "857641002203",
            "case_quantity": 1,
            "bottle_quantity": null,
            "size": "187ML",
            "pack": "24",
            "description": "BUZZBALLZ SOUR APPLE CHILLERS",
            "unit_price": 84.0,
            "discount": 21.12,
            "net_bottle_price": 2.62,
            "net_amount": 62.88
        },
        {
            "line_no": "451",
            "product_code": "00497208",
            "upc": "857641002654",
            "case_quantity": 1,
            "bottle_quantity": null,
            "size": "187ML",
            "pack": "24",
            "description": "BUZZBALLZ STRAWBERRY CHILLERS",
            "unit_price": 84.0,
            "discount": 21.12,
            "net_bottle_price": 2.62,
            "net_amount": 62.88
        },
        {
            "line_no": "452",
            "product_code": "00497088",
            "upc": "855200005542",
            "case_quantity": 1,
            "bottle_quantity": null,
            "size": "187ML",
            "pack": "24",
            "description": "BUZZBALLZ WATERMELON CHILLERS",
            "unit_price": 84.0,
            "discount": 21.12,
            "net_bottle_price": 2.62,
            "net_amount": 62.88
        },
        {
            "line_no": "453",
            "product_code": "00929454",
            "upc": "074806186398",
            "case_quantity": 1,
            "bottle_quantity": null,
            "size": "10Z",
            "pack": "24",
            "description": "DAILY'S BAHAMA MAMA 24CT",
            "unit_price": 54.0,
            "discount": 17.28,
            "net_bottle_price": 1.53,
            "net_amount": 36.72
        },
        {
            "line_no": "454",
            "product_code": "00929414",
            "upc": "074806186107",
            "case_quantity": 1,
            "bottle_quantity": null,
            "size": "10Z",
            "pack": "24",
            "description": "DAILY'S BLUE HAWAIIAN 24CT",
            "unit_price": 54.0,
            "discount": 17.28,
            "net_bottle_price": 1.53,
            "net_amount": 36.72
        },
        {
            "line_no": "455",
            "product_code": "00929484",
            "upc": "074806186602",
            "case_quantity": 1,
            "bottle_quantity": null,
            "size": "10Z",
            "pack": "24",
            "description": "DAILY'S FIREWORKS 24CT",
            "unit_price": 54.0,
            "discount": 17.28,
            "net_bottle_price": 1.53,
            "net_amount": 36.72
        },
        {
            "line_no": "456",
            "product_code": "00929404",
            "upc": "074806018927",
            "case_quantity": 1,
            "bottle_quantity": null,
            "size": "10Z",
            "pack": "24",
            "description": "DAILY'S HURRICANE 24CT",
            "unit_price": 54.0,
            "discount": 17.28,
            "net_bottle_price": 1.53,
            "net_amount": 36.72
        },
        {
            "line_no": "457",
            "product_code": "00929804",
            "upc": "00074806189405",
            "case_quantity": 1,
            "bottle_quantity": null,
            "size": "10Z",
            "pack": "24",
            "description": "DAILY'S JAMAICAN SMILE 24CT",
            "unit_price": 54.0,
            "discount": 17.28,
            "net_bottle_price": 1.53,
            "net_amount": 36.72
        },
        {
            "line_no": "458",
            "product_code": "00929604",
            "upc": "074806184103",
            "case_quantity": 1,
            "bottle_quantity": null,
            "size": "10Z",
            "pack": "24",
            "description": "DAILY'S MARGARITA POUCH 24CT",
            "unit_price": 54.0,
            "discount": 17.28,
            "net_bottle_price": 1.53,
            "net_amount": 36.72
        },
        {
            "line_no": "459",
            "product_code": "00929474",
            "upc": "00074806188309",
            "case_quantity": 1,
            "bottle_quantity": null,
            "size": "10Z",
            "pack": "24",
            "description": "DAILY'S PEACH ON THE BEACH 24C",
            "unit_price": 54.0,
            "discount": 17.28,
            "net_bottle_price": 1.53,
            "net_amount": 36.72
        },
        {
            "line_no": "460",
            "product_code": "00929624",
            "upc": "074806184400",
            "case_quantity": 1,
            "bottle_quantity": null,
            "size": "10Z",
            "pack": "24",
            "description": "DAILY'S PINA COLADA POUCH 24CT",
            "unit_price": 54.0,
            "discount": 17.28,
            "net_bottle_price": 1.53,
            "net_amount": 36.72
        },
        {
            "line_no": "461",
            "product_code": "00929614",
            "upc": "074806184202",
            "case_quantity": 1,
            "bottle_quantity": null,
            "size": "10Z",
            "pack": "24",
            "description": "DAILY'S STRAWBERRY POUCH 24CT",
            "unit_price": 54.0,
            "discount": 17.28,
            "net_bottle_price": 1.53,
            "net_amount": 36.72
        },
        {
            "line_no": "462",
            "product_code": "00929494",
            "upc": "074806186503",
            "case_quantity": 1,
            "bottle_quantity": null,
            "size": "10Z",
            "pack": "24",
            "description": "DAILY'S WILD BERRY MARGARITA",
            "unit_price": 54.0,
            "discount": 17.28,
            "net_bottle_price": 1.53,
            "net_amount": 36.72
        }
    ],
    "summary_breakdown": [
        {
            "bottles": null,
            "cases": null,
            "liters": null,
            "category_description": "LIQUOR",
            "local_tax": null,
            "net_amount": null
        },
        {
            "bottles": null,
            "cases": null,
            "liters": null,
            "category_description": "WINE",
            "local_tax": null,
            "net_amount": null
        },
        {
            "bottles": null,
            "cases": null,
            "liters": null,
            "category_description": "BEER",
            "local_tax": null,
            "net_amount": null
        },
        {
            "bottles": null,
            "cases": null,
            "liters": null,
            "category_description": "SPECIALTY",
            "local_tax": null,
            "net_amount": null
        },
        {
            "bottles": null,
            "cases": null,
            "liters": null,
            "category_description": "SALES TAX",
            "local_tax": null,
            "net_amount": null
        }
    ],
    "total_bottles_footer": null,
    "total_each_footer": null,
    "total_net_amount_due": null
}

=== Per-field confidence scores (%) ===

{
    "distributor_name": 96.03,
    "distributor_address": 99.99,
    "city": 98.99,
    "country": 99.97,
    "distributor_state_permit_no": 100.0,
    "distributor_phone": 100.0,
    "sold_to_name": 99.92,
    "sold_to_address": 99.92,
    "sold_to_phone": 99.36,
    "customer_account_no": 98.49,
    "invoice_no": 95.11,
    "invoice_date": 100.0,
    "page_no": 99.99,
    "customer_purchase_order_no": 98.69,
    "route_no": 99.98,
    "salesman_liquor": 100.0,
    "salesman_wine": 100.0,
    "salesman_beer": 100.0,
    "salesman_misc": 100.0,
    "license_liquor": 100.0,
    "license_wine": 100.0,
    "license_beer": 100.0,
    "special_instructions": 98.69,
    "items": [
        {
            "line_no": 100.0,
            "product_code": 100.0,
            "upc": 100.0,
            "case_quantity": 100.0,
            "bottle_quantity": 98.69,
            "size": 99.99,
            "pack": 99.95,
            "description": 99.99,
            "unit_price": 100.0,
            "discount": 100.0,
            "net_bottle_price": 100.0,
            "net_amount": 100.0
        },
        {
            "line_no": 100.0,
            "product_code": 100.0,
            "upc": 100.0,
            "case_quantity": 100.0,
            "bottle_quantity": 98.69,
            "size": 99.99,
            "pack": 99.95,
            "description": 99.97,
            "unit_price": 100.0,
            "discount": 100.0,
            "net_bottle_price": 100.0,
            "net_amount": 100.0
        },
        {
            "line_no": 100.0,
            "product_code": 100.0,
            "upc": 100.0,
            "case_quantity": 100.0,
            "bottle_quantity": 98.69,
            "size": 99.99,
            "pack": 99.95,
            "description": 99.99,
            "unit_price": 100.0,
            "discount": 100.0,
            "net_bottle_price": 100.0,
            "net_amount": 100.0
        },
        {
            "line_no": 100.0,
            "product_code": 100.0,
            "upc": 99.99,
            "case_quantity": 100.0,
            "bottle_quantity": 98.69,
            "size": 99.99,
            "pack": 99.95,
            "description": 99.91,
            "unit_price": 100.0,
            "discount": 100.0,
            "net_bottle_price": 100.0,
            "net_amount": 100.0
        },
        {
            "line_no": 100.0,
            "product_code": 99.97,
            "upc": 99.99,
            "case_quantity": 100.0,
            "bottle_quantity": 98.69,
            "size": 99.99,
            "pack": 99.95,
            "description": 99.88,
            "unit_price": 100.0,
            "discount": 100.0,
            "net_bottle_price": 100.0,
            "net_amount": 99.99
        },
        {
            "line_no": 100.0,
            "product_code": 98.98,
            "upc": 100.0,
            "case_quantity": 100.0,
            "bottle_quantity": 98.69,
            "size": 99.99,
            "pack": 99.95,
            "description": 99.92,
            "unit_price": 100.0,
            "discount": 100.0,
            "net_bottle_price": 100.0,
            "net_amount": 99.99
        },
        {
            "line_no": 100.0,
            "product_code": 100.0,
            "upc": 99.99,
            "case_quantity": 100.0,
            "bottle_quantity": 98.69,
            "size": 99.99,
            "pack": 99.95,
            "description": 99.53,
            "unit_price": 100.0,
            "discount": 100.0,
            "net_bottle_price": 100.0,
            "net_amount": 99.99
        },
        {
            "line_no": 100.0,
            "product_code": 100.0,
            "upc": 99.96,
            "case_quantity": 100.0,
            "bottle_quantity": 98.69,
            "size": 99.99,
            "pack": 99.95,
            "description": 99.52,
            "unit_price": 100.0,
            "discount": 100.0,
            "net_bottle_price": 100.0,
            "net_amount": 99.99
        },
        {
            "line_no": 100.0,
            "product_code": 100.0,
            "upc": 99.99,
            "case_quantity": 100.0,
            "bottle_quantity": 98.69,
            "size": 99.99,
            "pack": 99.95,
            "description": 99.97,
            "unit_price": 100.0,
            "discount": 100.0,
            "net_bottle_price": 100.0,
            "net_amount": 99.99
        },
        {
            "line_no": 100.0,
            "product_code": 100.0,
            "upc": 99.52,
            "case_quantity": 100.0,
            "bottle_quantity": 98.69,
            "size": 99.99,
            "pack": 99.95,
            "description": 99.94,
            "unit_price": 100.0,
            "discount": 100.0,
            "net_bottle_price": 100.0,
            "net_amount": 99.99
        },
        {
            "line_no": 99.99,
            "product_code": 99.99,
            "upc": 94.13,
            "case_quantity": 100.0,
            "bottle_quantity": 98.69,
            "size": 99.99,
            "pack": 99.95,
            "description": 99.96,
            "unit_price": 100.0,
            "discount": 100.0,
            "net_bottle_price": 100.0,
            "net_amount": 99.99
        },
        {
            "line_no": 100.0,
            "product_code": 99.99,
            "upc": 99.96,
            "case_quantity": 100.0,
            "bottle_quantity": 98.69,
            "size": 99.99,
            "pack": 99.95,
            "description": 99.43,
            "unit_price": 100.0,
            "discount": 100.0,
            "net_bottle_price": 100.0,
            "net_amount": 99.99
        },
        {
            "line_no": 100.0,
            "product_code": 99.99,
            "upc": 99.9,
            "case_quantity": 100.0,
            "bottle_quantity": 98.69,
            "size": 99.99,
            "pack": 99.95,
            "description": 99.85,
            "unit_price": 100.0,
            "discount": 100.0,
            "net_bottle_price": 100.0,
            "net_amount": 99.99
        },
        {
            "line_no": 100.0,
            "product_code": 99.98,
            "upc": 97.68,
            "case_quantity": 100.0,
            "bottle_quantity": 98.69,
            "size": 99.99,
            "pack": 99.95,
            "description": 99.93,
            "unit_price": 100.0,
            "discount": 100.0,
            "net_bottle_price": 100.0,
            "net_amount": 99.99
        }
    ],
    "summary_breakdown": [
        {
            "bottles": 98.69,
            "cases": 98.69,
            "liters": 98.69,
            "category_description": 99.89,
            "local_tax": 98.69,
            "net_amount": 98.69
        },
        {
            "bottles": 98.69,
            "cases": 98.69,
            "liters": 98.69,
            "category_description": 99.98,
            "local_tax": 98.69,
            "net_amount": 98.69
        },
        {
            "bottles": 98.69,
            "cases": 98.69,
            "liters": 98.69,
            "category_description": 99.71,
            "local_tax": 98.69,
            "net_amount": 98.69
        },
        {
            "bottles": 98.69,
            "cases": 98.69,
            "liters": 98.69,
            "category_description": 98.19,
            "local_tax": 98.69,
            "net_amount": 98.69
        },
        {
            "bottles": 98.69,
            "cases": 98.69,
            "liters": 98.69,
            "category_description": 97.84,
            "local_tax": 98.69,
            "net_amount": 98.69
        }
    ],
    "total_bottles_footer": 98.69,
    "total_each_footer": 98.69,
    "total_net_amount_due": 98.69
}

Overall average confidence: 99.61%
'''
